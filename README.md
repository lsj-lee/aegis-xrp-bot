# 🛡️ AEGIS (Advanced Strategy Bot) - M5 Edition

**AEGIS**는 최신 MacBook M5 환경에 최적화된 암호화폐(XRP, BTC) 시장 분석 및 전략 수립 봇입니다.
머신러닝(RandomForest)과 생성형 AI(Google Gemini 2.5)를 결합하여 정밀한 매수/매도 타점을 산출하고, 구글 시트를 통해 실시간 리포트를 제공합니다.

## 🚀 주요 기능

1.  **M5 연산 기지 (`data_bank_builder.py`)**
    -   **데이터 수집:** Yahoo Finance(미국장) 및 Upbit(한국장) 실시간 시세 확보.
    -   **머신러닝 분석:** Scikit-learn의 RandomForestRegressor를 활용한 단기 가격 패턴 학습 및 예측.
    -   **데이터 릴레이:** 분석 결과(예측가, 판단 근거)를 Google Sheets(`AEGIS_ML_Storage`)로 전송.

2.  **클라우드 AI 본부 (`aegis_strategy_ai.py`)**
    -   **고도화 분석:** Google Gemini-2.5-flash 모델을 활용하여 머신러닝 데이터와 거시 지표를 종합 분석.
    -   **전략 수립:** 단기/중기/장기 저점(매수) 및 고점(매도) 타점 정밀 산출.
    -   **리포트 발행:** 최종 전략 리포트를 Google Sheets(`AEGIS_Daily_Report Results`)에 기록 및 자율 학습 데이터 축적.

3.  **통합 지휘 시스템 (`aegis_full_test.py`)**
    -   전체 작전(데이터 수집 -> ML 분석 -> AI 전략 수립)을 원클릭으로 수행하는 통합 테스트 스크립트.

## 🛠️ 설치 및 환경 설정 (MacBook M5)

### 1. 필수 요구 사항
-   Python 3.10 이상 (M5 Apple Silicon 호환 확인)
-   Google Cloud Platform 서비스 계정 키 (`.json`)
-   Google Gemini API Key

### 2. 프로젝트 설치
```bash
git clone https://github.com/your-repo/aegis-bot.git
cd aegis-bot
pip install -r requirements.txt
```

### 3. 환경 변수 설정 (`.env`)
프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 아래 정보를 입력하십시오.
`GCP_CREDS_PATH`는 반드시 따옴표 없이 절대 경로 또는 상대 경로로 입력해야 합니다.

```env
# Google Cloud Service Account Key 경로
GCP_CREDS_PATH=./creds/your-service-account-key.json

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here
```

## ⚔️ 실행 방법

### 전체 작전 수행 (권장)
데이터 수집부터 AI 리포트 생성까지 일괄 수행합니다.
```bash
python3 aegis_full_test.py
```

### 개별 모듈 실행
**1단계: 데이터 수집 및 ML 분석**
```bash
python3 data_bank_builder.py
```

**2단계: AI 전략 수립 및 리포트 발행**
(1단계 완료 후 실행)
```bash
python3 aegis_strategy_ai.py
```

### 시스템 점검 (Light Test)
네트워크 연결 없이 로직 및 데이터 구조를 빠르게 점검합니다.
```bash
python3 aegis_light_test.py
```

## 📂 파일 구조
-   `data_bank_builder.py`: 데이터 수집 및 머신러닝 엔진.
-   `aegis_strategy_ai.py`: Gemini AI 기반 전략 생성기.
-   `aegis_full_test.py`: 전체 프로세스 통합 실행 스크립트.
-   `aegis_light_test.py`: 시스템 무결성 점검 스크립트.
-   `requirements.txt`: 의존성 패키지 목록.

---
**System Architecture:** MacBook Pro M5 / Python 3.12 / Scikit-learn / Google Gemini
**Commander:** lsj
