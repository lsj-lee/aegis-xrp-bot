import gspread
import sys
from google.oauth2.service_account import Credentials
import json
import os
import re
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestRegressor

load_dotenv()

class AegisM5ResearchCenter:
    def __init__(self, sheet_name, key_file_path):
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # 💡 따옴표 등을 제거하고 깨끗한 경로 문자열을 가져옵니다.
        key_file = key_file_path.strip('"').strip("'")
        
        # 현재 실행 위치(cwd)를 기준으로 절대 경로 확인
        abs_key_path = os.path.abspath(key_file)
        
        if not os.path.isfile(abs_key_path):
            raise ValueError(f"❌ 인증 열쇠 파일을 찾을 수 없습니다.\n확인된 경로: {abs_key_path}\n현재 폴더 파일 목록: {os.listdir('.')}")
            
        creds = Credentials.from_service_account_file(abs_key_path, scopes=scopes)
        self.client = gspread.authorize(creds)
        self.sheet_name = sheet_name

    # ... (이후 clean_df, get_upbit_price 등 기존 로직과 동일) ...
    def clean_df(self, df):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    def get_upbit_price(self, ticker="KRW-XRP"):
        # Validate ticker type and format (e.g., "KRW-BTC") to prevent injection and errors
        if not isinstance(ticker, str) or not re.match(r"^[A-Z0-9]+-[A-Z0-9]+$", ticker):
            return "N/A"

        try:
            url = "https://api.upbit.com/v1/ticker"
            response = requests.get(url, params={"markets": ticker}, timeout=5).json()
            return response[0]['trade_price']
        except (requests.RequestException, ValueError, KeyError, IndexError):
            return "N/A"

    def run_m5_machine_learning(self, df):
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
            trend = "상승 에너지 우세" if prediction > latest_price else "하락 압력 우세"
            reason = f"과거 3일 패턴 분석 결과 {trend} 구간 진입으로 판단됨"
            return prediction, reason
        except (ValueError, KeyError, IndexError):
            return 0, "분석 불가"

    def collect_and_relay(self):
        print("🚀 [연구소] 맥북 M5 머신러닝 데이터 릴레이 가동...")
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
            except gspread.exceptions.WorksheetNotFound:  # Security Fix: Explicitly catch only gspread.exceptions.WorksheetNotFound to avoid masking other errors.
                storage_sheet = spreadsheet.add_worksheet(title="AEGIS_ML_Storage", rows="10", cols="6")
            
            storage_sheet.clear()
            storage_sheet.update(range_name="A1", values=[
                ["항목", "실시간_업비트", "M5_ML_예측가(USD)", "M5_ML_판단근거", "데이터_기준시간"],
                ["XRP", xrp_upbit, xrp_pred, xrp_reason, pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')],
                ["BTC", btc_upbit, btc_pred, btc_reason, pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')]
            ])
            print(f"✅ 맥북 작전 완료: ML 결과($ {xrp_pred})를 구글 시트에 송신했습니다.")
        except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e:
            print(f"❌ 데이터 릴레이 실패: {e}")

def main():
    # Security: Use environment variable instead of hardcoded path to prevent credential leakage
    creds_path = os.getenv("GCP_CREDS_PATH")
    if not creds_path:
        raise ValueError("Critical Security Error: GCP_CREDS_PATH environment variable is not set. Hardcoding credentials is strictly prohibited.")

    # 💡 따옴표 등을 제거하고 깨끗한 경로 문자열을 가져옵니다.
    creds_path = creds_path.strip('"').strip("'")

    if not os.path.isfile(creds_path):
        raise FileNotFoundError(f"Service account key path is not a file: {creds_path}")

    if not os.access(creds_path, os.R_OK):
        raise PermissionError(f"Service account key file is not readable: {creds_path}")

    collector = AegisM5ResearchCenter("AEGIS_Daily_Report", creds_path)
    collector.collect_and_relay()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)