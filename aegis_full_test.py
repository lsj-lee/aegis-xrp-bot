import subprocess
import time
from datetime import datetime
import os
import sys

# 💾 파일 제목: aegis_full_test.py (마스터 관제탑 - 가상환경 최적화)
# 🚀 사유: 1단계 수집기부터 6단계 전략 도출까지 로컬 환경에서 일괄 실행 및 가상환경(venv) 강제 적용

def run_module(step_name, file_name):
    print(f"\n▶️ [{step_name}] 작전 개시: {file_name} 가동 중...")
    try:
        # sys.executable을 통해 현재 실행 중인 가상환경(.venv)의 파이썬을 정확히 타겟팅합니다.
        result = subprocess.run([sys.executable, file_name], check=True)
        print(f"   ✅ [{step_name}] 완료.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ [{step_name}] 실패! (에러 코드: {e.returncode})")
        print(f"   🚨 치명적 오류 발생. 작전을 즉각 중단합니다.")
        return False
    except FileNotFoundError:
        print(f"   ❌ [오류] {file_name} 파일을 찾을 수 없습니다.")
        return False

def main():
    start_time = datetime.now()
    print("=" * 60)
    print(f"🛡️ AEGIS 통합 지휘 통제소 (마스터 관제탑) 가동")
    print(f"📅 작전 개시 일시: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 🚀 파이프라인 실행 순서 정의 (수집기가 1단계로 포함됨)
    pipeline = [
        ("1단계: 다차원 데이터 수집/병합", "aegis_collector.py"),
        ("2단계: M5 머신러닝 연산", "aegis_ml_engine.py"),
        ("3단계: 클라우드 동기화", "aegis_syncer.py"),
        ("4단계: 제2참모 (통찰 분석)", "aegis_agent_insight.py"),
        ("5단계: 제3참모 (논리 분석)", "aegis_agent_logic.py"),
        ("6단계: 수석 전략관 (최종 브리핑)", "aegis_strategy_final.py")
    ]

    for step_name, file_name in pipeline:
        # 파일 존재 여부를 먼저 확인하여 불필요한 에러 방지
        if not os.path.exists(file_name):
            print(f"⚠️ [{file_name}] 파일이 현재 디렉토리에 없습니다. 작전을 중단합니다.")
            return
            
        success = run_module(step_name, file_name)
        if not success:
            print("\n⚠️ 파이프라인 가동이 중단되었습니다. 터미널 로그를 확인하십시오.")
            return
        
        # 각 모듈이 데이터를 안전하게 저장할 수 있도록 2초의 I/O 쿨다운 부여
        time.sleep(2) 

    end_time = datetime.now()
    elapsed_time = end_time - start_time
    print("\n" + "=" * 60)
    print(f"✨ [전 작전 성공] 모든 임무가 M5 연산 기지에서 완벽히 수행되었습니다.")
    print(f"⏱️ 총 소요 시간: {elapsed_time}")
    print("=" * 60)

if __name__ == "__main__":
    main()