import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
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

# --- [메인 로직] ---
def main():
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

if __name__ == "__main__":
    main()
