import json
import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai 
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

def run_target_prediction_strategy():
    print("🧠 [2~4단계] 업비트 기준 환산 및 추측 근거 강화 엔진 가동...")
    
    try:
        with open("collected_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ 오류: 1단계 수집 데이터가 없습니다.")
        return

    memory_file = "learning_memory.json"
    memory = json.load(open(memory_file, "r")) if os.path.exists(memory_file) else []

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    macro_data = data.get('all_time_analysis', {})
    
    # 💡 프롬프트 핵심 수정: 업비트 단가 활용 및 추측 이유 강제
    prompt = f"""
    [지휘 지침: 저점/고점 정밀 타겟팅]
    구글 시트에 입력될 보고서이므로, 말이 길어지지 않게 최대한 핵심만 압축해서 작성하라.

    [분석 데이터]
    1. 수학적 역사 데이터 (업비트 원화 실시간 가격 포함): {json.dumps(macro_data, ensure_ascii=False)}
    2. 사령관 전략 지표: {json.dumps(data.get('payload', []), ensure_ascii=False)}
    3. 과거 오답 노트: {json.dumps(memory[-3:], ensure_ascii=False)}

    [출력 필수 형식 및 제약사항]
    - 불확실한 부분은 "확실하지 않음"이라고 명시.
    - [중요 1] 예상 타점을 제시할 때, 제공된 '현재가(업비트KRW)'와 '현재가(USD)'의 비율(김치 프리미엄)을 계산하여, 단순 환율이 아닌 **'업비트 원화(KRW) 가격 기준'**으로 제시하라. (예: $1.50 (업비트 기준 약 2,100원))
    - [중요 2] 예상 타점 끝에는 항상 "(추측입니다)"를 적고, 바로 줄을 바꿔 "- 추측 이유: [가장 결정적인 근거 1문장]"을 반드시 명시하라.
    - 불필요한 서론/결론은 빼고 아래 4개 항목의 '제목'과 '핵심 내용'만 출력.
    
    1. 현재 가격 최저점 판별 (확률 및 근거 2줄 요약)
    2. 단기 타점 (1주일~1개월, 달러/업비트 원화 타점 + 추측 이유)
    3. 중기 타점 (3개월~6개월, 3월 1일 정책 반영, 달러/업비트 원화 타점 + 추측 이유)
    4. 장기 타점 (1년 이상, 2026 대불장 반영, 달러/업비트 원화 타점 + 추측 이유)
    """

    try:
        print("📡 Gemini 2.5 본부에서 업비트 단가 연동 계산 중...")
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        report = response.text

        new_memory = {
            "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "target_predictions": report[:400].replace("\n", " ")
        }
        memory.append(new_memory)
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=4)

        print("📤 [4단계] 구글 시트 전송 작전 개시...")
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file("creds xrp coin.json", scopes=scopes)
        gc = gspread.authorize(creds)
        
        spreadsheet = gc.open("AEGIS_Daily_Report")
        
        try:
            worksheet = spreadsheet.worksheet("AEGIS_Daily_Report Results")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="AEGIS_Daily_Report Results", rows="100", cols="10")
            
        worksheet.clear()
        
        paragraphs = [p.strip() for p in report.split('\n\n') if p.strip()]
        cell_values = [[p] for p in paragraphs]
        
        header = [[f"🛡️ AEGIS 타점 정밀 분석 리포트 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"], ["="*60]]
        final_values = header + cell_values
        
        try:
            worksheet.update(values=final_values, range_name="A1")
        except TypeError:
            worksheet.update("A1", final_values)

        print("✅ [4단계 완료] 업비트 기준 원화 환산 및 추측 이유가 추가된 리포트가 구글 시트에 기록되었습니다.")

    except Exception as e:
        print(f"❌ AI 분석 또는 시트 전송 실패: {e}")

if __name__ == "__main__":
    run_target_prediction_strategy()