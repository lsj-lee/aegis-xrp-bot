import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
import datetime
import time

# --- Configuration ---
st.set_page_config(
    page_title="AEGIS COMMAND CENTER",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Cyberpunk/Dark Theme aesthetics
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main {
        background: #0e1117;
    }
    h1, h2, h3 {
        color: #00ff41 !important;
        font-family: 'Courier New', monospace;
    }
    .stMetric {
        background-color: #1f1f1f;
        border: 1px solid #333;
        padding: 10px;
        border-radius: 5px;
    }
    .stMetric label {
        color: #888 !important;
    }
    .stMetric div[data-testid="stMetricValue"] {
        color: #00ff41 !important;
        font-family: 'Courier New', monospace;
    }
    div.stButton > button:first-child {
        background-color: #00ff41;
        color: #000;
        border: none;
        font-weight: bold;
        font-family: 'Courier New', monospace;
    }
    div.stButton > button:hover {
        background-color: #00cc33;
        color: #000;
    }
    pre {
        background-color: #000 !important;
        color: #00ff41 !important;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
DATA_FILE = "aegis_dashboard_data.json"
LOG_FILE = "aegis_system.log"

def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def load_logs(lines=50):
    if not os.path.exists(LOG_FILE):
        return "Log file not found."
    try:
        # Read last N lines using a simpler approach for stability
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception as e:
        return f"Error reading logs: {e}"

# --- Dashboard Layout ---

# Sidebar
with st.sidebar:
    st.title("🛡️ AEGIS SYSTEM")
    st.markdown("---")

    # System Status Mockup
    st.subheader("System Status")

    # Check if a python process related to aegis is running
    # This is a simple check, might need refinement for exact process matching
    is_running = os.popen("pgrep -f aegis_main_system.py").read().strip()
    if is_running:
        st.success("🟢 ONLINE")
    else:
        st.error("🔴 OFFLINE")

    st.markdown("---")
    if st.button("🔄 REFRESH DASHBOARD"):
        st.rerun()

    st.markdown("### Manual Override")
    if st.button("🚀 TRIGGER ANALYSIS"):
        # Run in background
        os.system("python aegis_main_system.py &")
        st.toast("System started in background...", icon="🚀")

# Main Content
st.title("AEGIS COMMAND CENTER")
st.markdown(f"**Last Updated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

data = load_data()

if data:
    # --- KPI Row ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Price (USD)", f"${data.get('price', 0):.4f}")
    with col2:
        prob = data.get('prob', 0)
        st.metric("AI Probability", f"{prob:.2f}%", delta_color="normal" if prob > 50 else "inverse")
    with col3:
        fng = data.get('fng', 50)
        st.metric("Fear & Greed", f"{fng}", delta_color="off")
    with col4:
        judgment = data.get('judgment', 'NEUTRAL')
        st.metric("Judgment", judgment)

    # --- Charts Row ---
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2])

    with c1:
        # Probability Gauge
        fig_prob = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = prob,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "AI Bull Probability"},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#00ff41"},
                'bgcolor': "black",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 40], 'color': '#ff3333'},
                    {'range': [40, 60], 'color': '#ffff33'},
                    {'range': [60, 100], 'color': '#33ff33'}],
            }
        ))
        fig_prob.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white", 'family': "Courier New"})
        st.plotly_chart(fig_prob, use_container_width=True)

    with c2:
        # F&G Gauge
        fig_fng = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = fng,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Fear & Greed Index"},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#00ff41"},
                'bgcolor': "black",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 25], 'color': '#ff3333'}, # Extreme Fear
                    {'range': [25, 50], 'color': '#ff9933'}, # Fear
                    {'range': [50, 75], 'color': '#ffff33'}, # Greed
                    {'range': [75, 100], 'color': '#33ff33'}], # Extreme Greed
            }
        ))
        fig_fng.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={'color': "white", 'family': "Courier New"})
        st.plotly_chart(fig_fng, use_container_width=True)

    with c3:
        # Radar Chart for Advanced Metrics
        metrics = data.get('advanced_metrics', {})
        if metrics:
            # Select relevant metrics and normalize if needed or just plot raw values
            # Using absolute values for some, or just plotting a subset
            radar_cols = ['XRP_RSI_14', 'ls_ratio', 'funding_rate']
            # We can also add normalized volatility or momentum if available in the passed dict

            # Since advanced_metrics might have many keys, let's pick a few standard ones plus what we saved
            # Note: ls_ratio and funding_rate are in the top level dict, not necessarily in advanced_metrics (which came from latest_data)
            # Let's construct a display dict

            radar_data = {
                'RSI': data.get('rsi', 50),
                'L/S Ratio': data.get('ls_ratio', 1.0) * 10, # Scale up for visibility
                'Funding Rate': data.get('funding_rate', 0) * 1000, # Scale up
                'Fear Index': data.get('fng', 50),
                'Prob': data.get('prob', 50)
            }

            fig_radar = go.Figure(data=go.Scatterpolar(
              r=list(radar_data.values()),
              theta=list(radar_data.keys()),
              fill='toself',
              line_color='#00ff41'
            ))

            fig_radar.update_layout(
              polar=dict(
                radialaxis=dict(
                  visible=True,
                  range=[0, 100] # Adjust range as needed
                ),
                bgcolor='#1f1f1f'
              ),
              paper_bgcolor="rgba(0,0,0,0)",
              font={'color': "white", 'family': "Courier New"},
              title="Multi-Dimensional Analysis (NDA)"
            )
            st.plotly_chart(fig_radar, use_container_width=True)
        else:
            st.info("No Advanced Metrics Available")

    # --- Tabs ---
    tab1, tab2, tab3 = st.tabs(["📝 AI REPORT", "💻 SYSTEM LOGS", "💾 RAW DATA"])

    with tab1:
        st.markdown("### 🧠 Gemini Insight")
        report_text = data.get('report', "No report available.")
        st.markdown(report_text)

    with tab2:
        st.markdown("### 🖥️ Real-time Logs")
        logs = load_logs()
        st.code(logs, language='bash')

    with tab3:
        st.json(data)

else:
    st.warning("⚠️ No Dashboard Data Found. Run the AEGIS System first.")
    if st.button("Initialize System Now"):
        os.system("python aegis_main_system.py &")
        st.info("System initializing... please wait and refresh.")
