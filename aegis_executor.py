import pandas as pd
import yfinance as yf
import requests
import datetime
import json
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

# 🧬 AEGIS Evolution Architecture (Transformer/TFT Based)
class AegisEvolution(nn.Module):
    def __init__(self, input_size, d_model=128, nhead=4, num_layers=3, dropout=0.2):
        super(AegisEvolution, self).__init__()

        # Feature Embedding Layer (Dense -> High Dim)
        self.feature_embedding = nn.Sequential(
            nn.Linear(input_size, d_model),
            nn.LayerNorm(d_model),
            nn.GELU()
        )

        # Transformer Encoder Block (Self-Attention + FeedForward)
        # batch_first=True ensures input is (Batch, Seq, Feature)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model*4,
            dropout=dropout,
            batch_first=True,
            activation='gelu'
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # Final Output Head (Value Projection)
        self.head = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        # x: (Batch, Input_Size)

        # 1. Embed Features
        x = self.feature_embedding(x) # -> (Batch, d_model)

        # 2. Add Sequence Dimension for Transformer (SeqLen=1)
        x = x.unsqueeze(1) # -> (Batch, 1, d_model)

        # 3. Apply Transformer Encoder
        x = self.transformer_encoder(x) # -> (Batch, 1, d_model)

        # 4. Remove Sequence Dimension
        x = x.squeeze(1) # -> (Batch, d_model)

        # 5. Output Probability
        return self.head(x)

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
    if not client: return "[🧠 AI 직관] Client 초기화 실패."
    try:
        # [Step 1: Quantitative Logic (English)] - Deep Reasoning
        prompt_step_1 = f"""
        Analyze XRP using the following 'Dawn's Edge' logic:
        1. NDA Formula: $NDA = (D \\times M) / (A \\times p) \\times (In/En)$ where D=Duration, M=Momentum, A=Acceleration, p=probability.
        2. TE Formula: $TE = T \\times (1/U) \\times (En) \\div (R/O)$ where T=Time, U=Uncertainty, En=Entropy, R/O=Risk/Opportunity.

        Current Stats:
        - Price: ${data_dict['price']:.4f} (KRW {data_dict['price'] * data_dict['krw_usd_rate']:,.0f})
        - Probability: {data_dict['prob']:.2f}%
        - Long/Short Ratio: {data_dict['ls_ratio']:.2f}
        - Fear & Greed: {data_dict['fng']}
        - Funding Rate: {data_dict['funding_rate']:.4f}%
        - RSI: {data_dict['rsi']:.2f}

        Task: Provide a detailed logical deduction in English, explicitly calculating or estimating the values for the variables in the NDA and TE formulas based on the stats.
        """
        res_1 = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_step_1).text

        # [Step 2: AI Evolution Research (English)] - Code Generation
        prompt_step_2 = """
        As an AI Architect, write a Python class for an improved PyTorch model named 'AegisEvolution' to replace the current simple DNN.
        The model MUST be based on Transformer or TFT (Temporal Fusion Transformer) architecture and optimized for MacBook M5 MPS acceleration.

        Requirements:
        1. Class name: `AegisEvolution`
        2. Inherit from `nn.Module`.
        3. `__init__` must accept `input_size` (int).
        4. Use `nn.TransformerEncoder` or similar advanced layers.
        5. Include `forward(self, x)` method.
        6. Ensure input shape handling for (Batch, Input_Size) -> (Batch, Seq, Feature) if needed.

        IMPORTANT: Provide ONLY the executable Python code block. Do not add markdown backticks or explanations.
        """
        res_2 = client.models.generate_content(model='gemini-2.5-flash', contents=prompt_step_2).text

        # 💾 Save Generated Code Proposal (Robust Handling)
        try:
            # Clean up potential markdown formatting
            code_content = res_2.replace("```python", "").replace("```", "").strip()

            with open("aegis_evolution_proposal.py", "w", encoding='utf-8') as f:
                f.write(f"# Auto-generated by AEGIS 4.0 on {datetime.datetime.now()}\n")
                f.write("import torch\nimport torch.nn as nn\nimport math\n\n") # Add common imports
                f.write(code_content)
        except Exception as e:
            print(f"⚠️ Failed to save evolution code: {e}")

        # [Step 3: Final Rigid Assembly (Korean Output)]
        final_prompt = f"""
        You are 'AEGIS 4.0'. Synthesize the following inputs into a formal Korean report.

        Strict Rules:
        1. Use ONLY Korean for headings.
        2. You MUST include the literal formulas $NDA$ and $TE$ in the text and explain their values derived in Step 1.
        3. Strictly Include all technical details from the research/code section.
        4. Do NOT summarize generally; be specific about the formulas and code architecture.

        [Input Analysis from Step 1]: {res_1}
        [Input Code from Step 2]: {res_2}

        REPORT STRUCTURE (Mandatory):
        [🎯 타점 분석]: Summarize price levels and market alerts based on the stats provided.
        [🧠 AEGIS 사고의 사슬]: Translate the Step 1 reasoning into Korean. Explicitly show the $NDA$ and $TE$ formulas and their calculated implications for the current market state (F&G {data_dict['fng']}). Mention 'Frog Strategy' if relevant.
        [🧬 에이지스 진화 연구]: Explain the architectural improvements in the generated code (Step 2) in detail (Korean). Discuss why Transformer/TFT is better than simple DNN for this data.
        [💻 진화 코드 제안]: Display the 'AegisEvolution' class code from Step 2 verbatim.
        [🔥 최종 액션 플랜]: Conclusion (강세/약세/중립), Confidence Level (%), and 4 specific actionable strategies.
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=final_prompt)

        return response.text.strip() if response.text else "Output Blocked by Safety Filter."
    except Exception as e:
        return f"[🧠 AI 직관] 분석 실패: {e}"

def run_daily_execution():
    print("🔮 [AEGIS 4.0 Evolution & Gemini 하이브리드 - 보안 모드 가동]")
    
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
    input_size = X_live_scaled.shape[1]
    model = AegisEvolution(input_size=input_size).to(device)

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

    code_analysis = f"""[🎯 타점 분석] & [🤖 DNN & 선물 지표]
⚡ 단기 (1~2주): 매수 {fmt_price(st_buy)} / 매도 {fmt_price(st_sell)}
🌊 중기 (1~3개월): 매집 {fmt_price(mt_buy)} / 익절 {fmt_price(mt_sell)}
🌌 장기 (6개월+): 최후선 {fmt_price(lt_buy)} / 목표 {fmt_price(lt_sell_final)}
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

    # 💾 Save Dashboard Data (Command Center)
    dashboard_data = {
        'timestamp': datetime.datetime.now().isoformat(),
        'price': current_price,
        'prob': prob_percent,
        'fng': current_fng,
        'ls_ratio': ls_ratio,
        'funding_rate': funding_rate,
        'rsi': rsi_val,
        'advanced_metrics': advanced_metrics,
        'judgment': "BULLISH" if prob_percent > 60 else "BEARISH" if prob_percent < 40 else "NEUTRAL",
        'report': f"{code_analysis}\n\n{gemini_analysis}"
    }
    try:
        with open('aegis_dashboard_data.json', 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Dashboard data save failed: {e}")
    
    return {
        'date': end_date, 'price': current_price, 'fng': current_fng,
        'prob': prob_percent, 'decision': "분석 완료", 'long_term': analysis_data['long_term'],
        'commentary': f"{code_analysis}\n\n{gemini_analysis}"
    }

if __name__ == "__main__":
    result = run_daily_execution()
    print("\n" + result['commentary'])
