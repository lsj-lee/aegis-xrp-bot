import json
import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai 
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

def run_target_prediction_strategy():
    print("🧠 [본부] M5 근거를 포함한 최종 전략 분석 엔진 가동...")
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds xrp coin.json", scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open("AEGIS_Daily_Report")

    try:
        storage_sheet = spreadsheet.worksheet("AEGIS_ML_Storage")
        ml_values = storage_sheet.get_all_values()
        # [1][3]은 XRP 근거, [2][3]은 BTC 근거
        ml_context = {
            "XRP": {"현재가": ml_values[1][1], "ML예측": ml_values[1][2], "ML근거": ml_values[1][3]},
            "BTC": {"현재가": ml_values[2][1], "ML예측": ml_values[2][2], "ML근거": ml_values[2][3]}
        }
    except:
        ml_context = "데이터 부재"

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"""
    [지휘 지침: AEGIS 하이브리드 리포트]
    맥북 M5 연구소가 직접 분석한 'ML 판단 근거'를 전략 리포트에 적극 반영하라.

    [핵심 분석 데이터]
    - 맥북 M5 연구소 분석 데이터: {json.dumps(ml_context, ensure_ascii=False)}
    
    [출력 필수 형식]
    1. 현재 가격 최저점 판별 (확률 및 근거)
    2. 단기 타점: **맥북 M5의 판단 근거를 반드시 언급**하며 업비트 원화 타점 제시.
    3. 중기 타점: 3월 1일 정책 반영 + 업비트 원화 타점 + 추측 이유.
    4. 장기 타점: 2026 대불장 사이클 반영 + 업비트 원화 타점 + 추측 이유.
    
    * 타점 제시 시 "추측 이유"를 작성할 때 M5의 수학적 의견을 사령관님의 전략 지표와 융합할 것.
    """

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        report = response.text

        try:
            worksheet = spreadsheet.worksheet("AEGIS_Daily_Report Results")
        except:
            worksheet = spreadsheet.add_worksheet(title="AEGIS_Daily_Report Results", rows="100", cols="10")
        
        worksheet.clear()
        paragraphs = [p.strip() for p in report.split('\n\n') if p.strip()]
        cell_values = [[f"🛡️ AEGIS 분산 지능 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"], ["="*60]] + [[p] for p in paragraphs]
        
        try: worksheet.update(values=cell_values, range_name="A1")
        except: worksheet.update("A1", cell_values)
        print("✅ [본부] M5 근거가 반영된 리포트 전송 완료.")
    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")

if __name__ == "__main__":
    run_target_prediction_strategy()