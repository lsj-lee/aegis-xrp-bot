import os
import sys
import time
import datetime
import subprocess
import argparse
from pathlib import Path # New import for object-oriented path handling

# --- Module-level Constants ---
# Project root directory: Dynamically determined as the parent directory of this script.
PROJECT_ROOT = Path(__file__).resolve().parent

# Virtual environment Python executable path: Assumes a '.venv' directory at the project root.
PYTHON_EXEC = PROJECT_ROOT / ".venv" / "bin" / "python"

# Evolution queue directory and proposal file pattern.
EVOLUTION_QUEUE_DIR = PROJECT_ROOT / "evolution_queue"
PROPOSAL_FILE_PATTERN = "*_proposal.py"

# Sleep mode configuration specific to macOS.
SLEEP_WAIT_SECONDS = 10
MAC_SLEEP_COMMAND = "pmset sleepnow" 

# Pipeline steps configuration.
# Each tuple contains: (script_filename_relative_to_project_root, step_description).
PIPELINE_STEPS = [
    ("data_bank_builder.py", "[STEP 1] 최신 데이터 뱅크 업데이트 중..."),
    ("data_preprocessor.py", "[STEP 2] 데이터 전처리 및 라벨링 중..."),
    ("aegis_brain_trainer.py", "[STEP 3] MPS 가속 기반 딥러닝 뇌 재설계 중..."),
    ("aegis_system_evolver.py", "[STEP 3.5] 시스템 자가 진화 코드 제안 생성 중..."),
    ("aegis_automation.py", "[STEP 4] 완성된 뇌를 통한 오늘의 확률 진단 및 리포트 기록 중...")
]

