import json
import os
from datetime import datetime
from dotenv import load_dotenv
from google import genai 

# 1. 환경 설정 로드 [cite: 2026-02-11]
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def run_integrated_strategy():
    print("🧠 [2단계] 동적 AI 전략 분석 엔진 기동 중...")
    
    # 1. 수집된 가변 데이터 로드 [cite: 2026-02-24]
    try:
        with open("collected_data.json", "r", encoding="utf-8") as f:
            data_bank = json.load(f)
            indicators = data_bank.get('payload', [])
            total_count = data_bank.get('total_items', 0)
    except FileNotFoundError:
        print("❌ 오류: collected_data.json이 없습니다. 1단계를 실행하십시오.")
        return

    if total_count == 0:
        print("⚠️ 경고: 수집된 지표가 0개입니다. 시트 내용을 확인하십시오.")
        return

    # 2. 동적 프롬프트 생성 (지표의 종류와 개수에 무관하게 작동) [cite: 2026-01-30]
    indicator_summary = ""
    for idx, item in enumerate(indicators, 1):
        indicator_summary += f"{idx}. {item['지표']}\n"
        indicator_summary += f"   - 실시간 수치: {item['실시간_데이터']}\n"
        indicator_summary += f"   - 사령관의 분석의미: {item['사령관_분석의미']}\n\n"

    prompt = f"""
    [명령] 사령관 lsj의 지휘소 분석 데이터 기반 통합 전략 수립
    
    현재 수집된 총 {total_count}개의 핵심 지표 데이터는 다음과 같다:
    {indicator_summary}
    
    [분석 요구사항]
    1. 수집된 모든 지표들 사이의 상관관계를 분석하여 현재 시장의 '절대적 국면'을 정의하라.
    2. 사령관이 직접 작성한 '분석의미'와 '실시간 수치'의 괴리를 찾아내어 기회 혹은 위기 요인을 도출하라.
    3. 3월 1일 미국 정책 이벤트 등 핵심 일정과 연계하여, 사령관이 지금 즉시 실행해야 할 3가지 우선 작전을 하달하라.
    4. 분석 내용 중 가장 상징적인 숫자가 있다면 이를 기반으로 작전명을 명명하라.
    """

    # 3. 차세대 엔진(Gemini 2.5) 교신 [cite: 2026-02-24]
    client = genai.Client(api_key=API_KEY)
    
    print(f"📡 {total_count}개의 지표를 Gemini 2.5 본부로 전송 중...")
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        report_content = response.text

        # 4. 출력 및 보고서 파일 저장 [cite: 2026-02-24]
        print("\n" + "═"*60)
        print(f"🛡️ [AEGIS 2.0 동적 전략 리포트 - 지표 {total_count}종]")
        print("═"*60)
        print(report_content)
        print("═"*60)

        filename = f"AEGIS_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"🛡️ AEGIS DYNAMIC REPORT - {datetime.now()}\n")
            f.write(f"Indicators Tracked: {total_count}\n")
            f.write("="*60 + "\n")
            f.write(report_content)
            f.write("\n" + "="*60 + "\n")
            f.write("System: MacBook Pro M5 | Processor: Gemini 2.5 Flash")

        print(f"\n✅ 작전 완료: {total_count}개 지표가 반영된 리포트가 '{filename}'으로 저장되었습니다.")

    except Exception as e:
        print(f"❌ AI 분석 중 치명적 오류: {e}")

if __name__ == "__main__":
    run_integrated_strategy()