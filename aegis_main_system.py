import os
import sys
import time
import datetime
import subprocess
import argparse
from pathlib import Path

# --- Module-level Constants ---

# Core Paths Configuration
PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXEC = PROJECT_ROOT / ".venv" / "bin" / "python"

# Evolution System Configuration
EVOLUTION_QUEUE_DIR = PROJECT_ROOT / "evolution_queue"
PROPOSAL_FILE_PATTERN = "*_proposal.py"

# Sleep Mode Configuration (macOS specific)
SLEEP_WAIT_SECONDS = 10
# Changed to list for subprocess.run for robustness and security
MAC_SLEEP_COMMAND = ["pmset", "sleepnow"] 

# Pipeline Steps Configuration
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
    This consolidates logging output for consistency.
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level:<5}] {message}")

def check_pending_proposals():
    """
    Checks if there are pending proposals in the evolution queue directory.
    If found, prints a message with instructions for review and approval.
    """
    if EVOLUTION_QUEUE_DIR.exists() and EVOLUTION_QUEUE_DIR.is_dir():
        proposals = list(EVOLUTION_QUEUE_DIR.glob(PROPOSAL_FILE_PATTERN))
        if proposals:
            print_status(f"🚀 [시스템 진화 감지] {len(proposals)}개의 대기 중인 시스템 업데이트 제안이 있습니다!")
            print_status(f"👉 'python aegis_system_evolver.py --review' 명령어로 검토 및 승인하세요.")
            print("-" * 65)

