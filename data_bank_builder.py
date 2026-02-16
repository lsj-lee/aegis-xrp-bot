import pandas as pd
import yfinance as yf
import requests
import datetime
import time
import os
import json

def load_asset_list():
    # asset_list.json 파일을 읽어오는 함수
    file_path = os.path.expanduser("~/Desktop/xrp_research/asset_list.json")
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            # base_assets와 macro_indicators를 하나로 합침
            combined_tickers = {**data.get('base_assets', {}), **data.get('macro_indicators', {})}
            return combined_tickers
    except FileNotFoundError:
        print("⚠️ asset_list.json 파일을 찾을 수 없어 기본값으로 작동합니다.")
        return {"XRP": "XRP-USD", "BTC": "BTC-USD"}

def build_aegis_data_bank():
    print("🚀 AEGIS 3.0 [1단계] 목록 파일 기반 데이터 수집 시작...")
    
    # 1. 외부 파일에서 수집 목록 가져오기
    tickers = load_asset_list()
    
    end_date = datetime.datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.datetime.now() - datetime.timedelta(days=10*365)).strftime('%Y-%m-%d')

    main_df = pd.DataFrame()

    # 2. 목록에 있는 자산들 순차적으로 수집
    for name, ticker in tickers.items():
        print(f"📡 {name} ({ticker}) 데이터 수집 중...")
        try:
            data = yf.download(ticker, start=start_date, end=end_date, interval='1d')
            if not data.empty:
                main_df[name] = data['Close']
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ {name} 수집 실패: {e}")

    # 3. 특수 지표 계산 (목록에 GOLD와 COPPER가 있을 경우에만 실행)
    if 'GOLD' in main_df.columns and 'COPPER' in main_df.columns:
        main_df['Gold_Copper_Ratio'] = main_df['GOLD'] / main_df['COPPER']
    
    # 4. 공포지수 수집 (이것은 API 주소가 고정이라 그대로 유지)
    print("😨 공포·탐욕 지수 수집 중...")
    try:
        fng_url = "https://api.alternative.me/fng/?limit=1100"
        response = requests.get(fng_url).json()
        fng_list = [{'Date': datetime.datetime.fromtimestamp(int(d['timestamp'])).strftime('%Y-%m-%d'), 
                     'Fear_Greed': int(d['value'])} for d in response['data']]
        fng_df = pd.DataFrame(fng_list).set_index('Date')
        fng_df.index = pd.to_datetime(fng_df.index)
        main_df = main_df.join(fng_df, how='left')
    except: pass

    # 5. 데이터 정제 및 저장
    main_df.ffill(inplace=True)
    main_df.dropna(inplace=True)

    output_path = os.path.expanduser("~/Desktop/xrp_research/historical_data_3y.csv")
    main_df.to_csv(output_path)
    
    print(f"\n✅ 구축 완료! 수집된 지표: {list(main_df.columns)}")

if __name__ == "__main__":
    build_aegis_data_bank()