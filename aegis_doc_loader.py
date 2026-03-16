import os
import re
import docx
import gspread
import json
import time
import shutil
from google.oauth2.service_account import Credentials
from google import genai
from google.genai import types
from datetime import datetime
from dotenv import load_dotenv

# 💾 파일 제목: aegis_doc_loader.py (AEGIS 0단계 마스터: 순수 지표명 자가 증식 롤백본)
# 🚀 사유: 6열 대시보드 확장으로 인한 시스템 혼선을 막기 위해, 'XRP 지표' 탭에는 오직 '지표명'만 단일로 자동 추가되도록 로직 간소화

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, "aegis_data", "docs")
ARCHIVE_DIR = os.path.join(DOCS_DIR, "archive")
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def get_weapon_chain(gc):
    try:
        ws = gc.open("AEGIS_Daily_Report").worksheet("AEGIS_Settings")
        rows = ws.get_all_values()
        chain = []
        for row in rows[1:4]:
            if len(row) > 1 and row[1].strip(): chain.append(row[1].strip())
            if len(row) > 3 and row[3].strip(): chain.append(row[3].strip())
            if len(row) > 4 and row[4].strip(): chain.append(row[4].strip())
        return chain if chain else ["gemini-2.5-flash", "gemini-2.5-pro"]
    except: return ["gemini-2.5-flash", "gemini-2.5-pro"]

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text.strip())
    return "\n".join(full_text)

def get_core_name(raw_name):
    return raw_name.replace("[지표]", "").replace("[테마]", "").replace(" ", "").replace("_", "").strip()

def parse_chunk_with_ai(client, weapons, chunk_text, indicator_names):
    
    prompt = f"""
    당신은 퀀트 투자 데이터의 '수석 객관적 정보 수집관'입니다. 
    아래는 리포트의 [특정 구간 분할(Chunk)] 텍스트입니다. 

    [타겟 지표 목록 (이름을 절대 변형하지 말고 가급적 그대로 사용할 것)]
    {', '.join(indicator_names)}

    [분할된 구간 텍스트]
    {chunk_text}

    [🚨 5대 필수 지침 🚨]
    1. 전수 조사: 이 구간에 등장하는 모든 코인 종목, 거시 경제, 세력 내러티브를 하나도 빠짐없이 모조리 발굴하십시오.
    2. 독립적 분석 (짬뽕 엄격 금지): 지표별로 반드시 독립된 'topic'과 'analysis' 쌍을 만드십시오. 관련 없는 내용을 섞는 것을 엄격히 금지합니다.
    3. 네이밍 규칙: topic 이름은 반드시 `[지표] 이름` 또는 `[테마] 이름` 형식으로 작성하십시오. 위 [타겟 지표 목록]에 있는 단어라면 언더바(_)까지 100% 똑같이 적으십시오.
    4. 분석 내용: 유튜버의 팩트와 주장을 2~3줄로 명확히 요약하되, 특정 날짜(예: 3월 14일)는 적지 마십시오.
    5. 특이점: 관점이 180도 바뀌었다면 analysis 내용 맨 앞에 [🚨 관점 역전] 태그를 붙이십시오.
    """

    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "insights": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "topic": types.Schema(type=types.Type.STRING),
                        "analysis": types.Schema(type=types.Type.STRING)
                    },
                    required=["topic", "analysis"]
                )
            )
        },
        required=["insights"]
    )

    for model_name in weapons:
        try:
            response = client.models.generate_content(
                model=model_name, contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1, response_mime_type="application/json", response_schema=response_schema
                )
            )
            data = json.loads(response.text)
            return data.get("insights", [])
        except Exception as e:
            print(f"      ⚠️ [{model_name}] 판독 실패 ({e}). 다음 무기로 교체합니다.")
            time.sleep(2)
            
    return []

