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
        """맥북 M5 뉴럴 엔진 활용: 랜덤 포레스트 가격 예측 [cite: 2026-02-11]"""
        try:
            ml_df = df[['Close']].copy()
            ml_df['Lag1'] = ml_df['Close'].shift(1)
            ml_df['Lag2'] = ml_df['Close'].shift(2)
            ml_df['Lag3'] = ml_df['Close'].shift(3)
            ml_df = ml_df.dropna()
            
            X = ml_df[['Lag1', 'Lag2', 'Lag3']]
            y = ml_df['Close']
            
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
            
            latest_data = pd.DataFrame({
                'Lag1': [df['Close'].iloc[-1]],
                'Lag2': [df['Close'].iloc[-2]],
                'Lag3': [df['Close'].iloc[-3]]
            })
            return round(float(model.predict(latest_data)[0]), 4)
        except: return 0

    def collect_and_relay(self):
        print("🚀 [연구소] 맥북 M5 머신러닝 및 데이터 릴레이 가동...")
        
        # 1. 역사적 데이터 및 업비트 가격 수집
        xrp_df = self.clean_df(yf.download("XRP-USD", period="max", progress=False))
        btc_df = self.clean_df(yf.download("BTC-USD", period="max", progress=False))
        
        xrp_upbit = self.get_upbit_price("KRW-XRP")
        btc_upbit = self.get_upbit_price("KRW-BTC")

        # 2. 맥북 로컬 머신러닝 연산 (M5 전담)
        xrp_pred = self.run_m5_machine_learning(xrp_df)
        btc_pred = self.run_m5_machine_learning(btc_df)

        # 3. 구글 시트 중간 기지에 데이터 적재 (Relay Station)
        try:
            spreadsheet = self.client.open(self.sheet_name)
            try:
                storage_sheet = spreadsheet.worksheet("AEGIS_ML_Storage")
            except:
                storage_sheet = spreadsheet.add_worksheet(title="AEGIS_ML_Storage", rows="10", cols="5")
            
            storage_sheet.clear()
            storage_sheet.update(range_name="A1", values=[
                ["항목", "실시간_업비트", "M5_ML_예측가(USD)", "데이터_기준시간"],
                ["XRP", xrp_upbit, xrp_pred, pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')],
                ["BTC", btc_upbit, btc_pred, pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')]
            ])
            
            # 클라우드 봇용 로컬 파일도 생성
            storage = {
                "XRP": {"upbit": xrp_upbit, "ml_pred": xrp_pred},
                "BTC": {"upbit": btc_upbit, "ml_pred": btc_pred}
            }
            with open("collected_data.json", "w", encoding="utf-8") as f:
                json.dump(storage, f, ensure_ascii=False, indent=4)
                
            print(f"✅ 맥북 작전 완료: ML 결과($ {xrp_pred})를 구글 시트에 송신했습니다.")
            
        except Exception as e:
            print(f"❌ 데이터 릴레이 실패: {e}")

if __name__ == "__main__":
    collector = AegisM5ResearchCenter("AEGIS_Daily_Report", "creds xrp coin.json")
    collector.collect_and_relay()