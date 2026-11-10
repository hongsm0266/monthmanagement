import socket
socket.setdefaulttimeout(15.0) 

import streamlit as st
import pandas as pd
import numpy as np
import json
import gspread
from google.oauth2.service_account import Credentials
import traceback
from datetime import datetime, timedelta
import plotly.graph_objects as go 
import re 
import time

# 1. 화면 기본 설정
st.set_page_config(page_title="충청호남팀 영업사원 주차별 VDT 목표 관리", layout="wide")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1yZdc4BL5CHLwBQ2QGp8zD5_ov7LDKsEcnrONdQvDyHI/edit?gid=1748736055#gid=1748736055"

# 🚀 접속 시 초기값 강제 세팅 
if 'init_v14' not in st.session_state:
    st.session_state['view_target'] = "충청호남팀 전체"
    st.session_state['hc_selector'] = "✨ 인원별 상세 실적 (선택 시 우선 적용)"
    st.session_state['view_mode'] = "주간 추이 (최근 8주)"
    st.session_state['t_amt'] = True  
    st.session_state['t_sales'] = False
    st.session_state['t_next'] = False
    st.session_state['t_avg'] = False
    st.session_state['t_wd'] = False
    st.session_state['t_we'] = False
    st.session_state['t_walk'] = False
    st.session_state['t_move'] = False
    st.session_state['t_est'] = False
    st.session_state['t_cnt'] = False
    st.session_state['t_rate'] = False
    st.session_state['t_unit'] = False
    st.session_state['wow_week'] = None 
    st.session_state['init_v14'] = True

toggle_keys = ['t_amt', 't_sales', 't_next', 't_avg', 't_wd', 't_we', 't_walk', 't_move', 't_est', 't_cnt', 't_rate', 't_unit']
EXCLUDED_HCS = ["장재형", "강지인", "신재민"]

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

