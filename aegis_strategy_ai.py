import json
import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai 

load_dotenv()

def run_target_prediction_strategy():
    print("🧠 [2~4단계] 저점/고점 정밀 타겟팅 및 자가 발전 엔진 가동...")
    
    # 1단계 데이터 로드
    try:
        with open("collected_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ 오류: 1단계 수집 데이터가 없습니다. data_bank_builder.py를 먼저 실행하세요.")
        return

    # 3단계: 자가 발전 메모리 로드
    memory_file = "learning_memory.json"
    memory = json.load(open(memory_file, "r")) if os.path.exists(memory_file) else []

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    macro_data = data.get('all_time_analysis', {})
    
    # AI 프롬프트 (엄격한 지휘 통제)
    prompt = f"""
    [지휘 지침: 저점/고점 정밀 타겟팅 작전]
    너의 최우선 임무는 사령관을 위해 코인의 '현재 최저점 여부'와 '단기, 중기, 장기 저점 및 고점'을 분석하여 타점을 제공하는 것이다.

    [분석 데이터]
    1. 맥북 M5 수학적 역사 데이터: {json.dumps(macro_data, ensure_ascii=False)}
    2. 사령관 전략 지표: {json.dumps(data.get('payload', []), ensure_ascii=False)}
    3. 과거 예측 오답 노트 (학습용): {json.dumps(memory[-3:], ensure_ascii=False)}

    [출력 필수 형식 및 제약사항]
    - 불확실한 미래 가격이나 모호한 정보에 대해서는 단정 짓지 말고 "확실하지 않음" 또는 "알 수 없습니다"라고 명시하라.
    - 예측되는 타점(가격)을 제시할 때는 반드시 문장 끝에 "(추측입니다)"라고 밝혀라.
    - 아래 4가지 항목을 정확히 나누어 보고하라:
      1. 현재 가격 최저점 판별: (현재 가격이 진정한 바닥일 확률 % 및 근거)
      2. 단기 타점 (1주일~1개월): 예상 저점 및 고점
      3. 중기 타점 (3개월~6개월): 3월 1일 정책 이벤트 등 반영한 예상 저점 및 고점
      4. 장기 타점 (1년 이상): 2026년 대불장 사이클을 반영한 예상 저점 및 고점
    """

    try:
        print("📡 Gemini 2.5 본부에서 타점 계산 중...")
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        report = response.text

        # 3단계: 자가 발전 (오늘 예측한 단기 저점/고점을 저장하여 내일 검증)
        new_memory = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "target_predictions": report[:400].replace("\n", " "), # 예측 타점 요약 저장
            "reflection": "다음 실행 시 실제 가격과 비교하여 예측 정확도를 평가할 것."
        }
        memory.append(new_memory)
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=4)

        # 4단계: 결과 출력 및 보고서 저장
        filename = f"AEGIS_Target_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"🛡️ AEGIS 타점 정밀 분석 리포트 ({datetime.now()})\n")
            f.write("="*60 + "\n")
            f.write(report)
            f.write("\n" + "="*60 + "\n")
            f.write("System: MacBook Pro M5 | Mode: Target Prediction & Self-Evolution")

        print("\n" + "═"*60 + "\n" + report + "\n" + "═"*60)
        print(f"✅ [4단계 완료] 타점 분석 리포트 '{filename}' 저장 및 자가 발전 메모리 업데이트 완료.")

    except Exception as e:
        print(f"❌ AI 분석 실패: {e}")

if __name__ == "__main__":
    run_target_prediction_strategy()