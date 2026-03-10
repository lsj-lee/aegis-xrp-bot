import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RESULTS_DIR = os.path.join("aegis_data", "results")

def run_syncer():
    print("=" * 60)
    print(f"🌐 [3단계] AEGIS 클라우드 데이터 동기화 분과 가동")
    print("=" * 60)

    # 1. 가장 최근의 결과 파일 찾기
    if not os.path.exists(RESULTS_DIR):
        print("❌ 결과 폴더가 없습니다.")
        return

    files = [f for f in os.listdir(RESULTS_DIR) if f.startswith("result_") and f.endswith(".json")]
    if not files:
        print("❌ 동기화할 결과 파일이 없습니다.")
        return
        
    latest_file = max(files) # 이름순 정렬 시 가장 최신 날짜
    file_path = os.path.join(RESULTS_DIR, latest_file)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        result_data = json.load(f)

    # 2. 구글 시트 연결
    print(f"   🔗 구글 클라우드 본부 연결 중...")
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    doc = gc.open("AEGIS_Daily_Report")

    # 3. XRP 지표 탭 업데이트 (B열 최신화)
    data_ws = doc.worksheet("XRP 지표")
    current_data = data_ws.get_all_values()
    updates = []
    
    raw_latest = result_data.get("raw_latest", {})
    for idx, row in enumerate(current_data):
        if idx == 0 or not row[0].strip(): continue
        name = row[0].strip()
        if name in raw_latest:
            updates.append({'range': f'B{idx+1}', 'values': [[raw_latest[name]]]})
            
    if updates:
        data_ws.batch_update(updates)
        print(f"   ✅ [XRP 지표] 탭 수치 {len(updates)}건 갱신 완료.")

    # 4. AEGIS_History 탭 업데이트 (M5 예측 기록)
    history_ws = doc.worksheet("AEGIS_History")
    history_ws.append_row([
        result_data["timestamp"], 
        f"{result_data['current_price']:.4f}", 
        f"{result_data['predict_1d']}", 
        f"{result_data['predict_7d']}", 
        f"{result_data['predict_30d']}", 
        result_data["indicators"]
    ])
    print(f"   ✅ [AEGIS_History] 탭 M5 타격 기록 전송 완료.")
    print("=" * 60)

if __name__ == "__main__":
    run_syncer()