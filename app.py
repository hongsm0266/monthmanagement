import streamlit as st
import pandas as pd
from datetime import date
import re
import os
import json
import gspread
from google.oauth2.service_account import Credentials
import io
import urllib.request
import urllib.parse
import base64

# 1. 화면 기본 설정
st.set_page_config(page_title="충청호남팀 견적 관리 및 TM 진도", layout="wide")

# --- 구글 시트 연동 설정 ---
SHEET_NAME = "견적관리대장로우"

# ⭐ 발급받으신 ImgBB API 키 영구 탑재 완료!
IMGBB_API_KEY = "1cecb3f4e313203e40d78882356ef1ca"

@st.cache_resource
def init_connection():
    try:
        creds_json = st.secrets["gcp"]["key"]
        creds_dict = json.loads(creds_json)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error("구글 API 키(Secrets) 설정이 안 되어 있거나 오류가 발생했습니다. 세팅을 확인해주세요.")
        return None

client = init_connection()

if os.path.exists("logo.png"): HANSSEM_CI_URL = "logo.png"
elif os.path.exists("hanssem.png"): HANSSEM_CI_URL = "hanssem.png"
else: HANSSEM_CI_URL = "https://raw.githubusercontent.com/github/explore/main/topics/png/png.png"

# --- 커스텀 CSS (PAPERLOGY 폰트 최적화 및 아이콘 보호 적용) ---
st.markdown("""
<style>
    /* 💡 PAPERLOGY 웹폰트 CDN 로드 */
    @font-face { font-family: 'Paperlogy'; src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@1.0/Paperlogy-8Bold.woff2') format('woff2'); font-weight: 700; font-display: swap; }
    @font-face { font-family: 'Paperlogy'; src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@1.0/Paperlogy-9Black.woff2') format('woff2'); font-weight: 900; font-display: swap; }
    @font-face { font-family: 'Paperlogy'; src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@1.0/Paperlogy-6SemiBold.woff2') format('woff2'); font-weight: 600; font-display: swap; }
    @font-face { font-family: 'Paperlogy'; src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@1.0/Paperlogy-5Medium.woff2') format('woff2'); font-weight: 500; font-display: swap; }
    @font-face { font-family: 'Paperlogy'; src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@1.0/Paperlogy-4Regular.woff2') format('woff2'); font-weight: 400; font-display: swap; }

    /* 💡 텍스트가 표시되는 영역에만 Paperlogy를 확실히 덮어씌움 */
    html, body, p, span, label, button, input, select, textarea, h1, h2, h3, h4, h5, h6, th, td {
        font-family: 'Paperlogy', -apple-system, sans-serif !important;
    }

    /* 🚨 시스템 아이콘 영역(화살표, 구름 등) 폰트 변환 강제 차단 */
    .stIconMaterial, .material-icons, [data-testid*="stIcon"], [data-baseweb="icon"] {
        font-family: "Material Symbols Rounded", "Material Icons", sans-serif !important;
        font-weight: 400 !important;
    }

    .main .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {
        max-width: 100% !important;
        padding-left: 1rem !important; padding-right: 1rem !important;
        padding-top: 1.5rem !important; padding-bottom: 1rem !important;
    }
    
    h1, h2, h3 { font-weight: 900 !important; color: #0f172a !important; font-size: 24px !important; letter-spacing: -0.5px !important; }

    .login-card-title { color: #0f172a; font-size: 22px !important; font-weight: 900 !important; margin-top: 15px; margin-bottom: 5px; }
    .login-card-sub { color: #64748b; font-size: 13px; margin-bottom: 20px; font-weight: 600; }
    
    div.stButton > button { 
        background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important; color: white !important; font-size: 15px !important; font-weight: 800 !important; 
        border-radius: 8px !important; padding: 10px 15px !important; border: none !important; height: auto !important; min-height: 45px; box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        border-bottom: 4px solid #1e3a8a !important; transition: all 0.1s ease !important; 
    }
    div.stButton > button:hover { transform: translateY(-2px) !important; }
    div.stButton > button:active { transform: translateY(2px) !important; border-bottom: 1px solid #1e3a8a !important; margin-bottom: 3px !important; }
    
    div.element-container:has(.red-btn) + div.element-container div.stButton > button { background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%) !important; border-bottom: 4px solid #991b1b !important; }
    div.element-container:has(.yellow-btn) + div.element-container div.stButton > button { background: linear-gradient(180deg, #facc15 0%, #eab308 100%) !important; border-bottom: 4px solid #a16207 !important; color: #1c1917 !important; }

    .user-info-box { background-color: #f1f5f9; border: 2px solid #0284c7; padding: 12px 16px; border-radius: 8px; text-align: right; }
    .user-info-name { font-size: 18px !important; font-weight: 900 !important; color: #0369a1 !important; }
    .user-info-sub { font-size: 12px !important; color: #64748b !important; font-weight: 600; }
    .table-header-banner { background-color: #0056b3; color: white; padding: 10px 16px; border-radius: 6px 6px 0 0; font-weight: 800; font-size: 16px; margin-bottom: -10px; display: flex; justify-content: space-between; align-items: center;}

    [data-testid="stDataFrame"] th svg { display: none !important; }
    [data-testid="stDataFrame"] th { font-weight: 900 !important; color: #0f172a !important; font-size: 14px !important; background-color: #f8fafc !important; }

    .dash-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 8px; }
    .dash-card { 
        background: white; border-radius: 8px; padding: 14px 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.06); 
        border: 1px solid #e2e8f0; text-align: center; border-top: 5px solid #3b82f6; 
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    .dash-card.green { border-top-color: #10b981; }
    .dash-card.purple { border-top-color: #8b5cf6; }
    .dash-card.orange { border-top-color: #f97316; }
    .dash-card.red { border-top-color: #ef4444; }
    .dash-title { font-size: 12px; color: #64748b; font-weight: 700; margin-bottom: 6px; letter-spacing: -0.5px; word-break: keep-all;}
    .dash-value { font-size: 18px; color: #0f172a; font-weight: 900; letter-spacing: -0.5px; word-break: keep-all;}
    
    [data-testid="stExpander"] {
        background-color: #f8fafc !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    }
    [data-testid="stExpander"] summary {
        background-color: #e0f2fe !important; 
        border-radius: 10px 10px 0 0 !important;
        padding-top: 12px !important;
        padding-bottom: 12px !important;
        border-bottom: 1px solid #bae6fd !important;
    }
    [data-testid="stExpander"] summary p {
        font-size: 16px !important;
        font-weight: 900 !important;
        color: #0369a1 !important;
    }
</style>
""", unsafe_allow_html=True)

