import pandas as pd
import yfinance as yf
import requests
import datetime
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
import os
import warnings
import numpy as np
import sys

# Try importing shared logic from data_preprocessor
try:
    from data_preprocessor import calculate_advanced_features
except ImportError:
    # Fallback definition if import fails (e.g. running in different env)
    def calculate_advanced_features(df):
        """
        7가지 타임프레임(Micro, Meso, Macro)에 대한 심층 지표를 계산합니다.
        (Fallback Local Definition)
        """
        # [Micro] 1d, 7d
        df['XRP_Vol_7d'] = df['XRP'].pct_change().rolling(7).std()
        df['XRP_Momentum_7d'] = df['XRP'].pct_change(7)

        # [Meso] 14d, 30d
        df['MA14'] = df['XRP'].rolling(14).mean()
        if 'MA30' not in df.columns:
            df['MA30'] = df['XRP'].rolling(30).mean()

        df['XRP_MA14_Div'] = (df['XRP'] - df['MA14']) / df['MA14']
        df['XRP_MA30_Div'] = (df['XRP'] - df['MA30']) / df['MA30']

        # Bollinger Bands (30d, 2std) for Meso Volatility
        rolling_mean = df['XRP'].rolling(window=30).mean()
        rolling_std = df['XRP'].rolling(window=30).std()
        df['XRP_BB_Upper'] = rolling_mean + (rolling_std * 2)
        df['XRP_BB_Lower'] = rolling_mean - (rolling_std * 2)
        df['XRP_BB_Width'] = (df['XRP_BB_Upper'] - df['XRP_BB_Lower']) / rolling_mean

        # [Macro] 90d, 180d, 365d
        for window in [90, 180, 365]:
            df[f'XRP_Max{window}'] = df['XRP'].rolling(window).max()
            df[f'XRP_Min{window}'] = df['XRP'].rolling(window).min()
            df[f'XRP_Dist_Max{window}'] = (df['XRP'] - df[f'XRP_Max{window}']) / df[f'XRP_Max{window}']
            df[f'XRP_Dist_Min{window}'] = (df['XRP'] - df[f'XRP_Min{window}']) / df[f'XRP_Min{window}']

        return df

try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    genai = None

warnings.filterwarnings('ignore')

# 🔑 보안 강화
def load_api_key():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.strip().split("=")[1]
    return os.getenv("GEMINI_API_KEY")

GEMINI_API_KEY = load_api_key()
client = None
if HAS_GEMINI and GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ Client 초기화 오류: {e}")
        client = None
elif HAS_GEMINI and not GEMINI_API_KEY:
    print("⚠️ 경고: API 키를 찾을 수 없습니다. .env 파일을 확인하세요.")
elif not HAS_GEMINI:
    print("⚠️ 경고: google-genai 모듈이 설치되지 않았습니다. AI 분석 기능이 제한됩니다.")

