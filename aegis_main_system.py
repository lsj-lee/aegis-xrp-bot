import os
import sys
import time
import datetime
import subprocess
import argparse
import glob

# =============================================================================
# Configuration Constants
# =============================================================================
QUEUE_DIR = "evolution_queue"
PROPOSAL_SUFFIX = "_proposal.py"
# Relative path to the Python executable within the virtual environment
VENV_PYTHON_RELATIVE_PATH = os.path.join(".venv", "bin", "python")
MAC_SLEEP_COMMAND = "pmset sleepnow" # Command for macOS sleep mode
LINE_SEPARATOR = "=" * 65 # Consistent separator for console output

# =============================================================================
# Helper Functions
# =============================================================================
def check_pending_proposals():
    """
    Checks if there are pending proposals in the evolution queue directory.
    If proposals are found, it prints an informative message.
    """
    if os.path.exists(QUEUE_DIR):
        proposals = glob.glob(os.path.join(QUEUE_DIR, f"*{PROPOSAL_SUFFIX}"))
        if proposals:
            print(f"\n🚀 [시스템 진화 감지] {len(proposals)}개의 대기 중인 시스템 업데이트 제안이 있습니다!")
            print(f"👉 'python aegis_system_evolver.py --review' 명령어로 검토 및 승인하세요.")
            print("-" * 65)

def _execute_script(python_exec_path: str, script_path: str, project_dir: str, step_msg: str) -> bool:
    """
    Executes a given Python script as a subprocess.

    Args:
        python_exec_path (str): Absolute path to the Python executable.
        script_path (str): Absolute path to the script to be executed.
        project_dir (str): The current working directory for the subprocess.
        step_msg (str): Message to display before executing the script.

    Returns:
        bool: True if the script executed successfully, False otherwise.
    """
    print(f"\n{step_msg}")

    # Validate if the script file itself exists
    if not os.path.exists(script_path):
        print(f"⚠️ 오류: 스크립트 파일 '{script_path}'을(를) 찾을 수 없습니다. 파이프라인을 중단합니다.")
        return False

    try:
        # Before attempting to run, perform a basic check for the Python executable itself.
        # This helps provide a clearer error message early if the virtual environment is broken.
        if not os.path.exists(python_exec_path):
            print(f"⚠️ 실행 실패: 지정된 Python 실행기 '{python_exec_path}'을(를) 찾을 수 없습니다.")
            print("   가상 환경이 활성화되었거나, '.venv/bin/python' 경로가 올바른지 확인하세요.")
            return False

        # Execute the script using subprocess.run
        # cwd ensures that relative imports/paths within the child script work correctly
        # check=False allows us to manually handle the return code for custom error messages.
        result = subprocess.run(
            [python_exec_path, script_path],
            cwd=project_dir,
            check=False,
            text=True, # Capture stdout/stderr as text
            capture_output=True # Capture output for potential logging/debugging
        )

        if result.returncode != 0:
            print(f"⚠️ '{os.path.basename(script_path)}' 실행 중 오류 발생 (Exit Code: {result.returncode})")
            if result.stdout:
                print(f"--- STDOUT ---\n{result.stdout.strip()}")
            if result.stderr:
                print(f"--- STDERR ---\n{result.stderr.strip()}")
            return False
        
        # Optional: Print stdout/stderr even on success if needed for debugging
        # if result.stdout:
        #     print(f"--- Script Output ---\n{result.stdout.strip()}")

        return True

    except FileNotFoundError:
        # This specifically catches if the *command itself* (python_exec_path) wasn't found in PATH
        # or the provided path was completely wrong, even if os.path.exists passed.
        print(f"⚠️ 치명적 오류: Python 실행기 '{python_exec_path}'을(를) 찾을 수 없습니다.")
        print("   시스템 PATH에 없거나, 가상 환경 설정에 문제가 있을 수 있습니다. 경로를 다시 확인하세요.")
        return False
    except Exception as e:
        print(f"⚠️ 예기치 못한 오류 발생 ({os.path.basename(script_path)}): {e}")
        return False