# 🚨 신규 인원 3명 소속(둔산) 완벽 반영
HC_DB = {
    "00033448": {"name": "장재형", "dealer": "둔산"}, "00038617": {"name": "이대운", "dealer": "둔산"},
    "00041990": {"name": "강지인", "dealer": "둔산"}, "00040110": {"name": "장영종", "dealer": "광양"},
    "00040112": {"name": "임현", "dealer": "광양"}, "00040113": {"name": "하행우", "dealer": "광양"},
    "00042008": {"name": "김경율", "dealer": "세종"}, "00044932": {"name": "강희성", "dealer": "세종"},
    "00044933": {"name": "한유진", "dealer": "세종"}, "00040744": {"name": "빙지영", "dealer": "목포"},
    "00040755": {"name": "윤덕수", "dealer": "목포"}, "00043657": {"name": "최병하", "dealer": "익산"},
    "00043825": {"name": "이은혜", "dealer": "익산"}, "00033249": {"name": "임준수", "dealer": "충주"},
    "00033479": {"name": "류승태", "dealer": "여수"}, "00042423": {"name": "라태현", "dealer": "여수"},
    "00044183": {"name": "김동휘", "dealer": "여수"},
    "00045152": {"name": "천민선", "dealer": "둔산"},
    "00045153": {"name": "박준수", "dealer": "둔산"},
    "00043761": {"name": "한지훈", "dealer": "둔산"}
}

REGION_MAP = {
    "충청상권": ["둔산", "목포", "세종", "충주"], 
    "호남상권": ["익산", "광양", "여수"]
}

PRODUCT_KEYWORDS = {
    "침실단품": ["화장대", "서랍장", "리즈"], "수납": ["붙박이장", "드레스룸", "옷장", "샘키즈", "샘베딩", "뮤트", "스케치", "아임빅", "바흐"],
    "침실": ["침대", "매트리스", "포시즌", "노뜨", "그로브오크", "포에트", "호텔침대", "어반글로우"],
    "거실": ["소파", "리클라이너", "스위브", "뉴플루드", "인피니", "뉴인피니", "테이즈", "키안티", "페타", "플로에", "거실장", "아카이브", "MVME"],
    "다이닝": ["식탁", "테이블", "식탁의자", "디아고", "리브업", "인칸토", "리니아"],
    "책상의자 - 알로/조이": ["책상의자", "알로"], "자녀방 책상": ["조이"]
}

if 'logged_in' not in st.session_state: st.session_state.update({'logged_in': False, 'hc_id': '', 'hc_name': '', 'dealer': '', 'is_master': False})
if 'success_msg' not in st.session_state: st.session_state['success_msg'] = ""
if 'warning_msg' not in st.session_state: st.session_state['warning_msg'] = ""
if 'uploader_key' not in st.session_state: st.session_state['uploader_key'] = 0
if 'confirm_delete' not in st.session_state: st.session_state['confirm_delete'] = False
if 'to_del_list' not in st.session_state: st.session_state['to_del_list'] = []

if not st.session_state['logged_in']:
    st.write(""); st.write("")
    col_left, col_center, col_right = st.columns([1, 1.2, 1])
    with col_center:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.image(HANSSEM_CI_URL, width=180) 
        st.markdown("""<div class="login-card-title">충청호남팀 견적관리 로그인</div><div class="login-card-sub">견적 등록 및 TM 진도율 실시간 통합 시스템</div></div>""", unsafe_allow_html=True)
        login_id = st.text_input("아이디 (사번)", placeholder="사번 8자리를 입력하세요")
        login_pw = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
        st.write("")
        if st.button("로그인", use_container_width=True):
            # 🚀 [보강 1] 사번에 000이 빠져있어도 8자리로 자동 맞춤 처리
            pad_id = str(login_id).strip().zfill(8) if login_id else ""
            input_pw = str(login_pw).strip()
            
            if pad_id == "00000000" and input_pw == "0000":
                st.session_state.update({'logged_in': True, 'hc_id': "0000", 'hc_name': "총괄관리자", 'dealer': "마스터", 'is_master': True}); st.rerun()
            elif pad_id in HC_DB and str(login_id).strip() == input_pw: # 아이디/비번을 0 뺀 상태로 동일하게 쳐도 허용
                st.session_state.update({'logged_in': True, 'hc_id': pad_id, 'hc_name': HC_DB[pad_id]['name'], 'dealer': HC_DB[pad_id]['dealer'], 'is_master': False}); st.rerun()
            else: st.error("정보가 일치하지 않습니다.")
    st.stop()

today = date.today()
my_id, my_name, my_dealer, is_master = st.session_state['hc_id'], st.session_state['hc_name'], st.session_state['dealer'], st.session_state['is_master']

def clean_and_enforce_types(df):
    req_cols = ['선택/삭제', '상담일', '상담번호', 'HC_ID', 'HC명', '대리점명', '고객명', '연락처', '주소', '상품', '현장유형', '견적금액', '1차_TM', '1차_TM_일자', '1차_증빙', '2차_TM', '2차_TM_일자', '2차_증빙', '3차_TM', '3차_TM_일자', '3차_증빙', '계약완료', '계약완료금액', '상담메모', 'is_self', '세부품목']
    if df is None or df.empty:
        edf = pd.DataFrame(columns=req_cols)
        for col in ['선택/삭제', '1차_TM', '2차_TM', '3차_TM', '계약완료', 'is_self']: edf[col] = False
        edf['견적금액'] = 0
        edf['계약완료금액'] = 0
        return edf
    df = df.copy()
    if '상품(대분류)' in df.columns: df = df.rename(columns={'상품(대분류)': '상품'})
    for col in req_cols:
        if col not in df.columns: df[col] = False if col in ['선택/삭제', '1차_TM', '2차_TM', '3차_TM', '계약완료', 'is_self'] else ''
    for col in ['상담일', '1차_TM_일자', '2차_TM_일자', '3차_TM_일자']:
        df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        df[col] = df[col].apply(lambda x: None if pd.isna(x) else x)
    for col in ['선택/삭제', '1차_TM', '2차_TM', '3차_TM', '계약완료', 'is_self']: df[col] = df[col].apply(lambda x: True if str(x).strip().upper() == 'TRUE' or x is True or x == 1 or x == '1' else False).astype(bool)
    
    df['견적금액'] = pd.to_numeric(df['견적금액'], errors='coerce').fillna(0).astype(int)
    df['계약완료금액'] = pd.to_numeric(df['계약완료금액'], errors='coerce').fillna(0).astype(int)
    
    for col in ['HC_ID', '상담번호', '연락처', '상담메모', '고객명', '주소', '상품', '현장유형', 'HC명', '대리점명', '1차_증빙', '2차_증빙', '3차_증빙', '세부품목']:
        df[col] = df[col].astype(str).replace(['nan', 'NaN', 'None', '<NA>'], '')
        # 시트에 0이 빠진 사번이 있어도 여기서 자동으로 8자리 채워줌
        if col == 'HC_ID': df[col] = df[col].str.replace(r'\.0$', '', regex=True).apply(lambda x: str(x).strip().zfill(8) if str(x).strip() else '')
        elif col == '상담번호': df[col] = df[col].str.replace(r'\.0$', '', regex=True)
    return df[req_cols]