# 🏗️ Legacy DNN Model Architecture
class AegisDNN(nn.Module):
    def __init__(self, input_size):
        super(AegisDNN, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    def forward(self, x): return self.network(x)

# 🛠️ Data Helpers
def get_upbit_krw_price():
    try:
        url = "https://api.upbit.com/v1/ticker?markets=KRW-XRP"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        return float(data[0]['trade_price'])
    except Exception as e:
        print(f"⚠️ Upbit 가격 조회 실패: {e}")
        return None

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 🧬 Features used by the pre-trained AegisDNN (Do not change order or content without retraining)
LEGACY_FEATURES = [
    'XRP', 'DXY', 'NASDAQ',
    'XRP_Return_1d', 'XRP_Vol_1d',
    'Ret_Week', 'Ret_Month', 'Ret_3Month', 'Ret_6Month', 'Ret_Year',
    'MA7', 'MA30', 'MA90', 'MA180', 'MA200',
    'XRP_RSI_14', 'DXY_Return_1d', 'NASDAQ_Return_1d'
]

def get_gemini_insight(data_dict, am):
    if not HAS_GEMINI:
        return "[🧠 AI 직관] Google Generative AI 모듈 미설치로 분석 불가."
    if not client:
        return "[🧠 AI 직관] Client 초기화 실패로 분석 불가."
    try:
        # Safe access to dict keys (am = advanced metrics)
        def s(key, fmt="{:.4f}"): return fmt.format(am.get(key, 0))

        prompt = f"""
        ROLE:
        You are Aegis, a sovereign AI agent specializing in XRP market analysis. You operate with a "Multi-Dimensional Space-Time" analysis framework.

        CONTEXT:
        Current Price: ${data_dict['price']:.4f} (KRW 1 XRP = {data_dict['krw_usd_rate']:.2f} KRW)
        Machine Learning Probability of Rise (3-day): {data_dict['prob']:.2f}%
        Market Sentiment (Fear & Greed): {data_dict['fng']}
        Funding Rate: {data_dict['funding_rate']:.4f}% | Long/Short Ratio: {data_dict['ls_ratio']:.2f}

        DATA INPUTS (7-Timeframe Analysis):

        [Micro - Short Term Volatility & Momentum (1d, 7d)]
        - 1d Return: {s('XRP_Return_1d', '{:.2%}')}
        - 7d Volatility: {s('XRP_Vol_7d', '{:.4f}')}
        - 7d Momentum (ROC): {s('XRP_Momentum_7d', '{:.2%}')}
        - RSI (14d): {s('XRP_RSI_14', '{:.2f}')}

        [Meso - Trend & Pattern (14d, 30d)]
        - MA14 Divergence: {s('XRP_MA14_Div', '{:.2%}')}
        - MA30 Divergence: {s('XRP_MA30_Div', '{:.2%}')}
        - Bollinger Band Width (30d): {s('XRP_BB_Width', '{:.4f}')} (Lower implies squeeze)

        [Macro - Cycle & Relative Position (90d, 180d, 365d)]
        - Distance from 90d High: {s('XRP_Dist_Max90', '{:.2%}')} | Low: {s('XRP_Dist_Min90', '{:.2%}')}
        - Distance from 365d High: {s('XRP_Dist_Max365', '{:.2%}')} | Low: {s('XRP_Dist_Min365', '{:.2%}')}
        - Long Term Trend (Price vs MA200): {"Above" if am.get('XRP',0) > am.get('MA200',0) else "Below"}

        INSTRUCTIONS:
        1. **Perception (Analysis):** Analyze each timeframe layer independently. What is the story of the Micro, Meso, and Macro data?
        2. **Criticism (Reflexion):** Adopt a "Devil's Advocate" persona (Multi-Agent Critic). Criticize your own initial perception. Are you overreacting to short-term noise? Are you ignoring a macro downtrend? Is the machine probability ({data_dict['prob']:.2f}%) trustworthy given the funding rates?
        3. **Synthesis (Conclusion):** Synthesizing the analysis and the critique, provide a final actionable conclusion.

        OUTPUT FORMAT:
        [🧠 AEGIS Chain-of-Thought]
        1. 🔍 Micro/Meso/Macro Analysis: (Brief bullet points summarizing the 3 layers)
        2. ⚖️ Critic's Review: (Counter-arguments and risk assessment)

        [🔥 Final Action Plan]
        - Verdict: (Buy / Sell / Wait)
        - Confidence: (Low / Medium / High)
        - Strategy: (Specific guidance)
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"[🧠 AI 직관] 연결 장애: {e}"

def run_daily_execution():
    print("🔮 [AEGIS 3.0 DNN & Gemini 하이브리드 - 보안 모드 가동]")
    
    tickers = {'XRP': 'XRP-USD', 'DXY': 'DX-Y.NYB', 'NASDAQ': '^IXIC', 'USDKRW': 'KRW=X'}
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.datetime.now() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
    
    df = pd.DataFrame()
    for name, ticker in tickers.items():
        data = yf.download(ticker, start=start_date, end=end_date, interval='1d', progress=False)
        if not data.empty:
            df[name] = data['Close']

    usd_krw_rate = float(df['USDKRW'].dropna().iloc[-1]) if 'USDKRW' in df else 1400.0

    # Market Sentiment & Futures Data
    try:
        response = requests.get("https://api.alternative.me/fng/?limit=2").json()
        current_fng = int(response['data'][0]['value'])
    except:
        current_fng = 50

    try:
        fund_res = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=XRPUSDT", timeout=5).json()
        funding_rate = float(fund_res['lastFundingRate']) * 100
        ls_res = requests.get("https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=XRPUSDT&period=1d&limit=1", timeout=5).json()
        ls_ratio = float(ls_res[0]['longShortRatio'])
    except:
        funding_rate = 0.01; ls_ratio = 1.0

    df.ffill(inplace=True)
    ml_df = pd.DataFrame()
    ml_df['XRP'] = df['XRP']; ml_df['DXY'] = df['DXY']; ml_df['NASDAQ'] = df['NASDAQ']

    # Legacy Feature Calculation
    ml_df['XRP_Return_1d'] = df['XRP'].pct_change()
    ml_df['XRP_Vol_1d'] = ml_df['XRP_Return_1d'].abs()
    ml_df['Ret_Week'] = df['XRP'].pct_change(7); ml_df['Ret_Month'] = df['XRP'].pct_change(30)
    ml_df['Ret_3Month'] = df['XRP'].pct_change(90); ml_df['Ret_6Month'] = df['XRP'].pct_change(180)
    ml_df['Ret_Year'] = df['XRP'].pct_change(365)
    ml_df['MA7'] = df['XRP'].rolling(7).mean(); ml_df['MA30'] = df['XRP'].rolling(30).mean()
    ml_df['MA90'] = df['XRP'].rolling(90).mean(); ml_df['MA180'] = df['XRP'].rolling(180).mean()
    ml_df['MA200'] = df['XRP'].rolling(200).mean(); ml_df['XRP_RSI_14'] = calculate_rsi(df['XRP'])
    ml_df['DXY_Return_1d'] = df['DXY'].pct_change(); ml_df['NASDAQ_Return_1d'] = df['NASDAQ'].pct_change()

    # 🚀 Advanced Feature Calculation (for Gemini)
    ml_df = calculate_advanced_features(ml_df)

    latest_data = ml_df.dropna().iloc[-1:]
    current_price = latest_data['XRP'].values[0]

    # 🇰🇷 [업비트 원화 가격 조회 및 김치프리미엄 반영 환율 계산]
    upbit_price = get_upbit_krw_price()
    if upbit_price and current_price > 0:
        krw_usd_rate = upbit_price / current_price  # 실질 환율 (김프 포함)
    else:
        krw_usd_rate = usd_krw_rate

    ma200 = latest_data['MA200'].values[0]
    rsi_val = latest_data['XRP_RSI_14'].values[0]

    # Load Base Data for Scaling (Handling new columns in CSV)
    data_path = os.path.expanduser("~/Desktop/xrp_research/ml_ready_data.csv")
    if not os.path.exists(data_path):
        data_path = "ml_ready_data.csv"

    base_df = pd.read_csv(data_path, index_col='Date', parse_dates=True)

    # 🛡️ STRICTLY Select Legacy Features for DNN
    # We verify that LEGACY_FEATURES exist in base_df.
    # If base_df has new columns (from upgraded preprocessor), we ignore them here.
    dnn_features_df = base_df[LEGACY_FEATURES]
    
    scaler = StandardScaler()
    scaler.fit(dnn_features_df)

    # Scale current live data (subset to legacy features)
    X_live_legacy = latest_data[LEGACY_FEATURES]
    X_live_scaled = scaler.transform(X_live_legacy)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model_path = os.path.expanduser("~/Desktop/xrp_research/aegis_brain.pth")
    if not os.path.exists(model_path):
        model_path = "aegis_brain.pth"

    # Model expects input size corresponding to LEGACY_FEATURES
    model = AegisDNN(input_size=len(LEGACY_FEATURES)).to(device)

    # If the model file exists, load it.
    if os.path.exists(model_path):
        try:
            model.load_state_dict(torch.load(model_path, map_location=device))
        except RuntimeError as e:
            print(f"⚠️ 모델 로드 경고: {e}. (재학습 필요할 수 있음)")

    model.eval()

    with torch.no_grad():
        prediction = model(torch.tensor(X_live_scaled, dtype=torch.float32).to(device)).item()
    prob_percent = prediction * 100

    # 타점 계산 로직
    st_buy = current_price * 0.95; st_sell = current_price * 1.15
    mt_buy = current_price * 0.85; mt_sell = current_price * 1.45
    lt_buy = current_price * 0.70; lt_sell_final = 5.89

    def fmt_price(usd_price):
        krw_price = usd_price * krw_usd_rate
        return f"${usd_price:.2f} (₩{krw_price:,.0f})"

    # 경보 로직
    warning_msg = "🟢 시장 안정"
    if ls_ratio > 2.5:
        warning_msg = "🔴 롱 스퀴즈 경보 (Long Squeeze)"
    elif ls_ratio < 0.5:
        warning_msg = "🔴 숏 스퀴즈 경보 (Short Squeeze)"
    if abs(funding_rate) > 0.05:
        warning_msg += " / 🟠 펀딩비 과열"

    code_analysis = f"""[🎯 타점 분석 (Timeframe Zone)]
⚡ 단기 (1~2주): 매수 {fmt_price(st_buy)} / 매도 {fmt_price(st_sell)}
🌊 중기 (1~3개월): 매집 {fmt_price(mt_buy)} / 익절 {fmt_price(mt_sell)}
🌌 장기 (6개월+): 최후선 {fmt_price(lt_buy)} / 목표 {fmt_price(lt_sell_final)}

[🤖 DNN & 선물 지표]
- 확률: {prob_percent:.2f}% / 롱숏: {ls_ratio:.2f} / 펀딩: {funding_rate:.4f}%

[⚠️ 시장 경보]
{warning_msg}"""

    analysis_data = {
        'price': current_price, 'prob': prob_percent, 'funding_rate': funding_rate, 
        'ls_ratio': ls_ratio, 'long_term': "상승" if current_price > ma200 else "하락",
        'fng': current_fng, 'rsi': rsi_val, 'krw_usd_rate': krw_usd_rate
    }
    
    # Convert latest_data row to dict for Gemini
    advanced_metrics = latest_data.to_dict(orient='records')[0]

    gemini_analysis = get_gemini_insight(analysis_data, advanced_metrics)
    
    return {
        'date': end_date, 'price': current_price, 'fng': current_fng,
        'prob': prob_percent, 'decision': "분석 완료", 'long_term': analysis_data['long_term'],
        'commentary': f"{code_analysis}\n\n{gemini_analysis}"
    }

if __name__ == "__main__":
    result = run_daily_execution()
    print("\n" + result['commentary'])
