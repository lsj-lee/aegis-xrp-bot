import os
import json
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf
import requests
from dotenv import load_dotenv

# 💾 파일 제목: aegis_collector.py (최종 수정본 - Series 에러 및 슬래시 경로 해결)
# 🚀 사유: yfinance의 Series 반환 에러 해결 및 파일명 특수문자(/) 치환 로직 추가.

load_dotenv()
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(ROOT_DIR, "aegis_data", "raw")
os.makedirs(RAW_DATA_DIR, exist_ok=True)

def save_vault(name, data):
    # 슬래시(/) 등 파일명 금지 문자 치환
    safe_name = name.replace("/", "_").replace("\\", "_")
    with open(os.path.join(RAW_DATA_DIR, f"{safe_name}.json"), 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(data.items())), f, ensure_ascii=False, indent=2)

def collect_yahoo(name, ticker):
    try:
        print(f"   ⏳ [YAHOO] {name} ({ticker}) 1년치 인양 중...")
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        if data.empty: return False
        
        vault = {}
        for index, row in data.iterrows():
            dt = index.strftime("%Y-%m-%d")
            # .item()을 사용하여 Series 형식을 순수 float으로 변환 (에러 해결 핵심)
            vault[dt] = {
                "Open": float(row['Open'].iloc[0]) if hasattr(row['Open'], 'iloc') else float(row['Open']),
                "High": float(row['High'].iloc[0]) if hasattr(row['High'], 'iloc') else float(row['High']),
                "Low": float(row['Low'].iloc[0]) if hasattr(row['Low'], 'iloc') else float(row['Low']),
                "Close": float(row['Close'].iloc[0]) if hasattr(row['Close'], 'iloc') else float(row['Close'])
            }
        save_vault(name, vault)
        return True
    except Exception as e:
        print(f"      ⚠️ YAHOO 에러: {e}")
        return False

def collect_upbit(name, symbol):
    try:
        print(f"   ⏳ [UPBIT] {name} ({symbol}) 1년치 인양 중...")
        url = "https://api.upbit.com/v1/candles/days"
        params = {"market": symbol, "count": 200}
        res = requests.get(url, params=params, timeout=10).json()
        
        last_date = res[-1]['candle_date_time_utc']
        params2 = {"market": symbol, "count": 165, "to": last_date}
        res2 = requests.get(url, params=params2, timeout=10).json()
        
        full_res = res + res2
        vault = {}
        for row in full_res:
            dt = row['candle_date_time_kst'].split('T')[0]
            vault[dt] = {
                "Open": float(row['opening_price']),
                "High": float(row['high_price']),
                "Low": float(row['low_price']),
                "Close": float(row['trade_price'])
            }
        save_vault(name, vault)
        return True
    except Exception as e:
        print(f"      ⚠️ UPBIT 에러: {e}")
        return False

def run_collector():
    print("=" * 60)
    print("📡 [정규 작전] AEGIS 1년 데이터 광폭 수집기 (V2-최종)")
    print("=" * 60)
    
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    gc = gspread.authorize(Credentials.from_service_account_file(creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    
    worksheet = gc.open("AEGIS_Daily_Report").worksheet("XRP 지표")
    rows = worksheet.get_all_values()
    
    success_count = 0
    for idx, row in enumerate(rows):
        if idx == 0 or not row[0]: continue
        
        name = row[0].strip()
        src = row[3].strip().upper() if len(row) > 3 else ""
        ticker = row[4].strip() if len(row) > 4 else ""
        
        if src == "YAHOO" and ticker:
            if collect_yahoo(name, ticker): success_count += 1
        elif src == "UPBIT" and ticker:
            if collect_upbit(name, ticker): success_count += 1
            
    print(f"\n✅ [작전 종료] 총 {success_count}개 지표 1년 데이터 확보 성공!")
    print("=" * 60)

if __name__ == "__main__":
    run_collector()