def _execute_system_command(command: list[str], description: str) -> bool:
    """
    Executes a generic system command using subprocess.run.
    Replaces os.system for better control and error handling.
    
    Args:
        command (list[str]): The command and its arguments as a list.
        description (str): A descriptive message for the command being executed.

    Returns:
        bool: True if the command executed successfully, False otherwise.
    """
    print_status(f"🛠️ {description} 실행 중: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print_status(f"⚠️ {description} 실패 (Exit Code: {result.returncode})", level="ERROR")
            if result.stdout:
                print_status(f"--- STDOUT ---\n{result.stdout.strip()}", level="ERROR")
            if result.stderr:
                print_status(f"--- STDERR ---\n{result.stderr.strip()}", level="ERROR")
            return False
        else:
            print_status(f"✅ {description} 성공.")
            # For system commands, often stdout is empty on success or not critical to show.
            return True
    except FileNotFoundError:
        print_status(f"⚠️ 명령어 '{command[0]}'을(를) 찾을 수 없습니다. 경로 설정 또는 설치 여부를 확인하세요.", level="ERROR")
        return False
    except Exception as e:
        print_status(f"⚠️ 예기치 못한 오류 발생 ({description}): {e}", level="ERROR")
        return False

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
    print_status(f"\n{step_msg}")
    
    script_path = PROJECT_ROOT / script_name
    
    # Validate if the script file exists before attempting to run it.
    if not script_path.exists():
        print_status(f"⚠️ 오류: {script_path} 파일을 찾을 수 없습니다. 파이프라인을 중단합니다.", level="ERROR")
        return False
    if not script_path.is_file():
        print_status(f"⚠️ 오류: {script_path}은(는) 파일이 아닙니다. 파이프라인을 중단합니다.", level="ERROR")
        return False

    try:
        # Execute the script using subprocess.run.
        # - cwd=PROJECT_ROOT ensures that relative imports/paths within subprocesses work correctly.
        # - capture_output=True and text=True capture stdout/stderr as strings.
        # - check=False prevents CalledProcessError, allowing manual returncode check.
        command = [str(PYTHON_EXEC), str(script_path)]
        result = subprocess.run(
            command, 
            cwd=PROJECT_ROOT, 
            capture_output=True, 
            text=True, 
            check=False 
        )

        # Check the return code of the subprocess to determine success or failure.
        if result.returncode != 0:
            print_status(f"⚠️ {script_name} 실행 중 오류 발생 (Exit Code: {result.returncode})", level="ERROR")
            if result.stdout:
                print_status(f"--- {script_name} STDOUT ---\n{result.stdout.strip()}", level="ERROR")
            if result.stderr:
                print_status(f"--- {script_name} STDERR ---\n{result.stderr.strip()}", level="ERROR")
            print_status(" 파이프라인을 중단합니다.", level="ERROR")
            return False
        else:
            # For successful steps, we assume the sub-script handles its own informative output.
            # Printing captured stdout/stderr here would make the main script output very verbose.
            pass

    except FileNotFoundError:
        # This specific error indicates that PYTHON_EXEC itself could not be found.
        # This check should ideally be done once before the pipeline starts, but kept here as a fallback.
        print_status(f"⚠️ 실행 실패: '{PYTHON_EXEC}'을(를) 찾을 수 없습니다.", level="ERROR")
        print_status("    가상 환경이 설정되었는지 또는 '.venv' 경로가 올바른지 확인하세요. 파이프라인을 중단합니다.", level="ERROR")
        return False
    except Exception as e:
        # Catch any other unexpected errors during subprocess execution.
        print_status(f"⚠️ 예기치 못한 오류 발생 ({script_name}): {e}. 파이프라인을 중단합니다.", level="ERROR")
        return False
        
    return True # Step completed successfully

def run_pipeline(auto_sleep: bool = False):
    """
    Executes the main AEGIS system pipeline, orchestrating various AI operations.
    
    Args:
        auto_sleep (bool): If True, the system will attempt to enter sleep mode 
                           after successful pipeline completion.
    """
    start_time = time.time()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print_status(f"\n☀️ [AEGIS 3.0 일간 통합 파이프라인 가동] - {now_str}")
    print_status(f"📁 프로젝트 경로: {PROJECT_ROOT}")
    print_status(f"🐍 파이썬 실행기: {PYTHON_EXEC}")
    print_status(f"💤 자동 수면 모드: {'ON' if auto_sleep else 'OFF'}")
    print("="*65)

    # 1. Early validation for Python executable to prevent later failures.
    # This ensures the environment is correctly set up before starting any pipeline steps.
    if not PYTHON_EXEC.exists():
        print_status(f"❌ 오류: 지정된 파이썬 실행기 '{PYTHON_EXEC}'을(를) 찾을 수 없습니다.", level="CRITICAL")
        print_status("    가상 환경이 활성화되었는지, 또는 .venv 경로가 올바른지 확인하세요. 파이프라인 종료.", level="CRITICAL")
        sys.exit(1)
    if not PYTHON_EXEC.is_file():
        print_status(f"❌ 오류: '{PYTHON_EXEC}'은(는) 실행 가능한 파일이 아닙니다. 파이프라인 종료.", level="CRITICAL")
        sys.exit(1)

    # Check for pending proposals (moved after initial setup info)
    check_pending_proposals()

    # 2. Execute each step in the predefined pipeline.
    for script_name, step_msg in PIPELINE_STEPS:
        if not _execute_pipeline_step(script_name, step_msg):
            print_status("\n❌ 파이프라인이 중간에 중단되었습니다. 문제 해결 후 다시 시도하세요.", level="ERROR")
            sys.exit(1) # Exit with a non-zero code to indicate failure

    end_time = time.time()
    elapsed_minutes = (end_time - start_time) / 60

    print("\n=================================================================")
    print_status(f"✅ 모든 시스템이 성공적으로 완료되었습니다! (총 소요시간: {elapsed_minutes:.1f}분)")
    print_status("🎯 이제 구글 시트에서 AI의 '오늘자 성적표'를 확인하세요.")
    print("=================================================================")

    if auto_sleep:
        print_status(f"\n🌙 임무를 완수했습니다. {SLEEP_WAIT_SECONDS}초 뒤 맥북을 절전 모드(Sleep)로 전환합니다...")
        time.sleep(SLEEP_WAIT_SECONDS)
        # Use the new helper function for system commands
        if not _execute_system_command(MAC_SLEEP_COMMAND, "맥북 절전 모드 전환"):
            print_status("⚠️ 자동 절전 모드 전환에 실패했습니다. 수동으로 전환해주세요.", level="WARNING")
    else:
        print_status("\n✨ 시스템이 종료되었습니다. (자동 수면 모드 미실행)")

def main():
    """Main entry point for the AEGIS system, handles argument parsing and pipeline execution."""
    parser = argparse.ArgumentParser(
        description="AEGIS Main System Pipeline - Orchestrates daily AI operations."
    )
    # New argument for explicit sleep mode control, recommended for clarity.
    parser.add_argument(
        "--enable-sleep", 
        action="store_true", 
        help=f"Enables automatic sleep mode ({SLEEP_WAIT_SECONDS}s wait, then '{' '.join(MAC_SLEEP_COMMAND)}') after successful pipeline completion."
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

if __name__ == "__main__":
    main()