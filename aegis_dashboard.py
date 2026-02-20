import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
import subprocess
import shutil
import numpy as np
import requests
import json
import datetime
import re

# --- [페이지 설정: 넓은 화면 모드] ---
st.set_page_config(
    page_title="AEGIS 통합 커맨드 센터",
    page_icon="🛡️",
    layout="wide"
)

# --- [전역 상수] ---
CONFIG_FILE = ".aegis_config.json"
COMMAND_IMAGES_DIR = "command_images"
USER_REQUESTS_FILE = "user_requests.txt"

# --- [스타일링: 다크 테마 및 커스텀 CSS] ---
st.markdown("""
    <style>
    .stMetric { background-color: #111827; padding: 20px; border-radius: 15px; border: 1px solid #374151; color: white; }
    .main { background-color: #030712; }
    div[data-testid="stSidebar"] { background-color: #111827; }
    h1, h2, h3 { color: #E5E7EB !important; }
    p, label { color: #9CA3AF !important; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- [설정 저장 및 불러오기 (Persistence)] ---
def load_config():
    """설정 파일(.aegis_config.json)에서 GitHub 정보를 불러옴"""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"설정 로드 중 오류: {str(e)}")
        return {}

def save_config(owner, repo, token):
    """GitHub 정보를 설정 파일에 저장"""
    data = {
        "github_owner": owner,
        "github_repo": repo,
        "github_token": token
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True, "설정이 성공적으로 저장되었습니다."
    except Exception as e:
        return False, f"설정 저장 실패: {str(e)}"

# --- [Git 자동화 유틸리티] ---
def git_push_changes(files_to_add, commit_message):
    """
    지정된 파일들을 git add, commit, push 합니다.
    :param files_to_add: 리스트 형태의 파일 경로 (예: ['user_requests.txt', 'command_images/'])
    :param commit_message: 커밋 메시지
    """
    logs = []
    try:
        # 1. Add
        subprocess.run(["git", "add"] + files_to_add, check=True, capture_output=True, text=True)
        logs.append(f"Git Add: {files_to_add}")

        # 2. Commit
        subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True, text=True)
        logs.append(f"Git Commit: {commit_message}")

        # 3. Push
        result = subprocess.run(["git", "push"], check=True, capture_output=True, text=True)
        logs.append("Git Push: Success")
        return True, "\n".join(logs)

    except subprocess.CalledProcessError as e:
        # Commit 할 것이 없는 경우 (Clean working tree) 등
        if "nothing to commit" in str(e.stdout) or "nothing to commit" in str(e.stderr):
             return True, "변경 사항이 없어 커밋하지 않았습니다."
        return False, f"Git 명령 오류: {e.stderr if e.stderr else str(e)}"
    except Exception as e:
        return False, f"Git 실행 중 오류: {str(e)}"

# --- [GitHub API 유틸리티 함수] ---
def get_github_repo_info():
    """git remote 명령어로 현재 리포지토리 정보 (owner, repo) 추출"""
    try:
        result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        if result.returncode == 0:
            url = result.stdout.strip()
            # SSH URL 처리 (git@github.com:owner/repo.git)
            if url.startswith("git@"):
                parts = url.split(":")[-1].replace(".git", "").split("/")
                if len(parts) >= 2:
                    return parts[-2], parts[-1]
            # HTTPS URL 처리 (https://github.com/owner/repo.git)
            elif url.startswith("http"):
                parts = url.replace(".git", "").split("/")
                if len(parts) >= 2:
                    return parts[-2], parts[-1]
    except Exception:
        pass
    return "lsj-lee", "aegis-xrp-bot"  # 기본값

def fetch_prs(owner, repo, token):
    """GitHub API를 통해 열린 PR 목록 조회"""
    if not token:
        return [], "GitHub Token이 필요합니다."

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json(), None
        else:
            return [], f"GitHub API 오류: {response.status_code} - {response.text}"
    except Exception as e:
        return [], str(e)

def merge_pr(owner, repo, pr_number, token):
    """GitHub API를 통해 PR 병합 (Merge)"""
    if not token:
        return False, "GitHub Token이 필요합니다."

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/merge"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    payload = {"commit_title": f"Merge pull request #{pr_number} from dashboard", "merge_method": "merge"}
    try:
        response = requests.put(url, headers=headers, json=payload)
        if response.status_code == 200:
            return True, "병합 성공!"
        else:
            return False, f"병합 실패: {response.status_code} - {response.text}"
    except Exception as e:
        return False, str(e)

def create_pr_from_changes(owner, repo, token, files_to_add, commit_msg, pr_title, pr_body):
    """
    새로운 브랜치를 생성하고 변경사항을 커밋/푸시한 후 PR을 생성합니다.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"cmd/order-{timestamp}"
    original_branch = "main" # Default fallback

    try:
        # 0. 현재 브랜치 확인
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
        if res.returncode == 0:
            original_branch = res.stdout.strip()

        # 1. 브랜치 생성 및 이동
        subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True, text=True)

        # 2. Add & Commit
        subprocess.run(["git", "add"] + files_to_add, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True, text=True)

        # 3. Push
        subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True, text=True)

        # 4. PR 생성 API 호출
        # 기본 브랜치 확인
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        default_branch = "main"
        try:
            repo_info = requests.get(repo_url, headers=headers).json()
            default_branch = repo_info.get("default_branch", "main")
        except:
            pass

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        payload = {
            "title": pr_title,
            "body": pr_body,
            "head": branch_name,
            "base": default_branch
        }

        resp = requests.post(url, headers=headers, json=payload)

        # 5. 원래 브랜치 복귀
        subprocess.run(["git", "checkout", original_branch], check=True, capture_output=True, text=True)

        if resp.status_code == 201:
            pr_data = resp.json()
            return True, f"PR 생성 성공: #{pr_data['number']} {pr_data['html_url']}"
        else:
            return False, f"PR 생성 실패 ({resp.status_code}): {resp.text}"

    except Exception as e:
        # 오류 발생 시 원래 브랜치로 복구 시도
        subprocess.run(["git", "checkout", original_branch], capture_output=True, text=True)
        return False, f"PR 프로세스 중 오류: {str(e)}"

