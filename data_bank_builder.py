import gspread
from google.oauth2.service_account import Credentials
import json
import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests # 업비트 통신용 무기 추가
from dotenv import load_dotenv

load_dotenv()

class AegisAllTimeCollector:
    def __init__(self, sheet_name, key_file):
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(key_file, scopes=scopes)
        self.client = gspread.authorize(creds)
        self.sheet_name = sheet_name

    def clean_df(self, df):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    def calculate_rsi(self, series, window=14):
        clean_series = pd.Series(np.ravel(series))
        delta = clean_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def get_upbit_price(self, ticker="KRW-XRP"):
        """업비트 실시간 원화 가격 스캔 [cite: 2026-02-11]"""
        try:
            url = f"https://api.upbit.com/v1/ticker?markets={ticker}"
            response = requests.get(url, timeout=5).json()
            return response[0]['trade_price']
        except Exception as e:
            print(f"⚠️ 업비트 통신 장애: {e}")
            return "N/A"

    def get_all_time_history(self, ticker="XRP-USD", upbit_ticker="KRW-XRP"):
        results = {}
        print(f"📡 [{ticker}] 글로벌 달러 및 업비트({upbit_ticker}) 데이터 동시 스캔 중...")

        try:
            # 업비트 실시간 원화 가격 확보
            upbit_price = self.get_upbit_price(upbit_ticker)
            
            df_max = yf.download(ticker, period="max", interval="1d", progress=False)
            if df_max.empty: return {}
            df_max = self.clean_df(df_max) 

            ath = float(np.nanmax(df_max['High'].values))
            atl = float(np.nanmin(df_max['Low'].values))
            current_price = float(df_max['Close'].values[-1])
            drawdown = ((current_price - ath) / ath) * 100

            results['역사적_분석'] = {
                "상장일": str(df_max.index[0].date()),
                "역대_최고점(ATH)": round(ath, 4),
                "고점_대비_하락률": f"{round(drawdown, 2)}%",
                "현재가(USD)": current_price,
                "현재가(업비트KRW)": upbit_price # AI에게 넘겨줄 핵심 데이터
            }

            intervals = {
                "1시간봉": {"int": "1h", "period": "730d"},
                "1일봉": {"int": "1d", "period": "max"},
                "1주봉": {"int": "1wk", "period": "max"},
                "1월봉": {"int": "1mo", "period": "max"},
                "3월봉": {"int": "3mo", "period": "max"}
            }

            for name, cfg in intervals.items():
                try:
                    df = yf.download(ticker, period=cfg['period'], interval=cfg['int'], progress=False)
                    df = self.clean_df(df)
                    if len(df) > 15:
                        rsi = self.calculate_rsi(df['Close']).iloc[-1]
                        ma20 = float(np.nanmean(df['Close'].values[-20:]))
                        cp = float(df['Close'].values[-1])
                        results[name] = {
                            "RSI": round(float(rsi), 2) if not pd.isna(rsi) else "N/A",
                            "Trend": "상승" if cp > ma20 else "하락"
                        }
                except: continue

            monthly_df = yf.download(ticker, period="max", interval="1mo", progress=False)
            monthly_df = self.clean_df(monthly_df)
            clean_close = pd.Series(np.ravel(monthly_df['Close']), index=monthly_df.index)
            
            for res_name, res_rule in [("6월봉", "6ME"), ("1년봉", "1YE")]:
                res_df = clean_close.resample(res_rule).last().dropna()
                if len(res_df) > 5:
                    rsi = self.calculate_rsi(res_df).iloc[-1]
                    results[res_name] = {
                        "RSI": round(float(rsi), 2) if not pd.isna(rsi) else "N/A",
                        "Trend": "상승" if len(res_df) > 1 and float(res_df.iloc[-1]) > float(res_df.iloc[-2]) else "하락"
                    }
        except Exception as e:
            print(f"⚠️ {ticker} 분석 중 오류: {e}")

        return results

    def collect_all(self):
        print("🚀 [1단계] AEGIS 4.3 (업비트 실시간 연동) 관측 엔진 가동...")
        xrp_history = self.get_all_time_history("XRP-USD", "KRW-XRP")
        btc_history = self.get_all_time_history("BTC-USD", "KRW-BTC")
        
        try:
            worksheet = self.client.open(self.sheet_name).worksheet("AEGIS_Daily_Report")
            rows = worksheet.get_all_values()[1:]
            payload = [{"지표": r[0], "사령관_분석의미": r[1] if len(r)>1 else ""} for r in rows if r[0]]

            storage = {
                "update_time": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
                "all_time_analysis": {"XRP": xrp_history, "BTC": btc_history},
                "payload": payload
            }
            
            with open("collected_data.json", "w", encoding="utf-8") as f:
                json.dump(storage, f, ensure_ascii=False, indent=4)
            print(f"✅ 수집 완료: 업비트 실시간 원화 가격 연동이 완료되었습니다.")
            
        except Exception as e:
            print(f"❌ 시트 수집 오류: {e}")

if __name__ == "__main__":
    collector = AegisAllTimeCollector("AEGIS_Daily_Report", "creds xrp coin.json")
    collector.collect_all()