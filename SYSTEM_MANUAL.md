# 🛡️ AEGIS 시스템 단계별 기능 설명서 (Unified System Manual v4.0)

본 문서는 AEGIS(Advanced Evolutionary General Intelligence System)의 전체 코드 구조와 각 파일의 기능, 그리고 상호작용 흐름을 단계별로 설명합니다.

---

## 1. 시스템 개요 (System Overview)

AEGIS는 **XRP 시세 예측 및 자동 매매 전략 수립**을 위한 인공지능 시스템입니다.
이 시스템은 단순한 데이터 분석을 넘어, **Gemini AI를 활용한 코드 자가 진화(Self-Evolution)**, GitHub Pull Request 자동 생성, Streamlit 기반의 대시보드 제어 기능을 통합하여 지속적으로 성장하는 구조를 갖추고 있습니다.

---

## 2. 핵심 파일 및 기능 분석 (Key Components)

### 2.1. `aegis_main_system.py` (중앙 통제 시스템)
시스템의 메인 진입점(Entry Point)이자 오케스트레이터입니다.

*   **기능**:
    *   전체 파이프라인(`Data` -> `Preprocess` -> `Train` -> `Evolve` -> `Report`)을 순차적으로 실행합니다.
    *   `subprocess`를 사용하여 각 단계의 스크립트를 독립된 프로세스로 실행하며, 로그를 `aegis_system.log`에 기록합니다.
    *   macOS 절전 모드(`pmset sleepnow`)를 제어하여 작업 완료 후 전력을 관리합니다.
*   **주요 함수**:
    *   `run_pipeline()`: 정의된 `PIPELINE_STEPS` 리스트를 순회하며 실행.
    *   `check_pending_proposals()`: `evolution_queue/` 디렉토리를 확인하여 대기 중인 진화 제안이 있는지 알림.

### 2.2. `data_bank_builder.py` (데이터 수집 모듈)
분석에 필요한 기초 데이터를 수집하고 저장합니다.

*   **기능**:
    *   `yfinance`를 사용하여 XRP 및 주요 거시경제 지표(달러 인덱스, 나스닥 등) 데이터를 수집합니다.
    *   `alternative.me` API를 통해 '공포·탐욕 지수(Fear & Greed Index)'를 가져옵니다.
    *   수집된 데이터를 `historical_data_3y.csv` (또는 지정된 경로)에 저장하여 후속 단계에서 사용할 수 있게 합니다.

### 2.3. `aegis_executor.py` (전략 분석 및 리포트 생성)
실질적인 AI 두뇌 역할을 하며, 데이터 분석과 Gemini AI 추론을 결합합니다.

*   **기능**:
    *   **로컬 분석**: 학습된 PyTorch 모델(`aegis_brain.pth`)을 로드하여 XRP의 상승 확률을 예측합니다.
    *   **Gemini 추론 (3단계 프로세스)**:
        1.  **Quantitative Logic**: $NDA$, $TE$ 공식을 기반으로 정량적 논리 추론 수행.
        2.  **Code Evolution**: 시스템 개선을 위한 Python 코드(Transformer/TFT 모델 등)를 Gemini가 직접 작성.
        3.  **Unified Report**: 로컬 데이터와 클라우드 지식(뉴스/거시경제)을 결합하여 `[A. Local Brain]`, `[B. Gemini Reasoning]`, `[C. Unified Command]` 구조의 최종 리포트 작성.
    *   **결과 저장**: 분석 결과를 `aegis_dashboard_data.json`에 저장하여 대시보드와 연동합니다.

### 2.4. `aegis_dashboard.py` (통합 커맨드 센터 - UI)
사용자(사령관)가 시스템을 모니터링하고 제어하는 Streamlit 기반 인터페이스입니다.

*   **기능**:
    *   **대시보드**: `aegis_dashboard_data.json`을 시각화하여 가격, 예측 확률, 공포 지수, 통합 리포트를 표시합니다.
    *   **즉시 분석 요청**: 버튼 클릭 시 `aegis_automation.py`를 실행하여 실시간 분석을 수행합니다. (검증 필요)
    *   **시스템 업데이트 센터**: Git Pull, 데이터 동기화, 모델 점검을 원클릭으로 수행합니다.
    *   **GitHub PR Manager**: 열려 있는 Pull Request를 조회하고, 승인(Merge)하거나 폐기(Close)합니다.
    *   **Jules 연결**: `https://jules.google.com/session`으로 연결하여 AI 에이전트와 직접 소통합니다.
    *   **스케줄링**: `crontab`을 제어하여 자동 실행 스케줄(매일/매주/간격)을 관리합니다.

