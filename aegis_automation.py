import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import warnings
warnings.filterwarnings('ignore')

from aegis_executor import run_daily_execution

def update_google_sheet(report_data):
    print("📊 구글 시트에 AI 상세 리포트를 전송합니다...")
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = "/Users/lsj/Desktop/구글 연결 키/creds xrp coin.json"
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        
        sheet_name = "AEGIS_Daily_Report" 
        sheet = client.open(sheet_name).sheet1
        
        # [날짜, 가격, 공포지수, 확률, 판정, 추세, 상세 리포트]
        row_data = [
            report_data['date'],
            report_data['price'],
            report_data['fng'],
            f"{report_data['prob']:.2f}%",
            report_data['decision'],
            report_data['long_term'],
            report_data['commentary']
        ]
        
        sheet.append_row(row_data)
        print(f"✅ 구글 시트('{sheet_name}') 업데이트 완료!")
        
    except Exception as e:
        print(f"⚠️ 시트 업데이트 오류 발생: {e}")

def run_automated_pipeline():
    print(f"⏰ [AEGIS 3.0 자동화 파이프라인 가동] - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    result = run_daily_execution()
    if result:
        print("\n" + result['commentary'])
        update_google_sheet(result)

if __name__ == "__main__":
    run_automated_pipeline()