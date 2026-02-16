import os
import sys
import time
import datetime
import subprocess

def run_pipeline():
    start_time = time.time()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n☀️ [AEGIS 3.0 일간 통합 파이프라인 가동] - {now_str}")
    print("="*65)

    # 🚀 실행할 파이썬 파일들을 순서대로 리스트업 (함수 이름 몰라도 무조건 실행됨)
    steps = [
        ("[STEP 1] 최신 데이터 뱅크 업데이트 중...", "data_bank_builder.py"),
        ("[STEP 2] 데이터 전처리 및 라벨링 중...", "data_preprocessor.py"),
        ("[STEP 3] MPS 가속 기반 딥러닝 뇌 재설계 중...", "aegis_dnn_trainer.py"),
        ("[STEP 4] 완성된 뇌를 통한 오늘의 확률 진단 중...", "aegis_executor.py"),
        ("[STEP 5] 구글 시트(Cloud)에 분석 리포트 전송 중...", "aegis_automation.py")
    ]

    for step_msg, script_file in steps:
        print(f"\n{step_msg}")
        
        # 터미널에서 직접 실행하는 것과 완전히 동일한 방식 (독립 프로세스 실행)
        result = subprocess.run([sys.executable, script_file])
        
        # 만약 중간에 에러가 나면 다음 단계로 넘어가지 않고 즉시 중단
        if result.returncode != 0:
            print(f"⚠️ {script_file} 내부에서 치명적 오류가 발생하여 시스템을 긴급 정지합니다.")
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