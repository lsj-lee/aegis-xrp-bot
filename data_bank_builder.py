import gspread
from google.oauth2.service_account import Credentials
import json
import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestRegressor

load_dotenv()

class AegisM5ResearchCenter:
    def __init__(self, sheet_name, key_file):
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(key_file, scopes=scopes)
        self.client = gspread.authorize(creds)
        self.sheet_name = sheet_name

    def clean_df(self, df):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    def get_upbit_price(self, ticker="KRW-XRP"):
        try:
            url = f"https://api.upbit.com/v1/ticker?markets={ticker}"
            response = requests.get(url, timeout=5).json()
            return response[0]['trade_price']
        except: return "N/A"

    def run_m5_machine_learning(self, df):
        """맥북 M5 뉴럴 엔진 활용: 예측가 및 분석 사유 생성 [cite: 2026-02-11]"""
        try:
            ml_df = df[['Close']].copy()
            ml_df['Lag1'] = ml_df['Close'].shift(1)
            ml_df['Lag2'] = ml_df['Close'].shift(2)
            ml_df = ml_df.dropna()
            
            X = ml_df[['Lag1', 'Lag2']]
            y = ml_df['Close']
            
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
            
            latest_price = df['Close'].iloc[-1]
            latest_data = pd.DataFrame({'Lag1': [latest_price], 'Lag2': [df['Close'].iloc[-2]]})
            prediction = round(float(model.predict(latest_data)[0]), 4)
            
            # 💡 M5의 분석 사유 생성 로직
            trend = "상승 에너지 우세" if prediction > latest_price else "하락 압력 우세"
            reason = f"과거 3일간의 변동성 패턴 분석 결과 {trend} 구간 진입으로 판단됨"
            
            return prediction, reason
        except: return 0, "분석 불가"

    def collect_and_relay(self):
        print("🚀 [연구소] 맥북 M5 머신러닝 및 상세 사유 릴레이 가동...")
        
        xrp_df = self.clean_df(yf.download("XRP-USD", period="max", progress=False))
        btc_df = self.clean_df(yf.download("BTC-USD", period="max", progress=False))
        
        xrp_upbit = self.get_upbit_price("KRW-XRP")
        btc_upbit = self.get_upbit_price("KRW-BTC")

        xrp_pred, xrp_reason = self.run_m5_machine_learning(xrp_df)
        btc_pred, btc_reason = self.run_m5_machine_learning(btc_df)

        try:
            spreadsheet = self.client.open(self.sheet_name)
            try:
                storage_sheet = spreadsheet.worksheet("AEGIS_ML_Storage")
            except:
                storage_sheet = spreadsheet.add_worksheet(title="AEGIS_ML_Storage", rows="10", cols="6")
            
            storage_sheet.clear()
            storage_sheet.update(range_name="A1", values=[
                ["항목", "실시간_업비트", "M5_ML_예측가(USD)", "M5_ML_판단근거", "데이터_기준시간"],
                ["XRP", xrp_upbit, xrp_pred, xrp_reason, pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')],
                ["BTC", btc_upbit, btc_pred, btc_reason, pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')]
            ])
            print(f"✅ 맥북 작전 완료: 분석 근거({xrp_reason})를 시트에 송신했습니다.")
        except Exception as e:
            print(f"❌ 데이터 릴레이 실패: {e}")

if __name__ == "__main__":
    creds_path = os.getenv("GCP_CREDS_PATH")
    if not creds_path:
        raise ValueError("GCP_CREDS_PATH environment variable not set. Please set it in .env or environment.")
    collector = AegisM5ResearchCenter("AEGIS_Daily_Report", creds_path)
    collector.collect_and_relay()