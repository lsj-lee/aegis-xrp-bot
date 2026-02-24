import json
import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai 
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

def run_target_prediction_strategy():
    print("🧠 [2~4단계] 타점 정밀 분석 및 시트 자동화 엔진 가동...")
    
    # 1단계 데이터 로드
    try:
        with open("collected_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ 오류: 1단계 수집 데이터가 없습니다.")
        return

    # 3단계: 자가 발전 메모리 로드
    memory_file = "learning_memory.json"
    memory = json.load(open(memory_file, "r")) if os.path.exists(memory_file) else []

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    macro_data = data.get('all_time_analysis', {})
    
    # AI 프롬프트
    prompt = f"""
    [지휘 지침: 저점/고점 정밀 타겟팅 작전]
    너의 최우선 임무는 코인의 '현재 최저점 여부'와 '단기, 중기, 장기 저점 및 고점'을 분석하여 타점을 제공하는 것이다.

    [분석 데이터]
    1. 맥북 M5 수학적 역사 데이터: {json.dumps(macro_data, ensure_ascii=False)}
    2. 사령관 전략 지표: {json.dumps(data.get('payload', []), ensure_ascii=False)}
    3. 과거 예측 오답 노트 (학습용): {json.dumps(memory[-3:], ensure_ascii=False)}

    [출력 필수 형식 및 제약사항]
    - 불확실한 미래 가격은 "확실하지 않음" 또는 "알 수 없습니다"라고 명시.
    - 예상 타점(가격) 제시 시 문장 끝에 "(추측입니다)"라고 밝힐 것.
    - 다음 4가지 항목을 나누어 보고하라:
      1. 현재 가격 최저점 판별 (확률 % 및 근거)
      2. 단기 타점 (1주일~1개월): 예상 저점 및 고점
      3. 중기 타점 (3개월~6개월): 3월 1일 정책 이벤트 등 반영
      4. 장기 타점 (1년 이상): 2026년 대불장 사이클 반영
    """

    try:
        print("📡 Gemini 2.5 본부에서 타점 계산 중...")
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        report = response.text

        # 3단계: 자가 발전 메모리 저장
        new_memory = {
            "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "target_predictions": report[:400].replace("\n", " ")
        }
        memory.append(new_memory)
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=4)

        # 백업용 텍스트 파일 저장 (선택 사항)
        with open("AEGIS_Latest_Report.txt", "w", encoding="utf-8") as f:
            f.write(report)

        # 🚀 4단계: 구글 시트 'AEGIS_Daily_Report Results'에 전송
        print("📤 [4단계] 구글 시트 전송 작전 개시...")
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file("creds xrp coin.json", scopes=scopes)
        gc = gspread.authorize(creds)
        
        # 1. 스프레드시트 열기
        spreadsheet = gc.open("AEGIS_Daily_Report")
        
        # 2. 'AEGIS_Daily_Report Results' 탭 찾기 (없으면 자동 생성)
        try:
            worksheet = spreadsheet.worksheet("AEGIS_Daily_Report Results")
        except gspread.exceptions.WorksheetNotFound:
            print("⚠️ 'AEGIS_Daily_Report Results' 탭이 없어 새로 생성합니다.")
            worksheet = spreadsheet.add_worksheet(title="AEGIS_Daily_Report Results", rows="100", cols="10")
            
        # 3. 기존 내용 완벽하게 지우기 (초기화)
        worksheet.clear()
        
        # 4. 리포트 텍스트를 A열에 한 줄씩 예쁘게 들어가도록 배열 구조로 변환
        report_lines = report.split('\n')
        cell_values = [[line] for line in report_lines]
        
        # 5. 헤더(제목)와 함께 A1 셀부터 덮어쓰기
        header = [[f"🛡️ AEGIS 타점 정밀 분석 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"], ["="*60]]
        final_values = header + cell_values
        
        # 라이브러리 버전 호환성을 위한 안전한 업데이트 방식
        try:
            worksheet.update(values=final_values, range_name="A1")
        except TypeError:
            worksheet.update("A1", final_values)

        print("\n" + "═"*60 + "\n" + report + "\n" + "═"*60)
        print("✅ [4단계 완료] 구글 시트 'AEGIS_Daily_Report Results' 탭에 최신 리포트가 덮어쓰기 되었습니다.")

    except Exception as e:
        print(f"❌ AI 분석 또는 시트 전송 실패: {e}")

if __name__ == "__main__":
    run_target_prediction_strategy()