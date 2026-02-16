# framework.py

def calculate_longterm_sync_score(data):
    """최대 기간 데이터를 바탕으로 2020년 폭등장 직전의 거시 패턴과 대조"""
    points = 0
    total = 4
    
    # 1. 달러 약세 진입 확인 (현재가가 200일 장기 추세선 아래에 있는가?)
    if data['DXY'] < data['DXY_200ma']: points += 1
    
    # 2. 산업 유동성 강세 확인 (구리/금 비율이 높은가?)
    if data['copper_gold_ratio'] > 0.16: points += 1
    
    # 3. 침팬지 털기(역행) 확인 (과매도 상태인가?)
    if data['fng'] <= 25 and data['xrp_rsi'] <= 40: points += 1
    
    # 4. 위험자산 선호장 확인 (러셀이 선방하는가?)
    if data['russell_sp_ratio'] > 0.35: points += 1
    
    return (points / total) * 100

def get_macro_score(data, sync_val):
    """어슴새벽 가치관을 반영한 매크로 총점 (최대 22점)"""
    score = 10 # 기본 인프라 설계 점수
    
    if data['fng'] <= 15: score += 4
    if data['DXY'] < data['DXY_200ma']: score += 3 # 달러 대세 하락장
    if sync_val >= 75: score += 3 # 2020 프랙탈 일치
    if data['price'] < data['xrp_200ma']: score += 2 # XRP 장기 저평가 구간
    
    return score