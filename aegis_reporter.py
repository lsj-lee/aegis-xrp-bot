import os
import re
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import warnings

warnings.filterwarnings('ignore')

# .env 파일 로드
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# 기본값은 로컬 실행 환경에 맞춤 (필요시 .env에서 재정의)
GOOGLE_SHEETS_CREDS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "credentials.json")

def get_sheet_data():
    """구글 시트에서 최신 데이터를 가져옵니다."""
    print("📊 구글 시트 데이터를 불러오는 중...")

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDS_PATH, scope)
        client = gspread.authorize(creds)

        sheet_name = "AEGIS_Daily_Report"
        sheet = client.open(sheet_name).sheet1

        # 모든 데이터 가져오기 (마지막 행이 최신)
        data = sheet.get_all_values()
        if len(data) < 2:
            print("⚠️ 데이터가 충분하지 않습니다.")
            return None

        latest_row = data[-1]
        print(f"✅ 최신 데이터 로드 완료 ({latest_row[0]})")
        return latest_row

    except Exception as e:
        print(f"⚠️ 구글 시트 연결 오류: {e}")
        return None

def parse_report(row):
    """행 데이터를 파싱하여 구조화된 딕셔너리로 반환합니다."""
    # Row format based on aegis_automation.py:
    # [date, price, fng, prob%, decision, long_term, commentary]

    if not row or len(row) < 7:
        print("⚠️ 데이터 형식이 올바르지 않습니다.")
        return None

    data = {
        'date': row[0],
        'price': row[1],
        'fng': row[2],
        'prob': row[3].replace('%', ''),
        'decision': row[4],
        'long_term': row[5],
        'commentary': row[6]
    }

    # Commentary 파싱 (Funding Rate, LS Ratio, Targets)
    commentary = data['commentary']

    # 1. Funding Rate & LS Ratio
    # Pattern: - 확률: {prob_percent:.2f}% / 롱숏: {ls_ratio:.2f} / 펀딩: {funding_rate:.4f}%
    fr_ls_match = re.search(r"롱숏:\s*([\d\.]+)\s*/\s*펀딩:\s*([-\d\.]+)%", commentary)
    if fr_ls_match:
        data['ls_ratio'] = float(fr_ls_match.group(1))
        data['funding_rate'] = float(fr_ls_match.group(2))
    else:
        data['ls_ratio'] = 0.0
        data['funding_rate'] = 0.0

    # 2. Targets
    # ⚡ 단기 (1~2주): 매수 ${st_buy:.2f} / 매도 ${st_sell:.2f}
    st_match = re.search(r"⚡ 단기.*?매수 \$(.*?)\s*/\s*매도 \$(.*?)(\n|$)", commentary)
    data['st_buy'] = st_match.group(1) if st_match else "N/A"
    data['st_sell'] = st_match.group(2).strip() if st_match else "N/A"

    # 🌊 중기 (1~3개월): 매집 ${mt_buy:.2f} / 익절 ${mt_sell:.2f}
    mt_match = re.search(r"🌊 중기.*?매집 \$(.*?)\s*/\s*익절 \$(.*?)(\n|$)", commentary)
    data['mt_buy'] = mt_match.group(1) if mt_match else "N/A"
    data['mt_sell'] = mt_match.group(2).strip() if mt_match else "N/A"

    # 🌌 장기 (6개월+): 최후선 ${lt_buy:.2f} / 목표 ${lt_sell_final}
    lt_match = re.search(r"🌌 장기.*?최후선 \$(.*?)\s*/\s*목표 \$(.*?)(\n|$)", commentary)
    data['lt_buy'] = lt_match.group(1) if lt_match else "N/A"
    data['lt_sell'] = lt_match.group(2).strip() if lt_match else "N/A"

    return data

def generate_message(data):
    """텔레그램 메시지를 생성합니다."""

    try:
        prob = float(data['prob'])
    except ValueError:
        prob = 0.0

    ls_ratio = data['ls_ratio']
    funding_rate = data['funding_rate']
    long_term = data['long_term'] # 상승/하락

    # 1. 타임프레임별 전략
    strategy_msg = ""
    if prob >= 70:
        strategy_msg = "🚀 **강력 매수 (Strong Buy)**\n확률 70% 이상, 적극 진입 권장."
    elif prob >= 60:
        strategy_msg = "📈 **매수 우위 (Buy)**\n상승 확률 높음, 분할 매수 유효."
    elif prob <= 40:
        strategy_msg = "📉 **매도 우위 (Sell)**\n하락 확률 높음, 리스크 관리 필요."
    else:
        strategy_msg = "👀 **관망 (Hold)**\n방향성 불확실, 시장 추이 관찰."

    reason_msg = f"• 기계 확률: {prob}%\n• 롱/숏 비율: {ls_ratio} ( > 1.0 매수 우세)\n• 펀딩비: {funding_rate}%"

    # 2. 목표가 리스트
    targets_msg = f"""
⚡ **단기 (1~2주)**: 진입 ${data['st_buy']} / 목표 ${data['st_sell']}
🌊 **중기 (1~3개월)**: 진입 ${data['mt_buy']} / 목표 ${data['mt_sell']}
🌌 **장기 (6개월+)**: 진입 ${data['lt_buy']} / 목표 ${data['lt_sell']}
""".strip()

    # 3. 추세 및 경보
    warning_msg = ""
    warning_emoji = "🟢"

    if ls_ratio > 2.5:
        warning_msg += "⚠️ **롱 스퀴즈 경보**: 롱 포지션 과열, 급락 주의!\n"
        warning_emoji = "🔴"
    elif ls_ratio < 0.5:
        warning_msg += "⚠️ **숏 스퀴즈 경보**: 숏 포지션 과열, 급등 가능성!\n"
        warning_emoji = "🔴"

    if abs(funding_rate) > 0.05:
        warning_msg += "⚠️ **펀딩비 과열**: 변동성 확대 예상.\n"
        warning_emoji = "🟠"

    if not warning_msg:
        warning_msg = "안정적인 시장 흐름입니다."

    trend_msg = f"{warning_emoji} 현재 추세: **{long_term}** (MA200 기준)\n{warning_msg}"

    # 최종 메시지 조립
    message = f"""
📊 **[AEGIS 3.0] 일일 브리핑** ({data['date']})

1️⃣ **타임프레임 전략**
{strategy_msg}
{reason_msg}

2️⃣ **기간별 목표가 (Target Price)**
{targets_msg}

3️⃣ **추세 및 변동성 경보**
{trend_msg}
"""
    return message.strip()

def send_telegram_message(message):
    """텔레그램으로 메시지를 전송합니다."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 없습니다. (.env 확인)")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ 텔레그램 메시지 전송 성공!")
        else:
            print(f"⚠️ 전송 실패: {response.text}")
    except Exception as e:
        print(f"⚠️ 연결 오류: {e}")

if __name__ == "__main__":
    row = get_sheet_data()
    if row:
        parsed_data = parse_report(row)
        if parsed_data:
            msg = generate_message(parsed_data)
            print("----- 생성된 메시지 -----")
            print(msg)
            print("-----------------------")
            send_telegram_message(msg)