def get_or_create_sheet(spreadsheet, sheet_name):
    try: return spreadsheet.worksheet(sheet_name)
    except: return spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="27")

def load_data_from_sheet(gc_client, is_master_mode, current_user):
    try:
        spreadsheet = gc_client.open(SHEET_NAME)
        if is_master_mode:
            all_records = []
            for name in list(set([info["name"] for info in HC_DB.values()])):
                try: 
                    records = spreadsheet.worksheet(name).get_all_records()
                    if records: all_records.extend(records)
                except: continue
            return clean_and_enforce_types(pd.DataFrame(all_records) if all_records else None)
        else:
            try: records = get_or_create_sheet(spreadsheet, current_user).get_all_records()
            except: records = []
            return clean_and_enforce_types(pd.DataFrame(records) if records else None)
    except: return clean_and_enforce_types(None)

@st.cache_data(ttl=60) 
def load_perf_sheet(_gc_client):
    try:
        data = _gc_client.open(SHEET_NAME).worksheet("시트1").get("B32:AG200")
        if data:
            safe_rows = [r + [''] * (32 - len(r)) for r in data]
            return pd.DataFrame(safe_rows)
        return pd.DataFrame()
    except Exception as e:
        print(f"VDT 데이터를 가져오지 못했습니다 (API 한도 또는 시트 오류): {e}")
        return pd.DataFrame()

# 🚀 VDT 지표 매핑 (F=4, G=5, H=6, I=7, R=16, T=18, U=19, W=21, Y=23)
def get_perf_metrics(perf_df, target_id, target_name):
    default = { 'F': 0, 'G': 0, 'H': 0, 'I': 0, 'J': 0, 'R': 0, 'T': 0, 'U': 0, 'W': 0, 'Y': 0 }
    if perf_df is None or perf_df.empty: return default
    
    def clean_val(v):
        if not v or pd.isna(v): return 0.0
        v_str = str(v).replace('%', '').replace(',', '').replace('원', '').replace('건', '').strip()
        multiplier = 1
        if '억' in v_str:
            v_str = v_str.replace('억', '')
            multiplier = 100000000
        elif '만' in v_str:
            v_str = v_str.replace('만', '')
            multiplier = 10000
        v_str = re.sub(r'[^\d\.-]', '', v_str)
        if not v_str: return 0.0
        try: return float(v_str) * multiplier
        except: return 0.0

    sums = { 'F': 0, 'G': 0, 'H': 0, 'I': 0, 'J': 0, 'R': 0, 'T': 0, 'U': 0, 'W': 0, 'Y': 0 }

    if target_id == "ALL":
        all_names = [v['name'] for v in HC_DB.values()]
        for _, row in perf_df.iterrows():
            vals = row.values
            if any(n in "".join([str(x).strip() for x in vals]) for n in all_names):
                sums['F'] += clean_val(vals[4]); sums['G'] += clean_val(vals[5]); sums['H'] += clean_val(vals[6]); sums['I'] += clean_val(vals[7])
                sums['R'] += clean_val(vals[16]); sums['T'] += clean_val(vals[18]); sums['U'] += clean_val(vals[19]); sums['W'] += clean_val(vals[21]); sums['Y'] += clean_val(vals[23])
        if sums['H'] > 0: sums['J'] = (sums['I'] / sums['H']) * 100
        return sums
        
    elif str(target_id).startswith("REGION_"):
        region_name = str(target_id).replace("REGION_", "")
        allowed_dealers = REGION_MAP.get(region_name, [])
        dealer_names = [v['name'] for v in HC_DB.values() if v['dealer'] in allowed_dealers]
        for _, row in perf_df.iterrows():
            vals = row.values
            if any(n in "".join([str(x).strip() for x in vals]) for n in dealer_names):
                sums['F'] += clean_val(vals[4]); sums['G'] += clean_val(vals[5]); sums['H'] += clean_val(vals[6]); sums['I'] += clean_val(vals[7])
                sums['R'] += clean_val(vals[16]); sums['T'] += clean_val(vals[18]); sums['U'] += clean_val(vals[19]); sums['W'] += clean_val(vals[21]); sums['Y'] += clean_val(vals[23])
        if sums['H'] > 0: sums['J'] = (sums['I'] / sums['H']) * 100
        return sums
        
    elif str(target_id).startswith("DEALER_"):
        dealer_name = str(target_id).replace("DEALER_", "")
        dealer_names = [v['name'] for v in HC_DB.values() if v['dealer'] == dealer_name]
        for _, row in perf_df.iterrows():
            vals = row.values
            if any(n in "".join([str(x).strip() for x in vals]) for n in dealer_names):
                sums['F'] += clean_val(vals[4]); sums['G'] += clean_val(vals[5]); sums['H'] += clean_val(vals[6]); sums['I'] += clean_val(vals[7])
                sums['R'] += clean_val(vals[16]); sums['T'] += clean_val(vals[18]); sums['U'] += clean_val(vals[19]); sums['W'] += clean_val(vals[21]); sums['Y'] += clean_val(vals[23])
        if sums['H'] > 0: sums['J'] = (sums['I'] / sums['H']) * 100
        return sums
        
    else:
        # 🚀 [보강 2] 시트에 적힌 사번이 42008 이든 00042008 이든 둘 다 찾아서 누락 없이 합산
        possible_ids = [
            str(target_id), 
            str(target_id).zfill(8), 
            str(int(target_id)) if str(target_id).isdigit() else "",
            target_name
        ]
        possible_ids = list(set([pid for pid in possible_ids if pid])) # 중복 제거 및 빈 값 제거
        
        for _, row in perf_df.iterrows():
            vals = row.values
            row_str = "".join([str(x).strip() for x in vals])
            if any(pid in row_str for pid in possible_ids):
                sums['F'] += clean_val(vals[4]); sums['G'] += clean_val(vals[5]); sums['H'] += clean_val(vals[6]); sums['I'] += clean_val(vals[7])
                sums['R'] += clean_val(vals[16]); sums['T'] += clean_val(vals[18]); sums['U'] += clean_val(vals[19]); sums['W'] += clean_val(vals[21]); sums['Y'] += clean_val(vals[23])
                
        if sums['H'] > 0: sums['J'] = (sums['I'] / sums['H']) * 100
        return sums