### 2.5. `aegis_system_evolver.py` (자가 진화 시스템)
사용자의 요청이나 AI의 제안에 따라 시스템 코드를 스스로 수정하고 GitHub PR을 생성합니다.

*   **기능**:
    *   `user_requests.txt`에 저장된 사용자 요구사항을 읽어옵니다.
    *   **타겟 파일 선정**: 요청 내용에 따라 `aegis_dashboard.py`, `aegis_main_system.py` 등 수정할 파일을 지능적으로 선택합니다.
    *   **코드 생성**: Gemini에게 현재 코드와 요구사항을 입력하여 개선된 코드를 생성받습니다.
    *   **제안 검증**: 생성된 코드를 `AegisValidator`로 검사(문법 오류, 모델 구조 확인)합니다.
    *   **Auto-PR**: 검증된 코드로 새 Git 브랜치를 만들고, GitHub API를 통해 Pull Request를 자동으로 생성합니다.

### 2.6. `aegis_lib.py` (보안 및 검증 라이브러리)
시스템 안정성과 보안을 담당하는 공용 라이브러리입니다.

*   **기능**:
    *   `AegisValidator`:
        *   `validate_proposal()`: Python 문법 검사 및 PyTorch 모델 구조 호환성(MPS 지원 등) 확인.
        *   `validate_command()`: 중요한 명령 실행 전 Jules 세션을 통한 '검증(Verification)' 절차를 강제합니다. (자동 승인 방지)
        *   `analyze_impact()`: 작업의 위험도를 분석하고 세션 링크를 생성합니다.

---

## 3. 단계별 워크플로우 (Operational Workflows)

### 3.1. 일일 자동 실행 (Daily Routine)
1.  **시작**: `aegis_main_system.py` 실행 (수동 또는 Cron 스케줄).
2.  **데이터 수집**: `data_bank_builder.py`가 최신 시장 데이터를 수집.
3.  **전처리**: `data_preprocessor.py`가 기술적 지표 계산 및 데이터 정규화.
4.  **모델 학습**: `aegis_brain_trainer.py`가 최신 데이터로 AI 모델 재학습 (MPS 가속).
5.  **자가 진화**: `aegis_system_evolver.py`가 개선점을 찾아 PR 생성 (선택적).
6.  **최종 분석**: `aegis_automation.py`가 Gemini와 협업하여 통합 리포트 작성 및 대시보드 데이터 갱신.
7.  **종료**: (설정된 경우) macOS 절전 모드 진입.

### 3.2. 사령관 수동 명령 및 분석 (Manual Analysis)
1.  **대시보드 접속**: `streamlit run aegis_dashboard.py`.
2.  **분석 요청**: "즉시 분석 시작 (Start Immediate Analysis)" 버튼 클릭.
3.  **검증 단계**:
    *   시스템이 작업을 일시 중단하고 '검증 대기(Verification Pending)' 상태로 전환.
    *   제공된 **Jules Session 링크**를 통해 AI 에이전트와 대화하며 작전 계획 확인.
    *   "Sync Verification Status" 버튼으로 승인 상태 동기화.
4.  **실행**: 승인 완료 후 분석 스크립트가 실행되고, 결과가 대시보드 하단에 표시됨.

### 3.3. 시스템 진화 및 PR 처리 (Evolution & PR)
1.  **요청 등록**: 대시보드나 `user_requests.txt`를 통해 기능 추가 요청 (예: "RSI 지표 계산식 변경해줘").
2.  **진화 실행**: `aegis_system_evolver.py`가 실행되어 코드 수정안 생성.
3.  **PR 생성**: 검증 통과 시 GitHub에 `evolution/auto-timestamp` 브랜치로 Push 및 PR 생성.
4.  **승인(Merge)**:
    *   대시보드의 '통합 커맨드 센터' > 'GitHub PR Manager' 접속.
    *   생성된 PR 내용을 확인하고 "승인 및 병합" 버튼 클릭.
    *   GitHub API를 통해 Main 브랜치로 병합되고, 로컬 시스템은 다음 업데이트 시 이를 반영(`git pull`).

---

## 4. 환경 설정 (Configuration)

### 필수 파일
*   `.env`: `GEMINI_API_KEY=...` (Gemini 사용을 위한 API 키)
*   `.aegis_config.json`: GitHub 연동 정보 (`owner`, `repo`, `token`) 저장. (대시보드에서 설정 가능)

### 주요 경로
*   `PROJECT_ROOT`: 프로젝트 최상위 폴더.
*   `PROJECT_ROOT/evolution_queue/`: 생성된 진화 제안 코드가 저장되는 대기열.
*   `PROJECT_ROOT/command_images/`: 대시보드에서 업로드한 이미지 저장소.

---
**작성일**: 2025년 05월 27일
**작성자**: AEGIS System Architecture (Jules)
