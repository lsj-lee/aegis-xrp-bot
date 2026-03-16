import subprocess
import time
from datetime import datetime
import os
import sys

def run_module(step_name, file_name):
    print(f"\n▶️ [{step_name}] 작전 개시: {file_name} 가동 중...")
    try:
        subprocess.run([sys.executable, file_name], check=True)
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

    pipeline = [
        ("0단계: 통합 문서(Docx) 지식 스캔 및 시트 장전", "aegis_doc_loader.py"),
        ("1단계: 다차원 데이터 수집 및 자가 치유", "aegis_collector.py"),
        ("2단계: M5 머신러닝 연산", "aegis_ml_engine.py"),
        ("3단계: 클라우드 동기화", "aegis_syncer.py"),
        ("4단계: 제2참모 (통찰 분석)", "aegis_agent_insight.py"),
        ("5단계: 제3참모 (논리 분석)", "aegis_agent_logic.py"),
        ("6단계: 수석 전략관 (최종 브리핑)", "aegis_strategy_final.py")
    ]

    for step_name, file_name in pipeline:
        if not os.path.exists(file_name):
            print(f"⚠️ [{file_name}] 파일 부재. 작전 중단.")
            return
            
        success = run_module(step_name, file_name)
        if not success:
            print("\n⚠️ 파이프라인 가동이 중단되었습니다.")
            return
        
        if "참모" in step_name or "전략관" in step_name:
            print("   ⏳ API 탄약(할당량) 보호를 위해 10초간 시스템을 냉각합니다...")
            time.sleep(10)
        else:
            time.sleep(2) 

    elapsed_time = datetime.now() - start_time
    print("\n" + "=" * 60)
    print(f"✨ [전 작전 성공] 모든 임무가 M5 기지에서 완벽히 수행되었습니다.")
    print(f"⏱️ 총 소요 시간: {elapsed_time}")
    print("=" * 60)

if __name__ == "__main__":
    main()