def save_data_to_sheet(gc_client, df, is_master_mode, current_user):
    try:
        spreadsheet = gc_client.open(SHEET_NAME)
        headers = [['선택/삭제', '상담일', '상담번호', 'HC_ID', 'HC명', '대리점명', '고객명', '연락처', '주소', '상품', '현장유형', '견적금액', '1차_TM', '1차_TM_일자', '1차_증빙', '2차_TM', '2차_TM_일자', '2차_증빙', '3차_TM', '3차_TM_일자', '3차_증빙', '계약완료', '계약완료금액', '상담메모', 'is_self', '세부품목']]
        def _prepare(d):
            safe_list = []
            for row in [d.columns.values.tolist()] + d.values.tolist():
                safe_row = []
                for cell in row:
                    if isinstance(cell, bool): safe_row.append("TRUE" if cell else "FALSE")
                    else: safe_row.append("" if str(cell).strip().lower() in ['nan', 'none', 'nat', '<na>'] else str(cell))
                safe_list.append(safe_row)
            return safe_list
            
        if is_master_mode:
            for name in list(set([info["name"] for info in HC_DB.values()])):
                group_df = df[df['HC명'] == name]
                sheet = get_or_create_sheet(spreadsheet, name); sheet.clear()
                if not group_df.empty: sheet.update('A1', _prepare(group_df))
                else: sheet.update('A1', headers)
        else:
            sheet = get_or_create_sheet(spreadsheet, current_user); sheet.clear()
            my_df = df[df['HC명'] == current_user]
            if not my_df.empty: sheet.update('A1', _prepare(my_df))
            else: sheet.update('A1', headers)
        return True
    except: return False

if 'data' not in st.session_state:
    loaded_data = load_data_from_sheet(client, is_master, my_name) if client else clean_and_enforce_types(None)
    if loaded_data is not None and not loaded_data.empty:
        loaded_data = loaded_data.sort_values(by='상담일', ascending=False).reset_index(drop=True)
    st.session_state['data'] = loaded_data

def upload_to_imgbb(file_obj, file_name):
    try:
        url = "https://api.imgbb.com/1/upload"
        req = urllib.request.Request(url, data=urllib.parse.urlencode({"key": IMGBB_API_KEY, "image": base64.b64encode(file_obj.read()).decode("utf-8"), "name": file_name.split('.')[0]}).encode("utf-8"))
        res = json.loads(urllib.request.urlopen(req).read().decode("utf-8"))
        return res["data"]["url"] if res.get("success") else None
    except: return None

def parse_product_summary(block):
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    prod_lines, in_prod = [], False
    for l in lines:
        if l in ["상담 상품", "상품정보"]: in_prod = True; continue
        if l in ["구매 동기", "할인혜택 적용", "시방서", "시방서 (선택)"]: in_prod = False
        if l.lower() == 'goods': continue
        if in_prod and not re.search(r'^\d+$', l) and not re.search(r'[\d,]+원$', l) and l not in ["홈퍼니싱 솔루션", "홈플래너 설계"] and not re.match(r'^\d{6,}$', l) and len(l) > 3 and "고객님" not in l and "상담" not in l and "견적" not in l: 
            prod_lines.append(l)

    res = []
    for p in prod_lines:
        matched = False
        if "책상" in p and "의자" in p: res.append("책상의자 - 알로/조이"); continue
        for cat, keywords in PRODUCT_KEYWORDS.items():
            if any(k in p for k in keywords): res.append(cat); matched = True; break
        if not matched: res.append("자녀방 책상" if "책상" in p else "기타(홈퍼니싱)")
    
    seen = set(); top = []
    for r in res:
        if r not in seen and r != "기타(홈퍼니싱)": seen.add(r); top.append(r)
        if len(top) >= 3: break
        
    cat_summary = " / ".join(top) if top else "기타(홈퍼니싱)"
    detail_str = re.sub(r'(?i)^goods\s*,\s*', '', " , ".join(prod_lines))
    return cat_summary, detail_str

def parse_raw_text(text, master_mode):
    records, skipped = [], 0
    for block in text.split("상담일\n")[1:]:
        block = "상담일\n" + block 
        hc_m = re.search(r'영업사원\n(\d+)\s+([가-힣]+)', block)
        if hc_m:
            # 🚀 [보강 3] 복사해 온 텍스트에 0이 빠져있어도 무조건 8자리 사번으로 패딩
            p_id = hc_m.group(1).zfill(8)
            if not master_mode and p_id != my_id: skipped += 1; continue
            p_name = hc_m.group(2)
        else: p_id, p_name = my_id, my_name
                
        d_m = re.search(r'상담일\n([\d-]+)', block)
        n_m = re.search(r'상담번호\n(\d+)', block)
        if d_m and n_m:
            c_m = re.search(r'([가-힣]+)\s+고객님', block)
            c_name = c_m.group(1) if c_m else ""
            is_self = bool(c_name and p_name and c_name.strip() == p_name.strip())
            amt_m = re.search(r'결제 예정 금액\n([\d,]+)', block)
            ph_m = re.search(r'휴대폰 번호\n([\d-]+)', block)
            ad_m = re.search(r'주소\n(.+)', block)
            ty_m = re.search(r'현장 유형\n([^\n]+)', block)
            
            cat_summary, detail_str = parse_product_summary(block)
            
            records.append({
                '선택/삭제': False, '상담일': pd.to_datetime(d_m.group(1)).date(),
                '상담번호': n_m.group(1), 'HC_ID': p_id, 'HC명': p_name,
                '대리점명': HC_DB.get(p_id, {}).get("dealer", my_dealer), '고객명': f"[본인] {c_name}" if is_self else c_name,
                '연락처': ph_m.group(1) if ph_m else "", '주소': ad_m.group(1) if ad_m else "",
                '상품': cat_summary, '현장유형': ty_m.group(1) if ty_m else "",
                '견적금액': int(amt_m.group(1).replace(",", "")) if amt_m else 0,
                '1차_TM': False, '1차_TM_일자': None, '1차_증빙': '', '2차_TM': False, '2차_TM_일자': None, '2차_증빙': '', '3차_TM': False, '3차_TM_일자': None, '3차_증빙': '', 
                '계약완료': False, '계약완료금액': 0, '상담메모': '', 'is_self': is_self, '세부품목': detail_str 
            })
    return pd.DataFrame(records), skipped

