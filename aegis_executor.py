import pandas as pd
import yfinance as yf
import requests
import datetime
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
import os
import warnings
import google.generativeai as genai

warnings.filterwarnings('ignore')

# 🔑 보안 강화: .env 파일이나 시스템 환경 변수에서 키를 읽어옵니다.
# 만약 .env 파일을 쓰려면 'pip install python-dotenv' 후 load_dotenv()를 써야 하지만,
# 일단은 가장 확실하게 파일에서 직접 읽는 안전한 로직을 추가했습니다.
def load_api_key():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    return line.strip().split("=")[1]
    return os.getenv("GEMINI_API_KEY")

GEMINI_API_KEY = load_api_key()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠️ 경고: API 키를 찾을 수 없습니다. .env 파일을 확인하세요.")

class AegisDNN(nn.Module):
    def __init__(self, input_size):
        super(AegisDNN, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.BatchNorm1d(256),
            # nn.BatchNorm1d(256)은 입력 데이터의 스케일을 조절하여 학습 안정성을 높임
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

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_gemini_insight(data_dict):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        당신은 상위 1% 암호화폐 퀀트 애널리스트입니다.
        아래 데이터를 바탕으로 다음 세 가지 스케일(단/중/장기)에 맞춘 분석 리포트를 작성해주세요.

        출력 형식:
        [🧠 타임프레임별 거시 분석 (Gemini)]
        - 단기 (1~2주): (단기 변동성 및 청산 가능성 분석)
        - 중기 (1~3개월): (추세 및 매집/스윙 분석)
        - 장기 (6개월~1년 이상): (거시적 사이클 및 장기 시나리오)

        [🔥 최종 종합 액션 플랜]
        (기계 확률 {data_dict['prob']:.2f}%를 근거로 단호한 지시)

        [데이터 요약]
        - 현재가: ${data_dict['price']:.4f}, 확률: {data_dict['prob']:.2f}%
        - 펀딩비율: {data_dict['funding_rate']:.4f}%, 롱/숏 비율: {data_dict['ls_ratio']:.2f}
        """
        return model.generate_content(prompt).text.strip()
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
    ml_df['XRP_Return_1d'] = df['XRP'].pct_change()
    ml_df['XRP_Vol_1d'] = ml_df['XRP_Return_1d'].abs()
    ml_df['Ret_Week'] = df['XRP'].pct_change(7); ml_df['Ret_Month'] = df['XRP'].pct_change(30)
    ml_df['Ret_6Month'] = df['XRP'].pct_change(180); ml_df['Ret_Year'] = df['XRP'].pct_change(365)
    ml_df['MA7'] = df['XRP'].rolling(7).mean(); ml_df['MA30'] = df['XRP'].rolling(30).mean()
    ml_df['MA200'] = df['XRP'].rolling(200).mean(); ml_df['XRP_RSI_14'] = calculate_rsi(df['XRP'])
    ml_df['DXY_Return_1d'] = df['DXY'].pct_change(); ml_df['NASDAQ_Return_1d'] = df['NASDAQ'].pct_change()

    latest_data = ml_df.dropna().iloc[-1:]
    current_price = latest_data['XRP'].values[0]
    ma200 = latest_data['MA200'].values[0]
    rsi_val = latest_data['XRP_RSI_14'].values[0]

    base_df = pd.read_csv(os.path.expanduser("~/Desktop/xrp_research/ml_ready_data.csv"), index_col='Date', parse_dates=True)
    features = base_df.drop(columns=['Target_Buy_Signal', 'Future_XRP_3d'], errors='ignore')
    
    scaler = StandardScaler()
    scaler.fit(features)
    X_live_scaled = scaler.transform(latest_data[features.columns])

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model_path = os.path.expanduser("~/Desktop/xrp_research/aegis_brain.pth")
    model = AegisDNN(input_size=X_live_scaled.shape[1]).to(device)
    model.load_state_dict(torch.load(model_path))
    model.eval()

    with torch.no_grad():
        prediction = model(torch.tensor(X_live_scaled, dtype=torch.float32).to(device)).item()
    prob_percent = prediction * 100

    # 타점 계산 로직 (기존과 동일)
    st_buy = current_price * 0.95; st_sell = current_price * 1.15
    mt_buy = current_price * 0.85; mt_sell = current_price * 1.45
    lt_buy = current_price * 0.70; lt_sell_final = 5.89

    # 경보 로직 추가
    warning_msg = "🟢 시장 안정"
    if ls_ratio > 2.5:
        warning_msg = "🔴 롱 스퀴즈 경보 (Long Squeeze)"
    elif ls_ratio < 0.5:
        warning_msg = "🔴 숏 스퀴즈 경보 (Short Squeeze)"
    if abs(funding_rate) > 0.05:
        warning_msg += " / 🟠 펀딩비 과열"

    code_analysis = f"""[🎯 타점 분석 (Timeframe Zone)]
⚡ 단기 (1~2주): 매수 ${st_buy:.2f} / 매도 ${st_sell:.2f}
🌊 중기 (1~3개월): 매집 ${mt_buy:.2f} / 익절 ${mt_sell:.2f}
🌌 장기 (6개월+): 최후선 ${lt_buy:.2f} / 목표 ${lt_sell_final}

[🤖 DNN & 선물 지표]
- 확률: {prob_percent:.2f}% / 롱숏: {ls_ratio:.2f} / 펀딩: {funding_rate:.4f}%

[⚠️ 시장 경보]
{warning_msg}"""

    analysis_data = {
        'price': current_price, 'prob': prob_percent, 'funding_rate': funding_rate, 
        'ls_ratio': ls_ratio, 'long_term': "상승" if current_price > ma200 else "하락",
        'fng': current_fng, 'rsi': rsi_val
    }
    
    gemini_analysis = get_gemini_insight(analysis_data)
    
    return {
        'date': end_date, 'price': current_price, 'fng': current_fng,
        'prob': prob_percent, 'decision': "분석 완료", 'long_term': analysis_data['long_term'],
        'commentary': f"{code_analysis}\n\n{gemini_analysis}"
    }

if __name__ == "__main__":
    run_daily_execution()