# --- 커스텀 CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
    
    html, body, [class*="css"], [class*="st-"], th, td { font-family: 'Noto Sans KR', sans-serif !important; }
    
    .vdt-table-container { width: 100%; max-height: 65vh; overflow: auto; border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 10px; }
    .vdt-table-container::-webkit-scrollbar { width: 14px; height: 14px; }
    .vdt-table-container::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 8px; }
    .vdt-table-container::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 8px; border: 3px solid #f1f5f9; }
    
    .vdt-table { width: 100%; border-collapse: collapse; font-size: 12px; white-space: nowrap; }
    .vdt-table thead th { height: 34px; box-sizing: border-box; position: sticky; z-index: 10; background-clip: padding-box; }
    .vdt-table thead tr:nth-child(1) th { top: 0; }
    .vdt-table thead tr:nth-child(2) th { top: 33px; }
    .vdt-table thead tr:nth-child(3) th { top: 66px; }
    .vdt-table th { background-color: #0f172a; color: white; padding: 8px 10px; text-align: center; border: 1px solid #334155; font-weight: 600; }
    .vdt-table td { padding: 6px 10px; text-align: right; border: 1px solid #e2e8f0; }
    .vdt-table td.text-center { text-align: center; }
    
    .title-box { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 12px; border-radius: 8px; margin-bottom: 12px; }
    h1 { font-weight: 900 !important; color: white !important; font-size: 14px !important; margin: 0; }
    h3, h4 { font-size: 14px !important; font-weight: 900 !important; color: #1e293b !important; }
    
    /* WoW Table Styles */
    .wow-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .wow-table th { background-color: #1e293b; color: white; padding: 8px; text-align: center; border: 1px solid #334155; font-weight: 900; }
    .wow-table th.sub { background-color: #475569; font-size: 12px; }
    .wow-table td { padding: 8px; text-align: right; border: 1px solid #cbd5e1; background-color: white; }
    .wow-table td.name-col { text-align: center; font-weight: 900; background-color: #f8fafc; color: #0f172a; }
    .wow-up { color: #dc2626; font-weight: 900; }
    .wow-down { color: #2563eb; font-weight: 900; }
    .wow-same { color: #64748b; font-weight: 600; }
    .wow-highlight { background-color: #fef2f2 !important; font-weight: 900; }

    div[data-testid="metric-container"] { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    [data-testid="stMetricLabel"] { background-color: #e2e8f0 !important; padding: 4px 10px !important; border-radius: 6px !important; border-left: 5px solid #3b82f6 !important; display: inline-block !important; margin-bottom: 6px !important; }
    [data-testid="stMetricLabel"] * { font-size: 12px !important; font-weight: 900 !important; color: #0f172a !important; letter-spacing: -0.3px; }
    [data-testid="stMetricValue"] > div { font-size: 20px !important; font-weight: 900 !important; color: #1e3a8a !important; margin-top: 5px; }
    
    div.stButton > button { 
        background: #f8fafc !important; color: #020617 !important; font-size: 12px !important; font-weight: 900 !important; 
        border-radius: 6px !important; padding: 4px 6px !important; border: 1px solid #94a3b8 !important; height: auto !important; min-height: 32px; 
        border-bottom: 2px solid #64748b !important; transition: all 0.1s ease !important; letter-spacing: -0.5px !important;
    }
    div.stButton > button[kind="primary"] { 
        background: linear-gradient(180deg, #fee2e2 0%, #fecaca 100%) !important; color: #991b1b !important; 
        border: 1px solid #f87171 !important; border-bottom: 2px solid #ef4444 !important; 
    }
    
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(1) button { background-color: #faf5ff !important; border-color: #e9d5ff !important; color: #9333ea !important; border-bottom: 2px solid #d8b4fe !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(1) button[kind="primary"] { background: linear-gradient(180deg, #f3e8ff 0%, #e9d5ff 100%) !important; color: #3b0764 !important; border-bottom: 2px solid #7e22ce !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(3) button { background-color: #f0f9ff !important; border-color: #bae6fd !important; color: #0284c7 !important; border-bottom: 2px solid #7dd3fc !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(3) button[kind="primary"] { background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%) !important; color: #082f49 !important; border-bottom: 2px solid #0284c7 !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(9) button { background-color: #f0fdf4 !important; border-color: #bbf7d0 !important; color: #16a34a !important; border-bottom: 2px solid #86efac !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(9) button[kind="primary"] { background: linear-gradient(180deg, #dcfce7 0%, #bbf7d0 100%) !important; color: #052e16 !important; border-bottom: 2px solid #16a34a !important; }

    .btn-group-title { font-size: 12px; font-weight: 900; color: #1e293b; background: #e2e8f0; border-radius: 4px; padding: 4px 10px; margin-bottom: 6px; border-left: 4px solid #3b82f6; }
    .chart-btn-group { font-size: 11px; font-weight: 800; color: #475569; background: #e2e8f0; border-radius: 4px; padding: 2px 0; text-align: center; margin-bottom: 4px; border: 1px solid #cbd5e1;}
    .mode-toggle { font-size: 14px; font-weight: 900; color: #0f172a; display:flex; align-items:center; gap:10px;}
</style>
""", unsafe_allow_html=True)

current_date = datetime.now()
current_month = current_date.month

st.markdown(f"<div class='title-box'><h1>📊 충청호남팀 영업사원 주차별 VDT 목표 관리 ({current_month}월)</h1></div>", unsafe_allow_html=True)

def clean_str(val): return re.sub(r'\s+', '', str(val))
def safe_get(row, idx): return str(row[idx]).strip() if len(row) > idx else ""

# 🚀 금액 포맷 변환 시 음수(-) 완벽 인식 보강
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

def get_mapped_dealer(raw_d):
    c_d = clean_str(raw_d)
    if any(k in c_d for k in ["한밭", "INT충청", "701347", "세종2"]): return "세종"
    return raw_d.strip()

REGION_MAP = {
    "충청상권": ["둔산", "목포", "세종", "충주"], 
    "호남상권": ["광양", "여수", "익산"]
}

# 🚀 8주 트렌드 기준 맵핑
current_monday = current_date - timedelta(days=current_date.weekday())
trend_ranges = []
trend_labels = []
for i in range(7, -1, -1):
    w_start = current_monday - timedelta(weeks=i)
    w_end = w_start + timedelta(days=6)
    iso_year, iso_week, iso_day = w_start.isocalendar()
    trend_ranges.append((w_start, w_end))
    label = f"{iso_week}주 ({w_start.strftime('%m.%d')}~{w_end.strftime('%m.%d')})"
    trend_labels.append(label)

def get_trend_week_idx(m, d):
    try: 
        target_date = datetime(current_date.year, m, d)
        for i, (start, end) in enumerate(trend_ranges):
            if start.date() <= target_date.date() <= end.date(): return i
    except: pass
    return -1

month_list = [8, 9, 10, 11]
month_labels = [f"{m}월" for m in month_list]

def safe_api_call(func, *args, **kwargs):
    max_retries = 6
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if "429" in str(e):
                if attempt < max_retries - 1:
                    wait_time = 15 * (attempt + 1)
                    st.toast(f"⏳ 구글 서버 요청 과열로 대기 중입니다... ({wait_time}초 후 재시도)", icon="⚠️")
                    time.sleep(wait_time)
                    continue
            raise e

@st.cache_data(ttl=600)
def load_vdt_data():
    if not client: return pd.DataFrame(), {}, {}, {}, {}, [], {}, ""
    
    status_box = st.empty()
    try:
        status_box.info("🔍 0단계: 구글 시트 연결 중...")
        sh = safe_api_call(client.open_by_url, SHEET_URL)
        all_worksheets = [ws.title for ws in safe_api_call(sh.worksheets)]
        
        target_sheet_name = "주차별 목표 세팅"
        if target_sheet_name not in all_worksheets: 
            return pd.DataFrame(), {}, {}, {}, {}, [], {}, ""
        
        target_ws = sh.worksheet(target_sheet_name)
        status_box.info("📊 1단계: O~R열 목표 스캔 및 세종 통합 중...")
        all_targets = safe_api_call(target_ws.get_all_values)
        
        hc_to_dealer_master = {}
        hc_info_dict = {}         
        dealer_sales_sum = {} 
        
        for row in all_targets[15:]:
            if len(row) > 17:
                raw_dealer = str(row[14]).strip()
                hc_name = clean_str(row[15])
                tgt_str = str(row[17]).strip()
                
                if not raw_dealer or not hc_name: continue
                if raw_dealer in ['대리점', '대리점명', '구분'] or hc_name in ['HC', 'HC명', '영업사원', '이름']: continue
                if hc_name.isdigit(): continue
                
                dealer = get_mapped_dealer(raw_dealer)
                hc_to_dealer_master[hc_name] = dealer
                sales_target = clean_val(tgt_str) / 1000.0  
                
                if hc_name in hc_info_dict: 
                    hc_info_dict[hc_name]['tgt'] += sales_target
                else: 
                    hc_info_dict[hc_name] = {'dealer': dealer, 'tgt': sales_target}
                dealer_sales_sum[dealer] = dealer_sales_sum.get(dealer, 0.0) + sales_target

        hc_info_raw = [(info['dealer'], name, info['tgt']) for name, info in hc_info_dict.items()]

        status_box.info("🎯 2단계: 주차별 표 자동 스캔 및 배분 중...")
        
        week_row_idx, date_row_idx = -1, -1
        for i, row in enumerate(all_targets[:10]):
            row_str = "".join(str(c) for c in row)
            if "주" in row_str and re.search(r'\d+주', row_str) and week_row_idx == -1:
                week_row_idx = i
            if (re.search(r'\d+/\d+', row_str) or re.search(r'\d+\.\d+', row_str)) and date_row_idx == -1:
                date_row_idx = i
        
        week_cols = {}
        date_headers = {}
        if week_row_idx != -1:
            week_row = all_targets[week_row_idx]
            date_row = all_targets[date_row_idx] if date_row_idx != -1 else all_targets[week_row_idx+1]
            for col_idx, cell_val in enumerate(week_row):
                c_val = str(cell_val).strip()
                if "주" in c_val and col_idx >= 1: 
                    week_cols[c_val] = {'amt': col_idx, 'est': col_idx+1, 'cnt': col_idx+2}
                    date_headers[c_val] = str(date_row[col_idx]).strip() if col_idx < len(date_row) else ""
                
        if not week_cols:
            week_cols = {
                '1주차': {'amt': 1, 'est': 2, 'cnt': 3}, '2주차': {'amt': 4, 'est': 5, 'cnt': 6},   
                '3주차': {'amt': 7, 'est': 8, 'cnt': 9}, '4주차': {'amt': 10, 'est': 11, 'cnt': 12}, 
                '5주차': {'amt': 13, 'est': 14, 'cnt': 15}, 
            }
            date_headers = {wk: wk for wk in week_cols}
            
        week_keys = list(week_cols.keys())
        
        date_to_target_week = {}
        current_year = current_date.year
        for wk, d_str in date_headers.items():
            dates = re.findall(r'\d+', d_str)
            if len(dates) >= 4:
                try:
                    m1, d1, m2, d2 = map(int, dates[:4])
                    start_dt = datetime(current_year, m1, d1)
                    end_dt = datetime(current_year, m2, d2)
                    if m1 == 12 and m2 == 1: end_dt = datetime(current_year + 1, m2, d2)
                    curr = start_dt
                    while curr <= end_dt:
                        date_to_target_week[(curr.month, curr.day)] = wk
                        curr += timedelta(days=1)
                except: pass
            elif len(dates) >= 2:
                try:
                    m1, d1 = map(int, dates[:2])
                    date_to_target_week[(m1, d1)] = wk
                except: pass

        dealer_targets = {}
        for row in all_targets[:15]: 
            if len(row) > 0 and str(row[0]).strip():
                raw_d_name = str(row[0]).strip()
                if raw_d_name in ['대리점명', '구분', '대리점']: continue
                d_name = get_mapped_dealer(raw_d_name)
                if d_name not in dealer_targets:
                    dealer_targets[d_name] = {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys}
                for wk, cols in week_cols.items():
                    dealer_targets[d_name][wk]['amt'] += (clean_val(safe_get(row, cols['amt'])) / 1000.0) 
                    dealer_targets[d_name][wk]['est'] += clean_val(safe_get(row, cols['est']))
                    dealer_targets[d_name][wk]['cnt'] += clean_val(safe_get(row, cols['cnt']))

        raw_daily_sheets = [ws for ws in safe_api_call(sh.worksheets) if "/" in ws.title or "일" in ws.title]
        def sort_key(ws):
            try:
                nums = re.findall(r'\d+', ws.title)
                if len(nums) >= 2: return int(nums[0]) * 100 + int(nums[1])
            except: pass
            return 0
        daily_sheets = sorted(raw_daily_sheets, key=sort_key)
        
        valid_daily_sheets = [] 
        all_sheet_ids = {} 
        for ws in daily_sheets:
            nums = re.findall(r'\d+', ws.title)
            if len(nums) >= 2:
                m_val, d_val = int(nums[0]), int(nums[1])
                wk_name = date_to_target_week.get((m_val, d_val))
                tr_idx = get_trend_week_idx(m_val, d_val)
                mo_idx = month_list.index(m_val) if m_val in month_list else -1
                
                if wk_name or tr_idx != -1 or mo_idx != -1:
                    all_sheet_ids[ws.id] = (m_val, d_val, wk_name, tr_idx, mo_idx, ws)
                if wk_name:
                    valid_daily_sheets.append((m_val, wk_name, ws))

        status_box.info(f"📉 3단계: 일보 실적(계약액 K+N / 매출 S 누적) 스캔 중...")
        sheet_data_cache = {}
        for ws_id, info in all_sheet_ids.items():
            time.sleep(1.2) 
            sheet_data_cache[ws_id] = safe_api_call(info[-1].get_all_values)
        
        existing_hcs = [clean_str(h) for d, h, t in hc_info_raw]
        valid_dealers = list(set([d for d, _, _ in hc_info_raw]))
        
        acts = {clean_str(hc): {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for _, hc, _ in hc_info_raw}
        month_acts = {clean_str(hc): {'amt': 0, 'est': 0, 'cnt': 0} for _, hc, _ in hc_info_raw}
        hc_to_dealer = {clean_str(hc): dealer for dealer, hc, _ in hc_info_raw}
        
        real_dealer_monthly = {d: {'amt': 0, 'est': 0, 'cnt': 0} for d in valid_dealers}
        real_dealer_weekly = {d: {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for d in valid_dealers}
        
        trend_hc_w = {clean_str(hc): [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(8)] for _, hc, _ in hc_info_raw}
        trend_dealer_w = {d: [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(8)] for d in valid_dealers}
        trend_total_w = [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(8)]
        
        trend_hc_m = {clean_str(hc): [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(4)] for _, hc, _ in hc_info_raw}
        trend_dealer_m = {d: [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(4)] for d in valid_dealers}
        trend_total_m = [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(4)]

        for ws_id, info in all_sheet_ids.items():
            m_val, d_val, wk_info, tr_idx, mo_idx, ws = info
            d_data = sheet_data_cache[ws_id] 
            
            is_weekend = False
            try:
                sheet_date = datetime(current_date.year, m_val, d_val)
                is_weekend = sheet_date.weekday() >= 5 
            except: pass

            # 🚀 1. 기본 테이블 스캔 (행 1 ~ 34)
            for r_idx, row in enumerate(d_data):
                if r_idx >= 34: break 
                if len(row) > 3: 
                    temp_est = clean_val(safe_get(row, 4))
                    temp_cnt = clean_val(safe_get(row, 5))
                    
                    # 🚀 계약액 = K열(10) + N열(13) 반영! (마이너스도 clean_val에서 인식)
                    amt_k = clean_val(safe_get(row, 10))
                    amt_n = clean_val(safe_get(row, 13))
                    temp_amt = (amt_k + amt_n) / 1000.0       
                    
                    # 🚀 매출은 누적이므로 S열(18), Y열(24)에서 덮어쓰기 방식으로 저장할 준비
                    temp_sales = clean_val(safe_get(row, 18)) / 1000.0     
                    temp_next_sales = clean_val(safe_get(row, 24)) / 1000.0
                    
                    hc_name = clean_str(safe_get(row, 3)) 
                    if not hc_name and len(row) > 1: hc_name = clean_str(safe_get(row, 1)) 
                    if any(x in hc_name for x in ['합계', '소계', '총계', '목표', '대리점', '사번', '비고']): continue
                    if not hc_name: continue 
                        
                    matched_dealer = hc_to_dealer_master.get(hc_name)
                    if not matched_dealer:
                        row_header_str = clean_str("".join([safe_get(row, i) for i in range(4)]))
                        matched_dealer = get_mapped_dealer(row_header_str)
                        if not matched_dealer or matched_dealer not in valid_dealers: matched_dealer = "기타"
                        
                    if hc_name not in existing_hcs:
                        hc_info_raw.append((matched_dealer, hc_name, 0.0))
                        existing_hcs.append(hc_name)
                        acts[hc_name] = {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys}
                        month_acts[hc_name] = {'amt': 0, 'est': 0, 'cnt': 0}
                        hc_to_dealer[hc_name] = matched_dealer
                        trend_hc_w[hc_name] = [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(8)]
                        trend_hc_m[hc_name] = [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(4)]
                        if matched_dealer not in valid_dealers:
                            valid_dealers.append(matched_dealer)
                            real_dealer_monthly[matched_dealer] = {'amt': 0, 'est': 0, 'cnt': 0}
                            real_dealer_weekly[matched_dealer] = {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys}
                            trend_dealer_w[matched_dealer] = [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(8)]
                            trend_dealer_m[matched_dealer] = [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(4)]

                    # 🚀 누적(Delta) 합산: 계약액, 견적건, 계약건 (VDT 테이블용)
                    if wk_info:
                        acts[hc_name][wk_info]['est'] += temp_est
                        acts[hc_name][wk_info]['cnt'] += temp_cnt
                        acts[hc_name][wk_info]['amt'] += temp_amt
                        if m_val == current_month:
                            month_acts[hc_name]['est'] += temp_est
                            month_acts[hc_name]['cnt'] += temp_cnt
                            month_acts[hc_name]['amt'] += temp_amt
                                
                        if matched_dealer in valid_dealers:
                            if wk_info in real_dealer_weekly[matched_dealer]:
                                real_dealer_weekly[matched_dealer][wk_info]['est'] += temp_est
                                real_dealer_weekly[matched_dealer][wk_info]['cnt'] += temp_cnt
                                real_dealer_weekly[matched_dealer][wk_info]['amt'] += temp_amt
                            if m_val == current_month:
                                real_dealer_monthly[matched_dealer]['est'] += temp_est
                                real_dealer_monthly[matched_dealer]['cnt'] += temp_cnt
                                real_dealer_monthly[matched_dealer]['amt'] += temp_amt

                    # 🚀 주간 8주 트렌드 데이터 적재
                    if tr_idx != -1:
                        trend_hc_w[hc_name][tr_idx]['est'] += temp_est
                        trend_hc_w[hc_name][tr_idx]['cnt'] += temp_cnt
                        trend_hc_w[hc_name][tr_idx]['amt'] += temp_amt
                        # 매출, 이월매출은 해당 주간의 가장 마지막 날(Sheet) 값으로 덮어쓰기 (누적이므로)
                        trend_hc_w[hc_name][tr_idx]['sales'] = temp_sales
                        trend_hc_w[hc_name][tr_idx]['next_sales'] = temp_next_sales
                        
                        if is_weekend: trend_hc_w[hc_name][tr_idx]['amt_we'] += temp_amt
                        else: trend_hc_w[hc_name][tr_idx]['amt_wd'] += temp_amt
                            
                    # 🚀 월간 누적 트렌드 데이터 적재
                    if mo_idx != -1:
                        trend_hc_m[hc_name][mo_idx]['est'] += temp_est
                        trend_hc_m[hc_name][mo_idx]['cnt'] += temp_cnt
                        trend_hc_m[hc_name][mo_idx]['amt'] += temp_amt
                        # 매출, 이월매출 덮어쓰기 (월간 누적)
                        trend_hc_m[hc_name][mo_idx]['sales'] = temp_sales
                        trend_hc_m[hc_name][mo_idx]['next_sales'] = temp_next_sales
                        
                        if is_weekend: trend_hc_m[hc_name][mo_idx]['amt_we'] += temp_amt
                        else: trend_hc_m[hc_name][mo_idx]['amt_wd'] += temp_amt
                            
            # 🚀 2. 입주 일보 스캔 (행 35 ~ 60) -> M열 + R열 합산 (음수 자동 감산)
            if len(d_data) > 34:
                for r_idx, row in enumerate(d_data[34:]):
                    if len(row) > 17:
                        hc_name = clean_str(safe_get(row, 1)) 
                        if not hc_name: hc_name = clean_str(safe_get(row, 3))
                        if not hc_name or any(x in hc_name for x in ['합계', '소계', '총계', '목표', '대리점']): continue
                        
                        move_amt_m = clean_val(safe_get(row, 12)) / 1000.0 
                        move_amt_r = clean_val(safe_get(row, 17)) / 1000.0 
                        daily_move_amt = move_amt_m + move_amt_r
                        
                        matched_dealer = hc_to_dealer_master.get(hc_name)
                        if not matched_dealer or matched_dealer not in valid_dealers: continue
                        
                        if tr_idx != -1:
                            trend_hc_w[hc_name][tr_idx]['amt_move'] += daily_move_amt
                        if mo_idx != -1:
                            trend_hc_m[hc_name][mo_idx]['amt_move'] += daily_move_amt

        # 🚀 후처리: 개인(HC) 단위로 덮어쓰기 된 매출 데이터를 대리점/전체(Total)로 합산해주는 로직
        for hc_name in existing_hcs:
            matched_dealer = hc_to_dealer_master.get(hc_name, "기타")
            if matched_dealer in valid_dealers:
                for i in range(8):
                    # 주간 상위 롤업
                    trend_dealer_w[matched_dealer][i]['sales'] += trend_hc_w[hc_name][i]['sales']
                    trend_dealer_w[matched_dealer][i]['next_sales'] += trend_hc_w[hc_name][i]['next_sales']
                    trend_total_w[i]['sales'] += trend_hc_w[hc_name][i]['sales']
                    trend_total_w[i]['next_sales'] += trend_hc_w[hc_name][i]['next_sales']
                    
                    # 주중/주말 및 입주/계약건 등 누적 지표들도 여기서 안전하게 합산
                    trend_dealer_w[matched_dealer][i]['est'] += trend_hc_w[hc_name][i]['est']
                    trend_dealer_w[matched_dealer][i]['cnt'] += trend_hc_w[hc_name][i]['cnt']
                    trend_dealer_w[matched_dealer][i]['amt'] += trend_hc_w[hc_name][i]['amt']
                    trend_dealer_w[matched_dealer][i]['amt_we'] += trend_hc_w[hc_name][i]['amt_we']
                    trend_dealer_w[matched_dealer][i]['amt_wd'] += trend_hc_w[hc_name][i]['amt_wd']
                    trend_dealer_w[matched_dealer][i]['amt_move'] += trend_hc_w[hc_name][i]['amt_move']
                    
                    trend_total_w[i]['est'] += trend_hc_w[hc_name][i]['est']
                    trend_total_w[i]['cnt'] += trend_hc_w[hc_name][i]['cnt']
                    trend_total_w[i]['amt'] += trend_hc_w[hc_name][i]['amt']
                    trend_total_w[i]['amt_we'] += trend_hc_w[hc_name][i]['amt_we']
                    trend_total_w[i]['amt_wd'] += trend_hc_w[hc_name][i]['amt_wd']
                    trend_total_w[i]['amt_move'] += trend_hc_w[hc_name][i]['amt_move']
                    
                for i in range(4):
                    # 월간 상위 롤업
                    trend_dealer_m[matched_dealer][i]['sales'] += trend_hc_m[hc_name][i]['sales']
                    trend_dealer_m[matched_dealer][i]['next_sales'] += trend_hc_m[hc_name][i]['next_sales']
                    trend_total_m[i]['sales'] += trend_hc_m[hc_name][i]['sales']
                    trend_total_m[i]['next_sales'] += trend_hc_m[hc_name][i]['next_sales']
                    
                    trend_dealer_m[matched_dealer][i]['est'] += trend_hc_m[hc_name][i]['est']
                    trend_dealer_m[matched_dealer][i]['cnt'] += trend_hc_m[hc_name][i]['cnt']
                    trend_dealer_m[matched_dealer][i]['amt'] += trend_hc_m[hc_name][i]['amt']
                    trend_dealer_m[matched_dealer][i]['amt_we'] += trend_hc_m[hc_name][i]['amt_we']
                    trend_dealer_m[matched_dealer][i]['amt_wd'] += trend_hc_m[hc_name][i]['amt_wd']
                    trend_dealer_m[matched_dealer][i]['amt_move'] += trend_hc_m[hc_name][i]['amt_move']
                    
                    trend_total_m[i]['est'] += trend_hc_m[hc_name][i]['est']
                    trend_total_m[i]['cnt'] += trend_hc_m[hc_name][i]['cnt']
                    trend_total_m[i]['amt'] += trend_hc_m[hc_name][i]['amt']
                    trend_total_m[i]['amt_we'] += trend_hc_m[hc_name][i]['amt_we']
                    trend_total_m[i]['amt_wd'] += trend_hc_m[hc_name][i]['amt_wd']
                    trend_total_m[i]['amt_move'] += trend_hc_m[hc_name][i]['amt_move']

        status_box.info("🎯 4단계: 실적 데이터 기반 목표 배분 중...")
        
        dealer_active_hcs = {}
        for dealer, hc, _ in hc_info_raw:
            if dealer not in dealer_active_hcs: dealer_active_hcs[dealer] = []
            hc_clean = clean_str(hc)
            if hc_clean not in EXCLUDED_HCS:
                dealer_active_hcs[dealer].append(hc_clean)
                
        dealer_sales_sum_active = {}
        for dealer, hc, tgt in hc_info_raw:
            hc_clean = clean_str(hc)
            active_list = dealer_active_hcs.get(dealer, [])
            if active_list and hc_clean in active_list:
                dealer_sales_sum_active[dealer] = dealer_sales_sum_active.get(dealer, 0.0) + tgt
            elif not active_list:
                dealer_sales_sum_active[dealer] = dealer_sales_sum_active.get(dealer, 0.0) + tgt

        final_hc_sales_tgt = {}
        hc_weights = {}
        
        for dealer, hc, tgt in hc_info_raw:
            hc_clean = clean_str(hc)
            active_list = dealer_active_hcs.get(dealer, [])
            if hc_clean in EXCLUDED_HCS:
                final_hc_sales_tgt[hc_clean] = 0.0
                hc_weights[hc_clean] = 0.0
            else:
                d_sum_active = dealer_sales_sum_active.get(dealer, 0.0)
                original_dealer_sum = dealer_sales_sum.get(dealer, 0.0)
                weight = (tgt / d_sum_active) if d_sum_active > 0 else 0.0
                final_hc_sales_tgt[hc_clean] = original_dealer_sum * weight
                hc_weights[hc_clean] = weight 

        targets = {}
        for dealer, hc, _ in hc_info_raw:
            hc_clean = clean_str(hc)
            targets[hc_clean] = {}
            weight = hc_weights.get(hc_clean, 0.0)
            d_t = dealer_targets.get(dealer, {})
            for wk in week_keys:
                targets[hc_clean][wk] = {
                    'amt': d_t.get(wk, {}).get('amt', 0) * weight,
                    'est': d_t.get(wk, {}).get('est', 0) * weight,
                    'cnt': d_t.get(wk, {}).get('cnt', 0) * weight,
                }

        # 🚀 당월 매출액 최신 누적치 추출 (VDT 테이블용)
        latest_sales_dict = {}
        if valid_daily_sheets:
            latest_m, latest_wk, latest_sheet = valid_daily_sheets[-1]
            l_data = sheet_data_cache[latest_sheet.id]
            for row in l_data[:34]:
                if len(row) > 3:
                    hc_name_s = clean_str(safe_get(row, 3)) 
                    if not hc_name_s and len(row) > 1: hc_name_s = clean_str(safe_get(row, 1))
                    temp_s = (clean_val(safe_get(row, 18)) / 1000.0) # S열(18) 천원 단위 처리
                    if hc_name_s:
                        latest_sales_dict[hc_name_s] = temp_s

        status_box.info("✅ 데이터 구성 완료! UI 출력 중...")
        
        col_tuples = [
            ('기본정보', '대리점', '대리점'), ('기본정보', 'HC명', 'HC명'),
            ('🎯 당월매출', '인별매출(천)', '목표'), ('🎯 당월매출', '인별매출(천)', 'ACT'), ('🎯 당월매출', '인별매출(천)', '달성율(%)'),
            ('🌟 당월 합계', '계약액(천)', '목표'), ('🌟 당월 합계', '계약액(천)', 'ACT'), ('🌟 당월 합계', '계약액(천)', '달성율(%)'),
            ('🌟 당월 합계', '견적건', '목표'), ('🌟 당월 합계', '견적건', 'ACT'), ('🌟 당월 합계', '견적건', '달성율(%)'),
            ('🌟 당월 합계', '계약건', '목표'), ('🌟 당월 합계', '계약건', 'ACT'), ('🌟 당월 합계', '계약건', '달성율(%)')
        ]
        
        for wk in week_keys:
            wk_label = f"{wk} ({date_headers.get(wk, '')})"
            col_tuples.extend([(wk_label, '계약액(천)', '목표'), (wk_label, '계약액(천)', 'ACT'), (wk_label, '계약액(천)', '달성율(%)')])
            col_tuples.extend([(wk_label, '견적건', '목표'), (wk_label, '견적건', 'ACT'), (wk_label, '견적건', '달성율(%)')])
            col_tuples.extend([(wk_label, '계약건', '목표'), (wk_label, '계약건', 'ACT'), (wk_label, '계약건', '달성율(%)')])
            
        columns = pd.MultiIndex.from_tuples(col_tuples, names=['주차', '항목', '구분'])
        rows = []
        for dealer, hc, raw_sales_tgt in hc_info_raw:
            hc_clean = clean_str(hc)
            if hc_clean in EXCLUDED_HCS: continue
            
            sales_tgt = final_hc_sales_tgt.get(hc_clean, 0.0) 
            m_act = month_acts.get(hc_clean, {'amt': 0, 'est': 0, 'cnt': 0})
            s_act = latest_sales_dict.get(hc_clean, 0.0)

            if sales_tgt == 0.0 and m_act['amt'] == 0 and m_act['est'] == 0 and m_act['cnt'] == 0 and s_act == 0: continue

            row_data = [dealer, hc]
            row_data.extend([sales_tgt, s_act, 0.0])
            
            m_tgt_amt = sum([targets.get(hc_clean, {}).get(wk, {}).get('amt', 0) for wk in week_keys])
            m_tgt_est = sum([targets.get(hc_clean, {}).get(wk, {}).get('est', 0) for wk in week_keys])
            m_tgt_cnt = sum([targets.get(hc_clean, {}).get(wk, {}).get('cnt', 0) for wk in week_keys])
            
            row_data.extend([m_tgt_amt, m_act['amt'], 0.0, m_tgt_est, m_act['est'], 0.0, m_tgt_cnt, m_act['cnt'], 0.0])
            
            for wk in week_keys:
                t = targets.get(hc_clean, {}).get(wk, {'amt': 0, 'est': 0, 'cnt': 0})
                a = acts.get(hc_clean, {}).get(wk, {'amt': 0, 'est': 0, 'cnt': 0})
                row_data.extend([t['amt'], a['amt'], 0.0, t['est'], a['est'], 0.0, t['cnt'], a['cnt'], 0.0])
                
            rows.append(row_data)

        df = pd.DataFrame(rows, columns=columns)
        for col in df.columns[2:]:
            if col[2] == '달성율(%)':
                tgt_col, act_col = (col[0], col[1], '목표'), (col[0], col[1], 'ACT')
                df[col] = np.where(df[tgt_col] > 0, (df[act_col] / df[tgt_col] * 100).round(0), 0)
        
        # 상권 통합 (주간/월간 트렌드)
        trend_region_w = {"충청상권": [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(8)],
                             "호남상권": [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(8)]}
        trend_region_m = {"충청상권": [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(4)],
                             "호남상권": [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(4)]}
        
        for region, dealers in REGION_MAP.items():
            for d in dealers:
                dw_data = trend_dealer_w.get(d, [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(8)])
                dm_data = trend_dealer_m.get(d, [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(4)])
                for i in range(8):
                    trend_region_w[region][i]['amt'] += dw_data[i]['amt']
                    trend_region_w[region][i]['est'] += dw_data[i]['est']
                    trend_region_w[region][i]['cnt'] += dw_data[i]['cnt']
                    trend_region_w[region][i]['amt_wd'] += dw_data[i]['amt_wd']
                    trend_region_w[region][i]['amt_we'] += dw_data[i]['amt_we']
                    trend_region_w[region][i]['sales'] += dw_data[i]['sales']
                    trend_region_w[region][i]['next_sales'] += dw_data[i]['next_sales']
                    trend_region_w[region][i]['amt_move'] += dw_data[i]['amt_move']
                for i in range(4):
                    trend_region_m[region][i]['amt'] += dm_data[i]['amt']
                    trend_region_m[region][i]['est'] += dm_data[i]['est']
                    trend_region_m[region][i]['cnt'] += dm_data[i]['cnt']
                    trend_region_m[region][i]['amt_wd'] += dm_data[i]['amt_wd']
                    trend_region_m[region][i]['amt_we'] += dm_data[i]['amt_we']
                    trend_region_m[region][i]['sales'] += dm_data[i]['sales']
                    trend_region_m[region][i]['next_sales'] += dm_data[i]['next_sales']
                    trend_region_m[region][i]['amt_move'] += dm_data[i]['amt_move']

        now_m, now_d = current_date.month, current_date.day
        CURRENT_TABLE_WEEK = date_to_target_week.get((now_m, now_d))
        if not CURRENT_TABLE_WEEK: CURRENT_TABLE_WEEK = week_keys[-1] if week_keys else '1주차'
        
        trend_pack = {
            'W': {'hc': trend_hc_w, 'dlr': trend_dealer_w, 'tot': trend_total_w, 'reg': trend_region_w},
            'M': {'hc': trend_hc_m, 'dlr': trend_dealer_m, 'tot': trend_total_m, 'reg': trend_region_m}
        }

        status_box.empty()
        return df, date_headers, hc_to_dealer_master, real_dealer_monthly, real_dealer_weekly, week_keys, trend_pack, CURRENT_TABLE_WEEK

    except Exception as e:
        status_box.empty()
        st.error("🚨 데이터 구성 중 에러가 발생했습니다!")
        with st.expander("🛠️ 상세 에러 보기"): st.code(traceback.format_exc())
        return pd.DataFrame(), {}, {}, {}, {}, [], {}, ""

def calculate_subtotals(df, hc_to_dealer_master, real_dealer_monthly, real_dealer_weekly):
    if df.empty: return df
    
    result_rows = []
    dealer_col, hc_col = ('기본정보', '대리점', '대리점'), ('기본정보', 'HC명', 'HC명')
    
    for dealer, group in df.groupby(dealer_col, sort=False):
        for _, row in group.iterrows(): result_rows.append(row)
            
        subtotal = group.select_dtypes(include=[np.number]).sum()
        subtotal[dealer_col], subtotal[hc_col] = dealer, "합계"
        
        if dealer in real_dealer_monthly:
            subtotal[('🌟 당월 합계', '계약액(천)', 'ACT')] = real_dealer_monthly[dealer]['amt']
            subtotal[('🌟 당월 합계', '견적건', 'ACT')] = real_dealer_monthly[dealer]['est']
            subtotal[('🌟 당월 합계', '계약건', 'ACT')] = real_dealer_monthly[dealer]['cnt']
            
        if dealer in real_dealer_weekly:
            for wk, wk_data in real_dealer_weekly[dealer].items():
                wk_cols = [c[0] for c in df.columns if wk in c[0]]
                if wk_cols:
                    w_c = wk_cols[0]
                    subtotal[(w_c, '계약액(천)', 'ACT')] = wk_data['amt']
                    subtotal[(w_c, '견적건', 'ACT')] = wk_data['est']
                    subtotal[(w_c, '계약건', 'ACT')] = wk_data['cnt']
        
        for col in df.columns[2:]:
            if col[2] == '달성율(%)':
                tgt_col, act_col = (col[0], col[1], '목표'), (col[0], col[1], 'ACT')
                subtotal[col] = round((subtotal[act_col] / subtotal[tgt_col] * 100), 0) if subtotal[tgt_col] > 0 else 0.0
        result_rows.append(pd.Series(subtotal))

    grand_total = df.select_dtypes(include=[np.number]).sum()
    grand_total[dealer_col], grand_total[hc_col] = "🌟 총계", "🌟 총계"
    
    grand_total[('🌟 당월 합계', '계약액(천)', 'ACT')] = sum([real_dealer_monthly.get(d, {}).get('amt', 0) for d in df[dealer_col].unique()])
    grand_total[('🌟 당월 합계', '견적건', 'ACT')] = sum([real_dealer_monthly.get(d, {}).get('est', 0) for d in df[dealer_col].unique()])
    grand_total[('🌟 당월 합계', '계약건', 'ACT')] = sum([real_dealer_monthly.get(d, {}).get('cnt', 0) for d in df[dealer_col].unique()])
    
    some_dealer = df[dealer_col].unique()[0] if not df.empty else None
    if some_dealer and some_dealer in real_dealer_weekly:
        for wk in real_dealer_weekly[some_dealer].keys():
            wk_cols = [c[0] for c in df.columns if wk in c[0]]
            if wk_cols:
                w_c = wk_cols[0]
                grand_total[(w_c, '계약액(천)', 'ACT')] = sum([real_dealer_weekly.get(d, {}).get(wk, {}).get('amt', 0) for d in df[dealer_col].unique()])
                grand_total[(w_c, '견적건', 'ACT')] = sum([real_dealer_weekly.get(d, {}).get(wk, {}).get('est', 0) for d in df[dealer_col].unique()])
                grand_total[(w_c, '계약건', 'ACT')] = sum([real_dealer_weekly.get(d, {}).get(wk, {}).get('cnt', 0) for d in df[dealer_col].unique()])

    for col in df.columns[2:]:
        if col[2] == '달성율(%)':
            tgt_col, act_col = (col[0], col[1], '목표'), (col[0], col[1], 'ACT')
            grand_total[col] = round((grand_total[act_col] / grand_total[tgt_col] * 100), 0) if grand_total[tgt_col] > 0 else 0.0
    result_rows.append(pd.Series(grand_total))
    
    return pd.DataFrame(result_rows)

df_raw, date_headers, hc_to_dealer_master, real_dealer_monthly, real_dealer_weekly, week_keys_list, trend_pack, CURRENT_TABLE_WEEK = load_vdt_data()

if not df_raw.empty:
    final_df = calculate_subtotals(df_raw, hc_to_dealer_master, real_dealer_monthly, real_dealer_weekly)
    
    def set_view(target):
        st.session_state['view_target'] = target
        st.session_state['hc_selector'] = "✨ 인원별 상세 실적 (선택 시 우선 적용)"

    def on_hc_select():
        if st.session_state['hc_selector'] != "✨ 인원별 상세 실적 (선택 시 우선 적용)":
            st.session_state['view_target'] = st.session_state['hc_selector']

    def btn_type(target):
        return "primary" if st.session_state.get('view_target') == target else "secondary"
        
    vt = st.session_state['view_target']
    
    if vt == "충청호남팀 전체":
        chart_title = "충청호남팀 전체"
        sub_units = [("충청호남팀 통합", trend_pack['W']['tot'])]
    elif vt in ["충청팀 통합", "호남팀 통합"]:
        region_key = "충청상권" if vt == "충청팀 통합" else "호남상권"
        chart_title = f"{vt}"
        sub_units = [(f"{vt}", trend_pack['W']['reg'][region_key])]
    elif "대리점" in vt: 
        target_dealer = vt.replace(" 대리점", "")
        chart_title = f"{target_dealer} 대리점"
        sub_units = [(f"{target_dealer} 합계", trend_pack['W']['dlr'].get(target_dealer, [{'amt':0, 'est':0, 'cnt':0, 'sales':0, 'amt_move':0} for _ in range(8)]))]
    else: 
        parts = vt.replace("👤 ", "").split(" - ")
        target_hc = parts[1]
        chart_title = f"{target_hc} 님"
        sub_units = [(target_hc, trend_pack['W']['hc'].get(target_hc, [{'amt':0, 'est':0, 'cnt':0, 'sales':0, 'amt_move':0} for _ in range(8)]))]

    # 🚀 1. 주간 회의 전용 브리핑 보드 (최상단 배치)
    st.markdown("#### 💡 주간 회의 전용 브리핑 보드 (전주 대비 증감 분석)")
    
    wow_week_list = list(reversed(trend_labels))
    if st.session_state['wow_week'] not in wow_week_list:
        st.session_state['wow_week'] = wow_week_list[0]
        
    wow_col1, wow_col2 = st.columns([3, 7])
    with wow_col1:
        selected_wow_week = st.selectbox("👉 회의 기준 주차(Target) 선택", options=wow_week_list, key="wow_week")
        
    tgt_idx = trend_labels.index(selected_wow_week)
    
    if tgt_idx == 0:
        st.warning("선택하신 주차는 가장 과거 데이터이므로 전주(Previous)와 비교할 수 없습니다. 다른 주차를 선택해주세요.")
    else:
        prev_idx = tgt_idx - 1
        
        def render_wow_cell(prv_v, tgt_v, is_pct=False, is_unit=False):
            delta = tgt_v - prv_v
            if delta > 0: 
                v_str = f"+{int(delta):,}만" if is_unit else (f"+{delta:.1f}%" if is_pct else f"+{delta:,.0f}")
                return f"<span class='wow-up'>{v_str} 🔺</span>"
            elif delta < 0:
                v_str = f"{int(delta):,}만" if is_unit else (f"{delta:.1f}%" if is_pct else f"{delta:,.0f}")
                return f"<span class='wow-down'>{v_str} 🔻</span>"
            else:
                return "<span class='wow-same'>-</span>"

        unit_name, unit_data = sub_units[0]
        p_data = unit_data[prev_idx]
        t_data = unit_data[tgt_idx]
        
        p_amt, t_amt = p_data.get('amt',0), t_data.get('amt',0)
        p_sales, t_sales = p_data.get('sales',0), t_data.get('sales',0)
        p_est, t_est = p_data.get('est',0), t_data.get('est',0)
        p_cnt, t_cnt = p_data.get('cnt',0), t_data.get('cnt',0)
        
        p_move, t_move = p_data.get('amt_move',0), t_data.get('amt_move',0)
        p_walk, t_walk = p_amt - p_move, t_amt - t_move
        
        p_rate = (p_cnt / p_est * 100) if p_est > 0 else 0
        t_rate = (t_cnt / t_est * 100) if t_est > 0 else 0
        
        p_unit = (p_amt / (p_cnt * 10)) if p_cnt > 0 else 0
        t_unit = (t_amt / (t_cnt * 10)) if t_cnt > 0 else 0

        # 🚀 X축 지표, Y축 주차로 컴팩트하게 재배치된 HTML 브리핑 표 (오류 원천 차단)
        html_wow_list = [
            '<table class="wow-table" style="width: 100%; border: 2px solid #94a3b8; border-radius: 8px; overflow: hidden;">',
            '<thead>',
            '<tr style="background-color: #1e293b; color: white;">',
            f'<th style="padding: 10px; font-size: 13px; border-right: 2px solid #94a3b8;">주차 구분<br><span style="font-size:11px; color:#cbd5e1;">({chart_title})</span></th>',
            '<th style="padding: 10px;">💰 총 계약액<br>(천원)</th>',
            '<th style="padding: 10px;">💰 총 매출액<br>(천원)</th>',
            '<th style="padding: 10px;">📝 견적건<br>(건)</th>',
            '<th style="padding: 10px;">🤝 계약건<br>(건)</th>',
            '<th style="padding: 10px; background-color:#334155;">🚶 워크인 계약액<br>(천원)</th>',
            '<th style="padding: 10px; background-color:#334155;">🏠 입주 계약액<br>(천원)</th>',
            '<th style="padding: 10px;">📊 계약률<br>(%)</th>',
            '<th style="padding: 10px;">💸 객단가<br>(만원)</th>',
            '</tr>',
            '</thead>',
            '<tbody>',
            '<tr style="background-color: #f8fafc;">',
            f'<td style="text-align: center; font-weight: 900; border-right: 2px solid #94a3b8;">{trend_labels[prev_idx]} (전주)</td>',
            f'<td style="text-align: center; font-weight: 600;">{p_amt:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 600;">{p_sales:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 600;">{p_est:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 600;">{p_cnt:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 600; background-color:#f1f5f9;">{p_walk:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 600; background-color:#f1f5f9;">{p_move:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 600;">{p_rate:.1f}%</td>',
            f'<td style="text-align: center; font-weight: 600;">{int(p_unit):,}</td>',
            '</tr>',
            '<tr style="background-color: white;">',
            f'<td style="text-align: center; font-weight: 900; color: #1e3a8a; border-right: 2px solid #94a3b8;">{trend_labels[tgt_idx]} (당주)</td>',
            f'<td style="text-align: center; font-weight: 900; color: #1e3a8a;">{t_amt:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 900; color: #1e3a8a;">{t_sales:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 900; color: #1e3a8a;">{t_est:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 900; color: #1e3a8a;">{t_cnt:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 900; color: #1e3a8a; background-color:#f1f5f9;">{t_walk:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 900; color: #1e3a8a; background-color:#f1f5f9;">{t_move:,.0f}</td>',
            f'<td style="text-align: center; font-weight: 900; color: #1e3a8a;">{t_rate:.1f}%</td>',
            f'<td style="text-align: center; font-weight: 900; color: #1e3a8a;">{int(t_unit):,}</td>',
            '</tr>',
            '<tr style="background-color: #fef2f2;">',
            '<td style="text-align: center; font-weight: 900; color: #b91c1c; border-right: 2px solid #94a3b8;">전주 대비 증감</td>',
            f'<td style="text-align: center;">{render_wow_cell(p_amt, t_amt)}</td>',
            f'<td style="text-align: center;">{render_wow_cell(p_sales, t_sales)}</td>',
            f'<td style="text-align: center;">{render_wow_cell(p_est, t_est)}</td>',
            f'<td style="text-align: center;">{render_wow_cell(p_cnt, t_cnt)}</td>',
            f'<td style="text-align: center; background-color:#fee2e2;">{render_wow_cell(p_walk, t_walk)}</td>',
            f'<td style="text-align: center; background-color:#fee2e2;">{render_wow_cell(p_move, t_move)}</td>',
            f'<td style="text-align: center;">{render_wow_cell(p_rate, t_rate, is_pct=True)}</td>',
            f'<td style="text-align: center;">{render_wow_cell(p_unit, t_unit, is_unit=True)}</td>',
            '</tr>',
            '</tbody>',
            '</table>'
        ]
        
        st.markdown("".join(html_wow_list), unsafe_allow_html=True)
        
    st.markdown("---")

    # 🚀 2. 조직 및 인원 선택 버튼 (2번째 위치로 이동)
    st.markdown("#### 🔎 **실적 조회 (조직 및 인원 선택)**")
    st.markdown('<div id="org-buttons"></div>', unsafe_allow_html=True)
    c_org = st.columns([12, 2, 12, 9, 9, 9, 9, 2, 12, 9, 9, 9, 30])
    
    with c_org[0]: st.button("I 전체통합" if st.session_state['view_target'] != "충청호남팀 전체" else "✅ 전체통합", type=btn_type("충청호남팀 전체"), on_click=set_view, args=("충청호남팀 전체",), use_container_width=True)
    with c_org[1]: st.markdown("<div style='text-align:center; padding-top:5px; color:#cbd5e1; font-weight:bold; font-size:16px;'>|</div>", unsafe_allow_html=True)
    with c_org[2]: st.button("I 충청통합" if st.session_state['view_target'] != "충청팀 통합" else "✅ 충청통합", type=btn_type("충청팀 통합"), on_click=set_view, args=("충청팀 통합",), use_container_width=True)
    with c_org[3]: st.button("둔산" if st.session_state['view_target'] != "둔산 대리점" else "✅ 둔산", type=btn_type("둔산 대리점"), on_click=set_view, args=("둔산 대리점",), use_container_width=True)
    with c_org[4]: st.button("세종" if st.session_state['view_target'] != "세종 대리점" else "✅ 세종", type=btn_type("세종 대리점"), on_click=set_view, args=("세종 대리점",), use_container_width=True)
    with c_org[5]: st.button("목포" if st.session_state['view_target'] != "목포 대리점" else "✅ 목포", type=btn_type("목포 대리점"), on_click=set_view, args=("목포 대리점",), use_container_width=True)
    with c_org[6]: st.button("충주" if st.session_state['view_target'] != "충주 대리점" else "✅ 충주", type=btn_type("충주 대리점"), on_click=set_view, args=("충주 대리점",), use_container_width=True)
    with c_org[7]: st.markdown("<div style='text-align:center; padding-top:5px; color:#cbd5e1; font-weight:bold; font-size:16px;'>|</div>", unsafe_allow_html=True)
    with c_org[8]: st.button("I 호남통합" if st.session_state['view_target'] != "호남팀 통합" else "✅ 호남통합", type=btn_type("호남팀 통합"), on_click=set_view, args=("호남팀 통합",), use_container_width=True)
    with c_org[9]: st.button("광양" if st.session_state['view_target'] != "광양 대리점" else "✅ 광양", type=btn_type("광양 대리점"), on_click=set_view, args=("광양 대리점",), use_container_width=True)
    with c_org[10]: st.button("익산" if st.session_state['view_target'] != "익산 대리점" else "✅ 익산", type=btn_type("익산 대리점"), on_click=set_view, args=("익산 대리점",), use_container_width=True)
    with c_org[11]: st.button("여수" if st.session_state['view_target'] != "여수 대리점" else "✅ 여수", type=btn_type("여수 대리점"), on_click=set_view, args=("여수 대리점",), use_container_width=True)
    
    with c_org[12]:
        hc_list = ["✨ 인원별 상세 실적 (선택 시 우선 적용)"]
        for r_idx in range(len(final_df)):
            dealer = final_df.iloc[r_idx][('기본정보', '대리점', '대리점')]
            hc = final_df.iloc[r_idx][('기본정보', 'HC명', 'HC명')]
            if hc not in ["🌟 총계", "합계", "상권합계"] and hc not in EXCLUDED_HCS: hc_list.append(f"👤 {dealer} - {hc}")
            
        st.selectbox("인원선택", options=hc_list, key='hc_selector', on_change=on_hc_select, label_visibility="collapsed")

    st.markdown("---")
            
    def toggle_state(key):
        st.session_state[key] = not st.session_state[key]

    # 🚀 3. 8주 추이 및 월간 누적 트렌드 그래프
    
    t_c1, t_c2 = st.columns([7, 3])
    with t_c1: st.markdown(f"#### 📈 {chart_title} 실적 추이 그래프")
    with t_c2:
        st.markdown("<div class='mode-toggle'>", unsafe_allow_html=True)
        view_mode = st.radio("보기 기준", ["주간 추이 (최근 8주)", "월간 누적 추이 (8~11월)"], horizontal=True, label_visibility="collapsed", key='view_mode_selector')
        st.markdown("</div>", unsafe_allow_html=True)
        
    is_monthly = "월간" in view_mode
    if is_monthly:
        labels_arr = month_labels
        pack = trend_pack['M']
    else:
        labels_arr = trend_labels
        pack = trend_pack['W']

    if vt == "충청호남팀 전체":
        source_data = pack['tot']
    elif vt in ["충청팀 통합", "호남팀 통합"]:
        region_key = "충청상권" if vt == "충청팀 통합" else "호남상권"
        source_data = pack['reg'][region_key]
    elif "대리점" in vt: 
        target_dealer = vt.replace(" 대리점", "")
        source_data = pack['dlr'].get(target_dealer, [{'amt':0, 'est':0, 'cnt':0, 'sales':0, 'amt_wd':0, 'amt_we':0, 'amt_move':0} for _ in labels_arr])
    else: 
        parts = vt.replace("👤 ", "").split(" - ")
        target_hc = parts[1]
        source_data = pack['hc'].get(target_hc, [{'amt':0, 'est':0, 'cnt':0, 'sales':0, 'amt_wd':0, 'amt_we':0, 'amt_move':0} for _ in labels_arr])
    
    g_col1, g_col2, g_col3, g_col4 = st.columns([5, 3, 2, 2])
    
    with g_col1:
        st.markdown("<div class='chart-btn-group'>💰 재무 지표</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.button("계약액" if not st.session_state['t_amt'] else "✅ 계약액", on_click=toggle_state, args=('t_amt',), use_container_width=True, type="primary" if st.session_state['t_amt'] else "secondary")
        with c2: st.button("매출액" if not st.session_state['t_sales'] else "✅ 매출액", on_click=toggle_state, args=('t_sales',), use_container_width=True, type="primary" if st.session_state['t_sales'] else "secondary")
        with c3: st.button("이월매출" if not st.session_state['t_next'] else "✅ 이월매출", on_click=toggle_state, args=('t_next',), use_container_width=True, type="primary" if st.session_state['t_next'] else "secondary")
        with c4: st.button("평균(계약)" if not st.session_state['t_avg'] else "✅ 평균(계약)", on_click=toggle_state, args=('t_avg',), use_container_width=True, type="primary" if st.session_state['t_avg'] else "secondary")

    with g_col2:
        st.markdown("<div class='chart-btn-group'>🏢 분류 지표 (계약액)</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.button("주중" if not st.session_state['t_wd'] else "✅ 주중", on_click=toggle_state, args=('t_wd',), use_container_width=True, type="primary" if st.session_state['t_wd'] else "secondary")
        with c2: st.button("주말" if not st.session_state['t_we'] else "✅ 주말", on_click=toggle_state, args=('t_we',), use_container_width=True, type="primary" if st.session_state['t_we'] else "secondary")
        with c3: st.button("워크인" if not st.session_state['t_walk'] else "✅ 워크인", on_click=toggle_state, args=('t_walk',), use_container_width=True, type="primary" if st.session_state['t_walk'] else "secondary")
        with c4: st.button("입주" if not st.session_state['t_move'] else "✅ 입주", on_click=toggle_state, args=('t_move',), use_container_width=True, type="primary" if st.session_state['t_move'] else "secondary")

    with g_col3:
        st.markdown("<div class='chart-btn-group'>📝 건수 지표</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.button("견적건" if not st.session_state['t_est'] else "✅ 견적건", on_click=toggle_state, args=('t_est',), use_container_width=True, type="primary" if st.session_state['t_est'] else "secondary")
        with c2: st.button("계약건" if not st.session_state['t_cnt'] else "✅ 계약건", on_click=toggle_state, args=('t_cnt',), use_container_width=True, type="primary" if st.session_state['t_cnt'] else "secondary")

    with g_col4:
        st.markdown("<div class='chart-btn-group'>📊 효율 지표</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.button("계약률" if not st.session_state['t_rate'] else "✅ 계약률", on_click=toggle_state, args=('t_rate',), use_container_width=True, type="primary" if st.session_state['t_rate'] else "secondary")
        with c2: st.button("객단가" if not st.session_state['t_unit'] else "✅ 객단가", on_click=toggle_state, args=('t_unit',), use_container_width=True, type="primary" if st.session_state['t_unit'] else "secondary")
    
    y_amt = [w.get('amt', 0) for w in source_data]
    y_amt_억 = [v / 100000 for v in y_amt]
    y_sales = [w.get('sales', 0) for w in source_data]
    y_sales_억 = [v / 100000 for v in y_sales]
    y_next = [w.get('next_sales', 0) for w in source_data]
    y_next_억 = [v / 100000 for v in y_next]
    
    y_avg_val = sum(y_amt) / len(y_amt) if y_amt else 0
    y_avg_억 = [y_avg_val / 100000] * len(y_amt)
    
    y_wd = [w.get('amt_wd', 0) for w in source_data]
    y_wd_억 = [v / 100000 for v in y_wd]
    y_we = [w.get('amt_we', 0) for w in source_data]
    y_we_억 = [v / 100000 for v in y_we]
    
    # 🚀 워크인/입주 분리 및 비중(%) 텍스트 계산
    y_move = [w.get('amt_move', 0) for w in source_data]
    y_move_억 = [v / 100000 for v in y_move]
    y_walk_억 = [(a - m) / 100000 for a, m in zip(y_amt, y_move)]
    
    y_move_text = []
    y_walk_text = []
    for w_val, m_val, a_val in zip(y_walk_억, y_move_억, y_amt_억):
        if a_val > 0:
            y_move_text.append(f"<b>{m_val:.2f}억</b><br><span style='font-size:11px'>({(m_val/a_val*100):.1f}%)</span>")
            y_walk_text.append(f"<b>{w_val:.2f}억</b><br><span style='font-size:11px'>({(w_val/a_val*100):.1f}%)</span>")
        else:
            y_move_text.append(f"<b>{m_val:.2f}억</b>")
            y_walk_text.append(f"<b>{w_val:.2f}억</b>")
    
    y_est = [w.get('est', 0) for w in source_data]
    y_cnt = [w.get('cnt', 0) for w in source_data]
    y_rate = [(c / e * 100) if e > 0 else 0 for e, c in zip(y_est, y_cnt)]
    y_unit = [(a / (c * 10)) if c > 0 else 0 for a, c in zip(y_amt, y_cnt)] 
            
    any_active = any([st.session_state[k] for k in toggle_keys])
    
    if any_active:
        fig_trend = go.Figure()
        marker_sizes = [10] * (len(labels_arr)-1) + [20] # 최신 주차/월은 마커 크기 20
        
        if st.session_state['t_amt']:
            marker_colors = ['#0f172a'] * (len(labels_arr)-1) + ['#dc2626'] 
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_amt_억, mode='lines+markers+text', name='계약액', text=[f"<b>{v:.2f}억</b>" for v in y_amt_억], textposition='top center', textfont=dict(size=15, color='black'), line=dict(color='#0f172a', width=4), marker=dict(size=marker_sizes, color=marker_colors, line=dict(width=2, color='white'))))
        
        if st.session_state['t_sales']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_sales_억, mode='lines+markers+text', name='매출액', text=[f"<b>{v:.2f}억</b>" for v in y_sales_억], textposition='bottom right', textfont=dict(size=15, color='#0d9488'), line=dict(color='#14b8a6', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white'))))
            
        if st.session_state['t_next']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_next_억, mode='lines+markers+text', name='이월매출 (M+1)', text=[f"<b>{v:.2f}억</b>" for v in y_next_억], textposition='top left', textfont=dict(size=15, color='#d97706'), line=dict(color='#f59e0b', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white'))))
        
        if st.session_state['t_avg']:
            y_avg_text = [""] * (len(labels_arr)-1) + [f"<b>평균 {y_avg_억[-1]:.2f}억</b>"]
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_avg_억, mode='lines+text', name='평균선', text=y_avg_text, textposition='top right', textfont=dict(size=15, color='#475569'), line=dict(color='#94a3b8', width=2, dash='dash')))
        
        if st.session_state['t_wd']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_wd_억, mode='lines+markers+text', name='계약액(주중)', text=[f"<b>{v:.2f}억</b>" for v in y_wd_억], textposition='bottom center', textfont=dict(size=15, color='#0ea5e9'), line=dict(color='#0ea5e9', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white'))))
        
        if st.session_state['t_we']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_we_억, mode='lines+markers+text', name='계약액(주말)', text=[f"<b>{v:.2f}억</b>" for v in y_we_억], textposition='top right', textfont=dict(size=15, color='#ef4444'), line=dict(color='#ef4444', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white'))))
        
        if st.session_state['t_walk']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_walk_억, mode='lines+markers+text', name='워크인 계약액', text=y_walk_text, textposition='top left', textfont=dict(size=15, color='#f97316'), line=dict(color='#f97316', width=3, dash='dot')))
        
        if st.session_state['t_move']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_move_억, mode='lines+markers+text', name='입주 계약액', text=y_move_text, textposition='bottom right', textfont=dict(size=15, color='#a855f7'), line=dict(color='#a855f7', width=3, dash='dot')))

        if st.session_state['t_est']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_est, mode='lines+markers+text', name='견적건', text=[f"<b>{v:,.0f}건</b>" for v in y_est], textposition='top center', textfont=dict(size=15, color='#4338ca'), line=dict(color='#4338ca', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white')), yaxis='y2'))
        
        if st.session_state['t_cnt']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_cnt, mode='lines+markers+text', name='계약건', text=[f"<b>{v:,.0f}건</b>" for v in y_cnt], textposition='bottom center', textfont=dict(size=15, color='#10b981'), line=dict(color='#10b981', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white')), yaxis='y2'))

        if st.session_state['t_rate']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_rate, mode='lines+markers+text', name='계약률', text=[f"<b>{v:.1f}%</b>" for v in y_rate], textposition='top right', textfont=dict(size=15, color='#ca8a04'), line=dict(color='#ca8a04', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white')), yaxis='y3'))
        
        if st.session_state['t_unit']:
            fig_trend.add_trace(go.Scatter(x=labels_arr, y=y_unit, mode='lines+markers+text', name='객단가', text=[f"<b>{int(v):,}만</b>" for v in y_unit], textposition='bottom left', textfont=dict(size=15, color='#ec4899'), line=dict(color='#ec4899', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white')), yaxis='y4'))
            
        fig_trend.update_layout(
            height=450, margin=dict(l=20, r=20, t=60, b=20), plot_bgcolor='white', 
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
            annotations=[dict(xref='paper', yref='paper', x=0, y=1.1, xanchor='left', yanchor='bottom', text='<b>금액 (억)</b>', font=dict(size=13, color='#1e3a8a'), showarrow=False)],
            yaxis=dict(title="", tickformat=".1f", ticksuffix="억", dtick=0.5, gridcolor='#f1f5f9'),
            yaxis2=dict(title=dict(text="<b>건수 (건)</b>", font=dict(size=13, color='#ea580c')), overlaying='y', side='right', showgrid=False),
            yaxis3=dict(overlaying='y', visible=False),
            yaxis4=dict(overlaying='y', visible=False),
        )
        fig_trend.update_xaxes(showgrid=True, gridcolor='#f1f5f9', tickfont=dict(size=12, color='black'))
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("👆 위 세부 지표 버튼을 클릭하시면 실시간 추이 꺾은선 그래프가 나타납니다.")
    
    st.markdown("---")

    # 🚀 5. 하단 전체 상세 표 출력
    table_date_range = date_headers.get(CURRENT_TABLE_WEEK, "")
    st.markdown(f"""
    <div style='background-color: #f8fafc; padding: 15px; border-left: 5px solid #3b82f6; border-radius: 5px; margin-bottom: 20px;'>
        <h4 style='margin:0; color: #1e3a8a;'>📌 {current_month}월 {CURRENT_TABLE_WEEK} {table_date_range} 전체 VDT 현황 표</h4>
    </div>
    """, unsafe_allow_html=True)
    
    def render_custom_html_table(df):
        dealer_col, hc_col = ('기본정보', '대리점', '대리점'), ('기본정보', 'HC명', 'HC명')
        unique_dealers = [d for d in df[dealer_col].unique() if d not in ["🌟 총계", "충청상권", "호남상권"]]
        dealer_colors = {}
        colors = ['#f8fafc', '#ffffff']
        for idx, d in enumerate(unique_dealers): dealer_colors[d] = colors[idx % len(colors)]
            
        col_widths = [80, 90, 70, 70, 70, 70, 70, 70, 55, 55, 55, 55, 55, 55]
        col_lefts = [0, 80, 170, 240, 310, 380, 450, 520, 590, 645, 700, 755, 810, 865]
        
        html_list = ["<div class='vdt-table-container'><table class='vdt-table'><thead>"]
        
        html_list.append("<tr>")
        html_list.append(f"<th rowspan='3' style='position: sticky; top: 0; left: 0; z-index: 20; background-color: #0f172a; min-width: {col_widths[0]}px; max-width: {col_widths[0]}px; border-right: 1px solid #cbd5e1;'>대리점</th>")
        html_list.append(f"<th rowspan='3' style='position: sticky; top: 0; left: {col_lefts[1]}px; z-index: 20; background-color: #0f172a; min-width: {col_widths[1]}px; max-width: {col_widths[1]}px; border-right: 2px solid #94a3b8;'>HC명</th>")
        
        headers_l1 = []
        for col in df.columns[2:]:
            if col[0] not in headers_l1: headers_l1.append(col[0])
                
        for h1 in headers_l1:
            is_curr, is_monthly = CURRENT_TABLE_WEEK in h1, "당월" in h1
            style_parts = ["position: sticky; top: 0;"]
            
            if is_curr: style_parts.extend(["background-color: #1e3a8a;", "border: 3px solid #60a5fa;"])
            elif is_monthly: style_parts.extend(["background-color: #064e3b;", "color: #a7f3d0;", "border-top: 2px solid #047857;"])
            else: style_parts.append("background-color: #0f172a;")
                
            if h1 == '🎯 당월매출':
                style_parts.extend([f"left: {col_lefts[2]}px;", "z-index: 15;", "border-right: 3px solid #1e293b;"])
                html_list.append(f"<th colspan='3' style='{'; '.join(style_parts)}'>{h1}</th>")
            elif "🌟 당월 합계" in h1:
                style_parts.extend([f"left: {col_lefts[5]}px;", "z-index: 15;", "border-right: 4px solid #94a3b8;"])
                html_list.append(f"<th colspan='9' style='{'; '.join(style_parts)}'>{h1}</th>")
            else:
                style_parts.append("z-index: 10;")
                html_list.append(f"<th colspan='9' style='{'; '.join(style_parts)}'>{h1}</th>")
        html_list.append("</tr>")
        
        html_list.append("<tr>")
        for h1 in headers_l1:
            is_curr, is_monthly = CURRENT_TABLE_WEEK in h1, "당월" in h1
            base_styles = ["position: sticky; top: 33px;"]
            if is_curr: base_styles.extend(["background-color: #1e40af;", "border-left: 3px solid #60a5fa;", "border-right: 3px solid #60a5fa;"])
            elif is_monthly: base_styles.extend(["background-color: #065f46;", "color: #a7f3d0;"])
            else: base_styles.append("background-color: #0f172a;")
            
            if h1 == '🎯 당월매출':
                s_parts = base_styles.copy() + [f"left: {col_lefts[2]}px;", "z-index: 15;", "border-right: 3px solid #1e293b;"]
                html_list.append(f"<th colspan='3' style='{'; '.join(s_parts)}'>인별매출(천)</th>")
            elif "🌟 당월 합계" in h1:
                s1, s2, s3 = base_styles.copy() + [f"left: {col_lefts[5]}px;", "z-index: 15;"], base_styles.copy() + [f"left: {col_lefts[8]}px;", "z-index: 15;"], base_styles.copy() + [f"left: {col_lefts[11]}px;", "z-index: 15;", "border-right: 4px solid #94a3b8;"]
                html_list.append(f"<th colspan='3' style='{'; '.join(s1)}'>계약액(천)</th><th colspan='3' style='{'; '.join(s2)}'>견적건</th><th colspan='3' style='{'; '.join(s3)}'>계약건</th>")
            else:
                bg_style = f"style='{'; '.join(base_styles + ['z-index: 10;'])}'"
                html_list.append(f"<th colspan='3' {bg_style}>계약액(천)</th><th colspan='3' {bg_style}>견적건</th><th colspan='3' {bg_style}>계약건</th>")
        html_list.append("</tr>")
        
        html_list.append("<tr>")
        for c_idx, col in enumerate(df.columns[2:]):
            abs_idx = c_idx + 2
            is_curr, is_monthly = CURRENT_TABLE_WEEK in col[0], "당월" in col[0]
            is_first_of_week, is_last_of_week = (is_curr and col[1] == '계약액(천)' and col[2] == '목표'), (is_curr and col[1] == '계약건' and col[2] == '달성율(%)')
            is_last_of_sales, is_last_monthly = (col[0] == '🎯 당월매출' and col[2] == '달성율(%)'), ("🌟 당월 합계" in col[0] and col[1] == '계약건' and col[2] == '달성율(%)')
            
            style_parts = ["position: sticky; top: 66px;"]
            if is_curr:
                style_parts.extend(["background-color: #1d4ed8;", "border-bottom: 3px solid #60a5fa;"])
                if is_first_of_week: style_parts.append("border-left: 3px solid #60a5fa;")
                if is_last_of_week: style_parts.append("border-right: 3px solid #60a5fa;")
            elif is_monthly: style_parts.extend(["background-color: #047857;", "color: #a7f3d0;"])
            else: style_parts.append("background-color: #0f172a;")
                
            if abs_idx <= 13: style_parts.extend([f"left: {col_lefts[abs_idx]}px;", "z-index: 15;", f"min-width: {col_widths[abs_idx]}px;", f"max-width: {col_widths[abs_idx]}px;"])
            else: style_parts.extend(["z-index: 10;", "min-width: 60px;"])
            
            if is_last_of_sales: style_parts.append("border-right: 3px solid #1e293b;")
            if is_last_monthly: style_parts.append("border-right: 4px solid #94a3b8;")
                
            bg_style = f"style='{'; '.join(style_parts)}'"
            html_list.append(f"<th {bg_style}>{col[2]}</th>")
        html_list.append("</tr></thead><tbody>")
        
        for r_idx in range(len(df)):
            row = df.iloc[r_idx]
            dealer, hc = row[dealer_col], row[hc_col]
            
            if str(hc) == "합계" or str(hc) == "상권합계": bg_color, row_bg = "#e2e8f0", "style='background-color: #e2e8f0; font-weight: bold;'"
            elif "🌟" in str(hc): bg_color, row_bg = "#cbd5e1", "style='background-color: #cbd5e1; font-weight: bold;'"
            else: bg_color, row_bg = dealer_colors.get(dealer, '#ffffff'), f"style='background-color: {dealer_colors.get(dealer, '#ffffff')};'"
                
            html_list.append(f"<tr {row_bg}>")
            html_list.append(f"<td class='text-center' style='position: sticky; left: 0; z-index: 6; background-color: {bg_color}; min-width: {col_widths[0]}px; max-width: {col_widths[0]}px; border-right: 1px solid #cbd5e1;'>{dealer}</td>")
            html_list.append(f"<td class='text-center' style='position: sticky; left: {col_lefts[1]}px; z-index: 6; background-color: {bg_color}; min-width: {col_widths[1]}px; max-width: {col_widths[1]}px; border-right: 2px solid #94a3b8;'>{hc}</td>")
            
            for c_idx, val in enumerate(row[2:]):
                abs_idx = c_idx + 2
                col_obj = df.columns[c_idx + 2]
                is_curr, is_monthly = CURRENT_TABLE_WEEK in col_obj[0], "당월" in col_obj[0]
                is_first_of_week, is_last_of_week = (is_curr and col[1] == '계약액(천)' and col[2] == '목표'), (is_curr and col[1] == '계약건' and col[2] == '달성율(%)')
                is_last_of_sales, is_last_monthly = (col[0] == '🎯 당월매출' and col[2] == '달성율(%)'), ("🌟 당월 합계" in col[0] and col[1] == '계약건' and col[2] == '달성율(%)')
                
                style_parts = []
                if is_curr:
                    style_parts.append("background-color: rgba(37, 99, 235, 0.12);")
                    if is_first_of_week: style_parts.append("border-left: 3px solid #3b82f6;")
                    if is_last_of_week: style_parts.append("border-right: 3px solid #3b82f6;")
                elif is_monthly:
                    if abs_idx <= 13: 
                        solid_bg = '#ebf6f2'
                        if bg_color == '#f8fafc': solid_bg = '#e4f1ef'
                        elif bg_color == '#e2e8f0': solid_bg = '#d1dbda'
                        elif bg_color == '#cbd5e1': solid_bg = '#bcc7c7'
                        style_parts.append(f"background-color: {solid_bg};")
                    else: style_parts.append("background-color: rgba(5, 150, 105, 0.08);")
                else: style_parts.append(f"background-color: {bg_color};")
                
                if abs_idx <= 13: style_parts.extend([f"position: sticky; left: {col_lefts[abs_idx]}px;", "z-index: 5;", f"min-width: {col_widths[abs_idx]}px;", f"max-width: {col_widths[abs_idx]}px;"])
                if is_last_of_sales: style_parts.append("border-right: 3px solid #1e293b;")
                if is_last_monthly: style_parts.append("border-right: 4px solid #94a3b8;")
                    
                if col_obj[2] == '달성율(%)':
                    val_str = f"{val:.0f}%" 
                    if val >= 100: val_str = f"<span style='color: #047857; font-weight: 900;'>{val_str}</span>" if is_monthly else f"<span style='color: #1d4ed8; font-weight: 900;'>{val_str}</span>"
                    elif val > 0: val_str = f"<span style='font-weight: 600;'>{val_str}</span>"
                else: val_str = f"{val:,.0f}"
                    
                border_style = f"{'; '.join(style_parts)}" if style_parts else ""
                html_list.append(f"<td style='{border_style}'>{val_str}</td>")
            html_list.append("</tr>")
            
        html_list.append("</tbody></table></div>")
        return "".join(html_list)
    
    table_html = render_custom_html_table(final_df)
    st.markdown(table_html, unsafe_allow_html=True)