def run_doc_loader():
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    current_month_str = now.strftime("%Y-%m")
    timestamp_prefix = now.strftime("[%d일 %H:%M]")
    
    print("=" * 60)
    print(f"📄 [0단계 마스터] AEGIS 시계열 문서 정밀 타격 및 지표명 증식 ({now_str})")
    print("=" * 60)

    docx_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".docx") and not f.startswith("~")]
    if not docx_files:
        print("   ✅ 대기 중인 문서가 없습니다.")
        return

    print(f"   🔗 구글 클라우드 연결 중...")
    creds_path = os.getenv("GCP_CREDS_PATH").strip('"').strip("'")
    gc = gspread.authorize(Credentials.from_service_account_file(creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]))
    doc_sheet = gc.open("AEGIS_Daily_Report")
    saebyeok_ws = doc_sheet.worksheet("어슴새벽")
    
    # 지표 탭 로드
    indicator_ws = doc_sheet.worksheet("XRP 지표")
    indicator_data = indicator_ws.get_all_values()
    if not indicator_data:
        indicator_data = [["지표명"]]
        
    existing_indicators_set = {row[0].strip() for row in indicator_data if row and row[0].strip()}
    target_indicator_names = [row[0].strip() for row in indicator_data[1:] if row and row[0].strip()]

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    weapons = get_weapon_chain(gc)
    
    all_insights = []
    
    # 문서 스캔
    docx_files.sort(key=lambda f: os.path.getmtime(os.path.join(DOCS_DIR, f)))
    for filename in docx_files:
        file_path = os.path.join(DOCS_DIR, filename)
        full_text = extract_text_from_docx(file_path)
        
        chunks = re.split(r'\n(?=▶️ 영상 구간:)', full_text)
        chunks = [c.strip() for c in chunks if len(c.strip()) > 50]
        
        if len(chunks) == 0:
            chunks = [full_text[i:i+6000] for i in range(0, len(full_text), 6000)]
            
        print(f"\n   🔪 문서 분할 완료: '{filename}' ➔ 총 {len(chunks)}개 구간 스캔")
        
        for chunk_idx, chunk_text in enumerate(chunks):
            print(f"      🎯 [구간 {chunk_idx+1}/{len(chunks)}] 스캔 중...")
            insights = parse_chunk_with_ai(client, weapons, chunk_text, target_indicator_names)
            all_insights.extend(insights)
            time.sleep(1)

    if not all_insights:
        return

    # ==============================================================
    # 1. 어슴새벽 탭 업데이트 로직 (내용 시계열 누적)
    # ==============================================================
    saebyeok_data = saebyeok_ws.get_all_values()
    if not saebyeok_data or not saebyeok_data[0]:
        saebyeok_data = [["지표명 / 테마"]]
        
    headers = saebyeok_data[0]
    if headers[0].strip() == "" or headers[0] == current_month_str:
        headers[0] = "지표명 / 테마" 
    
    if current_month_str not in headers:
        headers.append(current_month_str)
    
    month_col_idx = headers.index(current_month_str)
    
    row_map = {}
    for i, row in enumerate(saebyeok_data):
        if i > 0 and len(row) > 0 and row[0].strip():
            row_map[get_core_name(row[0].strip())] = i

    print("\n   [실시간 시계열 Upsert(내용 누적) 현황 모니터링]")
    for item in all_insights:
        topic = str(item.get("topic", "")).strip()
        analysis = str(item.get("analysis", "")).strip()
        
        if not topic or not analysis: continue
            
        core_topic = get_core_name(topic)
        formatted_content = f"{timestamp_prefix} {analysis}"

        if core_topic in row_map:
            r_idx = row_map[core_topic]
            while len(saebyeok_data[r_idx]) <= month_col_idx:
                saebyeok_data[r_idx].append("")
            
            existing_val = saebyeok_data[r_idx][month_col_idx].strip()
            if existing_val:
                saebyeok_data[r_idx][month_col_idx] = existing_val + "\n\n" + formatted_content
                print(f"      📍 [내용 누적] '{topic}' ➔ 기존 내용 아래에 덧붙임")
            else:
                saebyeok_data[r_idx][month_col_idx] = formatted_content
                print(f"      📍 [첫 기록] '{topic}' ➔ 이번 달 칸에 내용 최초 작성")
        else:
            new_row = [""] * (month_col_idx + 1)
            new_row[0] = topic
            new_row[month_col_idx] = formatted_content
            saebyeok_data.append(new_row)
            row_map[core_topic] = len(saebyeok_data) - 1
            print(f"      ✨ [신규 행 파기] 새로운 지표/테마 발굴: '{topic}'")

    max_cols = max(len(row) for row in saebyeok_data)
    for row in saebyeok_data:
        while len(row) < max_cols:
            row.append("")

    saebyeok_ws.clear()
    try:
        saebyeok_ws.update(values=saebyeok_data, range_name="A1")
    except TypeError:
        saebyeok_ws.update("A1", saebyeok_data)

    # ==============================================================
    # 💡 2. XRP 지표 탭 업데이트 로직 (오직 지표명만 단일 추가!)
    # ==============================================================
    print("\n   🤖 [XRP 지표 탭 자가 증식 작업 시작]")
    new_indicators_added = 0
    
    for item in all_insights:
        topic = str(item.get("topic", "")).strip()
        if not topic: continue
            
        # [테마]가 없는 순수 지표만 선별
        if "[테마]" not in topic:
            clean_indicator = topic.replace("[지표]", "").strip() 
            
            # 기존 명단에 없으면 오직 이름 하나만 딱 추가
            if clean_indicator and clean_indicator not in existing_indicators_set:
                indicator_data.append([clean_indicator])
                existing_indicators_set.add(clean_indicator)
                print(f"      📈 [타겟 명단 확장] '{clean_indicator}' ➔ XRP 지표 탭 1열에 자동 등록!")
                new_indicators_added += 1

    if new_indicators_added > 0:
        indicator_ws.clear()
        try:
            indicator_ws.update(values=indicator_data, range_name="A1")
        except TypeError:
            indicator_ws.update("A1", indicator_data)
        print(f"   ✅ XRP 지표 탭 진화 완료: 신규 타겟 {new_indicators_added}개 단일 추가됨")
    else:
        print("   ✅ 추가할 신규 지표 타겟이 없습니다.")

    # 3. 폴더 클리닝
    print("\n   🗂️ 물리적 폴더 클리닝 (Auto-Archiving) 진행")
    for filename in docx_files:
        try:
            shutil.move(os.path.join(DOCS_DIR, filename), os.path.join(ARCHIVE_DIR, filename))
        except Exception:
            pass

if __name__ == "__main__":
    run_doc_loader()