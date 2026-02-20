# TARGET: aegis_main_system.py
# AEGIS System v4.0.0 Unified Command
import os
import sys
import time
import datetime
import subprocess
import argparse
from pathlib import Path

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
    except Exception as e:
        # Log to stderr if file logging fails, but don't crash the main process.
        print(f"[{timestamp}] [ERROR] Failed to write to log file: {e}", file=sys.stderr)

def _execute_command(
    command: list[str | Path],
    description: str,
    cwd: Path | None = None,
    log_output_on_success: bool = False
) -> bool:
    """
    Executes a generic system or Python script command using subprocess.run,
    providing unified logging and robust error handling.

    Args:
        command (list[str | Path]): The command and its arguments as a list.
                                  Paths will be converted to strings before execution.
        description (str): A descriptive message for the command being executed.
        cwd (Path | None): The current working directory for the subprocess.
                           Defaults to None, meaning the current process's cwd.
        log_output_on_success (bool): If True, stdout/stderr are logged even on successful completion.

    Returns:
        bool: True if the command executed successfully, False otherwise.
    """
    # Convert all Path objects in the command list to strings for subprocess.run
    processed_command = [str(c) for c in command]
    cmd_str = ' '.join(processed_command)
    print_status(f"🛠️ {description} 실행 중: {cmd_str}")

    try:
        result = subprocess.run(
            processed_command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            print_status(f"⚠️ {description} 실패 (Exit Code: {result.returncode})", level="ERROR")
            if result.stdout:
                print_status(f"--- STDOUT ---\n{result.stdout.strip()}", level="ERROR")
            if result.stderr:
                print_status(f"--- STDERR ---\n{result.stderr.strip()}", level="ERROR")
            return False
        else:
            print_status(f"✅ {description} 성공.", level="INFO")
            if log_output_on_success and result.stdout:
                print_status(f"--- STDOUT ---\n{result.stdout.strip()}", level="DEBUG")
            return True
    except FileNotFoundError:
        print_status(f"⚠️ 명령어 '{processed_command[0]}'을(를) 찾을 수 없습니다. 경로 설정 또는 설치 여부를 확인하세요.", level="ERROR")
        return False
    except Exception as e:
        print_status(f"⚠️ 예기치 못한 오류 발생 ({description}): {e}", level="ERROR")
        return False

def check_pending_proposals():
    """
    Checks if there are pending proposals in the evolution queue directory.
    If found, prints a message with instructions for review and approval using print_status.
    """
    if EVOLUTION_QUEUE_DIR.exists() and EVOLUTION_QUEUE_DIR.is_dir():
        proposals = list(EVOLUTION_QUEUE_DIR.glob(PROPOSAL_FILE_PATTERN))
        if proposals:
            print_status(f"\n🚀 [시스템 진화 감지] {len(proposals)}개의 대기 중인 시스템 업데이트 제안이 있습니다!")
            print_status(f"👉 'python aegis_system_evolver.py --review' 명령어로 검토 및 승인하세요.")
            print_status("-" * 65)

def _enter_sleep_mode() -> bool:
    """
    Attempts to put the system into sleep mode if running on macOS.
    Uses the unified command execution function.
    """
    if sys.platform != "darwin":
        print_status("⚠️ 절전 모드는 macOS에서만 지원됩니다. 현재 운영체제에서 건너뜜.", level="WARNING")
        return False

    print_status(f"🌙 {SLEEP_WAIT_SECONDS}초 후 절전 모드로 진입합니다...")
    time.sleep(SLEEP_WAIT_SECONDS)
    
    # MAC_SLEEP_COMMAND is 'pmset sleepnow', which needs to be split for _execute_command
    return _execute_command(MAC_SLEEP_COMMAND.split(), "시스템 절전")

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

    print_status(f"\n☀️ [AEGIS 3.0 일간 통합 파이프라인 가동] - {now_str}")
    print_status(f"📁 프로젝트 경로: {PROJECT_ROOT}")
    print_status(f"🐍 파이썬 실행기: {PYTHON_EXEC}")
    print_status(f"💤 자동 수면 모드: {'ON' if auto_sleep else 'OFF'}")
    print_status("="*65)

    # Validate Python executable early to prevent later failures.
    if not PYTHON_EXEC.exists():
        print_status(f"❌ 오류: 지정된 파이썬 실행기 '{PYTHON_EXEC}'을(를) 찾을 수 없습니다.", level="ERROR")
        print_status("    가상 환경이 활성화되었는지, 또는 .venv 경로가 올바른지 확인하세요. 파이프라인 종료.", level="ERROR")
        sys.exit(1)
    if not PYTHON_EXEC.is_file():
        print_status(f"❌ 오류: '{PYTHON_EXEC}'은(는) 실행 가능한 파일이 아닙니다. 파이프라인 종료.", level="ERROR")
        sys.exit(1)

    # Execute each step in the predefined pipeline.
    for script_name, step_msg in PIPELINE_STEPS:
        script_path = PROJECT_ROOT / script_name
        
        # Validate script file existence before attempting to run it.
        if not script_path.exists():
            print_status(f"⚠️ 오류: {script_path} 파일을 찾을 수 없습니다. 파이프라인을 중단합니다.", level="ERROR")
            sys.exit(1)
        if not script_path.is_file():
            print_status(f"⚠️ 오류: {script_path}은(는) 파일이 아닙니다. 파이프라인을 중단합니다.", level="ERROR")
            sys.exit(1)

        print_status(f"\n{step_msg}") # Print step description
        command_to_run = [PYTHON_EXEC, script_path]
        
        if not _execute_command(command_to_run, f"파이프라인 단계: {script_name}", cwd=PROJECT_ROOT):
            print_status("\n❌ 파이프라인이 중간에 중단되었습니다. 문제 해결 후 다시 시도하세요.", level="ERROR")
            sys.exit(1)

    end_time = time.time()
    elapsed_minutes = (end_time - start_time) / 60

    print_status("\n=================================================================")
    print_status(f"✅ 모든 시스템이 성공적으로 완료되었습니다! (총 소요시간: {elapsed_minutes:.1f}분)")
    print_status("🎯 구글 시트 및 대시보드 데이터(aegis_dashboard_data.json) 업데이트 완료.")
    print_status("🖥️  'streamlit run aegis_dashboard.py' 명령어로 커맨드 센터를 실행하세요.")
    print_status("=================================================================")

    if auto_sleep:
        if not _enter_sleep_mode():
            print_status("⚠️ 자동 절전 모드 전환에 실패했습니다. 수동으로 전환해주세요.", level="WARNING")
    else:
        print_status("\n✨ 시스템이 종료되었습니다. (자동 수면 모드 미실행)")

def main():
    """
    Main entry point for the AEGIS system, handles argument parsing and pipeline execution.
    """
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

if __name__ == "__main__":
    main()