def add_quotes_callback():
    txt = st.session_state.get('raw_input_area', '')
    if txt.strip():
        new_df, skipped = parse_raw_text(txt, is_master)
        if not new_df.empty:
            ldf = load_data_from_sheet(client, is_master, my_name)
            udf = clean_and_enforce_types(pd.concat([ldf, new_df], ignore_index=True) if not ldf.empty else new_df).sort_values(by='상담일', ascending=False).reset_index(drop=True)
            if save_data_to_sheet(client, udf, is_master, my_name):
                st.session_state.update({'data': udf, 'success_msg': f"성공적으로 {len(new_df)}건을 추가했습니다!", 'uploader_key': st.session_state['uploader_key'] + 1})
        else: st.session_state['warning_msg'] = "추가된 견적이 없습니다."
        if skipped > 0: st.session_state['warning_msg'] = f"타 사원의 견적 {skipped}건 제외됨."
        st.session_state['raw_input_area'] = ""

col_head_left, col_head_right = st.columns([2, 1])
with col_head_left:
    st.title("충청호남팀 견적 관리 및 TM 진도")
    st.caption(f"기준일: {today.strftime('%Y년 %m월 %d일')} | 실시간 자동 동기화 서버 연결됨")

with col_head_right:
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    sub_col1, sub_col2 = st.columns([3, 1])
    with sub_col1:
        if is_master: st.markdown(f"<div class='user-info-box'><span class='user-info-name'>{my_name} 님</span></div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='user-info-box'><span class='user-info-name'>{my_name} 님 ({my_dealer})</span><br><span class='user-info-sub'>사번: {my_id}</span></div>", unsafe_allow_html=True)
    with sub_col2:
        if st.button("로그아웃"): 
            st.session_state.clear() 
            st.rerun()
        
    if is_master:
        if 'selected_hc' not in st.session_state: st.session_state['selected_hc'] = "🌟 전체보기 (모든 영업사원)"
        dealers = sorted(list(set([info['dealer'] for info in HC_DB.values()])))
        all_hc_list = ["🌟 전체보기 (모든 영업사원)"]
        all_hc_list.append("🌍 [충청상권] 통합 조회")
        all_hc_list.append("🌍 [호남상권] 통합 조회")
        for d in dealers: all_hc_list.append(f"🏢 [{d}] 대리점 전체보기")
        for info in HC_DB.values(): all_hc_list.append(f"👤 {info['name']} ({info['dealer']})")
        selected_hc = st.selectbox("마스터 전용 조회 필터", all_hc_list, key="selected_hc")

if is_master:
    my_df = st.session_state['data'].copy()
    if selected_hc == "🌟 전체보기 (모든 영업사원)": pass
    elif "통합 조회" in selected_hc:
        region_name = selected_hc.split("[")[1].split("]")[0]
        allowed_dealers = REGION_MAP.get(region_name, [])
        my_df = my_df[my_df['대리점명'].isin(allowed_dealers)]
    elif "대리점 전체보기" in selected_hc:
        dealer_name = selected_hc.split("[")[1].split("]")[0]
        my_df = my_df[my_df['대리점명'] == dealer_name]
    else:
        my_df = my_df[my_df['HC명'] == selected_hc.replace("👤 ", "").split(" (")[0]]
else: 
    my_df = st.session_state['data'][st.session_state['data']['HC_ID'] == my_id].copy()

st.markdown("---")

perf_df = load_perf_sheet(client)
if is_master:
    if selected_hc == "🌟 전체보기 (모든 영업사원)": target_id = target_name_perf = "ALL"
    elif "통합 조회" in selected_hc:
        region_name = selected_hc.split("[")[1].split("]")[0]
        target_id = target_name_perf = f"REGION_{region_name}"
    elif "대리점 전체보기" in selected_hc:
        dealer_name = selected_hc.split("[")[1].split("]")[0]
        target_id = target_name_perf = f"DEALER_{dealer_name}"
    else:
        target_name_perf = selected_hc.replace("👤 ", "").split(" (")[0]
        target_id = next((k for k, v in HC_DB.items() if v['name'] == target_name_perf), my_id)
else:
    target_id, target_name_perf = my_id, my_name

metrics = get_perf_metrics(perf_df, target_id, target_name_perf)
def fmt(n): return f"{int(round(n)):,}"

F_str, G_str, H_str, I_str = fmt(metrics['F']), fmt(metrics['G']), fmt(metrics['H']), fmt(metrics['I'])
J_str = f"{int(round(metrics['J']))}%" 
R_str, Y_str, W_str = fmt(metrics['R']), fmt(metrics['Y']), fmt(metrics['W'])
T_str, U_str = fmt(metrics['T']), fmt(metrics['U'])

growth = (metrics['T'] / metrics['U'] - 1) if metrics['U'] > 0 else 0
growth_html = ""
if metrics['U'] > 0:
    g_pct = int(round(abs(growth) * 100))
    if growth > 0: growth_html = f'<span style="color:#dc2626; font-size:14px; margin-left:4px;">(▲{g_pct}%)</span>'
    elif growth < 0: growth_html = f'<span style="color:#2563eb; font-size:14px; margin-left:4px;">(▼{g_pct}%)</span>'
    else: growth_html = f'<span style="color:#64748b; font-size:14px; margin-left:4px;">(-0%)</span>'

