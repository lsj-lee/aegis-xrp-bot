import os
import sys
import time
import datetime
import subprocess
import argparse
import shutil

def check_and_apply_evolution():
    PROPOSAL_FILE = "aegis_skeleton_proposal.py"
    BRIEFING_FILE = "aegis_briefing.md"

    if os.path.exists(PROPOSAL_FILE):
        print("\n🚀 [시스템 진화 감지] 새로운 시스템 업데이트 제안이 있습니다!")

        target_file = "aegis_main_system.py" # Default
        try:
            with open(PROPOSAL_FILE, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line.startswith("# TARGET:"):
                    target_file = first_line.split(":", 1)[1].strip()
        except Exception as e:
            print(f"⚠️ 제안 파일 읽기 실패: {e}")
            return

        if os.path.exists(BRIEFING_FILE):
            print(f"\n📄 [브리핑 파일 읽기] - {BRIEFING_FILE}")
            print("-" * 50)
            with open(BRIEFING_FILE, "r", encoding="utf-8") as f:
                print(f.read())
            print("-" * 50)

        # Visual Diff
        if shutil.which("code"):
            print(f"🖥️ VS Code를 실행하여 변경 사항을 비교합니다: {target_file} vs {PROPOSAL_FILE}")
            try:
                subprocess.run(["code", "--diff", target_file, PROPOSAL_FILE])
            except Exception as e:
                print(f"⚠️ VS Code 실행 실패: {e}")
        else:
            print("⚠️ 'code' 명령어를 찾을 수 없어 VS Code 비교를 건너뜁니다.")

        while True:
            choice = input("\n✅ 승인하시겠습니까? (y/n): ").strip().lower()
            if choice == 'y':
                print("\n🔄 시스템 업데이트를 시작합니다...")

                try:
                    subprocess.run(["git", "add", "."], check=False)
                    subprocess.run(["git", "commit", "-m", f"Backup before AEGIS Evolution ({datetime.datetime.now()})"], check=False)
                    print("💾 현재 상태 Git 백업 완료.")
                except Exception:
                    print("⚠️ Git 백업 실패. 계속 진행합니다.")

                try:
                    with open(PROPOSAL_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    if lines and lines[0].startswith("# TARGET:"):
                        new_code = "".join(lines[1:])
                    else:
                        new_code = "".join(lines)

                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(new_code)

                    print(f"✅ {target_file} 업데이트 완료.")

                    if os.path.exists(PROPOSAL_FILE): os.remove(PROPOSAL_FILE)
                    if os.path.exists(BRIEFING_FILE): os.remove(BRIEFING_FILE)

                    print("🔄 시스템을 재시작합니다...")
                    os.execv(sys.executable, [sys.executable] + sys.argv)

                except Exception as e:
                    print(f"❌ 업데이트 중 치명적 오류 발생: {e}")
                    return

            elif choice == 'n':
                del_choice = input("🗑️ 제안 파일을 삭제하시겠습니까? (y/n): ").strip().lower()
                if del_choice == 'y':
                    if os.path.exists(PROPOSAL_FILE): os.remove(PROPOSAL_FILE)
                    if os.path.exists(BRIEFING_FILE): os.remove(BRIEFING_FILE)
                    print("🗑️ 제안 파일이 삭제되었습니다.")
                else:
                    print("🔒 제안 파일을 보존합니다.")
                break
            else:
                print("⚠️ 잘못된 입력입니다.")

def run_pipeline(auto_sleep=False):
    check_and_apply_evolution()

    start_time = time.time()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 1. 경로 자동 인식: 절대 경로 설정
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

    # 2. 실행 엔진 설정: 가상환경 파이썬 경로 고정
    PYTHON_EXEC = os.path.join(PROJECT_DIR, ".venv", "bin", "python")

    print(f"\n☀️ [AEGIS 3.0 일간 통합 파이프라인 가동] - {now_str}")
    print(f"📁 프로젝트 경로: {PROJECT_DIR}")
    print(f"🐍 파이썬 실행기: {PYTHON_EXEC}")
    print(f"💤 자동 수면 모드: {'ON' if auto_sleep else 'OFF'}")
    print("="*65)

    # 3. 파일명 매칭: 실제 파일명 파이프라인 구성
    steps = [
        ("data_bank_builder.py", "[STEP 1] 최신 데이터 뱅크 업데이트 중..."),
        ("data_preprocessor.py", "[STEP 2] 데이터 전처리 및 라벨링 중..."),
        ("aegis_brain_trainer.py", "[STEP 3] MPS 가속 기반 딥러닝 뇌 재설계 중..."),
        ("aegis_automation.py", "[STEP 4] 완성된 뇌를 통한 오늘의 확률 진단 및 리포트 기록 중...")
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

    if auto_sleep:
        # 🌙 [자동 수면 모드] 완료 후 10초 대기 후 맥북 절전 모드 진입
        print("\n🌙 임무를 완수했습니다. 10초 뒤 맥북을 절전 모드(Sleep)로 전환합니다...")
        time.sleep(10)
        os.system("pmset sleepnow") # 애플 실리콘 맥북 강제 절전 모드 명령어
    else:
        print("\n✨ 시스템이 종료되었습니다. (자동 수면 모드 미실행)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AEGIS Main System Pipeline")
    parser.add_argument("--auto", action="store_true", help="Automatically sleep after completion")
    parser.add_argument("--sleep", action="store_true", help="Alias for --auto")

    args = parser.parse_args()

    # Enable sleep mode if either flag is present
    should_sleep = args.auto or args.sleep

    run_pipeline(auto_sleep=should_sleep)
