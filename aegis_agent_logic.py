import os
from google import genai
from google.genai import types
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
RESULTS_DIR = os.path.join("aegis_data", "results")

def run_logic_agent():
    print(f"⚙️ [제3참모] 논리 분석관 가동... 지표 간 시스템적 상관관계 분석 중")
    
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    doc = gc.open("AEGIS_Daily_Report")
    
    data_ws = doc.worksheet("XRP 지표")
    raw_indicators = data_ws.get_all_values()
    
    hard_data_text = "\n".join([f"- {r[0].strip()}: {r[1].strip()}" for r in raw_indicators[1:] if len(r) >= 2 and r[0].strip()])
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = f"""
    당신은 AEGIS 시스템의 '제3참모: 순수 논리 분석관'입니다. 인간의 견해나 외부 서사는 철저히 배제하고 데이터 간의 모순점만 찾으십시오.
    
    [입력 데이터 (원시 수치)]
    {hard_data_text}
    
    [임무]
    1. BTC 도미넌스, USDT 도미넌스, 구리/금 비율 등 지표 간의 상관관계를 기반으로 전체 유동성(Liquidity) 이동을 추적하십시오.
    2. 데이터 간 괴리가 발생하여 함정이 의심되는 구간이 있는지 시스템적으로 판단하십시오.
    3. 500자 이내의 논리 검증 보고서를 작성하십시오. 인사말은 생략하십시오.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2) # 논리성 극대화 (환각 차단)
    )
    
    report_path = os.path.join(RESULTS_DIR, "logic_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(response.text.strip())
        
    print(f"   ✅ [제3참모] 논리 보고서 작성 완료 ({report_path})")

if __name__ == "__main__":
    run_logic_agent()