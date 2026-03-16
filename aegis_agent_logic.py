import os
import time
from google import genai
from google.genai import types
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
RESULTS_DIR = os.path.join("aegis_data", "results")

def get_weapon_chain(gc):
    try:
        ws = gc.open("AEGIS_Daily_Report").worksheet("AEGIS_Settings")
        rows = ws.get_all_values()
        chain = []
        for row in rows[1:4]:
            if len(row) > 1 and row[1].strip(): chain.append(row[1].strip())
            if len(row) > 3 and row[3].strip(): chain.append(row[3].strip())
            if len(row) > 4 and row[4].strip(): chain.append(row[4].strip())
        return chain if chain else ["gemini-2.5-pro", "gemini-2.5-flash"]
    except: return ["gemini-2.5-pro", "gemini-2.5-flash"]

def run_logic_agent():
    print(f"⚙️ [제3참모] 논리 분석관 가동... 지표 간 시스템적 상관관계 분석 중")
    
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    gc = gspread.authorize(Credentials.from_service_account_file(creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    
    raw_indicators = gc.open("AEGIS_Daily_Report").worksheet("XRP 지표").get_all_values()
    
    # 💡 B열(1)이 아닌 C열(2)에서 하드 데이터를 가져오도록 수정
    hard_data_text = "\n".join([f"- {r[0].strip()}: {r[2].strip()}" for r in raw_indicators[1:] if len(r) >= 3 and r[0].strip()])
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"당신은 '제3참모: 순수 논리 분석관'입니다. 서사는 배제하고 원시 수치 간의 모순점만 2문단으로 찾으십시오.\n{hard_data_text}"

    weapons = get_weapon_chain(gc)
    for model_name in weapons:
        print(f"   🔫 [{model_name}] 무기 장착. 사격 시도...")
        try:
            response = client.models.generate_content(model=model_name, contents=prompt, config=types.GenerateContentConfig(temperature=0.1))
            with open(os.path.join(RESULTS_DIR, "logic_report.txt"), "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"   ✅ [명중] 논리적 모순 분석 완료.")
            return
        except Exception as e:
            print(f"   ⚠️ [총기 잼 발생] {model_name} 실패. 다음 무기로 교체합니다.")
            time.sleep(1)

if __name__ == "__main__":
    run_logic_agent()