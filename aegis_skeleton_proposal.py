# TARGET: aegis_main_system.py
# TARGET: aegis_main_system.py
import os
import sys
import time
import datetime
import subprocess
import argparse
import shutil

# --- 1. 전역 상수 정의 (Global Constants) ---
# Evolution Files
PROPOSAL_FILE = "aegis_skeleton_proposal.py"
BRIEFING_FILE = "aegis_briefing.md"
DEFAULT_TARGET_FILE = "aegis_main_system.py"

# Commands
VSCODE_COMMAND = "code"
GIT_COMMAND = "git"
GIT_ADD_ARGS = ["add", "."]
GIT_COMMIT_PREFIX = "Backup before AEGIS Evolution"
PMSET_SLEEP_COMMAND = "pmset sleepnow" # macOS specific command

# Messages
EVOLUTION_DETECTED_MSG = "🚀 [시스템 진화 감지] 새로운 시스템 업데이트 제안이 있습니다!"
BRIEFING_READ_MSG = "📄 [브리핑 파일 읽기] - {file}"
VISUAL_DIFF_MSG = "🖥️ VS Code를 실행하여 변경 사항을 비교합니다: {target_file} vs {proposal_file}"
VSCODE_NOT_FOUND_WARNING = "⚠️ 'code' 명령어를 찾을 수 없어 VS Code 비교를 건너뜁니다."
APPROVAL_PROMPT = "\n✅ 승인하시겠습니까? (y/n): "
INVALID_INPUT_WARNING = "⚠️ 잘못된 입력입니다."
UPDATE_START_MSG = "\n🔄 시스템 업데이트를 시작합니다..."
GIT_BACKUP_SUCCESS_MSG = "💾 현재 상태 Git 백업 완료."
GIT_BACKUP_FAILURE_WARNING = "⚠️ Git 백업 실패. 계속 진행합니다."
UPDATE_SUCCESS_MSG = "✅ {target_file} 업데이트 완료."
UPDATE_CRITICAL_ERROR_MSG = "❌ 업데이트 중 치명적 오류 발생: {e}"
RESTART_MSG = "🔄 시스템을 재시작합니다..."
DELETE_PROPOSAL_PROMPT = "🗑️ 제안 파일을 삭제하시겠습니까? (y/n): "
PROPOSAL_DELETED_MSG = "🗑️ 제안 파일이 삭제되었습니다."
PROPOSAL_KEPT_MSG = "🔒 제안 파일을 보존합니다."
READ_FILE_ERROR_MSG = "⚠️ 파일 읽기 실패 ({file}): {e}"
EXECUTION_FAILURE_MSG = "⚠️ 실행 실패: {executor}을(를) 찾을 수 없습니다. 가상환경이 설정되어 있는지 확인하세요."
UNEXPECTED_ERROR_MSG = "⚠️ 예기치 못한 오류 발생: {e}"
SCRIPT_NOT_FOUND_ERROR = "⚠️ 오류: {script_path} 파일을 찾을 수 없습니다."
SCRIPT_ERROR_MSG = "⚠️ {script_file} 실행 중 오류 발생 (Exit Code: {returncode})"
PIPELINE_SUCCESS_MSG = "✅ 모든 시스템이 성공적으로 완료되었습니다! (총 소요시간: {elapsed_minutes:.1f}분)"
AI_SCORE_CHECK_MSG = "🎯 이제 구글 시트에서 AI의 '오늘자 성적표'를 확인하세요."
AUTO_SLEEP_MSG = "\n🌙 임무를 완수했습니다. 10초 뒤 맥북을 절전 모드(Sleep)로 전환합니다..."
SYSTEM_EXIT_MSG = "\n✨ 시스템이 종료되었습니다. (자동 수면 모드 미실행)"

# --- 2. 로깅 헬퍼 함수 (Logging Helper Functions) ---
def _log_info(message):
    """일반 정보 메시지를 출력합니다."""
    print(message)

def _log_warning(message):
    """경고 메시지를 출력합니다."""
    print(message)

def _log_error(message):
    """오류 메시지를 출력합니다."""
    print(message, file=sys.stderr)

