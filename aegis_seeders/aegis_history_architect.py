import os
import json
import time
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from google import genai
from google.genai import types
from google.genai.errors import APIError
from dotenv import load_dotenv

# 💾 파일 제목: aegis_seeders/aegis_history_architect.py
# 🚀 사유: 점수에 대한 상세 분석 근거(Reason) 필드를 추가하여 '지능형 실록' 완성

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
RAW_DIR = os.path.join(ROOT_DIR, "aegis_data", "raw")
NEWS_DIR = os.path.join(ROOT_DIR, "aegis_data", "news_archive")

ARCHIVE_PATH = os.path.join(NEWS_DIR, "legal_events_history.json")
XRP_VAULT_PATH = os.path.join(RAW_DIR, "리플_고유_내러티브.json")
MACRO_VAULT_PATH = os.path.join(RAW_DIR, "거시경제_내러티브.json")

def get_fallback_models():
    load_dotenv(os.path.join(ROOT_DIR, '.env'))
    creds_path = os.getenv("GCP_CREDS_PATH")
    gc = gspread.authorize(Credentials.from_service_account_file(creds_path.strip('"').strip("'"), scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    settings_ws = gc.open("AEGIS_Daily_Report").worksheet("AEGIS_Settings")
    rows = settings_ws.get_all_values()
    chain = []
    for row in rows[1:4]: 
        if len(row) > 1 and row[1].strip(): chain.append(row[1].strip())
        if len(row) > 3 and row[3].strip(): chain.append(row[3].strip())
        if len(row) > 4 and row[4].strip(): chain.append(row[4].strip())
    return chain if chain else ["gemini-2.0-flash"]

def save_progress(mega_archive, xrp_vault, macro_vault):
    with open(ARCHIVE_PATH, 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(mega_archive.items())), f, ensure_ascii=False, indent=2)
    with open(XRP_VAULT_PATH, 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(xrp_vault.items())), f, ensure_ascii=False, indent=2)
    with open(MACRO_VAULT_PATH, 'w', encoding='utf-8') as f:
        json.dump(dict(sorted(macro_vault.items())), f, ensure_ascii=False, indent=2)

def run_archive_reconstruction():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(NEWS_DIR, exist_ok=True)
    load_dotenv(os.path.join(ROOT_DIR, '.env'))
    
    print("=" * 60)
    print("📜 [실록 편찬] 분석 근거가 포함된 2-Track 지능형 역사 복원 시작")
    print("=" * 60)

    mega_archive = {}
    if os.path.exists(ARCHIVE_PATH):
        with open(ARCHIVE_PATH, 'r', encoding='utf-8') as f: mega_archive = json.load(f)

    xrp_vault, macro_vault = {}, {}
    today = datetime.now()
    
    if mega_archive:
        start_date = datetime.strptime(max(mega_archive.keys()), "%Y-%m-%d") + timedelta(days=1)
        print(f"💾 이어하기 진격: {start_date.strftime('%Y-%m-%d')}부터 시작")
    else:
        start_date = today - timedelta(days=2000)
        print("💾 초기화 상태: 2000일 전부터 전수 조사 시작")

    fallback_chain = get_fallback_models()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    chunk_size = 20 # 분석 근거 텍스트가 추가되어 응답이 길어지므로 구간을 20일로 더 좁힘 (안전제일)
    current_start = start_date

    while current_start < today:
        current_end = min(current_start + timedelta(days=chunk_size - 1), today)
        s_str, e_str = current_start.strftime("%Y-%m-%d"), current_end.strftime("%Y-%m-%d")
        print(f"\n📡 역사 발굴 및 정밀 분석 중: {s_str} ~ {e_str}")

        prompt = f"""
        당신은 최고급 AI 데이터 분석가입니다. 기간: {s_str} ~ {e_str}
        [임무] 날짜별로 두 카테고리의 핵심 뉴스, 점수, 그리고 그 점수를 매긴 '분석 근거'를 작성하십시오.
        1. XRP 고유: 소송, 파트너십, 기술 업데이트
        2. 거시 경제: 금리, 물가, 전쟁, 비트코인 흐름
        [점수] 0(재앙) ~ 100(폭등), 50(중립)
        [응답 포맷] 반드시 아래 JSON 구조만 엄수하십시오:
        {{
          "YYYY-MM-DD": {{
            "xrp_score": 숫자,
            "xrp_headline": "한 줄 요약",
            "xrp_reason": "점수 부여 근거 (2문장 이내)",
            "macro_score": 숫자,
            "macro_headline": "한 줄 요약",
            "macro_reason": "점수 부여 근거 (2문장 이내)"
          }}
        }}
        """

        success = False
        for model in fallback_chain:
            try:
                response = client.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json"))
                data = json.loads(response.text)
                
                for dt, info in data.items():
                    mega_archive[dt] = info
                    xs, ms = float(info.get('xrp_score', 50)), float(info.get('macro_score', 50))
                    xrp_vault[dt] = {"Open": xs, "High": xs+1.5, "Low": xs-1.5, "Close": xs}
                    macro_vault[dt] = {"Open": ms, "High": ms+1.5, "Low": ms-1.5, "Close": ms}
                
                save_progress(mega_archive, xrp_vault, macro_vault)
                success = True
                print(f"   ✅ [{model}] 작전 성공! {len(data)}일치 분석 데이터 저장 완료.")
                time.sleep(5)
                break
            except: continue
                
        if not success:
            print("🚨 할당량 초과. 작전을 일시 중단합니다."); break
            
        current_start = current_end + timedelta(days=1)

    print("\n✨ 작전 종료. 근거가 포함된 '지능형 실록' 구축 완료.")

if __name__ == "__main__":
    run_archive_reconstruction()