# =============================================================================
# Main Pipeline Function
# =============================================================================
def run_pipeline(auto_sleep: bool = False):
    """
    Runs the AEGIS main system pipeline, executing a series of Python scripts
    in a defined order.
    """
    check_pending_proposals()

    start_time = time.time()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Determine the project's absolute directory
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    # Construct the absolute path to the Python executable in the virtual environment
    PYTHON_EXEC = os.path.join(PROJECT_DIR, VENV_PYTHON_RELATIVE_PATH)

    print(f"\n☀️ [AEGIS 3.0 일간 통합 파이프라인 가동] - {now_str}")
    print(f"📁 프로젝트 경로: {PROJECT_DIR}")
    print(f"🐍 파이썬 실행기: {PYTHON_EXEC}")
    print(f"💤 자동 수면 모드: {'ON' if auto_sleep else 'OFF'}")
    print(LINE_SEPARATOR)

    # Validate Python executable path early to prevent multiple errors later
    if not os.path.exists(PYTHON_EXEC):
        print(f"⚠️ 치명적 오류: 지정된 Python 실행기 '{PYTHON_EXEC}'을(를) 찾을 수 없습니다.")
        print("   가상 환경이 올바르게 설정되어 있는지 확인해주세요. 파이프라인을 시작할 수 없습니다.")
        print(LINE_SEPARATOR)
        return

    # Define the pipeline steps: (script_filename, descriptive_message)
    steps = [
        ("data_bank_builder.py", "[STEP 1] 최신 데이터 뱅크 업데이트 중..."),
        ("data_preprocessor.py", "[STEP 2] 데이터 전처리 및 라벨링 중..."),
        ("aegis_brain_trainer.py", "[STEP 3] MPS 가속 기반 딥러닝 뇌 재설계 중..."),
        ("aegis_system_evolver.py", "[STEP 3.5] 시스템 자가 진화 코드 제안 생성 중..."),
        ("aegis_automation.py", "[STEP 4] 완성된 뇌를 통한 오늘의 확률 진단 및 리포트 기록 중...")
    ]

    # Execute each step of the pipeline
    for script_file, step_msg in steps:
        script_path = os.path.join(PROJECT_DIR, script_file)
        
        # Use the helper function to execute the script and handle errors
        success = _execute_script(PYTHON_EXEC, script_path, PROJECT_DIR, step_msg)
        if not success:
            print(f"⚠️ 파이프라인이 '{script_file}' 단계에서 중단되었습니다.")
            print(LINE_SEPARATOR)
            return # Stop the entire pipeline on the first error

    # =========================================================================
    # Pipeline Completion Summary
    # =========================================================================
    end_time = time.time()
    elapsed_minutes = (end_time - start_time) / 60

    print(f"\n{LINE_SEPARATOR}")
    print(f"✅ 모든 시스템이 성공적으로 완료되었습니다! (총 소요시간: {elapsed_minutes:.1f}분)")
    print("🎯 이제 구글 시트에서 AI의 '오늘자 성적표'를 확인하세요.")
    print(f"{LINE_SEPARATOR}")

    # Handle automatic sleep mode if enabled
    if auto_sleep:
        print("\n🌙 임무를 완수했습니다. 10초 뒤 맥북을 절전 모드(Sleep)로 전환합니다...")
        time.sleep(10)
        os.system(MAC_SLEEP_COMMAND) # Execute macOS sleep command
    else:
        print("\n✨ 시스템이 종료되었습니다. (자동 수면 모드 미실행)")

# =============================================================================
# Main Execution Block
# =============================================================================
if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="AEGIS Main System Pipeline - Automates daily AI system operations."
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Enable automatic sleep mode for macOS after the pipeline completes."
    )
    parser.add_argument(
        "--sleep",
        action="store_true",
        help="Alias for --auto. Enable automatic sleep mode for macOS after the pipeline completes."
    )

    args = parser.parse_args()

    # Determine if sleep mode should be enabled based on any of the flags
    should_sleep = args.auto or args.sleep

    # Run the main pipeline
    run_pipeline(auto_sleep=should_sleep)