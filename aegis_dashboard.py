import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
import subprocess
import shutil
import numpy as np

# --- [페이지 설정: 넓은 화면 모드] ---
st.set_page_config(
    page_title="AEGIS 커맨드 센터",
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
    </style>
    """, unsafe_allow_html=True)

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
        'prob': np.random.uniform(40, 90, size=days)  # 40~90% 확률
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
        # CSV 읽기 (헤더 그대로)
        df = pd.read_csv(file_path)

        # 1. 컬럼명 소문자 변환 및 공백 제거
        df.columns = df.columns.str.strip().str.lower()

        # 2. 날짜 컬럼 처리 ('date' -> 'timestamp'로 통일)
        if 'date' in df.columns and 'timestamp' not in df.columns:
            df.rename(columns={'date': 'timestamp'}, inplace=True)

        # 3. 필수 컬럼 확인
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            # 현재 컬럼 리스트 반환
            current_cols = list(df.columns)
            return None, f"필수 컬럼 누락: {missing_cols}. 현재 컬럼: {current_cols}"

        # 4. 인덱스 설정 및 날짜 파싱
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        # 5. 'prob' (예측 확률) 컬럼 처리
        if 'prob' not in df.columns:
            # 임의의 데이터 생성 (실제 데이터가 없을 경우 시각화용)
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
            # 모델 파일이 git으로 관리된다면 git pull로 업데이트됨.
            # 관리되지 않는다면 별도 다운로드 로직이 필요하나, 현재는 git pull 결과에 의존하거나 경고 메시지 출력.
            if os.path.exists("aegis_brain.pth"):
                logs.append("ℹ️ AI 모델 파일(aegis_brain.pth)이 존재합니다. (Git Pull로 최신화되었을 수 있음)")
            else:
                logs.append("⚠️ AI 모델 파일을 찾을 수 없습니다. (Git Pull로 가져오지 못함)")
        except Exception as e:
            logs.append(f"❌ 모델 확인 중 오류: {str(e)}")

    return logs

# --- [메인 로직] ---
def main():
    st.sidebar.title("🛡️ AEGIS")

    # 사이드바 메뉴 선택
    menu = st.sidebar.radio("메뉴 선택", ["대시보드", "업데이트 센터"])

    if menu == "대시보드":
        st.title("🛡️ AEGIS 커맨드 센터 (XRP-BOT)")
        st.caption("맥북 프로 M5 고성능 최적화 | 실시간 금융 데이터 시각화")

        # 1. 사이드바: 제어판
        st.sidebar.header("🎛️ 제어판")

        # 분석 기간 선택 (Radio Button)
        timeframe_options = {
            "1시간 (1H)": "1h",
            "1일 (1D)": "1D",
            "1주 (1W)": "1W",
            "1개월 (1M)": "1ME", # Pandas 2.x+ 대응
            "1년 (1Y)": "1YE"    # Pandas 2.x+ 대응
        }

        selected_label = st.sidebar.radio(
            "분석 기간 선택",
            list(timeframe_options.keys()),
            index=1 # 기본값: 1일
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

        # 2. 데이터 리샘플링 (Resampling)
        rule = timeframe_options[selected_label]

        # 리샘플링 집계 규칙 (소문자 키 사용)
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
            'prob': 'mean' # 예측 확률은 평균으로 집계
        }

        # 데이터프레임 리샘플링 실행
        try:
            # index가 DatetimeIndex인지 확인
            if not isinstance(raw_df.index, pd.DatetimeIndex):
                raw_df.index = pd.to_datetime(raw_df.index)

            df_resampled = raw_df.resample(rule).agg(agg_dict).dropna()
        except Exception as e:
            st.sidebar.error(f"리샘플링 오류: {e}")
            df_resampled = raw_df # 오류 시 원본 사용

        if df_resampled.empty:
            st.warning("선택한 기간에 해당하는 데이터가 없습니다.")
            return

        latest = df_resampled.iloc[-1]
        prev = df_resampled.iloc[-2] if len(df_resampled) > 1 else latest

        # 3. 핵심 지표 (Metrics) - 소문자 키 사용
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

        # 4. 차트 시각화 (캔들스틱 + 막대 그래프 통합)
        st.subheader(f"📊 {selected_label} 캔들스틱 및 예측 성공률")

        # 서브플롯 생성 (2행 1열, X축 공유)
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )

        # (1) 캔들스틱 차트 (메인)
        fig.add_trace(go.Candlestick(
            x=df_resampled.index,
            open=df_resampled['open'],
            high=df_resampled['high'],
            low=df_resampled['low'],
            close=df_resampled['close'],
            name="가격(OHLC)",
            increasing_line_color='#22C55E', # Green
            decreasing_line_color='#EF4444'  # Red
        ), row=1, col=1)

        # (2) 예측 성공률 (막대 그래프)
        # 색상 로직: 50% 이상이면 파란색, 미만이면 회색
        colors = ['#3B82F6' if v >= 50 else '#6B7280' for v in df_resampled['prob']]

        fig.add_trace(go.Bar(
            x=df_resampled.index,
            y=df_resampled['prob'],
            name="예측 성공률(%)",
            marker_color=colors
        ), row=2, col=1)

        # 레이아웃 업데이트 (다크 테마, UI 단순화)
        fig.update_layout(
            template="plotly_dark",
            xaxis_rangeslider_visible=False, # 하단 레인지 슬라이더 제거
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=600 # 전체 높이
        )

        # Y축 레이블 설정
        fig.update_yaxes(title_text="가격 ($)", row=1, col=1)
        fig.update_yaxes(title_text="성공률 (%)", range=[0, 100], row=2, col=1)

        # 전체 화면 꽉 채우기
        st.plotly_chart(fig, width="stretch")

        st.markdown("---")
        st.caption("System Status: 🟢 Online | Model: AEGIS v4.0.0 | Data Source: Local CSV (or Simulation)")

    elif menu == "업데이트 센터":
        st.title("🛠️ 시스템 업데이트 관리 센터")
        st.caption("시스템 구성요소를 최신 상태로 동기화합니다.")

        st.info("💡 업데이트 항목을 선택하고 실행 버튼을 눌러주세요.")

        with st.form("update_form"):
            st.markdown("### 업데이트 항목 선택")
            col1, col2 = st.columns(2)
            with col1:
                chk_code = st.checkbox("최신 시스템 코드 (GitHub main 브랜치)", value=True)
                chk_data = st.checkbox("최신 시세 데이터 (CSV 파일 동기화)", value=True)
            with col2:
                chk_model = st.checkbox("AI 모델 가중치 (aegis_brain.pth)", value=False)

            st.markdown("---")
            submitted = st.form_submit_button("🚀 선택 항목 업데이트 실행")

        if submitted:
            if not (chk_code or chk_data or chk_model):
                st.warning("⚠️ 업데이트할 항목을 하나 이상 선택해주세요.")
            else:
                with st.status("시스템 업데이트 진행 중...", expanded=True) as status:
                    st.write("🔄 업데이트 프로세스를 시작합니다...")
                    logs = run_update_process(chk_code, chk_data, chk_model)

                    for log in logs:
                        if "❌" in log:
                            st.error(log)
                        elif "⚠️" in log:
                            st.warning(log)
                        else:
                            st.success(log)

                    status.update(label="업데이트 완료!", state="complete", expanded=True)

                if st.button("시스템 재시작 (화면 새로고침)"):
                    st.rerun()

if __name__ == "__main__":
    main()