combined_val_str = f'<span style="color:#dc2626;">{T_str}</span> <span style="color:#94a3b8;">/</span> <span style="color:#2563eb;">{U_str}</span> {growth_html} <span style="color:#94a3b8;">/</span> <span style="color:#10b981;">{W_str}</span>'

dash_html = f"""
<div style="background: #f1f5f9; padding: 16px; border-radius: 12px; border: 1px solid #cbd5e1; width: 100%;">
    <div style="display:flex; justify-content: space-between; align-items:center; margin-bottom: 8px;">
        <div style="font-size: 16px; font-weight: 900; color: #0f172a;">🏆 영업 VDT 실적 현황</div>
        <div style="font-size: 12px; color: #64748b; font-weight: bold;">(당일 실시간 기준)</div>
    </div>
    <div class="dash-grid">
        <div class="dash-card"><div class="dash-title">견적건 (일)</div><div class="dash-value">{F_str}</div></div>
        <div class="dash-card"><div class="dash-title">견적건 (월누적)</div><div class="dash-value">{H_str}</div></div>
        <div class="dash-card green"><div class="dash-title">계약건 (일)</div><div class="dash-value">{G_str}</div></div>
        <div class="dash-card green"><div class="dash-title">계약건 (월누적)</div><div class="dash-value">{I_str}</div></div>
        <div class="dash-card purple"><div class="dash-title">계약율</div><div class="dash-value" style="color:#9333ea;">{J_str}</div></div>
        <div class="dash-card orange"><div class="dash-title">계약금액 (월누적)</div><div class="dash-value">{R_str}</div></div>
        <div class="dash-card red"><div class="dash-title" style="letter-spacing:-1px;">당월/전월(동일자)/전월마감</div><div class="dash-value" style="font-size:14px; word-break:keep-all;">{combined_val_str}</div></div>
        <div class="dash-card"><div class="dash-title">익월 매출</div><div class="dash-value">{Y_str}</div></div>
    </div>
</div>
"""
st.markdown(dash_html, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------
# 🚀 9월/8월 고정 반영을 위한 로직 수정 부문
# -------------------------------------------------------------
st.subheader("📊 월별 견적 관리 지표 요약 (최근 2개월)")

temp_dates = pd.to_datetime(my_df['상담일'], errors='coerce')
valid_mask = temp_dates.notna()

if valid_mask.any():
    ym_series = temp_dates[valid_mask].dt.to_period('M')
else:
    ym_series = pd.Series(dtype='period[M]')

curr_period = pd.Period(today.strftime('%Y-%m'))
prev_period = curr_period - 1

ym_unique = [curr_period, prev_period]

month_cols = st.columns(len(ym_unique))
for idx, ym in enumerate(ym_unique):
    if valid_mask.any():
        m_df = my_df[valid_mask & (ym_series == ym)]
    else:
        m_df = pd.DataFrame()
        
    t_quotes = len(m_df)
    t_tm1 = len(m_df[m_df['1차_TM'] == True]) if not m_df.empty else 0
    t_tm2 = len(m_df[m_df['2차_TM'] == True]) if not m_df.empty else 0
    t_tm3 = len(m_df[m_df['3차_TM'] == True]) if not m_df.empty else 0
    t_contract = int(m_df['계약완료'].sum()) if not m_df.empty else 0
    t_tm_done = len(m_df[(m_df['1차_TM'] == True) | (m_df['2차_TM'] == True) | (m_df['3차_TM'] == True)]) if not m_df.empty else 0
    
    t_tm_rate = (t_tm_done / t_quotes * 100) if t_quotes > 0 else 0
    t_cont_rate = (t_contract / t_quotes * 100) if t_quotes > 0 else 0
    
    month_badge = ""
    if idx == 0:
        month_badge = "<span style='color:white; background-color:#3b82f6; font-size:12px; padding:2px 8px; border-radius:10px; margin-left:6px; vertical-align:middle;'>(당월)</span>"
    elif idx == 1:
        month_badge = "<span style='color:white; background-color:#f59e0b; font-size:12px; padding:2px 8px; border-radius:10px; margin-left:6px; vertical-align:middle;'>(전월)</span>"
    
    with month_cols[idx]:
        st.markdown(f"""
        <div style="background:#f8fafc; padding:18px; border-radius:12px; border:2px solid #e2e8f0; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <div style="font-size:18px; font-weight:900; color:#0f172a; margin-bottom:12px; border-bottom: 2px solid #cbd5e1; padding-bottom: 8px;">
                📅 {ym.year}년 {ym.month}월 요약본 {month_badge}
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <div style="text-align:center;"><div style="font-size:13px; color:#64748b; font-weight:bold;">총 견적</div><div style="font-size:22px; font-weight:900; color:#2563eb;">{t_quotes}건</div></div>
                <div style="text-align:center;"><div style="font-size:13px; color:#64748b; font-weight:bold;">전체 TM 진행률</div><div style="font-size:22px; font-weight:900; color:#dc2626;">{t_tm_rate:.1f}%</div></div>
                <div style="text-align:center;"><div style="font-size:13px; color:#64748b; font-weight:bold;">계약 완료(율)</div><div style="font-size:20px; font-weight:900; color:#10b981;">{t_contract}건 <span style="font-size:14px;">({t_cont_rate:.1f}%)</span></div></div>
            </div>
            <div style="font-size:15px; color:#334155; text-align:center; background:#e2e8f0; border-radius:8px; padding:10px; margin-top: 8px;">
                <b style="color:#0f172a; font-size:16px;">✔️ 세부 진행건수</b> &nbsp;👉&nbsp;
                1차 완료 <span style="font-size:18px; font-weight:900; color:#2563eb;">{t_tm1}</span>건 &nbsp;|&nbsp; 
                2차 완료 <span style="font-size:18px; font-weight:900; color:#10b981;">{t_tm2}</span>건 &nbsp;|&nbsp; 
                3차 완료 <span style="font-size:18px; font-weight:900; color:#8b5cf6;">{t_tm3}</span>건
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

if is_master and 'selected_hc' in st.session_state and st.session_state['selected_hc'] != "🌟 전체보기 (모든 영업사원)":
    if "통합 조회" in st.session_state['selected_hc']:
        region_name = st.session_state['selected_hc'].split("[")[1].split("]")[0]
        st.markdown(f"<h3>견적 및 TM 목록 <span style='color: #0369a1; font-size: 20px; background-color: #e0f2fe; padding: 4px 12px; border-radius: 8px; border: 2px solid #7dd3fc; margin-left: 8px; vertical-align: middle;'>👉 현재 선택: 🌍 [{region_name}] 통합 조회 중</span></h3>", unsafe_allow_html=True)
    elif "대리점 전체보기" in st.session_state['selected_hc']:
        dealer_name = st.session_state['selected_hc'].split("[")[1].split("]")[0]
        st.markdown(f"<h3>견적 및 TM 목록 <span style='color: #0369a1; font-size: 20px; background-color: #e0f2fe; padding: 4px 12px; border-radius: 8px; border: 2px solid #7dd3fc; margin-left: 8px; vertical-align: middle;'>👉 현재 선택: 🏢 [{dealer_name}] 대리점 전체 조회 중</span></h3>", unsafe_allow_html=True)
    else:
        sel_name = st.session_state['selected_hc'].replace("👤 ", "").split(" (")[0]
        sel_id = next((k for k, v in HC_DB.items() if v['name'] == sel_name), "알수없음")
        st.markdown(f"<h3>견적 및 TM 목록 <span style='color: #0369a1; font-size: 20px; background-color: #e0f2fe; padding: 4px 12px; border-radius: 8px; border: 2px solid #7dd3fc; margin-left: 8px; vertical-align: middle;'>👉 현재 선택: 👤 {sel_name} (사번: {sel_id})</span></h3>", unsafe_allow_html=True)
else:
    if is_master: st.markdown(f"<h3>견적 및 TM 목록 <span style='color: #0369a1; font-size: 20px; background-color: #e0f2fe; padding: 4px 12px; border-radius: 8px; border: 2px solid #7dd3fc; margin-left: 8px; vertical-align: middle;'>👉 현재 선택: 🌟 모든 영업사원 통합</span></h3>", unsafe_allow_html=True)
    else: st.subheader("견적 및 TM 목록")

filter_tab = st.radio("표시 모드 선택", ["전체 목록 보기", "본인 작성 견적만 보기"], horizontal=True)

display_df = my_df.copy()
if filter_tab == "본인 작성 견적만 보기": display_df = display_df[display_df['is_self'] == True]

col_add, col_up = st.columns([1, 1])

with col_add:
    with st.expander("➕ 한샘 시스템 복사해서 새 견적 추가", expanded=True):
        st.text_area("텍스트를 붙여넣으세요", height=150, key="raw_input_area", label_visibility="collapsed")
        st.button("🚀 견적 추가 및 시트 저장", on_click=add_quotes_callback, use_container_width=True)

with col_up:
    with st.expander("📸 TM 증빙 퀵 업로더 (적용할 견적을 확인 후 바로 올리세요!)", expanded=True):
        temp_df = display_df.copy()
        if not temp_df.empty:
            quote_list = ["--- 견적을 선택하세요 ---"] + (temp_df['상담일'].astype(str) + " | " + temp_df['고객명'] + " (" + temp_df['상담번호'] + ")").tolist()
            
            u1, u2 = st.columns([2, 1])
            with u1: sel_quote = st.selectbox("견적 선택", quote_list, label_visibility="collapsed", key=f"q_{st.session_state['uploader_key']}")
            with u2: sel_tm = st.selectbox("TM 차수", ["1차_증빙", "2차_증빙", "3차_증빙"], label_visibility="collapsed", key=f"t_{st.session_state['uploader_key']}")
            
            u3, u4 = st.columns([2, 1])
            with u3: uploaded_img = st.file_uploader("사진 선택", type=['jpg', 'jpeg', 'png'], label_visibility="collapsed", key=f"f_{st.session_state['uploader_key']}")
            with u4:
                st.markdown("<div style='margin-top:2px;'></div>", unsafe_allow_html=True)
                if st.button("📤 사진 즉시 업로드", use_container_width=True, type="primary"):
                    if sel_quote == "--- 견적을 선택하세요 ---" or not uploaded_img: st.warning("견적 선택 및 사진을 올려주세요!")
                    else:
                        q_no = re.search(r'\((.*?)\)', sel_quote).group(1)
                        with st.spinner("서버에 전송 중..."):
                            img_url = upload_to_imgbb(io.BytesIO(uploaded_img.read()), f"{q_no}_{sel_tm}_{today.strftime('%Y%m%d')}.jpg")
                            if img_url:
                                st.session_state['data'].loc[st.session_state['data']['상담번호'] == q_no, sel_tm] = img_url
                                if save_data_to_sheet(client, st.session_state['data'], is_master, my_name):
                                    st.success("업로드 완료!"); st.session_state['uploader_key'] += 1; st.rerun()
                                else: st.error("시트 저장 실패.")
        else:
            st.info("먼저 견적을 등록해주세요!")

if st.session_state['success_msg']: st.success(st.session_state['success_msg']); st.session_state['success_msg'] = ""
if st.session_state['warning_msg']: st.warning(st.session_state['warning_msg']); st.session_state['warning_msg'] = ""

if not display_df.empty:
    alert_list = []
    for _, row in display_df.iterrows():
        msgs = []
        for i in [1, 2, 3]:
            if row.get(f'{i}차_TM') == True:
                missing = []
                d_val = row.get(f'{i}차_TM_일자')
                p_val = row.get(f'{i}차_증빙')
                if pd.isna(d_val) or str(d_val).strip() in ['', 'None']: missing.append("일자")
                if pd.isna(p_val) or str(p_val).strip() in ['', 'None']: missing.append("증빙")
                if missing: msgs.append(f"{i}차({','.join(missing)})")
        if msgs: alert_list.append(" ".join(msgs))
        else: alert_list.append("")
    display_df['🚨 TM누락 확인'] = alert_list

col_order = ["선택/삭제", "상담일", "상담번호", "HC명", "대리점명", "고객명", "연락처", "주소", "상품", "세부품목", "현장유형", "견적금액", "🚨 TM누락 확인", "1차_TM", "1차_TM_일자", "1차_증빙", "2차_TM", "2차_TM_일자", "2차_증빙", "3차_TM", "3차_TM_일자", "3차_증빙", "계약완료", "계약완료금액", "상담메모"] if is_master else ["선택/삭제", "상담일", "상담번호", "고객명", "연락처", "주소", "상품", "세부품목", "현장유형", "견적금액", "🚨 TM누락 확인", "1차_TM", "1차_TM_일자", "1차_증빙", "2차_TM", "2차_TM_일자", "2차_증빙", "3차_TM", "3차_TM_일자", "3차_증빙", "계약완료", "계약완료금액", "상담메모"]

if not display_df.empty:
    action_placeholder = st.empty()
    
    col_banner, col_check = st.columns([3, 1])
    with col_banner:
        st.markdown("<div style='margin-top: 5px;' class='table-header-banner'>상세 견적 목록 (수정 후 바로 위쪽의 '저장' 버튼을 꼭 눌러주세요!)</div>", unsafe_allow_html=True)
    with col_check:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        select_all = st.checkbox("✅ 현재 목록 전체 선택", key=f"sel_all_{st.session_state['uploader_key']}")
        if select_all:
            display_df['선택/삭제'] = True
    
    edited_df = st.data_editor(display_df, column_order=col_order, column_config={
        "선택/삭제": st.column_config.CheckboxColumn("선택/삭제", width="small"), 
        "상담일": st.column_config.DateColumn("상담일", format="MM/DD", width="small"),
        "상담번호": st.column_config.TextColumn("상담번호", width="small", disabled=True), 
        "고객명": st.column_config.TextColumn("고객명", width="small"),
        "연락처": st.column_config.TextColumn("연락처", width="small"),
        "주소": st.column_config.TextColumn("주소", width="medium"),
        "상품": st.column_config.TextColumn("상품", width="small"),
        "세부품목": st.column_config.TextColumn("세부품목 (더블클릭)", width="medium", help="더블클릭하여 전체 내용을 확인하세요."),
        "현장유형": st.column_config.TextColumn("현장유형", width="small"),
        "견적금액": st.column_config.NumberColumn("견적금액", format="%,d", width="small"), 
        "🚨 TM누락 확인": st.column_config.TextColumn("🚨 TM누락 확인", width="small", disabled=True), 
        "1차_TM": st.column_config.CheckboxColumn("1차", width="small"),
        "1차_TM_일자": st.column_config.DateColumn("1차 일자", format="MM/DD", width="small"), 
        "1차_증빙": st.column_config.LinkColumn("1차 증빙", display_text="🔗보기", width="small"),
        "2차_TM": st.column_config.CheckboxColumn("2차", width="small"), 
        "2차_TM_일자": st.column_config.DateColumn("2차 일자", format="MM/DD", width="small"),
        "2차_증빙": st.column_config.LinkColumn("2차 증빙", display_text="🔗보기", width="small"), 
        "3차_TM": st.column_config.CheckboxColumn("3차", width="small"),
        "3차_TM_일자": st.column_config.DateColumn("3차 일자", format="MM/DD", width="small"), 
        "3차_증빙": st.column_config.LinkColumn("3차 증빙", display_text="🔗보기", width="small"),
        "계약완료": st.column_config.CheckboxColumn("계약완료", width="small"), 
        "계약완료금액": st.column_config.NumberColumn("최종계약액", format="%,d", width="small"),
        "상담메모": st.column_config.TextColumn("상담메모", width="medium")
    }, hide_index=True, use_container_width=True, height=550) 
    
    with action_placeholder.container():
        action_col2, action_col3 = st.columns([1, 1])
        with action_col2:
            if not st.session_state['confirm_delete']:
                st.markdown('<span class="red-btn"></span>', unsafe_allow_html=True)
                if st.button("🗑️ 1번 - 선택한 견적 완전 삭제하기", use_container_width=True):
                    to_del = edited_df[edited_df['선택/삭제'] == True]['상담번호'].tolist()
                    if to_del:
                        st.session_state['confirm_delete'] = True
                        st.session_state['to_del_list'] = to_del
                        st.rerun()
                    else: 
                        st.warning("삭제할 항목을 먼저 체크해 주세요!")
            else:
                st.markdown(f"<div style='background-color:#fee2e2; border: 2px solid #ef4444; padding:8px; border-radius:8px; color:#b91c1c; font-weight:900; text-align:center; margin-bottom:8px;'>⚠️ 정말 {len(st.session_state['to_del_list'])}건을 영구 삭제하시겠습니까? (이 작업은 되돌릴 수 없습니다!)</div>", unsafe_allow_html=True)
                del_c1, del_c2 = st.columns(2)
                with del_c1:
                    st.markdown('<span class="red-btn"></span>', unsafe_allow_html=True)
                    if st.button("✅ 네, 완전히 삭제합니다", use_container_width=True):
                        with st.spinner("삭제 중..."):
                            st.session_state['data'] = clean_and_enforce_types(st.session_state['data'][~st.session_state['data']['상담번호'].isin(st.session_state['to_del_list'])])
                            if save_data_to_sheet(client, st.session_state['data'], is_master, my_name): 
                                st.success("삭제 완료!")
                                st.session_state['uploader_key'] += 1
                                st.session_state['confirm_delete'] = False
                                st.rerun()
                with del_c2:
                    if st.button("❌ 아니오, 취소합니다", use_container_width=True):
                        st.session_state['confirm_delete'] = False
                        st.rerun()

        with action_col3:
            st.markdown('<span class="yellow-btn"></span>', unsafe_allow_html=True)
            if st.button("💾 2번 - 견적 리스트 작성 / 수정 후 최종 저장 (필수)", use_container_width=True):
                with st.spinner("저장 중..."):
                    tdf = edited_df.copy()
                    if '🚨 TM누락 확인' in tdf.columns: tdf = tdf.drop(columns=['🚨 TM누락 확인'])
                    tdf['선택/삭제'] = False 
                    
                    global_df = st.session_state['data'].copy()
                    global_df = global_df.drop(display_df.index, errors='ignore')
                    new_global_df = clean_and_enforce_types(pd.concat([global_df, tdf]).sort_values(by='상담일', ascending=False).reset_index(drop=True))
                    
                    if save_data_to_sheet(client, new_global_df, is_master, my_name): 
                        st.session_state['data'] = new_global_df
                        st.success("안전하게 전체 수정사항이 덮어쓰기 되었습니다!")
                        st.session_state['uploader_key'] += 1
                        st.rerun()
