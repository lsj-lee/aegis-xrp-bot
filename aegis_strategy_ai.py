import json
import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai 
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

def run_target_prediction_strategy():
    print("🧠 [본부] 클라우드 AI 전략 분석 엔진 가동...")
    
    # 1. 구글 시트 인증 및 접속
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds xrp coin.json", scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open("AEGIS_Daily_Report")

    # 2. 맥북이 남긴 ML 데이터 읽기
    try:
        storage_sheet = spreadsheet.worksheet("AEGIS_ML_Storage")
        ml_values = storage_sheet.get_all_values()
        # ml_values[1] -> XRP 데이터, ml_values[2] -> BTC 데이터
        ml_context = {
            "XRP": {"현재가": ml_values[1][1], "ML예측": ml_values[1][2]},
            "BTC": {"현재가": ml_values[2][1], "ML예측": ml_values[2][2]},
            "연산시간": ml_values[1][3]
        }
    except Exception as e:
        print(f"⚠️ ML 저장소를 찾을 수 없어 일반 분석을 진행합니다: {e}")
        ml_context = "데이터 부재"

    # 3. 제미나이 전략 분석
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"""
    [지휘 지침: AEGIS 분산 지능 리포트]
    맥북 M5 연구소가 계산한 머신러닝(ML) 데이터와 사령관님의 전략 지표를 융합하여 보고하라.

    [핵심 분석 데이터]
    - 맥북 M5 ML 연산 결과: {json.dumps(ml_context, ensure_ascii=False)}
    
    [출력 필수 형식]
    1. 현재 가격 최저점 판별 (확률 및 근거)
    2. 단기 타점: 맥북 M5 ML 예측가(${ml_values[1][2] if ml_context != "데이터 부재" else "N/A"})를 기준으로 업비트 원화 타점 제시 + 추측 이유
    3. 중기 타점: 3월 1일 정책 반영 + 업비트 원화 타점 + 추측 이유
    4. 장기 타점: 2026 대불장 사이클 반영 + 업비트 원화 타점 + 추측 이유
    
    * 모든 가격 옆에 (업비트 기준 약 000원) 병기 필수.
    * 타점 끝에 (추측입니다) 필수 기입.
    """

    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        report = response.text

        # 4. 결과 시트 기록 (기존 내용 삭제 후 덮어쓰기)
        try:
            worksheet = spreadsheet.worksheet("AEGIS_Daily_Report Results")
        except:
            worksheet = spreadsheet.add_worksheet(title="AEGIS_Daily_Report Results", rows="100", cols="10")
        
        worksheet.clear()
        paragraphs = [p.strip() for p in report.split('\n\n') if p.strip()]
        cell_values = [[f"🛡️ AEGIS 분산 지능 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"], ["="*60]] + [[p] for p in paragraphs]
        
        try: worksheet.update(values=cell_values, range_name="A1")
        except: worksheet.update("A1", cell_values)

        print("✅ [본부] 최종 전략 리포트 전송 완료.")

    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")

if __name__ == "__main__":
    run_target_prediction_strategy()