# --- 3. 시스템 진화 관련 헬퍼 함수 (Evolution Helper Functions) ---
def _read_evolution_metadata():
    """
    제안 및 브리핑 파일을 읽고, 타겟 파일 경로와 제안 내용을 추출합니다.
    Returns:
        tuple: (target_file_path, proposal_content, briefing_content) 또는 None (파일이 없거나 읽기 실패 시)
    """
    if not os.path.exists(PROPOSAL_FILE):
        return None

    _log_info(EVOLUTION_DETECTED_MSG)

    target_file = DEFAULT_TARGET_FILE
    proposal_content_lines = []
    briefing_content = ""

    try:
        with open(PROPOSAL_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines and lines[0].strip().startswith("# TARGET:"):
                target_file = lines[0].strip().split(":", 1)[1].strip()
                proposal_content_lines = lines[1:]
            else:
                proposal_content_lines = lines
    except Exception as e:
        _log_error(READ_FILE_ERROR_MSG.format(file=PROPOSAL_FILE, e=e))
        return None

    if os.path.exists(BRIEFING_FILE):
        try:
            _log_info(BRIEFING_READ_MSG.format(file=BRIEFING_FILE))
            _log_info("-" * 50)
            with open(BRIEFING_FILE, "r", encoding="utf-8") as f:
                briefing_content = f.read()
                _log_info(briefing_content)
            _log_info("-" * 50)
        except Exception as e:
            _log_warning(READ_FILE_ERROR_MSG.format(file=BRIEFING_FILE, e=e))

    return target_file, "".join(proposal_content_lines), briefing_content


def _perform_visual_diff(target_file, proposal_file):
    """VS Code를 사용하여 두 파일 간의 시각적 차이를 보여줍니다."""
    if shutil.which(VSCODE_COMMAND):
        _log_info(VISUAL_DIFF_MSG.format(target_file=target_file, proposal_file=proposal_file))
        try:
            subprocess.run([VSCODE_COMMAND, "--diff", target_file, proposal_file], check=False)
        except Exception as e:
            _log_warning(UNEXPECTED_ERROR_MSG.format(e=f"VS Code 실행 실패: {e}"))
    else:
        _log_warning(VSCODE_NOT_FOUND_WARNING)


def _confirm_action(prompt):
    """사용자에게 'y' 또는 'n' 입력을 받아 불리언 값을 반환합니다."""
    while True:
        choice = input(prompt).strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        else:
            _log_warning(INVALID_INPUT_WARNING)


def _backup_current_state(project_dir):
    """Git을 사용하여 현재 시스템 상태를 백업합니다."""
    try:
        # cwd를 PROJECT_DIR로 설정하여 .git 폴더를 찾도록 함
        subprocess.run([GIT_COMMAND] + GIT_ADD_ARGS, cwd=project_dir, check=False, capture_output=True)
        commit_message = f"{GIT_COMMIT_PREFIX} ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
        subprocess.run([GIT_COMMAND, "commit", "-m", commit_message], cwd=project_dir, check=False, capture_output=True)
        _log_info(GIT_BACKUP_SUCCESS_MSG)
        return True
    except Exception:
        # Git이 설치되지 않았거나, Git 저장소가 아니거나, 다른 오류가 발생해도 시스템 업데이트는 진행되어야 함.
        _log_warning(GIT_BACKUP_FAILURE_WARNING)
        return False


def _apply_evolution_update(target_file, proposal_content):
    """타겟 파일을 제안 내용으로 업데이트하고 제안 파일을 삭제합니다."""
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(proposal_content)
        _log_info(UPDATE_SUCCESS_MSG.format(target_file=target_file))

        if os.path.exists(PROPOSAL_FILE):
            os.remove(PROPOSAL_FILE)
        if os.path.exists(BRIEFING_FILE):
            os.remove(BRIEFING_FILE)
        return True
    except Exception as e:
        _log_error(UPDATE_CRITICAL_ERROR_MSG.format(e=e))
        return False


def _restart_system():
    """현재 스크립트를 재시작합니다."""
    _log_info(RESTART_MSG)
    os.execv(sys.executable, [sys.executable] + sys.argv)


def check_and_apply_evolution():
    """
    새로운 시스템 업데이트 제안을 확인하고, 사용자 승인 시 적용 후 시스템을 재시작합니다.
    """
    metadata = _read_evolution_metadata()
    if metadata is None:
        return # 제안 파일이 없거나 읽기 실패 시 진화 과정 스킵

    target_file, proposal_content, _ = metadata

    _perform_visual_diff(target_file, PROPOSAL_FILE)

    if _confirm_action(APPROVAL_PROMPT):
        _log_info(UPDATE_START_MSG)
        _backup_current_state(os.path.dirname(os.path.abspath(__file__))) # PROJECT_DIR 직접 전달

        if _apply_evolution_update(target_file, proposal_content):
            _restart_system()
        # _restart_system이 성공하면 이 아래 코드는 실행되지 않음
        # _apply_evolution_update 실패 시 False를 반환하고 함수 종료 (재시작 불가)
    else:
        if _confirm_action(DELETE_PROPOSAL_PROMPT):
            if os.path.exists(PROPOSAL_FILE): os.remove(PROPOSAL_FILE)
            if os.path.exists(BRIEFING_FILE): os.remove(BRIEFING_FILE)
            _log_info(PROPOSAL_DELETED_MSG)
        else:
            _log_info(PROPOSAL_KEPT_MSG)

# --- 4. 파이프라인 실행 헬퍼 함수 (Pipeline Execution Helper Function) ---
def _execute_pipeline_step(python_exec, script_path, cwd, step_msg, script_file_name):
    """
    단일 파이프라인 스크립트를 실행하고 결과를 보고합니다.
    Args:
        python_exec (str): 파이썬 실행기 경로.
        script_path (str): 실행할 스크립트의 전체 경로.
        cwd (str): 서브프로세스 실행 작업 디렉토리.
        step_msg (str): 해당 스텝에 대한 설명 메시지.
        script_file_name (str): 스크립트 파일 이름 (로그용).
    Returns:
        bool: 스크립트 실행 성공 여부.
    """
    _log_info(f"\n{step_msg}")
    
    if not os.path.exists(script_path):
        _log_error(SCRIPT_NOT_FOUND_ERROR.format(script_path=script_path))
        return False

    try:
        result = subprocess.run([python_exec, script_path], cwd=cwd, check=False) # check=False로 변경하여 returncode 직접 확인
        if result.returncode != 0:
            _log_error(SCRIPT_ERROR_MSG.format(script_file=script_file_name, returncode=result.returncode))
            return False
        return True
    except FileNotFoundError:
        _log_error(EXECUTION_FAILURE_MSG.format(executor=python_exec))
        return False
    except Exception as e:
        _log_error(UNEXPECTED_ERROR_MSG.format(e=e))
        return False

# --- 5. 메인 파이프라인 함수 (Main Pipeline Function) ---
def run_pipeline(auto_sleep=False):
    """
    AEGIS 시스템의 일간 통합 파이프라인을 실행합니다.
    Args:
        auto_sleep (bool): 파이프라인 완료 후 시스템을 절전 모드로 전환할지 여부.
    """
    check_and_apply_evolution()

    start_time = time.time()
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 경로 자동 인식: 절대 경로 설정
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

    # 실행 엔진 설정: 가상환경 파이썬 경로 고정 (macOS/Linux 기준)
    # Windows의 경우 .venv\Scripts\python.exe 로 변경 필요
    PYTHON_EXEC = os.path.join(PROJECT_DIR, ".venv", "bin", "python")

    _log_info(f"\n☀️ [AEGIS 3.0 일간 통합 파이프라인 가동] - {now_str}")
    _log_info(f"📁 프로젝트 경로: {PROJECT_DIR}")
    _log_info(f"🐍 파이썬 실행기: {PYTHON_EXEC}")
    _log_info(f"💤 자동 수면 모드: {'ON' if auto_sleep else 'OFF'}")
    _log_info("="*65)

    # 파일명 매칭: 실제 파일명 파이프라인 구성
    steps = [
        ("data_bank_builder.py", "[STEP 1] 최신 데이터 뱅크 업데이트 중..."),
        ("data_preprocessor.py", "[STEP 2] 데이터 전처리 및 라벨링 중..."),
        ("aegis_brain_trainer.py", "[STEP 3] MPS 가속 기반 딥러닝 뇌 재설계 중..."),
        ("aegis_system_evolver.py", "[STEP 3.5] 시스템 자가 진화 코드 제안 생성 중..."),
        ("aegis_automation.py", "[STEP 4] 완성된 뇌를 통한 오늘의 확률 진단 및 리포트 기록 중...")
    ]

    for script_file, step_msg in steps:
        script_path = os.path.join(PROJECT_DIR, script_file)
        if not _execute_pipeline_step(PYTHON_EXEC, script_path, PROJECT_DIR, step_msg, script_file):
            _log_error(f"❌ 파이프라인 '{script_file}' 스텝에서 오류가 발생하여 중단합니다.")
            return # 오류 발생 시 파이프라인 중단

    end_time = time.time()
    elapsed_minutes = (end_time - start_time) / 60

    _log_info("\n=================================================================")
    _log_info(PIPELINE_SUCCESS_MSG.format(elapsed_minutes=elapsed_minutes))
    _log_info(AI_SCORE_CHECK_MSG)
    _log_info("=================================================================")

    if auto_sleep:
        _log_info(AUTO_SLEEP_MSG)
        time.sleep(10)
        os.system(PMSET_SLEEP_COMMAND) # 애플 실리콘 맥북 강제 절전 모드 명령어
    else:
        _log_info(SYSTEM_EXIT_MSG)

# --- 6. 메인 실행 블록 (Main Execution Block) ---
def main():
    """
    AEGIS 시스템의 엔트리 포인트입니다.
    명령줄 인자를 파싱하고 파이프라인을 실행합니다.
    """
    parser = argparse.ArgumentParser(description="AEGIS Main System Pipeline")
    parser.add_argument("--auto", action="store_true", help="Automatically sleep after completion")
    parser.add_argument("--sleep", action="store_true", help="Alias for --auto")

    args = parser.parse_args()

    # --auto 또는 --sleep 플래그 중 하나라도 있으면 자동 수면 모드를 활성화
    should_sleep = args.auto or args.sleep

    run_pipeline(auto_sleep=should_sleep)

if __name__ == "__main__":
    main()