def save_user_request(request_text, image_filename=None, create_pr=False, gh_config=None):
    """사용자 요청사항을 파일에 저장하고 Git Push 또는 PR 생성 수행"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {request_text}"
    if image_filename:
        entry += f" [첨부 이미지: {image_filename}]"
    entry += "\n"

    try:
        # 파일 저장
        with open(USER_REQUESTS_FILE, "a", encoding="utf-8") as f:
            f.write(entry)

        files_to_sync = [USER_REQUESTS_FILE]
        if image_filename:
            files_to_sync.append(COMMAND_IMAGES_DIR)

        # PR 생성 모드
        if create_pr and gh_config and gh_config.get("token"):
             return create_pr_from_changes(
                gh_config["owner"],
                gh_config["repo"],
                gh_config["token"],
                files_to_sync,
                f"Command: {request_text[:30]}...",
                f"Commander Order: {request_text[:30]}...",
                f"Request Details:\n{request_text}"
             )

        # 기존 직접 Push 모드
        success, msg = git_push_changes(files_to_sync, f"Command: {request_text[:30]}...")

        if success:
             return True, "명령 저장 및 Git Push 완료"
        else:
             return True, f"명령은 저장되었으나 Git Push 실패: {msg}"

    except Exception as e:
        return False, f"저장 중 오류: {str(e)}"

# --- [스케줄링 유틸리티 함수] ---
def get_current_crontab():
    """현재 crontab 내용을 문자열 리스트로 반환"""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.splitlines()
        else:
            return [] # crontab이 없거나 권한 오류 시 빈 리스트 반환
    except FileNotFoundError:
        return []

def update_crontab(new_lines):
    """새로운 crontab 내용을 적용"""
    cron_content = "\n".join(new_lines) + "\n"
    try:
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=cron_content)
        if process.returncode == 0:
            return True, "스케줄이 성공적으로 업데이트되었습니다."
        else:
            return False, f"스케줄 업데이트 실패: {stderr.strip()}"
    except Exception as e:
        return False, f"오류 발생: {str(e)}"

def get_aegis_jobs():
    """# AEGIS-JOB 주석이 있는 작업만 추출"""
    lines = get_current_crontab()
    jobs = []
    for line in lines:
        if "# AEGIS-JOB" in line:
            parts = line.split()
            schedule = " ".join(parts[:5])
            command = " ".join(parts[5:]).replace(" # AEGIS-JOB", "")
            jobs.append({"schedule": schedule, "command": command})
    return jobs