def print_status(message: str, level: str = "INFO"):
    """
    Prints a formatted status message with a timestamp and level.
    This consolidates logging output for consistency and writes to a file.
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] [{level:<5}] {message}"
    print(log_line)

    try:
        with open("aegis_system.log", "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception:
        pass

def check_pending_proposals():
    """
    Checks if there are pending proposals in the evolution queue directory.
    If found, prints a message with instructions for review and approval.
    """
    if EVOLUTION_QUEUE_DIR.exists() and EVOLUTION_QUEUE_DIR.is_dir():
        # Use Path.glob() for a more pathlib-native way to find files
        proposals = list(EVOLUTION_QUEUE_DIR.glob(PROPOSAL_FILE_PATTERN))
        if proposals:
            print(f"\n🚀 [시스템 진화 감지] {len(proposals)}개의 대기 중인 시스템 업데이트 제안이 있습니다!")
            print(f"👉 'python aegis_system_evolver.py --review' 명령어로 검토 및 승인하세요.")
            print("-" * 65)

def _execute_pipeline_step(script_name: str, step_msg: str) -> bool:
    """
    Executes a single Python script as a subprocess for a pipeline step.
    Captures and prints subprocess stdout/stderr for better error diagnosis.

    Args:
        script_name (str): The name of the script file to execute (e.g., "data_bank_builder.py").
                           This name is relative to the PROJECT_ROOT.
        step_msg (str): The descriptive message for the current step.

    Returns:
        bool: True if the script executed successfully, False otherwise.
    """
    print(f"\n{step_msg}")
    
    script_path = PROJECT_ROOT / script_name
    
    # 1. Validate if the script file exists before attempting to run it.
    if not script_path.exists():
        print(f"⚠️ 오류: {script_path} 파일을 찾을 수 없습니다. 파이프라인을 중단합니다.")
        return False
    if not script_path.is_file():
        print(f"⚠️ 오류: {script_path}은(는) 파일이 아닙니다. 파이프라인을 중단합니다.")
        return False

    try:
        # 2. Execute the script using subprocess.run.
        #    - cwd=PROJECT_ROOT ensures that relative imports/paths within subprocesses work correctly.
        #    - capture_output=True and text=True capture stdout/stderr as strings.
        #    - check=False prevents CalledProcessError, allowing manual returncode check.
        result = subprocess.run(
            [str(PYTHON_EXEC), str(script_path)], 
            cwd=PROJECT_ROOT, 
            capture_output=True, 
            text=True, 
            check=False 
        )

        # 3. Check the return code of the subprocess to determine success or failure.
        if result.returncode != 0:
            print(f"⚠️ {script_name} 실행 중 오류 발생 (Exit Code: {result.returncode})")
            if result.stdout:
                print(f"--- {script_name} STDOUT ---")
                print(result.stdout.strip())
            if result.stderr:
                print(f"--- {script_name} STDERR ---")
                print(result.stderr.strip())
            print(" 파이프라인을 중단합니다.")
            return False
        else:
            # Optionally, print subprocess output even on success for detailed logs.
            # For this context, assuming successful subprocesses manage their own output,
            # so we only print their captured output on failure.
            # If full verbosity is desired, uncomment the following:
            # if result.stdout:
            #     print(f"--- {script_name} STDOUT ---")
            #     print(result.stdout.strip())
            pass

    except FileNotFoundError:
        # This specific error indicates that PYTHON_EXEC itself could not be found.
        print(f"⚠️ 실행 실패: '{PYTHON_EXEC}'을(를) 찾을 수 없습니다.")
        print("    가상 환경이 설정되었는지 또는 '.venv' 경로가 올바른지 확인하세요. 파이프라인을 중단합니다.")
        return False
    except Exception as e:
        # Catch any other unexpected errors during subprocess execution.
        print(f"⚠️ 예기치 못한 오류 발생 ({script_name}): {e}. 파이프라인을 중단합니다.")
        return False
        
    return True # Step completed successfully

def _enter_sleep_mode():
    """
    Attempts to put the system into sleep mode if running on macOS.
    Uses subprocess.run for better error handling than os.system.
    """
    if sys.platform == 'darwin': # Check if the operating system is macOS
        print(f"\n🌙 임무를 완수했습니다. {SLEEP_WAIT_SECONDS}초 뒤 맥북을 절전 모드(Sleep)로 전환합니다...")
        time.sleep(SLEEP_WAIT_SECONDS)
        try:
            # Use subprocess.run for better control and error handling
            # MAC_SLEEP_COMMAND is 'pmset sleepnow'
            result = subprocess.run(MAC_SLEEP_COMMAND.split(), check=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ 맥북이 성공적으로 절전 모드로 전환되었습니다.")
            else:
                print(f"⚠️ 맥북 절전 모드 전환 실패 (Exit Code: {result.returncode}).")
                if result.stderr:
                    print(f"   STDERR: {result.stderr.strip()}")
                print("   수동으로 전환해주세요.")
        except FileNotFoundError:
            print(f"⚠️ 'pmset' 명령어를 찾을 수 없습니다. macOS 환경이 아니거나, 'pmset'이 설치되지 않았을 수 있습니다. 수동으로 전환해주세요.")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ 맥북 절전 모드 전환 실패: 명령어 실행 중 오류 발생 (Exit Code: {e.returncode}).")
            if e.stderr:
                print(f"   STDERR: {e.stderr.strip()}")
            print("   수동으로 전환해주세요.")
        except Exception as e:
            print(f"⚠️ 예기치 못한 오류로 맥북 절전 모드 전환 실패: {e}. 수동으로 전환해주세요.")
    else:
        print("⚠️ 현재 운영체제는 macOS가 아닙니다. 절전 모드 기능을 건너뜝니다.")

def run_pipeline(auto_sleep: bool = False):
    """
    Executes the main AEGIS system pipeline, orchestrating various AI operations.
    
    Args:
        auto_sleep (bool): If True, the system will attempt to enter sleep mode 
                           after successful pipeline completion.
    """
    check_pending_proposals() # Check for pending system evolution proposals

    start_time = time.time()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n☀️ [AEGIS 3.0 일간 통합 파이프라인 가동] - {now_str}")
    print(f"📁 프로젝트 경로: {PROJECT_ROOT}")
    print(f"🐍 파이썬 실행기: {PYTHON_EXEC}")
    print(f"💤 자동 수면 모드: {'ON' if auto_sleep else 'OFF'}")
    print("="*65)

    # Validate Python executable early to prevent later failures.
    if not PYTHON_EXEC.exists():
        print(f"❌ 오류: 지정된 파이썬 실행기 '{PYTHON_EXEC}'을(를) 찾을 수 없습니다.")
        print("    가상 환경이 활성화되었는지, 또는 .venv 경로가 올바른지 확인하세요. 파이프라인 종료.")
        sys.exit(1) # Exit with an error code
    if not PYTHON_EXEC.is_file():
        print(f"❌ 오류: '{PYTHON_EXEC}'은(는) 실행 가능한 파일이 아닙니다. 파이프라인 종료.")
        sys.exit(1) # Exit with an error code

    # 4. Execute each step in the predefined pipeline.
    for script_name, step_msg in PIPELINE_STEPS:
        if not _execute_pipeline_step(script_name, step_msg):
            print("\n❌ 파이프라인이 중간에 중단되었습니다. 문제 해결 후 다시 시도하세요.")
            sys.exit(1) # Exit with a non-zero code to indicate failure

    end_time = time.time()
    elapsed_minutes = (end_time - start_time) / 60

    print("\n=================================================================")
    print(f"✅ 모든 시스템이 성공적으로 완료되었습니다! (총 소요시간: {elapsed_minutes:.1f}분)")
    print("🎯 이제 구글 시트에서 AI의 '오늘자 성적표'를 확인하세요.")
    print("=================================================================")

    if auto_sleep:
        _enter_sleep_mode()
    else:
        print("\n✨ 시스템이 종료되었습니다. (자동 수면 모드 미실행)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AEGIS Main System Pipeline - Orchestrates daily AI operations."
    )
    # New argument for explicit sleep mode control, recommended for clarity.
    parser.add_argument(
        "--enable-sleep", 
        action="store_true", 
        help=f"Enables automatic sleep mode ({SLEEP_WAIT_SECONDS}s wait, then '{MAC_SLEEP_COMMAND}') after successful pipeline completion."
    )
    # Existing arguments for backward compatibility, suppressed from help message.
    parser.add_argument(
        "--auto", 
        action="store_true", 
        help=argparse.SUPPRESS # Hides this argument from the --help output
    )
    parser.add_argument(
        "--sleep", 
        action="store_true", 
        help=argparse.SUPPRESS # Hides this argument from the --help output
    )

    args = parser.parse_args()

    # Determine if sleep mode should be enabled. Prioritizes --enable-sleep, 
    # but falls back to --auto or --sleep for backward compatibility.
    should_sleep = args.enable_sleep or args.auto or args.sleep

    run_pipeline(auto_sleep=should_sleep)