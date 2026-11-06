import socket
socket.setdefaulttimeout(15.0) 

import streamlit as st
import pandas as pd
import numpy as np
import json
import gspread
from google.oauth2.service_account import Credentials
import traceback
from datetime import datetime
import plotly.graph_objects as go 
import re 
import time

# 1. 화면 기본 설정
st.set_page_config(page_title="충청호남팀 영업사원 주차별 VDT 목표 관리", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1yZdc4BL5CHLwBQ2QGp8zD5_ov7LDKsEcnrONdQvDyHI/edit?gid=1748736055#gid=1748736055"

@st.cache_resource
def init_connection():
    try:
        creds_json = st.secrets["gcp"]["key"]
        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"구글 API 키 오류: {e}")
        return None

client = init_connection()

# --- 커스텀 CSS (Noto Sans KR 적용) ---
st.markdown("""
<style>
    /* 💡 Noto Sans KR 웹폰트 로드 */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

    /* 💡 전체 텍스트에 Noto Sans KR 적용 */
    html, body, p, span, label, button, input, select, textarea, h1, h2, h3, h4, h5, h6, th, td {
        font-family: 'Noto Sans KR', -apple-system, sans-serif !important;
    }

    /* 🚨 시스템 아이콘 폰트 깨짐 방지 */
    .stIconMaterial, .material-icons, [data-testid*="stIcon"], [data-baseweb="icon"] {
        font-family: "Material Symbols Rounded", "Material Icons", sans-serif !important;
        font-weight: 400 !important;
    }

    .main .block-container, [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] {
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

# 🚨 영업사원 명단
HC_DB = {
    "00033448": {"name": "장재형", "dealer": "둔산"},
    "00038617": {"name": "이대운", "dealer": "둔산"},
    "00041990": {"name": "강지인", "dealer": "둔산"},
    "00040110": {"name": "장영종", "dealer": "광양"},
    "00040112": {"name": "임현", "dealer": "광양"},
    "00040113": {"name": "하행우", "dealer": "광양"},
    "00042008": {"name": "김경율", "dealer": "세종"},
    "00044932": {"name": "강희성", "dealer": "세종"},
    "00044933": {"name": "한유진", "dealer": "세종"},
    "00040744": {"name": "빙지영", "dealer": "목포"},
    "00040755": {"name": "윤덕수", "dealer": "목포"},
    "00043657": {"name": "최병하", "dealer": "익산"},
    "00043825": {"name": "이은혜", "dealer": "익산"},
    "00033249": {"name": "임준수", "dealer": "충주"},
    "00033479": {"name": "류승태", "dealer": "여수"},
    "00042423": {"name": "라태현", "dealer": "여수"},
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
            pad_id = str(login_id).strip().zfill(8) if login_id else ""
            input_pw = str(login_pw).strip()
            
            if pad_id == "00000000" and input_pw == "0000":
                st.session_state.update({'logged_in': True, 'hc_id': "0000", 'hc_name': "총괄관리자", 'dealer': "마스터", 'is_master': True}); st.rerun()
            elif pad_id in HC_DB and str(login_id).strip() == input_pw: 
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
        data = _gc_client.open(SHEET_NAME).worksheet("시트1").get("B10:AG200")
        if data:
            safe_rows = [r + [''] * (32 - len(r)) for r in data]
            return pd.DataFrame(safe_rows)
        return pd.DataFrame()
    except Exception as e:
        print(f"VDT 데이터를 가져오지 못했습니다 (API 한도 또는 시트 오류): {e}")
        return pd.DataFrame()

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
                sums['F'] += clean_val(vals[4]); sums
