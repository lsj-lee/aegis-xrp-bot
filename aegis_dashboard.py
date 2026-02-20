import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# --- [페이지 설정: 넓은 화면 모드] ---
st.set_page_config(
    page_title="AEGIS Command Center",
    page_icon="🛡️",
    layout="wide"
)

# --- [줄스의 커스텀 스타일링] ---
st.markdown("""
    <style>
    .stMetric { background-color: #111827; padding: 20px; border-radius: 15px; border: 1px solid #374151; }
    .main { background-color: #030712; }
    </style>
    """, unsafe_allow_html=True)

# --- [데이터 로드 함수] ---
def get_aegis_data():
    mock_data = {
        "날짜": ["2026-02-18", "2026-02-19", "2026-02-20"],
        "현재가": [1.25, 1.30, 1.33],
        "예측확률": [48.5, 46.7, 42.4],
        "판단": ["HOLD", "WATCH", "WAIT"],
        "공포지수": [12, 10, 9]
    }
    return pd.DataFrame(mock_data)

# --- [메인 지휘 대시보드] ---
st.title("📊 AEGIS 실시간 금융 터미널")
st.caption(f"사령관님의 M5 맥북이 관리하는 최상위 보안 구역 | 현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

df = get_aegis_data()
latest = df.iloc[-1]

# 1. 핵심 지표 (Metrics)
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("오늘의 승률", f"{latest['예측확률']}%", "-2.3%")
with c2: st.metric("XRP 현재가", f"${latest['현재가']}", "+$0.03")
with c3: st.metric("공포지수", f"{latest['공포지수']}/100", "-1")
with c4: st.metric("최종 액션", latest['판단'])

st.divider()

# 2. 다차원 분석 (Charts) - 경고 해결 버전
left, right = st.columns([2, 1])

with left:
    st.subheader("📈 가격 및 확률 진화 추세")
    fig = px.line(df, x="날짜", y=["현재가", "예측확률"], 
                  markers=True, template="plotly_dark",
                  color_discrete_sequence=["#3B82F6", "#EF4444"])
    # ⚠️ 경고 해결: width='stretch' 사용
    st.plotly_chart(fig, width='stretch')

with right:
    st.subheader("🧬 NDA 다차원 균형")
    categories = ['관찰(O)', '연결(C)', '시각화(P)', '해결책(S)', '효율(E)']
    fig_radar = go.Figure(data=go.Scatterpolar(
        r=[85, 75, 95, 65, 90], theta=categories, fill='toself', line_color='#10B981'
    ))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=False)),
                            showlegend=False, template="plotly_dark")
    # ⚠️ 경고 해결: width='stretch' 사용
    st.plotly_chart(fig_radar, width='stretch')

st.markdown("---")
st.caption("🚨 AEGIS Intelligence System v4.0.0")