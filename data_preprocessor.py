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
    
    # 🚀 [핵심] 14가지 다차원 시공간 지표(Features) 생성
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
    
    # 정답지 라벨링 (3일 내 2% 이상 상승 시 1)
    df['Future_XRP_3d'] = df['XRP'].shift(-3)
    df['Target_Buy_Signal'] = np.where(df['Future_XRP_3d'] > df['XRP'] * 1.02, 1, 0)
    
    df = df.dropna()
    
    save_path = os.path.expanduser("~/Desktop/xrp_research/ml_ready_data.csv")
    df.to_csv(save_path)
    print(f"✅ 전처리 완료! 다차원 학습 데이터 수: {len(df)}세트")

if __name__ == "__main__":
    preprocess_for_dl()