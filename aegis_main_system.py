import os
import sys
import time
import datetime
import subprocess

def run_pipeline():
    start_time = time.time()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 1. 경로 자동 인식: 절대 경로 설정
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

    # 2. 실행 엔진 설정: 가상환경 파이썬 경로 고정
    PYTHON_EXEC = os.path.join(PROJECT_DIR, ".venv", "bin", "python")

    print(f"\n☀️ [AEGIS 3.0 일간 통합 파이프라인 가동] - {now_str}")
    print(f"📁 프로젝트 경로: {PROJECT_DIR}")
    print(f"🐍 파이썬 실행기: {PYTHON_EXEC}")
    print("="*65)

    # 3. 파일명 매칭: 실제 파일명 파이프라인 구성
    steps = [
        ("data_bank_builder.py", "[STEP 1] 최신 데이터 뱅크 업데이트 중..."),
        ("data_preprocessor.py", "[STEP 2] 데이터 전처리 및 라벨링 중..."),
        ("aegis_dnn_trainer.py", "[STEP 3] MPS 가속 기반 딥러닝 뇌 재설계 중..."),
        ("aegis_executor.py", "[STEP 4] 완성된 뇌를 통한 오늘의 확률 진단 중...")
    ]

    # 4. 실행 방식: subprocess.run + 절대 경로 + cwd 설정
    for script_file, step_msg in steps:
        print(f"\n{step_msg}")
        
        script_path = os.path.join(PROJECT_DIR, script_file)
        
        # 파일 존재 여부 확인
        if not os.path.exists(script_path):
            print(f"⚠️ 오류: {script_path} 파일을 찾을 수 없습니다.")
            return

        try:
            # subprocess.run 사용, cwd=PROJECT_DIR 로 설정하여 상대 경로 문제 해결
            result = subprocess.run([PYTHON_EXEC, script_path], cwd=PROJECT_DIR)

            if result.returncode != 0:
                print(f"⚠️ {script_file} 실행 중 오류 발생 (Exit Code: {result.returncode})")
                return # 중단
        except FileNotFoundError:
            print(f"⚠️ 실행 실패: {PYTHON_EXEC}을(를) 찾을 수 없습니다. 가상환경이 설정되어 있는지 확인하세요.")
            return
        except Exception as e:
            print(f"⚠️ 예기치 못한 오류 발생: {e}")
            return

    end_time = time.time()
    elapsed_minutes = (end_time - start_time) / 60

    print("\n=================================================================")
    print(f"✅ 모든 시스템이 성공적으로 완료되었습니다! (총 소요시간: {elapsed_minutes:.1f}분)")
    print("🎯 이제 구글 시트에서 AI의 '오늘자 성적표'를 확인하세요.")
    print("=================================================================")

    # 🌙 [자동 수면 모드] 완료 후 10초 대기 후 맥북 절전 모드 진입
    print("\n🌙 임무를 완수했습니다. 10초 뒤 맥북을 절전 모드(Sleep)로 전환합니다...")
    time.sleep(10)
    os.system("pmset sleepnow") # 애플 실리콘 맥북 강제 절전 모드 명령어

if __name__ == "__main__":
    run_pipeline()
