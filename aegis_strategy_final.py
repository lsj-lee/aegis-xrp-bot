import os
import json
import gspread
from google.oauth2.service_account import Credentials
from google import genai
from google.genai import types
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
RESULTS_DIR = os.path.join("aegis_data", "results")

def run_final_synthesis():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"👑 [수석 전략관] XRP 중심 전략 종합 및 시트 타격 가동... ({now_str})")
    
    # 1. 참모들의 보고서 수거
    insight_path = os.path.join(RESULTS_DIR, "insight_report.txt")
    logic_path = os.path.join(RESULTS_DIR, "logic_report.txt")
    
    try:
        with open(insight_path, "r", encoding="utf-8") as f: insight_text = f.read()
        with open(logic_path, "r", encoding="utf-8") as f: logic_text = f.read()
    except Exception as e:
        print(f"❌ [오류] 참모 보고서가 없습니다. 2참모, 3참모를 먼저 실행하십시오. ({e})")
        return

    # 2. M5 결과 수거 (최신 JSON) 및 XRP 현재가 추출
    files = [f for f in os.listdir(RESULTS_DIR) if f.startswith("result_") and f.endswith(".json")]
    if not files: 
        print("❌ [오류] M5 연산 결과 파일이 없습니다.")
        return
        
    latest_file = max(files)
    with open(os.path.join(RESULTS_DIR, latest_file), 'r', encoding='utf-8') as f:
        m5_data = json.load(f)
        
    xrp_current_price = m5_data.get('current_price', '알 수 없음')
    m5_text = f"XRP 현재가: {xrp_current_price}원, 1/7/30일 예측: {m5_data.get('predict_1d')}/{m5_data.get('predict_7d')}/{m5_data.get('predict_30d')}, 지표: {m5_data.get('indicators')}"

    # 3. 수석 전략관 AI 호출 (프롬프트 강화: XRP 록온)
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"""
    당신은 AEGIS의 수석 전략 참모입니다. 
    당신의 **유일한 타겟 자산은 '리플(XRP)'**입니다. 비트코인이나 다른 거시 경제 지표들은 시장의 흐름을 읽는 보조 지표로만 활용하고, 모든 전략적 결론과 가격 타점은 반드시 **리플(XRP)**을 기준으로 산출하십시오.

    [리플(XRP) 기준 가격 정보]
    - 현재가: {xrp_current_price} KRW (M5 엔진 기준)

    [제1참모: M5 기술 분석 (XRP 기준)]
    {m5_text}
    
    [제2참모: 통찰 분석]
    {insight_text}
    
    [제3참모: 논리 분석]
    {logic_text}

    [출력 엄수 규칙]
    파이썬이 구글 시트의 각 구역에 분산 기록할 수 있도록 특수 구분자([SEC_번호])를 반드시 사용하십시오.

    [SEC_1]
    🛡️ AEGIS 수석 전략 보고서 ({now_str})
    작전명: [장세 요약 슬로건 1줄]
    [SEC_2]
    ■ 참모별 핵심 브리핑
    - M5 수치(XRP): [요약]
    - 통찰 서사: [요약]
    - 논리 검증: [요약]
    [SEC_3]
    ■ 상충 및 일치 지점 분석 (Cross-Validation)
    [세 참모의 의견 충돌/일치 여부를 비판적으로 분석하여 XRP 투자에 대한 노이즈와 함정을 경고]
    [SEC_4]
    ■ 사령관 최종 권고 사항
    [종합 가중치 부여 후 즉각적인 XRP 행동 지침(매수/매도/관망) 제시]
    [SEC_5]
    ■ XRP 정밀 타점 (KRW / USD)
    - 현재 XRP 가격: {xrp_current_price} KRW
    - 단기(1개월): [XRP 타점] / [사유]
    - 중기(1년): [XRP 타점] / [사유]
    - 장기(대불장): [XRP 타점] / [사유]
    [SEC_6]
    [최종 한 줄 평]
    """

    print("   🔄 전략 종합 및 XRP 정밀 타점 산출 중...")
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.4) # 타점의 보수성과 논리성을 위해 온도 하향 조정
    )
    report = response.text

    # 4. 섹션 파싱 및 시트 정밀 타격
    sections = {}
    for i in range(1, 7):
        tag = f"[SEC_{i}]"
        next_tag = f"[SEC_{i+1}]" if i < 6 else None
        if tag in report:
            start_idx = report.find(tag) + len(tag)
            end_idx = report.find(next_tag) if next_tag and next_tag in report else len(report)
            sections[f"SEC_{i}"] = report[start_idx:end_idx].strip()
        else:
            sections[f"SEC_{i}"] = ""

    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    doc = gc.open("AEGIS_Daily_Report")
    
    results_ws = doc.worksheet("AEGIS_Daily_Report Results")
    results_ws.clear()

    def format_for_cells(text): return [[line] for line in text.split('\n')]

    updates = []
    if sections["SEC_1"]: updates.append({'range': 'A1', 'values': format_for_cells(sections["SEC_1"])})
    if sections["SEC_2"]: updates.append({'range': 'A5', 'values': format_for_cells(sections["SEC_2"])})
    if sections["SEC_3"]: updates.append({'range': 'A11', 'values': format_for_cells(sections["SEC_3"])})
    if sections["SEC_4"]: updates.append({'range': 'A17', 'values': format_for_cells(sections["SEC_4"])})
    if sections["SEC_5"]: updates.append({'range': 'A22', 'values': format_for_cells(sections["SEC_5"])})
    
    if updates:
        results_ws.batch_update(updates)

    if sections["SEC_6"]:
        history_ws = doc.worksheet("AEGIS_History")
        history_ws.update_cell(len(history_ws.get_all_values()), 7, sections["SEC_6"])

    print(f"   ✅ [본부] XRP 전용 최종 전략 리포트 시트 타격 완료!")

if __name__ == "__main__":
    run_final_synthesis()