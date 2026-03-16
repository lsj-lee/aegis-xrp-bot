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

    if not os.path.exists(RESULTS_DIR):
        print("❌ 결과 폴더가 없습니다.")
        return

    files = [f for f in os.listdir(RESULTS_DIR) if f.startswith("result_") and f.endswith(".json")]
    if not files:
        print("❌ 동기화할 결과 파일이 없습니다.")
        return
        
    latest_file = max(files)
    file_path = os.path.join(RESULTS_DIR, latest_file)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        result_data = json.load(f)

    print(f"   🔗 구글 클라우드 본부 연결 중...")
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    doc = gc.open("AEGIS_Daily_Report")

    data_ws = doc.worksheet("XRP 지표")
    current_data = data_ws.get_all_values()
    updates = []
    
    raw_latest = result_data.get("raw_latest", {})
    for idx, row in enumerate(current_data):
        if idx == 0 or not row[0].strip(): continue
        name = row[0].strip()
        if name in raw_latest:
            # 💡 B열(파일명)이 아닌 C열(현재값)에 데이터를 동기화하도록 수정!
            updates.append({'range': f'C{idx+1}', 'values': [[raw_latest[name]]]})
            
    if updates:
        data_ws.batch_update(updates)
        print(f"   ✅ [XRP 지표] 탭 M5 연산 수치 {len(updates)}건 갱신 완료.")

    history_ws = doc.worksheet("AEGIS_History")
    history_data = [
        result_data["timestamp"],
        result_data["current_price"],
        result_data["predict_1d"],
        result_data["predict_7d"],
        result_data["predict_30d"],
        result_data["indicators"]
    ]
    history_ws.append_row(history_data)
    print(f"   ✅ [AEGIS_History] 탭 로깅 완료.")

if __name__ == "__main__":
    run_syncer()