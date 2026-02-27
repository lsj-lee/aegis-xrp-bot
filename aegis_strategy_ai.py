import json
import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai 
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

def run_target_prediction_strategy():
    print("🧠 [본부] AEGIS 7.0 고도화된 저점/고점 분석 엔진 가동...")
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_path = os.getenv("GCP_CREDS_PATH")
    
    if not creds_path or not os.path.exists(creds_path):
        print("❌ 인증 파일 누락: GCP_CREDS_PATH 환경변수가 설정되지 않았거나 파일이 존재하지 않습니다.")
        return

    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open("AEGIS_Daily_Report")
    strategy_worksheet = spreadsheet.worksheet("AEGIS_Daily_Report")
    
    # 1. 데이터 로드
    all_values = strategy_worksheet.get_all_values()
    rows = all_values[1:]
    payload = [{"지표": r[0], "의미": r[1] if len(r)>1 else ""} for r in rows if r[0]]
    
    storage_sheet = spreadsheet.worksheet("AEGIS_ML_Storage")
    ml_values = storage_sheet.get_all_values()
    ml_context = {
        "XRP": {"현재가": ml_values[1][1], "ML예측": ml_values[1][2], "ML근거": ml_values[1][3]},
        "BTC": {"현재가": ml_values[2][1], "ML예측": ml_values[2][2], "ML근거": ml_values[2][3]}
    }

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # 💡 [프롬프트 강화] 저점/고점 분리 및 데이터 근거 명시 지시
    prompt = f"""
    [지휘 지침: AEGIS 정밀 타점 리포트]
    사령관님께 보고할 단기, 중기, 장기별 '저점(매수)' 및 '고점(매도)'을 데이터에 기반하여 정밀 산출하라.

    [입력 데이터]
    - 맥북 M5 ML 연산: {json.dumps(ml_context, ensure_ascii=False)}
    - 사령관 전략 지표: {json.dumps(payload, ensure_ascii=False)}

    [출력 필수 형식]
    각 기간(단기/중기/장기)마다 반드시 아래 구조를 유지할 것:
    
    ■ [기간명] 분석
    - 예상 저점(매수): [가격] (추측입니다)
    - 예상 고점(매도): [가격] (추측입니다)
    - 적용된 핵심 데이터: [M5 예측값, 특정 거시 지표 등 명시]
    - 전략적 사유: [데이터를 근거로 한 상세 설명]

    [제약 사항]
    1. 모든 가격은 업비트 원화(KRW)를 기준으로 작성하라.
    2. '적용된 핵심 데이터' 섹션에는 분석에 쓰인 구체적인 숫자나 지표명을 나열하라.
    3. 본문 마지막에 반드시 [시트 기록용] 태그와 함께 내일 분석에 반영할 한 줄 요약을 남겨라.
    """

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        report = response.text

        # 🚀 [자율 진화] 시트 기록 로직
        if "[시트 기록용]" in report:
            suggestion = report.split("[시트 기록용]")[1].split("\n")[0].strip()
            tag = f"AI_자율기록_{datetime.now().strftime('%m%d')}"

            # Optimization: Use already loaded data instead of making a new API call
            # Use set for O(1) lookup
            existing_tags = {r[0] for r in rows if r}

            if tag not in existing_tags:
                strategy_worksheet.append_row([tag, suggestion])

        # 🚀 리포트 결과 기록
        try:
            results_worksheet = spreadsheet.worksheet("AEGIS_Daily_Report Results")
        except:
            results_worksheet = spreadsheet.add_worksheet(title="AEGIS_Daily_Report Results", rows="100", cols="10")
        
        results_worksheet.clear()
        paragraphs = [p.strip() for p in report.split('\n\n') if p.strip()]
        header = [[f"🛡️ AEGIS 정밀 저점/고점 분석 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"], ["="*60]]
        final_values = header + [[p] for p in paragraphs]
        
        results_worksheet.update(values=final_values, range_name="A1")
        print("✅ 정밀 리포트 배달 완료.")

    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")

if __name__ == "__main__":
    run_target_prediction_strategy()