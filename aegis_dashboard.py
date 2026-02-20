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

def save_user_request(request_text):
    """사용자 요청사항을 파일에 저장"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {request_text}\n"
    try:
        with open("user_requests.txt", "a", encoding="utf-8") as f:
            f.write(entry)
        return True
    except Exception as e:
        return False

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
    if not os.path.exists(file_path) and os.path.exists(legacy_path):
        try:
            shutil.copy(legacy_path, file_path)
        except:
            pass

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

        # 3. 필수 컬럼 확인
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
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

                if os.path.exists(legacy_path):
                    shutil.copy(legacy_path, local_path)
                    logs.append(f"✅ 데이터 파일 동기화 완료: {legacy_path} -> {local_path}")
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
    st.sidebar.title("🛡️ AEGIS SYSTEM")

    # 사이드바 메뉴 선택
    menu = st.sidebar.radio("메뉴 선택", ["대시보드", "통합 커맨드 센터"])

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

        # 데이터 로드 실패 시 더미 데이터 사용 및 에러 표시
        if raw_df is None:
            st.error(f"⚠️ 데이터 로드 실패: {error_msg}")
            st.warning("🔄 시뮬레이션 모드로 전환합니다 (샘플 데이터 사용).")
            raw_df = create_dummy_data()

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
        fig.update_yaxes(title_text="가격 ($)", row=1, col=1)
        fig.update_yaxes(title_text="성공률 (%)", range=[0, 100], row=2, col=1)
        st.plotly_chart(fig, width="stretch")
        st.markdown("---")
        st.caption("System Status: 🟢 Online | Model: AEGIS v4.0.0 | Data Source: Local CSV (or Simulation)")

    elif menu == "통합 커맨드 센터":
        st.title("🛠️ AEGIS 통합 커맨드 센터")
        st.caption("시스템 제어, GitHub 연동, 명령 하달을 위한 중앙 통제실")

        # --- [설정 및 GitHub 연동] ---
        with st.expander("⚙️ 시스템 및 GitHub 설정", expanded=True):
            col1, col2 = st.columns(2)
            default_owner, default_repo = get_github_repo_info()

            with col1:
                repo_owner = st.text_input("GitHub Owner", value=default_owner)
                repo_name = st.text_input("Repository Name", value=default_repo)
            with col2:
                github_token = st.text_input("GitHub Token (PAT)", type="password", help="repo 권한이 있는 Personal Access Token 입력")

        st.divider()

        # --- [섹션 1: 시스템 업데이트] ---
        st.subheader("1️⃣ 시스템 업데이트 (Update Center)")
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
            st.warning("⚠️ GitHub Token을 입력해야 PR 목록을 불러올 수 있습니다.")
        else:
            if st.button("🔄 열린 PR 목록 불러오기"):
                prs, error = fetch_prs(repo_owner, repo_name, github_token)
                if error:
                    st.error(error)
                elif not prs:
                    st.info("✅ 현재 열려 있는 PR이 없습니다.")
                else:
                    st.session_state['prs'] = prs

            if 'prs' in st.session_state and st.session_state['prs']:
                st.write(f"총 {len(st.session_state['prs'])}개의 PR이 대기 중입니다.")
                for pr in st.session_state['prs']:
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**#{pr['number']} {pr['title']}**")
                            st.caption(f"작성자: {pr['user']['login']} | 생성일: {pr['created_at']}")
                            st.markdown(f"[PR 링크 바로가기]({pr['html_url']})")
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
            request_text = st.text_area("💡 추가 변경/요청 사항 입력", placeholder="예: 차트의 상승 색상을 더 밝은 녹색으로 변경해줘.", height=100)
            submit_request = st.form_submit_button("📩 명령 전송 (Send Command)")

        if submit_request and request_text:
            if save_user_request(request_text):
                st.success("✅ 명령이 성공적으로 접수되었습니다! ('user_requests.txt'에 저장됨)")
            else:
                st.error("❌ 명령 저장 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main()
