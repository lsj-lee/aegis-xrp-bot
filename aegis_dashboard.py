import streamlit as st
import pandas as pd
import os
import sys
import subprocess
import shutil
from aegis_lib import AegisValidator
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
DASHBOARD_DATA_FILE = "aegis_dashboard_data.json"

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
    """
    logs = []
    try:
        subprocess.run(["git", "add"] + files_to_add, check=True, capture_output=True, text=True)
        logs.append(f"Git Add: {files_to_add}")

        subprocess.run(["git", "commit", "-m", commit_message], check=True, capture_output=True, text=True)
        logs.append(f"Git Commit: {commit_message}")

        subprocess.run(["git", "push"], check=True, capture_output=True, text=True)
        logs.append("Git Push: Success")
        return True, "\n".join(logs)

    except subprocess.CalledProcessError as e:
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
            if url.startswith("git@"):
                parts = url.split(":")[-1].replace(".git", "").split("/")
                if len(parts) >= 2:
                    return parts[-2], parts[-1]
            elif url.startswith("http"):
                parts = url.replace(".git", "").split("/")
                if len(parts) >= 2:
                    return parts[-2], parts[-1]
    except Exception:
        pass
    return "lsj-lee", "aegis-xrp-bot"

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

def close_pr(owner, repo, pr_number, token):
    """GitHub API를 통해 PR 닫기 (Close)"""
    if not token:
        return False, "GitHub Token이 필요합니다."

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    payload = {"state": "closed"}
    try:
        response = requests.patch(url, headers=headers, json=payload)
        if response.status_code == 200:
            return True, "PR이 성공적으로 닫혔습니다 (폐기 완료)."
        else:
            return False, f"PR 닫기 실패: {response.status_code} - {response.text}"
    except Exception as e:
        return False, str(e)

def create_pr_from_changes(owner, repo, token, files_to_add, commit_msg, pr_title, pr_body):
    """
    새로운 브랜치를 생성하고 변경사항을 커밋/푸시한 후 PR을 생성합니다.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"cmd/order-{timestamp}"
    original_branch = "main"

    try:
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
        if res.returncode == 0:
            original_branch = res.stdout.strip()

        subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True, text=True)
        subprocess.run(["git", "add"] + files_to_add, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True, text=True)
        subprocess.run(["git", "push", "origin", branch_name], check=True, capture_output=True, text=True)

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
        subprocess.run(["git", "checkout", original_branch], check=True, capture_output=True, text=True)

        if resp.status_code == 201:
            pr_data = resp.json()
            return True, f"PR 생성 성공: #{pr_data['number']} {pr_data['html_url']}"
        else:
            return False, f"PR 생성 실패 ({resp.status_code}): {resp.text}"

    except Exception as e:
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
        with open(USER_REQUESTS_FILE, "a", encoding="utf-8") as f:
            f.write(entry)

        files_to_sync = [USER_REQUESTS_FILE]
        if image_filename:
            files_to_sync.append(COMMAND_IMAGES_DIR)

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

        success, msg = git_push_changes(files_to_sync, f"Command: {request_text[:30]}...")

        if success:
             return True, "명령 저장 및 Git Push 완료"
        else:
             return True, f"명령은 저장되었으나 Git Push 실패: {msg}"

    except Exception as e:
        return False, f"저장 중 오류: {str(e)}"

# --- [스케줄링 유틸리티 함수] ---
def get_current_crontab():
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.splitlines()
        else:
            return []
    except FileNotFoundError:
        return []

def update_crontab(new_lines):
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
    project_root = os.path.dirname(os.path.abspath(__file__))
    python_exec = sys.executable
    cmd = f"cd {project_root} && {python_exec} {script_path} --enable-sleep >> {project_root}/aegis_cron.log 2>&1"
    new_line = f"{cron_schedule} {cmd} # AEGIS-JOB"
    lines = get_current_crontab()
    lines.append(new_line)
    return update_crontab(lines)

def clear_aegis_jobs():
    lines = get_current_crontab()
    new_lines = [line for line in lines if "# AEGIS-JOB" not in line]
    return update_crontab(new_lines)


