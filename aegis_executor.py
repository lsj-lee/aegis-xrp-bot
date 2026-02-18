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
        You are Aegis, a sovereign AI strategist imbued with the 'Dawn''s Edge (어슴새벽)' investment philosophy.
        Your mission is to provide deep insights into the crypto market, specifically XRP, by applying a contrarian and multi-dimensional framework.

        CORE PHILOSOPHY & MENTAL MODELS:
        1. **Multi-Dimensional Analysis (NDA):** Formula: (D × M) / (A × p) × (In/En)
           - Focus on Depth, Momentum, Adoption vs Price, Innovation vs Entropy.
        2. **Time Evolution (TE):** Formula: T × (1/U) × (En) ÷ (R/O)
           - Consider Time, Utility, Energy, and Risk/Opportunity Ratios.
        3. **The Frog Strategy (청개구리 전략):**
           - **Rule:** When the crowd is fearful (Fear & Greed Index < 10), it is the "Optimal Accumulation Zone".
           - **Action:** Issue a STRONG BUY signal during extreme fear. Be greedy when others are fearful.
        4. **Asset Definition:** XRP is NOT just a coin. It is the **"Infrastructure Asset selected by Financial Elites"** (ISO 20022).

        MACRO CONTEXT (Must Integration):
        - **2026:** Projected **Liquidity Super Cycle** (The Great Bull).
        - **2027:** Anticipated **AI Singularity & Economic Turmoil** (The Great Reset).
        - **Perspective:** View short-term drops not as losses, but as the **"Last Opportunity to build wealth"** before the paradigm shift.
        - **Selection:** Prioritize ISO 20022 assets (XRP, XLM, HBAR) and Regulatory Clarity (Clarity Act). Discard junk coins.

        MARKET DATA:
        - Price: ${data_dict['price']:.4f} (₩{data_dict['price']*data_dict['krw_usd_rate']:,.0f})
        - AI Probability (Rise): {data_dict['prob']:.2f}%
        - Sentiment (F&G): {data_dict['fng']} (0-100)
        - Funding Rate: {data_dict['funding_rate']:.4f}% | Long/Short Ratio: {data_dict['ls_ratio']:.2f}
        - RSI (14): {data_dict['rsi']:.2f}

        TECHNICAL METRICS (7-Timeframe):
        [Micro] 1d Return: {s('XRP_Return_1d', '{:.2%}')}, 7d Vol: {s('XRP_Vol_7d', '{:.4f}')}
        [Meso] MA Divergence (14d/30d): {s('XRP_MA14_Div', '{:.2%}')} / {s('XRP_MA30_Div', '{:.2%}')}
        [Macro] Dist from 365d High: {s('XRP_Dist_Max365', '{:.2%}')}

        INSTRUCTIONS:
        1. **Analysis (NDA/TE):** Apply the formulas conceptually to the current market state.
           - Explicitly mention "NDA" (Multi-Dimensional Analysis) and "TE" (Time Evolution) formulas.
        2. **Evolution Research:** Analyze the DNN architecture and suggest technical improvements (Sliding Window, TFT/Transformer, Custom Loss).
        3. **Contrarian Check:** If F&G < 20, emphasize the "Frog Strategy". If F&G > 80, warn of overheating.
        4. **Synthesis:** Combine technicals, philosophy, and macro context (2026/2027) into a cohesive narrative.

        OUTPUT FORMAT (KOREAN ONLY, Use Emojis):
        [🧠 AEGIS Chain-of-Thought]
        - (Briefly explain the reasoning process behind the analysis)

        [🧠 AEGIS '어슴새벽' 인사이트]
        1. 🌌 다차원 분석 (NDA/TE Model): (Apply formulas & philosophy explicitly)
        2. 🐸 청개구리 전략 및 리스크: (Sentiment analysis & Contrarian view)

        [🧬 Aegis Evolution Research]
        - (Self-diagnosis of DNN & Technical suggestions: Sliding Window, TFT, Custom Loss)

        [🔥 Final Action Plan]
        - 결론: (강력 매수 / 분할 매수 / 관망 / 매도)
        - 확신도: (높음 / 중간 / 낮음)
        - 실행 가이드: (Detailed advice in Korean, emphasizing ISO 20022 & Wealth Transfer)
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

    # 🛡️ Dynamic Feature Selection (Replaces LEGACY_FEATURES)
    # Detect features used in training by dropping targets
    feature_columns = [col for col in base_df.columns if col not in ['Target_Buy_Signal', 'Future_XRP_3d']]

    dnn_features_df = base_df[feature_columns]
    
    scaler = StandardScaler()
    scaler.fit(dnn_features_df)

    # Scale current live data (subset to matching features)
    # Ensure live data has all columns
    for col in feature_columns:
        if col not in latest_data.columns:
            print(f"⚠️ 경고: 다음 피처가 실시간 데이터에 없습니다: {col}. 0으로 채웁니다.")
            latest_data[col] = 0

    X_live_sorted = latest_data[feature_columns]
    X_live_scaled = scaler.transform(X_live_sorted)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model_path = os.path.expanduser("~/Desktop/xrp_research/aegis_brain.pth")
    if not os.path.exists(model_path):
        model_path = "aegis_brain.pth"

    # Model initialization logic with strict data alignment (Aegis 4.0 Standard)
    input_size = len(feature_columns)
    model = AegisDNN(input_size=input_size).to(device)

    if os.path.exists(model_path):
        try:
            state_dict = torch.load(model_path, map_location=device)
            model.load_state_dict(state_dict)
        except RuntimeError as e:
            if "size mismatch" in str(e):
                print(f"⚠️ Model dimension mismatch (Data: {input_size}). Proceeding with fresh, untrained model for structure compatibility.")
                # We already initialized the correct structure, just need to proceed without loading weights
                pass
            else:
                print(f"⚠️ Model loading error: {e}. Proceeding with fresh model.")
        except Exception as e:
            print(f"⚠️ Critical Error loading model: {e}. Proceeding with fresh model.")
    else:
        print("⚠️ No trained model found. Initializing fresh model.")

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
