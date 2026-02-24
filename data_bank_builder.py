import gspread
from google.oauth2.service_account import Credentials
import json
import os
import requests
import yfinance as yf
from dotenv import load_dotenv

# 1. 기초 환경 로드 [cite: 2026-02-11]
load_dotenv()

class AegisDataCollector:
    def __init__(self, sheet_name, key_file):
        # 구글 시트 보안 연결 통로 확보 [cite: 2026-01-30]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(key_file, scopes=scopes)
        self.client = gspread.authorize(creds)
        self.sheet_name = sheet_name

    def get_fear_and_greed(self):
        """크립토 공포와 탐욕 지수 실시간 수집"""
        try:
            res = requests.get("https://api.alternative.me/fng/")
            data = res.json()
            return f"{data['data'][0]['value']} ({data['data'][0]['value_classification']})"
        except:
            return "수집 실패 (API 확인 필요)"

    def get_market_price(self, ticker):
        """야후 파이낸스를 통한 실시간 금융 데이터 수집 [cite: 2026-02-24]"""
        try:
            data = yf.Ticker(ticker)
            # 최신 종가 가져오기
            price = data.history(period="1d")['Close'].iloc[-1]
            return round(price, 4)
        except:
            return "수집 불가"

    def collect_all(self):
        print(f"📡 [1단계] '{self.sheet_name}' 본부 기반 실시간 데이터 수집 개시...")
        
        try:
            # 탭 이름 'AEGIS_Daily_Report' 직접 타격 [cite: 2026-02-24]
            worksheet = self.client.open(self.sheet_name).worksheet("AEGIS_Daily_Report")
            rows = worksheet.get_all_values()[1:] # 헤더 제외
            
            final_data = []
            
            # 사령관님의 M5 성능을 활용한 실시간 데이터 병렬 수집 준비 [cite: 2026-02-11]
            xrp_price = self.get_market_price("XRP-USD")
            btc_price = self.get_market_price("BTC-USD")
            gold_price = self.get_market_price("GC=F")
            copper_price = self.get_market_price("HG=F")
            fng_index = self.get_fear_and_greed()

            for row in rows:
                if not row[0]: continue
                
                indicator = row[0]
                manual_context = row[1] if len(row) > 1 else "내용 없음"
                live_value = "N/A"

                # 지표명에 따른 실시간 데이터 자동 매칭 로직
                if "공포" in indicator:
                    live_value = fng_index
                elif "XRP" in indicator:
                    live_value = f"{xrp_price} USD" # [교정 완료]
                elif "비트코인" in indicator:
                    live_value = f"{btc_price} USD" # [교정 완료]
                elif "구리/금" in indicator: 
                    try:
                        live_value = round(float(copper_price) / float(gold_price), 6)
                    except:
                        live_value = "계산 불가"

                final_data.append({
                    "지표": indicator,
                    "실시간_데이터": live_value,
                    "사령관_분석의미": manual_context
                })

            # 2단계 AI 학습을 위한 JSON 연료 저장 [cite: 2026-02-24]
            storage = {
                "update_time": "2026-02-24",
                "total_items": len(final_data),
                "payload": final_data
            }
            
            with open("collected_data.json", "w", encoding="utf-8") as f:
                json.dump(storage, f, ensure_ascii=False, indent=4)
                
            print(f"✅ 수집 성공: 총 {len(final_data)}개의 데이터가 'collected_data.json'에 장전되었습니다.")
            
        except Exception as e:
            print(f"❌ 수집 중 오류 발생: {e}")

if __name__ == "__main__":
    # 사령관님의 지휘소 설정값
    KEY_PATH = "creds xrp coin.json"
    SHEET_NAME = "AEGIS_Daily_Report"
    
    collector = AegisDataCollector(SHEET_NAME, KEY_PATH)
    collector.collect_all()