def add_aegis_job(cron_schedule, script_path="aegis_main_system.py"):
    """새로운 AEGIS 작업을 crontab에 추가"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    python_exec = sys.executable

    # 절대 경로로 명령어 구성
    cmd = f"cd {project_root} && {python_exec} {script_path} --enable-sleep >> {project_root}/aegis_cron.log 2>&1"
    new_line = f"{cron_schedule} {cmd} # AEGIS-JOB"

    lines = get_current_crontab()
    lines.append(new_line)

    return update_crontab(lines)

def clear_aegis_jobs():
    """모든 AEGIS 작업을 crontab에서 삭제"""
    lines = get_current_crontab()
    new_lines = [line for line in lines if "# AEGIS-JOB" not in line]
    return update_crontab(new_lines)


# --- [더미 데이터 생성 함수 (안전장치)] ---
def create_dummy_data(days=100):
    """데이터 로드 실패 시 UI 확인을 위한 더미 데이터를 생성합니다."""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq='D')

    # 랜덤 워크 가격 생성
    base_price = 1000
    changes = np.random.randn(days) * 10
    closes = base_price + np.cumsum(changes)

    data = {
        'timestamp': dates,
        'open': closes + np.random.randn(days) * 5,
        'high': closes + np.abs(np.random.randn(days) * 10),
        'low': closes - np.abs(np.random.randn(days) * 10),
        'close': closes,
        'volume': np.random.randint(1000, 50000, size=days),
        'prob': np.random.uniform(40, 90, size=days)
    }

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df

# --- [데이터 로드 함수] ---
@st.cache_data
def load_data():
    file_path = 'historical_data_3y.csv'

    # 레거시 경로 확인 (업데이트 후 복사되지 않았을 경우 대비)
    legacy_path = os.path.expanduser("~/Desktop/xrp_research/historical_data_3y.csv")

    # [수정] os.path.samefile을 사용하여 안전하게 파일 비교 및 복사
    try:
        if os.path.exists(legacy_path):
             # 대상 파일이 없거나, 있는데 서로 다른 파일인 경우 복사 시도
             should_copy = False
             if not os.path.exists(file_path):
                 should_copy = True
             else:
                 try:
                     if not os.path.samefile(legacy_path, file_path):
                         should_copy = True
                 except OSError:
                     # 파일 접근 권한 등의 문제로 비교 불가 시 안전하게 복사 시도
                     should_copy = True

             if should_copy:
                 shutil.copy(legacy_path, file_path)
    except Exception:
        pass # 복사 실패해도 로컬 파일 로드 시도

    if not os.path.exists(file_path):
        return None, f"파일을 찾을 수 없습니다: {file_path}"

    try:
        # CSV 읽기
        df = pd.read_csv(file_path)

        # 1. 컬럼명 소문자 변환 및 공백 제거 (핵심 로직)
        df.columns = df.columns.str.strip().str.lower()

        # 2. 날짜 컬럼 처리 ('date' -> 'timestamp'로 통일)
        if 'date' in df.columns and 'timestamp' not in df.columns:
            df.rename(columns={'date': 'timestamp'}, inplace=True)

        # [수정] 'xrp' 컬럼이 있으면 'close'로 인식
        if 'xrp' in df.columns:
            df.rename(columns={'xrp': 'close'}, inplace=True)

        # [수정] open, high, low 컬럼이 없으면 close 값으로 채움
        if 'close' in df.columns:
            for col in ['open', 'high', 'low']:
                if col not in df.columns:
                    df[col] = df['close']

        # [수정] volume 컬럼이 없으면 0으로 채움
        if 'volume' not in df.columns:
            df['volume'] = 0

        # 3. 필수 컬럼 확인 (최소한 timestamp와 close는 있어야 함)
        required_cols = ['timestamp', 'close']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            current_cols = list(df.columns)
            return None, f"필수 컬럼 누락: {missing_cols}. 현재 컬럼: {current_cols}"

        # 4. 인덱스 설정 및 날짜 파싱
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        # 5. 'prob' (예측 확률) 컬럼 처리
        if 'prob' not in df.columns:
            df['prob'] = 50 + (df['close'].pct_change().fillna(0) * 1000)
            df['prob'] = df['prob'].clip(0, 100)

        return df, None

    except Exception as e:
        return None, f"데이터 로드 중 치명적 오류: {str(e)}"

# --- [업데이트 센터 로직] ---
def run_update_process(update_code, update_data, update_model):
    logs = []

    # 1. 시스템 코드 업데이트
    if update_code:
        try:
            result = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True)
            if result.returncode == 0:
                logs.append(f"✅ 코드 업데이트 성공: {result.stdout.strip()}")
            else:
                logs.append(f"❌ 코드 업데이트 실패: {result.stderr.strip()}")
        except Exception as e:
            logs.append(f"❌ 코드 업데이트 오류: {str(e)}")

    # 2. 시세 데이터 업데이트
    if update_data:
        try:
            # data_bank_builder.py 실행
            result = subprocess.run([sys.executable, "data_bank_builder.py"], capture_output=True, text=True)
            if result.returncode == 0:
                logs.append("✅ 데이터 수집 스크립트 실행 완료.")

                # 레거시 경로에서 현재 디렉토리로 복사 시도
                legacy_path = os.path.expanduser("~/Desktop/xrp_research/historical_data_3y.csv")
                local_path = "historical_data_3y.csv"

                # [수정] SameFileError 방지 및 os.path.samefile 사용
                if os.path.exists(legacy_path):
                    try:
                        # 파일이 존재하고 서로 다른 파일인 경우에만 복사
                        if not os.path.exists(local_path) or not os.path.samefile(legacy_path, local_path):
                             shutil.copy(legacy_path, local_path)
                             logs.append(f"✅ 데이터 파일 동기화 완료: {legacy_path} -> {local_path}")
                        else:
                             logs.append("ℹ️ 데이터 파일이 이미 최신 위치에 있습니다 (동일 파일).")
                    except Exception as copy_err:
                        logs.append(f"❌ 파일 복사 중 오류: {str(copy_err)}")
                elif os.path.exists(local_path):
                    logs.append("ℹ️ 데이터 파일이 현재 디렉토리에 이미 존재합니다 (레거시 경로 미발견).")
                else:
                    logs.append("⚠️ 데이터 수집은 완료되었으나 결과 파일을 찾을 수 없습니다.")
            else:
                logs.append(f"❌ 데이터 수집 실패: {result.stderr.strip()}")
        except Exception as e:
            logs.append(f"❌ 데이터 업데이트 오류: {str(e)}")

    # 3. AI 모델 가중치 업데이트
    if update_model:
        try:
            if os.path.exists("aegis_brain.pth"):
                logs.append("ℹ️ AI 모델 파일(aegis_brain.pth)이 존재합니다. (Git Pull로 최신화되었을 수 있음)")
            else:
                logs.append("⚠️ AI 모델 파일을 찾을 수 없습니다. (Git Pull로 가져오지 못함)")
        except Exception as e:
            logs.append(f"❌ 모델 확인 중 오류: {str(e)}")

    return logs

# --- [메인 로직] ---
def main():
    try:
        st.sidebar.title("🛡️ AEGIS SYSTEM")

        # 사이드바 메뉴 선택
        menu = st.sidebar.radio("메뉴 선택", ["대시보드", "통합 커맨드 센터", "예약 및 스케줄 관리"])

        # [수정] ⚡ 실전 지휘 센터 (최상단)
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚡ 실전 지휘 센터")

        # 1. 즉시 분석 시작 버튼 (백그라운드 실행)
        if st.sidebar.button("🚀 즉시 분석 시작", use_container_width=True):
             with st.sidebar.status("작전 수행 중... (분석 엔진 가동)", expanded=True) as status:
                 try:
                     # aegis_automation.py 실행 (Blocking Call for UX feedback)
                     process = subprocess.run([sys.executable, "aegis_automation.py"], capture_output=True, text=True)
                     if process.returncode == 0:
                         st.sidebar.success("✅ 분석 및 보고 완료!")
                         with st.sidebar.expander("결과 로그 보기"):
                             st.code(process.stdout)
                     else:
                         st.sidebar.error("❌ 분석 실패")
                         with st.sidebar.expander("오류 로그 보기"):
                             st.code(process.stderr)
                 except Exception as e:
                     st.sidebar.error(f"실행 오류: {e}")
                 status.update(label="작전 종료", state="complete")

        # 2. 시스템 업데이트 실행 버튼 (PR 존재 여부에 따른 조건부 활성화)
        # 조건: st.session_state['prs']에 PR 목록이 있어야 활성화됨.
        pr_exists = ('prs' in st.session_state and st.session_state['prs'])

        if st.sidebar.button(
            "🚀 시스템 업데이트 실행",
            use_container_width=True,
            disabled=not pr_exists,
            help="대기 중인 PR이 있을 때만 활성화됩니다."
        ):
             with st.sidebar.status("작전 수행 중... (시스템 업데이트)", expanded=True) as status:
                 # PR 존재 시 실행되는 로직이므로, PR 병합 및 업데이트를 수행하는 것이 논리적이나,
                 # 기존 '시스템 업데이트' 로직(git pull 등)을 수행하도록 함.
                 logs = run_update_process(update_code=True, update_data=True, update_model=False)
                 for log in logs:
                    if "❌" in log: st.sidebar.error(log)
                    elif "⚠️" in log: st.sidebar.warning(log)
                    else: st.sidebar.write(log)
                 status.update(label="업데이트 완료", state="complete")

        if not pr_exists:
            st.sidebar.caption("⚠️ 대기 중인 PR이 없어 업데이트 버튼이 비활성화되었습니다.")

        # [수정] 사이드바에 상시 노출되는 명령 입력창 추가 (이미지 업로드 포함)
        st.sidebar.markdown("---")
        with st.sidebar.expander("📝 Commander's Log", expanded=False):
            cmd_input = st.text_area("명령 입력", placeholder="지시사항을 입력하세요...", key="sidebar_cmd_input")
            uploaded_file = st.file_uploader("이미지 첨부 (선택)", type=['png', 'jpg', 'jpeg'], key="sidebar_img_upload")

            if st.button("💾 전송 (Push)", key="sidebar_save_cmd"):
                if cmd_input or uploaded_file:
                    image_filename = None
                    # 이미지 저장 로직
                    if uploaded_file:
                        try:
                            if not os.path.exists(COMMAND_IMAGES_DIR):
                                os.makedirs(COMMAND_IMAGES_DIR)

                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            image_filename = f"{timestamp}_{uploaded_file.name}"
                            save_path = os.path.join(COMMAND_IMAGES_DIR, image_filename)

                            with open(save_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            st.sidebar.success(f"이미지 저장됨: {image_filename}")
                        except Exception as e:
                            st.sidebar.error(f"이미지 저장 실패: {e}")

                    # 명령 저장 및 Git Push 호출
                    success, msg = save_user_request(cmd_input if cmd_input else "(이미지 전송)", image_filename)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("내용을 입력하거나 이미지를 첨부하세요.")

        if menu == "대시보드":
            st.title("🛡️ AEGIS 대시보드 (XRP-BOT)")
            st.caption("맥북 프로 M5 고성능 최적화 | 실시간 금융 데이터 시각화")

            # 1. 사이드바: 제어판
            st.sidebar.header("🎛️ 제어판")

            # 분석 기간 선택
            timeframe_options = {
                "1시간 (1H)": "1h",
                "1일 (1D)": "1D",
                "1주 (1W)": "1W",
                "1개월 (1M)": "1ME",
                "1년 (1Y)": "1YE"
            }

            selected_label = st.sidebar.radio(
                "분석 기간 선택",
                list(timeframe_options.keys()),
                index=1
            )

            # 데이터 로드 시도
            raw_df, error_msg = load_data()

            # 데이터 로드 실패 시 에러 표시
            if raw_df is None:
                st.error("⚠️ 데이터 로드 실패")
                with st.expander("상세 오류 내용 보기"):
                    st.code(error_msg)
                st.info("ℹ️ 'historical_data_3y.csv' 파일이 현재 디렉토리에 있는지 확인해주세요.")
                return

            if raw_df.empty:
                st.error("데이터프레임이 비어 있습니다.")
                return

            # 2. 데이터 리샘플링
            rule = timeframe_options[selected_label]
            agg_dict = {
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'prob': 'mean'
            }

            try:
                if not isinstance(raw_df.index, pd.DatetimeIndex):
                    raw_df.index = pd.to_datetime(raw_df.index)
                df_resampled = raw_df.resample(rule).agg(agg_dict).dropna()
            except Exception as e:
                st.sidebar.error(f"리샘플링 오류: {e}")
                df_resampled = raw_df

            if df_resampled.empty:
                st.warning("선택한 기간에 해당하는 데이터가 없습니다.")
                return

            latest = df_resampled.iloc[-1]
            prev = df_resampled.iloc[-2] if len(df_resampled) > 1 else latest

            # 3. 핵심 지표 (Metrics)
            col1, col2, col3, col4 = st.columns(4)
            price_change = latest['close'] - prev['close']
            price_pct = (price_change / prev['close']) * 100 if prev['close'] != 0 else 0

            with col1:
                st.metric("현재가 (Close)", f"${latest['close']:.4f}", f"{price_pct:.2f}%")
            with col2:
                st.metric("시가 (Open)", f"${latest['open']:.4f}")
            with col3:
                st.metric("거래량 (Volume)", f"{int(latest['volume']):,}")
            with col4:
                st.metric("오늘의 승률 (Avg Prob)", f"{latest['prob']:.1f}%", delta_color="off")

            st.divider()

            # 4. 차트 시각화
            st.subheader(f"📊 {selected_label} 캔들스틱 및 예측 성공률")
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.7, 0.3],
                specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
            )

            fig.add_trace(go.Candlestick(
                x=df_resampled.index,
                open=df_resampled['open'],
                high=df_resampled['high'],
                low=df_resampled['low'],
                close=df_resampled['close'],
                name="가격(OHLC)",
                increasing_line_color='#22C55E',
                decreasing_line_color='#EF4444'
            ), row=1, col=1)

            colors = ['#3B82F6' if v >= 50 else '#6B7280' for v in df_resampled['prob']]
            fig.add_trace(go.Bar(
                x=df_resampled.index,
                y=df_resampled['prob'],
                name="예측 성공률(%)",
                marker_color=colors
            ), row=2, col=1)

            fig.update_layout(
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=600
            )
            fig.update_yaxes(title_text="가격 ($)", autorange=True, row=1, col=1)
            fig.update_yaxes(title_text="성공률 (%)", range=[0, 100], row=2, col=1)
            st.plotly_chart(fig, width="stretch")
            st.markdown("---")
            st.caption("System Status: 🟢 Online | Model: AEGIS v4.0.0 | Data Source: Local CSV (or Simulation)")

        elif menu == "통합 커맨드 센터":
            st.title("🛠️ AEGIS 통합 커맨드 센터")
            st.caption("시스템 제어, GitHub 연동, 명령 하달을 위한 중앙 통제실")

            # --- [설정 및 GitHub 연동] ---
            # [수정] 설정 불러오기
            config = load_config()

            with st.expander("⚙️ 시스템 및 GitHub 설정", expanded=True):
                col1, col2 = st.columns(2)
                default_owner_git, default_repo_git = get_github_repo_info()

                # config에 값이 있으면 우선 사용, 없으면 git 명령 결과 사용
                init_owner = config.get("github_owner", default_owner_git)
                init_repo = config.get("github_repo", default_repo_git)
                init_token = config.get("github_token", "")

                with col1:
                    repo_owner = st.text_input("GitHub Owner", value=init_owner).strip()
                    repo_name = st.text_input("Repository Name", value=init_repo).strip()
                with col2:
                    github_token = st.text_input("GitHub Token (PAT)", value=init_token, type="password", help="repo 권한이 있는 Personal Access Token 입력").strip()

                # [수정] 설정 저장 버튼
                if st.button("💾 설정 저장 (Save Config)"):
                    success, msg = save_config(repo_owner, repo_name, github_token)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

            st.divider()

            # --- [섹션 1: 시스템 업데이트] ---
            # 사이드바에 기능을 이전했으므로 메인 화면에서는 제거하거나 중복 배치 가능.
            # UX상 중복 배치는 혼란을 줄 수 있으나, 상세 옵션(체크박스) 제어는 메인에 남겨두는 것이 좋음.
            st.subheader("1️⃣ 시스템 업데이트 (Update Center)")
            st.info("💡 사이드바의 '🚀 시스템 업데이트 실행' 버튼을 통해서도 즉시 실행할 수 있습니다.")

            with st.form("update_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    chk_code = st.checkbox("최신 시스템 코드 (git pull)", value=True)
                with col2:
                    chk_data = st.checkbox("최신 시세 데이터 동기화", value=True)
                with col3:
                    chk_model = st.checkbox("AI 모델 가중치 확인", value=False)

                submit_update = st.form_submit_button("🚀 선택 항목 업데이트 실행")

            if submit_update:
                with st.status("시스템 업데이트 진행 중...", expanded=True) as status:
                    st.write("🔄 업데이트 프로세스를 시작합니다...")
                    logs = run_update_process(chk_code, chk_data, chk_model)
                    for log in logs:
                        if "❌" in log: st.error(log)
                        elif "⚠️" in log: st.warning(log)
                        else: st.success(log)
                    status.update(label="업데이트 완료!", state="complete", expanded=True)
                if st.button("시스템 재시작 (화면 새로고침)"):
                    st.rerun()

            st.divider()

            # --- [섹션 2: GitHub PR 관리] ---
            st.subheader("2️⃣ Pull Request 승인 및 병합 (One-Stop Merge)")

            if not github_token:
                st.warning("⚠️ GitHub Token이 입력되지 않았습니다. 상단 설정 메뉴에서 Token을 입력해주세요.")
                st.info("💡 GitHub Token은 PR 목록을 조회하고 병합하는 데 필수적입니다.")
            else:
                if st.button("🔄 열린 PR 목록 불러오기"):
                    prs, error = fetch_prs(repo_owner, repo_name, github_token)
                    if error:
                        st.error(error)
                    elif not prs:
                        st.info(f"✅ '{repo_owner}/{repo_name}' 저장소에 현재 열려 있는 PR이 없습니다.")
                    else:
                        st.session_state['prs'] = prs

                if 'prs' in st.session_state and st.session_state['prs']:
                    st.write(f"총 {len(st.session_state['prs'])}개의 PR이 대기 중입니다.")
                    for pr in st.session_state['prs']:
                        with st.container(border=True):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**#{pr['number']} {pr['title']}**")
                                st.caption(f"작성자: {pr['user']['login']}")
                                st.markdown(f"[PR 링크 바로가기]({pr['html_url']})")

                                # [수정] PR 상세 정보 (Expander)
                                with st.expander("📝 PR 상세 내용 보기"):
                                    st.markdown(pr.get('body', '설명 없음'))
                                    st.caption(f"생성일: {pr['created_at']}")

                            with col2:
                                if st.button(f"✅ 승인 및 병합 (#{pr['number']})", key=f"merge_{pr['number']}"):
                                    success, msg = merge_pr(repo_owner, repo_name, pr['number'], github_token)
                                    if success:
                                        st.success(f"#{pr['number']} 병합 성공!")
                                        # 목록 갱신을 위해 재실행 요청
                                        del st.session_state['prs']
                                        st.rerun()
                                    else:
                                        st.error(msg)

            st.divider()

            # --- [섹션 3: 사령관 명령 하달] ---
            st.subheader("3️⃣ 사령관 명령 입력 (Commander's Orders)")
            st.caption("추가 변경 사항이나 개선 요청을 입력하세요. 줄스(Jules)가 최우선으로 반영합니다.")

            with st.form("commander_request_form"):
                request_text = st.text_area("💡 추가 변경/요청 사항 입력", placeholder="예: 예약 시간을 5분 단위로 더 쪼개줘.", height=100)

                # [수정] PR 생성 옵션 추가
                use_pr = st.checkbox("Pull Request 생성 (권장)", value=True, help="체크 시, 변경 사항을 바로 반영하지 않고 PR을 생성하여 승인 절차를 거칩니다.")

                submit_request = st.form_submit_button("📩 명령 전송 (Send Command)")

            if submit_request and request_text:
                # GitHub 설정 전달
                gh_config = {"owner": repo_owner, "repo": repo_name, "token": github_token}

                success, msg = save_user_request(request_text, create_pr=use_pr, gh_config=gh_config)
                if success:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

        elif menu == "예약 및 스케줄 관리":
            st.title("🗓️ 예약 및 스케줄 관리 센터 (Scheduling Center)")
            st.caption("시스템 자동 실행 시간을 설정하고 관리합니다.")

            # 1. 현재 예약 현황
            st.subheader("1️⃣ 현재 예약된 스케줄")
            current_jobs = get_aegis_jobs()
            if not current_jobs:
                st.info("ℹ️ 현재 등록된 AEGIS 예약 작업이 없습니다.")
            else:
                job_df = pd.DataFrame(current_jobs)
                st.table(job_df)

            st.divider()

            # 2. 새로운 예약 추가
            st.subheader("2️⃣ 새로운 예약 추가")
            st.caption("매일, 매주, 또는 특정 간격으로 시스템을 자동 실행합니다.")

            tab1, tab2, tab3 = st.tabs(["매일 (Daily)", "매주 (Weekly)", "간격 (Interval)"])

            with tab1:
                st.markdown("##### 매일 정해진 시간에 실행")
                daily_time = st.time_input("실행 시간 선택", datetime.time(9, 0))
                if st.button("예약 적용 (Daily)", key="btn_daily"):
                    # Cron: MM HH * * *
                    cron_str = f"{daily_time.minute} {daily_time.hour} * * *"
                    success, msg = add_aegis_job(cron_str)
                    if success:
                        st.success(f"✅ 매일 {daily_time}에 실행 예약되었습니다.")
                        st.rerun()
                    else:
                        st.error(msg)

            with tab2:
                st.markdown("##### 매주 특정 요일, 특정 시간에 실행")
                col1, col2 = st.columns(2)
                with col1:
                    # 0=Sunday, 1=Monday ... but cron expects 0-6 (Sun-Sat) or 1-7 (Mon-Sun).
                    # Python datetime weekday: 0=Mon, 6=Sun.
                    # Cron: 0-6 (Sun-Sat). Usually 1=Mon. Let's use name map for clarity.
                    days_map = {"월요일": 1, "화요일": 2, "수요일": 3, "목요일": 4, "금요일": 5, "토요일": 6, "일요일": 0}
                    selected_day = st.selectbox("요일 선택", list(days_map.keys()))
                with col2:
                    weekly_time = st.time_input("실행 시간 선택", datetime.time(9, 0), key="weekly_time")

                if st.button("예약 적용 (Weekly)", key="btn_weekly"):
                    # Cron: MM HH * * W
                    cron_day = days_map[selected_day]
                    cron_str = f"{weekly_time.minute} {weekly_time.hour} * * {cron_day}"
                    success, msg = add_aegis_job(cron_str)
                    if success:
                        st.success(f"✅ 매주 {selected_day} {weekly_time}에 실행 예약되었습니다.")
                        st.rerun()
                    else:
                        st.error(msg)

            with tab3:
                st.markdown("##### 일정 시간 간격으로 실행")
                interval_hours = st.number_input("시간 간격 (Hour)", min_value=1, max_value=23, value=1)

            if st.button("예약 적용 (Interval)", key="btn_interval"):
                # Cron: 0 */N * * *
                cron_str = f"0 */{interval_hours} * * *"
                success, msg = add_aegis_job(cron_str)
                if success:
                    st.success(f"✅ {interval_hours}시간마다 실행 예약되었습니다.")
                    st.rerun()
                else:
                    st.error(msg)

            st.divider()

            # 3. 예약 관리 (삭제)
            st.subheader("3️⃣ 예약 초기화")
            if st.button("🗑️ 모든 AEGIS 예약 삭제 (Clear All)", type="primary"):
                success, msg = clear_aegis_jobs()
                if success:
                    st.warning("⚠️ 모든 AEGIS 예약이 삭제되었습니다.")
                    st.rerun()
                else:
                    st.error(msg)

    except Exception as e:
        # 전역 예외 처리 (Dashboard Crash 방지)
        st.error("🚨 시스템 오류 발생! (Crash Avoided)")
        st.code(str(e))
        st.info("오류가 지속되면 관리자에게 문의하거나 로그를 확인하세요.")

if __name__ == "__main__":
    main()
