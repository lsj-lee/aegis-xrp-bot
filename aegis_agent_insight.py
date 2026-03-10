import os
from google import genai
from google.genai import types
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
RESULTS_DIR = os.path.join("aegis_data", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

def run_insight_agent():
    print(f"👁️ [제2참모] 통찰 분석관 가동... 서사 및 심리 분석 중")
    
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    doc = gc.open("AEGIS_Daily_Report")
    
    data_ws = doc.worksheet("XRP 지표")
    saebyeok_ws = doc.worksheet("어슴새벽")
    
    raw_indicators = data_ws.get_all_values()
    saebyeok_data = saebyeok_ws.get_all_values()
    
    indicator_dict = {}
    for r in raw_indicators[1:]:
        if len(r) >= 2 and r[0].strip():
            indicator_dict[r[0].strip()] = {"수치": r[1].strip(), "견해": "없음"}
            
    for r in saebyeok_data[1:]:
        name = r[0].strip()
        if len(r) >= 2 and name in indicator_dict:
            indicator_dict[name]["견해"] = r[1].strip()

    analysis_text = "\n".join([f"- {k}: 수치({v['수치']}) / 견해({v['견해']})" for k, v in indicator_dict.items() if v['견해'] != "없음"])
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = f"""
    당신은 AEGIS 시스템의 '제2참모: 통찰 분석관'입니다. M5 기술 지표는 철저히 배제하고, 차트 이면의 인간 심리와 거시적 서사만 분석하십시오.
    
    [입력 데이터]
    {analysis_text}
    
    [임무]
    1. 어슴새벽의 견해와 현재 수치가 일치하는지(서사적 일관성) 대조하십시오.
    2. 1929 대공황 주기, 세력 매집, 엘리트 설계론 등의 관점에서 현재 시장 심리(Fear & Greed 등)를 해석하십시오.
    3. 500자 이내의 통찰 보고서를 작성하십시오. 인사말은 생략하십시오.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.8) # 창의성 극대화
    )
    
    report_path = os.path.join(RESULTS_DIR, "insight_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(response.text.strip())
        
    print(f"   ✅ [제2참모] 통찰 보고서 작성 완료 ({report_path})")

if __name__ == "__main__":
    run_insight_agent()