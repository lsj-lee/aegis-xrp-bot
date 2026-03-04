import os
import random
import time
from google import genai
from google.genai import types
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def run_strategic_ai():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🧠 [본부] 정밀 타점 브리핑 포맷 가동... ({now_str})")
    
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    doc = gc.open("AEGIS_Daily_Report")
    
    settings_ws = doc.worksheet("AEGIS_Settings")
    settings_data = settings_ws.get_all_values()
    
    def get_models_from_row(row_idx):
        models = []
        if len(settings_data) > row_idx:
            row = settings_data[row_idx]
            for idx in [1, 3, 4]: 
                if len(row) > idx and row[idx].strip():
                    models.append(row[idx].strip())
        return models

    high_tier_models = get_models_from_row(1)
    mid_tier_models = get_models_from_row(2)
    
    raw_models_to_try = []
    for m in high_tier_models + mid_tier_models:
        if "preview" not in m.lower() and "experimental" not in m.lower():
            if m not in raw_models_to_try:
                raw_models_to_try.append(m)

    if not raw_models_to_try:
        raw_models_to_try = ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

    def normalize_model(name):
        name = name.strip()
        return name if name.startswith("models/") else f"models/{name}"

    models_to_try = [normalize_model(m) for m in raw_models_to_try]
    
    try:
        primary_order = settings_data[11][1].strip() if len(settings_data[11]) > 1 else ""
        backup_memo = settings_data[11][2].strip() if len(settings_data[11]) > 2 else ""
        raw_order = f"{primary_order} {backup_memo}".strip()
        commander_order = raw_order[:500] if raw_order else "제공된 지표를 바탕으로 단기, 중기, 장기 타점을 정확히 산출하라."
        ai_tone = settings_data[12][1] if len(settings_data) > 12 and len(settings_data[12]) > 1 else "보고서형"
    except IndexError:
        commander_order = "제공된 지표를 바탕으로 단기, 중기, 장기 타점을 정확히 산출하라."
        ai_tone = "보고서형"

    daily_ws = doc.worksheet("AEGIS_Daily_Report")
    raw_guide = daily_ws.get('A2:B200') 
    
    guides = []
    for r in raw_guide:
        if len(r) >= 2 and r[0].strip():
            if len(r[0]) < 100:
                guides.append(f"■ {r[0]}: {r[1]}")
                
    random.shuffle(guides)
    shuffled_guide_text = "\n".join(guides)

    history_sheet = doc.worksheet("AEGIS_History")
    history_data = history_sheet.get_all_values()
    latest_stats = history_data[-1] if history_data else []
    m5_tech = latest_stats[5] if len(latest_stats) > 5 else "N/A"
    current_price_krw = latest_stats[1] if len(latest_stats) > 1 else "알 수 없음"

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # 🧠 [프롬프트 재설계] 사령관 맞춤형 구조화 포맷 강제
    final_prompt = f"""
    당신은 사령관 lsj의 수석 전략 참모입니다. 이전의 에세이 형식은 폐기하고, 오직 아래 제공된 [출력 양식]에 맞추어 브리핑하십시오.
    
    [사령관 마스터 가이드]
    {shuffled_guide_text}
    
    [M5 로컬 타격 데이터]
    - 현재가(KRW): {current_price_krw}
    - 1/7/30일 예측가(KRW): {latest_stats[2:5]}
    - 핵심 기술 지표: {m5_tech}
    
    [작성 엄수 규칙]
    1. 달러(USD) 가격은 현재가 환율(약 1,400원)을 가정하여 추산하여 병기하십시오.
    2. 단기, 중기, 장기의 '전략적 사유'는 반드시 M5의 기술 지표 수치와 마스터 가이드의 내용을 논리적으로 결합하여 작성하십시오.
    
    [출력 양식]
    ============================================================
    🛡️ AEGIS 정밀 타점 리포트
    * 작성 일시: {now_str}
    * 작전명: [오늘 장세를 요약하는 강력한 슬로건 1줄]
    ============================================================

    ■ 단기 분석 (1개월 이내)
    - 예상 타점 (XRP): [예상 KRW] / [예상 USD]
    - 전략적 사유: [이유 서술]

    ■ 중기 분석 (1년 이내)
    - 예상 타점 (XRP): [예상 KRW] / [예상 USD]
    - 전략적 사유: [이유 서술]

    ■ 장기 분석 (2026년 대불장 및 이후)
    - 예상 타점 (XRP): [예상 KRW] / [예상 USD]
    - 전략적 사유: [이유 서술]

    [요약] [핵심 결론 1줄]
    """

    report_generated = False
    
    for model_id in models_to_try:
        try:
            print(f"   🔄 [{model_id}] 무기로 전략 분석 시도 중... (과열 방지 3초 냉각)")
            time.sleep(3)
            
            response = client.models.generate_content(
                model=model_id, 
                contents=final_prompt,
                config=types.GenerateContentConfig(temperature=0.8, top_p=0.9) # 구조화를 위해 온도를 0.8로 약간 낮춤
            )
            report = response.text
            
            # 셀 분산 타격 (가독성)
            report_lines = report.split('\n')
            cell_values = [[line] for line in report_lines]
            
            results_ws = doc.worksheet("AEGIS_Daily_Report Results")
            results_ws.clear()
            results_ws.update(values=cell_values, range_name=f"A1:A{len(cell_values)}")
            
            if "[요약]" in report:
                summary = report.split("[요약]")[1].strip()
                history_sheet.update_cell(len(history_data), 7, summary)
                
            print(f"   ✅ [{model_id}] 타격 성공! 구조화된 정밀 포맷으로 갱신 완료!")
            report_generated = True
            break
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                print(f"   ⚠️ [{model_id}] 할당량 소진. 다음 순위 무기로 탄창을 교체합니다.")
                continue
            else:
                print(f"   ❌ [{model_id}] 에러: {error_msg}")
                continue

    if not report_generated:
        print("🛑 [본부] 등록된 모든 안정적 무기의 잔탄이 소진되었습니다.")

if __name__ == "__main__":
    run_strategic_ai()