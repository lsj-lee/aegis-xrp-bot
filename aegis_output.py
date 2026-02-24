# 3단계: 최종 출력 공정 [cite: 2026-02-24]
from datetime import datetime

def save_and_report(ai_content):
    print("📋 [3단계] 최종 전략 보고서 생성 중...")
    
    # 1. 보고서 파일명 설정 (날짜 포함)
    filename = f"AEGIS_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    
    # 2. 파일 저장
    with open(filename, "w", encoding="utf-8") as f:
        f.write("="*60 + "\n")
        f.write(f"🛡️ AEGIS STRATEGY REPORT ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n")
        f.write("="*60 + "\n\n")
        f.write(ai_content)
        f.write("\n\n" + "="*60 + "\n")
        f.write("지휘관: lsj | 시스템: MacBook Pro M5 [cite: 2026-02-11]\n")
        f.write("="*60 + "\n")
        
    print(f"✅ 보고서 저장 완료: {filename}")
    print(f"📢 사령관님, 오늘의 분석 작전이 성공적으로 종료되었습니다.")

# 이 코드는 보통 2단계 코드(aegis_strategy_ai.py)의 마지막에서 호출됩니다.