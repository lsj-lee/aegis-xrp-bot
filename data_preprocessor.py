import pandas as pd
import yfinance as yf
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_advanced_features(df):
    """
    7가지 타임프레임(Micro, Meso, Macro)에 대한 심층 지표를 계산합니다.
    """
    # [Micro] 1d, 7d
    df['XRP_Vol_7d'] = df['XRP'].pct_change().rolling(7).std()
    df['XRP_Momentum_7d'] = df['XRP'].pct_change(7)

    # [Meso] 14d, 30d
    df['MA14'] = df['XRP'].rolling(14).mean()
    # MA30 already calculated in main function, but let's be safe
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

# 🔴 메인 시스템이 찾을 수 있도록 이름을 'preprocess_for_dl'로 되돌렸습니다.
def preprocess_for_dl():
    print("⚙️ AEGIS 3.0 [2단계] 다차원 시공간 데이터 전처리 시작...")
    
    # 안정적인 8년치 데이터를 직접 수집하여 시공간 지표 생성
    tickers = {'XRP': 'XRP-USD', 'DXY': 'DX-Y.NYB', 'NASDAQ': '^IXIC'}
    df = pd.DataFrame()
    for name, ticker in tickers.items():
        data = yf.download(ticker, period="8y", interval='1d', progress=False)
        if not data.empty:
            df[name] = data['Close']
    df.ffill(inplace=True)
    
    # 🚀 [핵심] 14가지 다차원 시공간 지표(Features) 생성 (Legacy)
    df['XRP_Return_1d'] = df['XRP'].pct_change()
    df['XRP_Vol_1d'] = df['XRP_Return_1d'].abs() # 단기 변동성
    df['Ret_Week'] = df['XRP'].pct_change(7)
    df['Ret_Month'] = df['XRP'].pct_change(30)
    df['Ret_3Month'] = df['XRP'].pct_change(90)
    df['Ret_6Month'] = df['XRP'].pct_change(180)
    df['Ret_Year'] = df['XRP'].pct_change(365)
    
    df['MA7'] = df['XRP'].rolling(7).mean()
    df['MA30'] = df['XRP'].rolling(30).mean()
    df['MA90'] = df['XRP'].rolling(90).mean()
    df['MA180'] = df['XRP'].rolling(180).mean()
    df['MA200'] = df['XRP'].rolling(200).mean()
    
    df['XRP_RSI_14'] = calculate_rsi(df['XRP'])
    df['DXY_Return_1d'] = df['DXY'].pct_change()
    df['NASDAQ_Return_1d'] = df['NASDAQ'].pct_change()
    
    # 🚀 [업그레이드] 다차원 시공간 심층 지표 추가 (Micro/Meso/Macro)
    df = calculate_advanced_features(df)

    # 정답지 라벨링 (3일 내 2% 이상 상승 시 1)
    df['Future_XRP_3d'] = df['XRP'].shift(-3)
    df['Target_Buy_Signal'] = np.where(df['Future_XRP_3d'] > df['XRP'] * 1.02, 1, 0)
    
    df = df.dropna()
    
    save_path = os.path.expanduser("~/Desktop/xrp_research/ml_ready_data.csv")
    # For CI/CD or repo environment fallback
    if not os.path.exists(os.path.dirname(save_path)):
        save_path = "ml_ready_data.csv"

    df.to_csv(save_path)
    print(f"✅ 전처리 완료! 다차원 학습 데이터 수: {len(df)}세트")

if __name__ == "__main__":
    preprocess_for_dl()
