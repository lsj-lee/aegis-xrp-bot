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

def run_insight_agent():
    print(f"👁️ [제2참모] 통찰 분석관 가동... 서사 및 심리 분석 중")
    
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    gc = gspread.authorize(Credentials.from_service_account_file(creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    
    doc = gc.open("AEGIS_Daily_Report")
    raw_indicators = doc.worksheet("XRP 지표").get_all_values()
    saebyeok_data = doc.worksheet("어슴새벽").get_all_values()
    
    # 💡 B열(1)이 아닌 C열(2)에서 수치를 가져오도록 수정
    indicator_dict = {}
    for r in raw_indicators[1:]:
        if len(r) >= 3 and r[0].strip():
            indicator_dict[r[0].strip()] = {"수치": r[2].strip(), "견해": "없음"}
            
    for r in saebyeok_data[1:]:
        if len(r) >= 2 and r[0].strip() in indicator_dict:
            # 어슴새벽의 가장 마지막 열(최근 달)의 데이터를 가져옴
            indicator_dict[r[0].strip()]["견해"] = r[-1].strip()

    analysis_text = "\n".join([f"- {k}: 수치({v['수치']}) / 견해({v['견해']})" for k, v in indicator_dict.items() if v['견해'] != "없음"])
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"당신은 '제2참모: 통찰 분석관'입니다. 아래 데이터를 바탕으로 엘리트 세력의 의도와 대중 심리를 3문단으로 요약하십시오.\n{analysis_text}"

    weapons = get_weapon_chain(gc)
    for model_name in weapons:
        print(f"   🔫 [{model_name}] 무기 장착. 사격 시도...")
        try:
            response = client.models.generate_content(model=model_name, contents=prompt, config=types.GenerateContentConfig(temperature=0.3))
            with open(os.path.join(RESULTS_DIR, "insight_report.txt"), "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"   ✅ [명중] 통찰 분석 보고서 작성 완료.")
            return
        except Exception as e:
            print(f"   ⚠️ [총기 잼 발생] {model_name} 실패. 다음 무기로 교체합니다.")
            time.sleep(1)

if __name__ == "__main__":
    run_insight_agent()