# --- [메인 로직] ---
def main():
    try:
        st.sidebar.title("🛡️ AEGIS SYSTEM")

        # 사이드바 메뉴 선택
        menu = st.sidebar.radio("메뉴 선택", ["대시보드", "통합 커맨드 센터", "예약 및 스케줄 관리"])

        # 사이드바: Commander's Log
        st.sidebar.markdown("---")
        with st.sidebar.expander("📝 Commander's Log", expanded=False):
            cmd_input = st.text_area("명령 입력", placeholder="지시사항을 입력하세요...", key="sidebar_cmd_input")
            uploaded_file = st.file_uploader("이미지 첨부 (선택)", type=['png', 'jpg', 'jpeg'], key="sidebar_img_upload")

            if st.button("💾 전송 (Push)", key="sidebar_save_cmd"):
                if cmd_input or uploaded_file:
                    image_filename = None
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
                    success, msg = save_user_request(cmd_input if cmd_input else "(이미지 전송)", image_filename)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("내용을 입력하거나 이미지를 첨부하세요.")

        if menu == "대시보드":
            st.title("🛡️ AEGIS 통합 커맨드 센터 (v2.1 Test)")
            st.caption("맥북 프로 M5 고성능 최적화 | 실시간 금융 데이터 시각화")
            st.info(f"🚀 AEGIS 시스템 통신망 테스트 중: 줄스 응답 대기 완료 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

            # 1. [최상단 배치] 즉시 분석 시작 버튼
            if st.button("🚀 즉시 분석 시작 (Start Immediate Analysis)", use_container_width=True, type="primary"):
                 # [Verification Phase]
                 impact = AegisValidator.analyze_impact("Start Immediate Analysis")
                 if impact['risk_level'] == 'High':
                     st.error(f"🚫 실행 차단됨: {impact['message']}")
                     st.stop()
                 elif impact['risk_level'] == 'Medium':
                     st.warning(impact['message'])

                 with st.status("작전 수행 중... (분석 엔진 가동)", expanded=True) as status:
                     try:
                         process = subprocess.run([sys.executable, "aegis_automation.py"], capture_output=True, text=True)
                         if process.returncode == 0:
                             st.success("✅ 분석 및 보고 완료!")
                             st.rerun()
                         else:
                             st.error("❌ 분석 실패")
                             with st.expander("오류 로그 보기"):
                                 st.code(process.stderr)
                     except Exception as e:
                         st.error(f"실행 오류: {e}")
                     status.update(label="작전 종료", state="complete")

            st.divider()

            # 2. 핵심 지표 (Metrics) - JSON 데이터 기반
            price = "N/A"
            prob = "N/A"
            fng = "N/A"
            report_content = "분석 리포트가 없습니다."
            timestamp = "Unknown"

            if os.path.exists(DASHBOARD_DATA_FILE):
                try:
                    with open(DASHBOARD_DATA_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    price_val = data.get("price", 0)
                    prob_val = data.get("prob", 0)
                    fng_val = data.get("fng", 0)
                    timestamp = data.get("timestamp", "Unknown")
                    report_content = data.get("report", "분석 리포트가 없습니다.")

                    # Format Metrics
                    price = f"${price_val:.4f}"
                    prob = f"{prob_val:.1f}%"
                    fng = f"{fng_val}"
                except Exception as e:
                    st.error(f"데이터 로드 중 오류: {e}")

            # 3-Column Layout
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("현재 XRP 시세 (Price)", price)
            with col2:
                st.metric("AI 예측 점수 (Score)", prob)
            with col3:
                st.metric("공포 지수 (Fear Index)", fng)

            st.divider()

            # 3. 분석 결과 리포트 (하단 배치)
            st.subheader("📑 최신 분석 결과 리포트 (Latest Analysis Report)")
            st.caption(f"Report Generated at: {timestamp}")
            with st.container(border=True):
                st.markdown(report_content)

            st.markdown("---")

            # 4. Mission Status & Live Logs
            st.subheader("📡 Mission Status & Live Logs")
            with st.status("시스템 작전 상황 실시간 모니터링 중...", expanded=True) as status:
                st.write("✅ 시스템 통신망: 정상")
                st.write("✅ 데이터 파이프라인: 대기 중")
                log_file = "aegis_system.log"
                if os.path.exists(log_file):
                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                            last_logs = lines[-3:] if len(lines) >= 3 else lines
                            st.text("📋 최신 시스템 로그:")
                            for line in last_logs:
                                st.code(line.strip(), language="text")
                    except Exception:
                        st.warning("로그 파일을 읽을 수 없습니다.")
                else:
                    st.info("시스템 로그 파일이 아직 생성되지 않았습니다.")
                status.update(label="작전 수행 대기 중", state="running")
            st.caption("System Status: 🟢 Online | Model: AEGIS v4.0.0")

        elif menu == "통합 커맨드 센터":
            st.title("🛠️ AEGIS 통합 커맨드 센터")
            st.caption("시스템 제어, GitHub 연동, 명령 하달을 위한 중앙 통제실")

            # Section 1: System Update Center
            st.subheader("1️⃣ 시스템 업데이트 (Update Center)")
            col_up1, col_up2, col_up3 = st.columns(3)
            with col_up1:
                check_git = st.checkbox("최신 시스템 코드 (git pull)", value=True)
            with col_up2:
                check_data = st.checkbox("최신 시세 데이터 동기화", value=True)
            with col_up3:
                check_model = st.checkbox("AI 모델 가중치 확인", value=True)

            if st.button("🚀 선택 항목 업데이트 실행", type="primary", key="btn_update_system"):
                # [Command Verification]
                if check_git and not AegisValidator.validate_command(["git", "pull"]):
                    st.error("🚫 Git Pull Blocked.")
                    st.stop()
                if check_data and not AegisValidator.validate_command([sys.executable, "data_bank_builder.py"]):
                    st.error("🚫 Data Sync Blocked.")
                    st.stop()

                with st.status("시스템 업데이트 진행 중...", expanded=True) as status:
                    # 1. Git Pull
                    if check_git:
                        st.write("🔄 Git Pull 실행 중...")
                        try:
                            res = subprocess.run(["git", "pull"], capture_output=True, text=True)
                            if res.returncode == 0:
                                st.success(f"Git Pull 성공: {res.stdout.strip()}")
                            else:
                                st.error(f"Git Pull 실패: {res.stderr.strip()}")
                        except Exception as e:
                            st.error(f"Git 실행 오류: {e}")

                    # 2. Data Sync
                    if check_data:
                        st.write("📊 시세 데이터 동기화 중...")
                        try:
                            # data_bank_builder.py 실행
                            res = subprocess.run([sys.executable, "data_bank_builder.py"], capture_output=True, text=True)
                            if res.returncode == 0:
                                st.success("데이터 동기화 완료!")
                            else:
                                st.error(f"데이터 동기화 실패: {res.stderr.strip()}")
                        except Exception as e:
                            st.error(f"데이터 스크립트 실행 오류: {e}")

                    # 3. Model Check
                    if check_model:
                        st.write("🧠 AI 모델 점검 중...")
                        model_path = "aegis_brain.pth"
                        if os.path.exists(model_path):
                            size_mb = os.path.getsize(model_path) / (1024 * 1024)
                            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(model_path)).strftime('%Y-%m-%d %H:%M:%S')
                            st.info(f"모델 발견: {model_path} ({size_mb:.2f} MB) - 수정일: {mtime}")
                        else:
                            st.warning("⚠️ 학습된 모델 파일(aegis_brain.pth)을 찾을 수 없습니다.")

                    status.update(label="업데이트 작업 완료", state="complete")

            st.divider()

            config = load_config()
            with st.expander("⚙️ 시스템 및 GitHub 설정", expanded=True):
                col1, col2 = st.columns(2)
                default_owner_git, default_repo_git = get_github_repo_info()
                init_owner = config.get("github_owner", default_owner_git)
                init_repo = config.get("github_repo", default_repo_git)
                init_token = config.get("github_token", "")
                with col1:
                    repo_owner = st.text_input("GitHub Owner", value=init_owner).strip()
                    repo_name = st.text_input("Repository Name", value=init_repo).strip()
                with col2:
                    github_token = st.text_input("GitHub Token (PAT)", value=init_token, type="password", help="repo 권한이 있는 Personal Access Token 입력").strip()
                if st.button("💾 설정 저장 (Save Config)"):
                    success, msg = save_config(repo_owner, repo_name, github_token)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

            st.divider()

            # Section 2: GitHub PR Manager
            st.subheader("2️⃣ Pull Request 승인 및 병합 (One-Stop Merge)")
            if not github_token:
                st.warning("⚠️ GitHub Token이 입력되지 않았습니다. 상단 설정 메뉴에서 Token을 입력해주세요.")
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
                                with st.expander("📝 PR 상세 내용 보기"):
                                    st.markdown(pr.get('body', '설명 없음'))
                                    st.caption(f"생성일: {pr['created_at']}")
                            with col2:
                                if st.button(f"✅ 승인 및 병합 (#{pr['number']})", key=f"merge_{pr['number']}"):
                                    success, msg = merge_pr(repo_owner, repo_name, pr['number'], github_token)
                                    if success:
                                        st.success(f"#{pr['number']} 병합 성공!")
                                        del st.session_state['prs']
                                        st.rerun()
                                    else:
                                        st.error(msg)

                                # [PR 닫기 기능]
                                if st.button(f"🗑️ PR 닫기(Close) (#{pr['number']})", key=f"close_{pr['number']}"):
                                    st.session_state[f"confirm_close_{pr['number']}"] = True

                            # [안전 장치 연동] - 폐기 확인 팝업
                            if st.session_state.get(f"confirm_close_{pr['number']}"):
                                st.warning("⚠️ 이 작전 계획(PR)을 정말 폐기하시겠습니까? (Irreversible Action)")
                                impact = AegisValidator.analyze_impact(f"Close PR #{pr['number']}")
                                st.caption(f"🛡️ Aegis Risk Analysis: {impact['message']}")

                                c_conf, c_cancel = st.columns(2)
                                with c_conf:
                                    if st.button("확인 (Confirm)", key=f"conf_close_{pr['number']}"):
                                        success, msg = close_pr(repo_owner, repo_name, pr['number'], github_token)
                                        if success:
                                            st.success(f"#{pr['number']} 폐기 완료!")
                                            del st.session_state['prs'] # 목록 갱신 트리거
                                            del st.session_state[f"confirm_close_{pr['number']}"]
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                with c_cancel:
                                    if st.button("취소 (Cancel)", key=f"cancel_close_{pr['number']}"):
                                        del st.session_state[f"confirm_close_{pr['number']}"]
                                        st.rerun()

            st.divider()

            # Section 3: Commander's Orders
            st.subheader("3️⃣ 사령관 명령 입력 (Commander's Orders)")
            st.caption("추가 변경 사항이나 개선 요청을 입력하세요. 줄스(Jules)가 최우선으로 반영합니다.")
            with st.form("commander_request_form"):
                request_text = st.text_area("💡 추가 변경/요청 사항 입력", placeholder="예: 예약 시간을 5분 단위로 더 쪼개줘.", height=100)
                use_pr = st.checkbox("Pull Request 생성 (권장)", value=True, help="체크 시, 변경 사항을 바로 반영하지 않고 PR을 생성하여 승인 절차를 거칩니다.")
                submit_request = st.form_submit_button("📩 명령 전송 (Send Command)")

            if submit_request and request_text:
                # [Impact Analysis]
                impact = AegisValidator.analyze_impact(request_text)
                if impact['risk_level'] == 'High':
                    st.error(f"🚫 Critical Risk: {impact['message']}")
                    st.stop()
                elif impact['risk_level'] == 'Medium':
                    st.warning(f"⚠️ Notice: {impact['message']}")

                gh_config = {"owner": repo_owner, "repo": repo_name, "token": github_token}
                success, msg = save_user_request(request_text, create_pr=use_pr, gh_config=gh_config)
                if success:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

        elif menu == "예약 및 스케줄 관리":
            st.title("🗓️ 예약 및 스케줄 관리 센터 (Scheduling Center)")
            st.caption("시스템 자동 실행 시간을 설정하고 관리합니다.")

            st.subheader("1️⃣ 현재 예약된 스케줄")
            current_jobs = get_aegis_jobs()
            if not current_jobs:
                st.info("ℹ️ 현재 등록된 AEGIS 예약 작업이 없습니다.")
            else:
                job_df = pd.DataFrame(current_jobs)
                st.table(job_df)

            st.divider()

            st.subheader("2️⃣ 새로운 예약 추가")
            st.caption("매일, 매주, 또는 특정 간격으로 시스템을 자동 실행합니다.")
            tab1, tab2, tab3 = st.tabs(["매일 (Daily)", "매주 (Weekly)", "간격 (Interval)"])

            with tab1:
                st.markdown("##### 매일 정해진 시간에 실행")
                daily_time = st.time_input("실행 시간 선택", datetime.time(9, 0))
                if st.button("예약 적용 (Daily)", key="btn_daily"):
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
                    days_map = {"월요일": 1, "화요일": 2, "수요일": 3, "목요일": 4, "금요일": 5, "토요일": 6, "일요일": 0}
                    selected_day = st.selectbox("요일 선택", list(days_map.keys()))
                with col2:
                    weekly_time = st.time_input("실행 시간 선택", datetime.time(9, 0), key="weekly_time")
                if st.button("예약 적용 (Weekly)", key="btn_weekly"):
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
                cron_str = f"0 */{interval_hours} * * *"
                success, msg = add_aegis_job(cron_str)
                if success:
                    st.success(f"✅ {interval_hours}시간마다 실행 예약되었습니다.")
                    st.rerun()
                else:
                    st.error(msg)

            st.divider()

            st.subheader("3️⃣ 예약 초기화")
            if st.button("🗑️ 모든 AEGIS 예약 삭제 (Clear All)", type="primary"):
                success, msg = clear_aegis_jobs()
                if success:
                    st.warning("⚠️ 모든 AEGIS 예약이 삭제되었습니다.")
                    st.rerun()
                else:
                    st.error(msg)

    except Exception as e:
        st.error("🚨 시스템 오류 발생! (Crash Avoided)")
        st.code(str(e))
        st.info("오류가 지속되면 관리자에게 문의하거나 로그를 확인하세요.")

if __name__ == "__main__":
    main()
