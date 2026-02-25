import os
import subprocess
import time
from datetime import datetime

def run_operation(step_name, command):
    print(f"\n" + "="*50)
    print(f"🚀 {step_name} 개시...")
    print("="*50)
    
    start_time = time.time()
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {step_name} 성공!")
        print(result.stdout)
    else:
        print(f"❌ {step_name} 실패!")
        print(result.stderr)
        return False
        
    duration = time.time() - start_time
    print(f"⏱️ 소요 시간: {duration:.2f}초")
    return True

def main():
    print(f"🛡️ AEGIS 통합 지휘 시스템 실전 테스트 (시작 시간: {datetime.now().strftime('%H:%M:%S')})")
    
    if not run_operation("[1단계: M5 연산 기지 가동]", "python3 data_bank_builder.py"):
        print("🛑 1단계 오류로 인해 작전을 중단합니다.")
        return

    print("\n" + "📡 데이터 릴레이 대기 중 (3초)...")
    time.sleep(3)

    if not run_operation("[2단계: 클라우드 AI 본부 가동]", "python3 aegis_strategy_ai.py"):
        print("🛑 2단계 오류로 인해 작전을 중단합니다.")
        return

    print("\n" + "🏆" + "="*50)
    print("🎖️ 전면 실전 테스트 완료!")
    print("구글 시트를 확인하십시오.")
    print("="*50)

if __name__ == "__main__":
    main()