import socket
socket.setdefaulttimeout(60.0) 

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
import calendar

st.set_page_config(page_title="충청호남팀 영업사원 주차별 VDT 목표 관리", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1yZdc4BL5CHLwBQ2QGp8zD5_ov7LDKsEcnrONdQvDyHI/edit?gid=1748736055#gid=1748736055"

default_states = {
    'view_target': "충청호남팀 전체", 'hc_selector': "✨ 인원별 상세 실적 (선택 시 우선 적용)", 
    'view_mode': "주간 추이 (최근 8주)", 't_amt': True, 't_sales': False, 't_next': False,
    't_avg': False, 't_wd': False, 't_we': False, 't_walk': False, 't_move': False,
    't_est': False, 't_cnt': False, 't_rate': False, 't_unit': False, 
    't_onl': False, 't_can': False,
    'wow_prev': '🌟 [당일기준] 전월 누적', 'wow_curr': '🌟 [당일기준] 당월 누적'
}
for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

toggle_keys = ['t_amt', 't_sales', 't_next', 't_avg', 't_wd', 't_we', 't_walk', 't_move', 't_est', 't_cnt', 't_rate', 't_unit', 't_onl', 't_can']
EXCLUDED_HCS = ["장재형", "강지인"]

@st.cache_resource
def init_connection():
    try:
        creds_dict = json.loads(st.secrets["gcp"]["key"])
        creds = Credentials.from_service_account_info(
            creds_dict, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"구글 API 키 오류: {e}")
        return None

client = init_connection()
current_date = datetime.now()
current_month = current_date.month

css_styles = [
    "<style>",
    "@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');",
    "html, body, [class*='css'], [class*='st-'], th, td { font-family: 'Noto Sans KR', sans-serif !important; }",
    "div[data-testid='stTabs'] button { font-size: 15px !important; font-weight: 700 !important; color: #94a3b8 !important; }",
    "div[data-testid='stTabs'] button[aria-selected='true'] { color: #1d4ed8 !important; font-weight: 900 !important; border-bottom: 3px solid #1d4ed8 !important; }",
    "div[data-testid='stSelectbox'] div[data-baseweb='select'] > div { border: 2px solid #1e293b !important; background-color: #ffffff !important; color: #0f172a !important; font-weight: 900 !important; }",
    "div[data-testid='stSelectbox'] div[data-baseweb='select'] * { color: #0f172a !important; font-weight: 900 !important; }",
    ".vdt-table-container { width: 100%; max-height: 65vh; overflow: auto; border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 10px; }",
    ".vdt-table-container::-webkit-scrollbar { width: 14px; height: 14px; }",
    ".vdt-table-container::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 8px; }",
    ".vdt-table-container::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 8px; border: 3px solid #f1f5f9; }",
    ".vdt-table { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }",
    ".vdt-table tbody tr:hover { background-color: #dbeafe !important; font-weight: 900 !important; transition: all 0.1s ease-in-out; }",
    ".vdt-table tbody tr:hover td { background-color: transparent !important; color: #0f172a !important; }",
    ".vdt-table thead th { height: 34px; position: sticky; z-index: 10; }",
    ".vdt-table thead tr:nth-child(1) th { top: 0; }",
    ".vdt-table thead tr:nth-child(2) th { top: 33px; }",
    ".vdt-table thead tr:nth-child(3) th { top: 66px; }",
    ".vdt-table th { background-color: #0f172a; color: white; padding: 6px 8px; text-align: center; border: 1px solid #334155; font-weight: 700; }",
    ".vdt-table td { padding: 4px 8px; text-align: right; border: 1px solid #e2e8f0; }",
    ".title-box { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 12px 15px; border-radius: 8px; margin-bottom: 12px; }",
    "h1, h3, h4 { font-weight: 900 !important; margin: 0; }",
    "h1 { font-size: 16px !important; color: white !important; display:flex; align-items:center; }",
    "h4 { font-size: 14px !important; color: #1e293b !important; }",
    ".wow-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }",
    ".wow-table th { background-color: #1e293b; color: white; padding: 8px; text-align: center; border: 1px solid #334155; font-weight: 900; font-size: 13px;}",
    ".wow-table td { padding: 8px; text-align: right; border: 1px solid #cbd5e1; background-color: white; font-size: 14px; font-weight: 700;}",
    ".wow-up { color: #dc2626; font-weight: 900; }",
    ".wow-down { color: #2563eb; font-weight: 900; }",
    ".wow-same { color: #64748b; font-weight: 600; }",
    "div.stButton > button { background: #f8fafc !important; color: #020617 !important; font-size: 12px !important; font-weight: 900 !important; border-radius: 6px !important; padding: 4px 6px !important; border: 1px solid #94a3b8 !important; height: auto !important; min-height: 32px; border-bottom: 2px solid #64748b !important; transition: all 0.1s ease !important; }",
    "div.stButton > button[kind='primary'] { background: linear-gradient(180deg, #fee2e2 0%, #fecaca 100%) !important; color: #991b1b !important; border: 1px solid #f87171 !important; border-bottom: 2px solid #ef4444 !important; }",
    "#org-buttons + div[data-testid='stHorizontalBlock'] > div:nth-child(1) button { background-color: #faf5ff !important; border-color: #e9d5ff !important; color: #9333ea !important; border-bottom: 2px solid #d8b4fe !important; }",
    "#org-buttons + div[data-testid='stHorizontalBlock'] > div:nth-child(1) button[kind='primary'] { background: linear-gradient(180deg, #f3e8ff 0%, #e9d5ff 100%) !important; color: #3b0764 !important; border-bottom: 2px solid #7e22ce !important; }",
    "#org-buttons + div[data-testid='stHorizontalBlock'] > div:nth-child(3) button { background-color: #f0f9ff !important; border-color: #bae6fd !important; color: #0284c7 !important; border-bottom: 2px solid #7dd3fc !important; }",
    "#org-buttons + div[data-testid='stHorizontalBlock'] > div:nth-child(3) button[kind='primary'] { background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%) !important; color: #082f49 !important; border-bottom: 2px solid #0284c7 !important; }",
    "#org-buttons + div[data-testid='stHorizontalBlock'] > div:nth-child(9) button { background-color: #f0fdf4 !important; border-color: #bbf7d0 !important; color: #16a34a !important; border-bottom: 2px solid #86efac !important; }",
    "#org-buttons + div[data-testid='stHorizontalBlock'] > div:nth-child(9) button[kind='primary'] { background: linear-gradient(180deg, #dcfce7 0%, #bbf7d0 100%) !important; color: #052e16 !important; border-bottom: 2px solid #16a34a !important; }",
    ".chart-btn-group { font-size: 11px; font-weight: 800; color: #475569; background: #e2e8f0; border-radius: 4px; padding: 2px 0; text-align: center; margin-bottom: 4px; border: 1px solid #cbd5e1;}",
    ".mode-toggle { font-size: 14px; font-weight: 900; color: #0f172a; display:flex; align-items:center; gap:10px;}",
    "</style>"
]
st.markdown("".join(css_styles), unsafe_allow_html=True)

title_html = [
    "<div class='title-box'><h1>📊 충청호남팀 VDT 종합 관리 ",
    f"<span style='font-size:13px; font-weight:normal; color:#bae6fd; margin-left:10px;'>({current_date.strftime('%y년 %m월 %d일')} 기준)</span></h1></div>"
]
st.markdown("".join(title_html), unsafe_allow_html=True)

def clean_str(val): return re.sub(r'\s+', '', str(val))
def safe_get(row, idx): return str(row[idx]).strip() if len(row) > idx else ""

def clean_val(v):
    if not v or pd.isna(v): return 0.0
    v_str = str(v).replace('%', '').replace(',', '').strip()
    m = 100000000 if '억' in v_str else (10000 if '만' in v_str else 1)
    match = re.search(r'-?\d+(?:\.\d+)?', v_str)
    if match:
        try:
            return float(match.group()) * m
        except ValueError:
            return 0.0
    return 0.0

def get_mapped_dealer(raw_d):
    c_d = clean_str(raw_d)
    if any(k in c_d for k in ["한밭", "INT충청", "701347", "세종2"]): return "세종"
    return raw_d.strip()

REGION_MAP = {"충청상권": ["둔산", "목포", "세종", "충주"], "호남상권": ["광양", "여수", "익산"]}

current_monday = current_date - timedelta(days=current_date.weekday())
trend_ranges, trend_labels = [], []
for i in range(7, -1, -1):
    w_start = current_monday - timedelta(weeks=i)
    w_end = w_start + timedelta(days=6)
    iso_week = w_start.isocalendar()[1]
    trend_ranges.append((w_start, w_end))
    trend_labels.append(f"▪️ {iso_week}주 ({w_start.strftime('%m.%d')}~{w_end.strftime('%m.%d')})")

def get_trend_week_idx(m, d, y=current_date.year):
    try:
        t_d = datetime(y, m, d).date()
        for i, (s, e) in enumerate(trend_ranges):
            if s.date() <= t_d <= e.date(): return i
    except: pass
    return -1

def get_prev_month_date(dt_obj, months_back):
    m = dt_obj.month - months_back
    y = dt_obj.year
    while m <= 0:
        m += 12
        y -= 1
    last_day_of_target_month = calendar.monthrange(y, m)[1]
    target_d = min(dt_obj.day, last_day_of_target_month)
    return datetime(y, m, target_d).date()

def safe_api_call(func, *args, **kwargs):
    for attempt in range(6):
        try: return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and attempt < 5:
                time.sleep(15 * (attempt + 1))
                continue
            raise e

@st.cache_data(ttl=600, show_spinner=False)
def fetch_sheets():
    if not client: return [], [], []
    sh = safe_api_call(client.open_by_url, SHEET_URL)
    all_ws_objs = safe_api_call(sh.worksheets)
    all_ws = [ws.title for ws in all_ws_objs]
    
    target_ws = sh.worksheet("주차별 목표 세팅")
    all_targets = safe_api_call(target_ws.get_all_values)
    
    daily_ws = None
    for ws in all_ws_objs:
        if "모음" in ws.title or "통합" in ws.title:
            daily_ws = ws
            break
            
    all_daily_data = safe_api_call(daily_ws.get_all_values) if daily_ws else []
    return all_targets, all_daily_data, all_ws

with st.spinner("🚀 최신 일보 데이터를 초고속으로 스캔하고 있습니다..."):
    all_targets, all_daily_data, all_ws = fetch_sheets()

if not all_daily_data:
    st.error("🚨 일보 데이터를 불러오지 못했습니다.")
    st.stop()

available_dates_set = set()
for row in all_daily_data:
    r_head = clean_str("".join([safe_get(row, i) for i in range(min(5, len(row)))]))
    match = re.search(r'(?:(20\d{2})[년/.-]\s*)?([01]?\d)[월/.-]\s*([0-3]?\d)일?', r_head)
    if match and ("일반" in r_head or "입주" in r_head or "점별" in r_head):
        y_str, m_str, d_str = match.groups()
        y = int(y_str) if y_str else current_date.year
        m, d = int(m_str), int(d_str)
        try:
            available_dates_set.add(datetime(y, m, d).date())
        except: pass

available_dates = sorted(list(available_dates_set))
max_date_in_sheet = available_dates[-1] if available_dates else current_date.date()

all_normal_options = list(reversed(trend_labels))
curr_options = ['🌟 [당일기준] 당월 누적', '🌟 [당일기준] 전월 누적', '🌟 [당일기준] 전전월 누적', '🌟 [당일기준] 전년 누적'] + all_normal_options

is_weekly_selected = "▪️" in str(st.session_state.get('wow_curr', ''))

c_cal1, c_cal2 = st.columns([10, 2])
with c_cal2:
    st.markdown("<div style='font-size:13px; font-weight:900; color:#1e293b; margin-bottom:4px;'>조회 기준일 선택 📅</div>", unsafe_allow_html=True)
    selected_date = st.date_input(
        "기준일", 
        value=max_date_in_sheet, 
        min_value=available_dates[0] if available_dates else None, 
        max_value=current_date.date(), 
        disabled=is_weekly_selected, 
        label_visibility="collapsed"
    )
    if is_weekly_selected:
        st.markdown("<div style='font-size:11px; color:#ef4444; margin-top:2px; font-weight:bold;'>🔒 주간 실적 조회 중 (달력 잠김)</div>", unsafe_allow_html=True)

def process_vdt_data(all_targets, all_daily_data, selected_date):
    hc_to_dealer_master, hc_info_dict, dealer_sales_sum = {}, {}, {}
    for row in all_targets[15:]:
        if len(row) > 17:
            raw_dealer, hc_name, tgt_str = str(row[14]).strip(), clean_str(row[15]), str(row[17]).strip()
            if not raw_dealer or not hc_name or hc_name.isdigit() or hc_name in ['HC', 'HC명', '영업사원', '이름']: continue
            d = get_mapped_dealer(raw_dealer)
            hc_to_dealer_master[hc_name] = d
            tgt = clean_val(tgt_str) / 1000.0  
            if hc_name in hc_info_dict: hc_info_dict[hc_name]['tgt'] += tgt
            else: hc_info_dict[hc_name] = {'dealer': d, 'tgt': tgt}
            dealer_sales_sum[d] = dealer_sales_sum.get(d, 0.0) + tgt

    hc_info_raw = [(v['dealer'], k, v['tgt']) for k, v in hc_info_dict.items()]
    
    week_row_idx, date_row_idx = -1, -1
    for i, row in enumerate(all_targets[:10]):
        rs = "".join(str(c) for c in row)
        if "주" in rs and re.search(r'\d+주', rs) and week_row_idx == -1: week_row_idx = i
        if (re.search(r'\d+/\d+', rs) or re.search(r'\d+\.\d+', rs)) and date_row_idx == -1: date_row_idx = i
    
    week_cols, date_headers = {}, {}
    if week_row_idx != -1:
        wr = all_targets[week_row_idx]
        dr = all_targets[date_row_idx] if date_row_idx != -1 else all_targets[week_row_idx+1]
        for col_idx, cv in enumerate(wr):
            c_val = str(cv).strip()
            if "주" in c_val and col_idx >= 1: 
                week_cols[c_val] = {'amt': col_idx, 'est': col_idx+1, 'cnt': col_idx+2}
                date_headers[c_val] = str(dr[col_idx]).strip() if col_idx < len(dr) else ""
            
    if not week_cols:
        week_cols = {'1주차': {'amt': 1, 'est': 2, 'cnt': 3}, '2주차': {'amt': 4, 'est': 5, 'cnt': 6}, '3주차': {'amt': 7, 'est': 8, 'cnt': 9}, '4주차': {'amt': 10, 'est': 11, 'cnt': 12}, '5주차': {'amt': 13, 'est': 14, 'cnt': 15}}
        date_headers = {k: k for k in week_cols}
        
    week_keys = list(week_cols.keys())
    date_to_target_week = {}
    cy = current_date.year
    for wk, d_str in date_headers.items():
        dt = re.findall(r'\d+', d_str)
        if len(dt) >= 4:
            try:
                m1, d1, m2, d2 = map(int, dt[:4])
                s_dt = datetime(cy, m1, d1)
                e_dt = datetime(cy + (1 if m1==12 and m2==1 else 0), m2, d2)
                c = s_dt
                while c <= e_dt:
                    date_to_target_week[(c.month, c.day)] = wk
                    c += timedelta(days=1)
            except: pass
        elif len(dt) >= 2:
            try: date_to_target_week[(int(dt[0]), int(dt[1]))] = wk
            except: pass

    dealer_targets = {}
    for row in all_targets[:15]: 
        if len(row) > 0 and str(row[0]).strip():
            rd = str(row[0]).strip()
            if rd in ['대리점명', '구분', '대리점']: continue
            d_name = get_mapped_dealer(rd)
            if d_name not in dealer_targets: dealer_targets[d_name] = {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys}
            for wk, cols in week_cols.items():
                dealer_targets[d_name][wk]['amt'] += (clean_val(safe_get(row, cols['amt'])) / 1000.0) 
                dealer_targets[d_name][wk]['est'] += clean_val(safe_get(row, cols['est']))
                dealer_targets[d_name][wk]['cnt'] += clean_val(safe_get(row, cols['cnt']))

    existing_hcs = [clean_str(h) for d, h, t in hc_info_raw]
    
    daily_data = {}       
    raw_snapshots = {}
    daily_raw_totals = {} 
    
    sub_kw = ['합계', '소계', '총계', 'INT', '한밭', '위탁']
    exact_kw = ['목표', '사번', '비고', '계', '대리점', '이름', 'HC', 'HC명', '영업사원']
    dealer_names = ["둔산", "목포", "세종", "충주", "광양", "여수", "익산", "충청", "호남", "INT", "한밭"]
    curr_mode = ""

    for r_idx, row in enumerate(all_daily_data):
        row_header = clean_str("".join([safe_get(row, i) for i in range(min(5, len(row)))]))
        
        if "일반" in row_header or "입주" in row_header or "점별" in row_header:
            date_match = re.search(r'(?:(20\d{2})[년/.-]\s*)?([01]?\d)[월/.-]\s*([0-3]?\d)일?', row_header)
            if date_match:
                ys, ms, ds = date_match.groups()
                y = int(ys) if ys else current_date.year
                try: cur_dt = datetime(y, int(ms), int(ds)).date()
                except: cur_dt = datetime.min.date()
                
            if "일반" in row_header: curr_mode = "일반"
            elif "입주" in row_header: curr_mode = "입주"
            elif "점별" in row_header: curr_mode = "점별"
            continue
            
        if curr_mode == "일반" and len(row) > 3:
            raw_dealer = safe_get(row, 1) 
            raw_hc = safe_get(row, 3) 
            if not raw_hc and len(row) > 1: raw_hc = raw_dealer 
            hc_name = clean_str(raw_hc.split('(')[0]) 
            hc_name = re.sub(r'\d+', '', hc_name) 
            
            is_dealer = get_mapped_dealer(hc_name) in dealer_names or hc_name in dealer_names
            if not hc_name or any(x in hc_name for x in sub_kw) or hc_name in exact_kw or is_dealer:
                continue
                
            mapped_d = get_mapped_dealer(raw_dealer)
            if hc_name not in hc_to_dealer_master:
                hc_to_dealer_master[hc_name] = mapped_d
            if hc_name not in existing_hcs:
                existing_hcs.append(hc_name)

            t_est, t_cnt = clean_val(safe_get(row, 4)), clean_val(safe_get(row, 5))
            t_amt = clean_val(safe_get(row, 15)) 
            t_sales = clean_val(safe_get(row, 18)) 
            # 🚀 M+1 이월매출 X열(23번 인덱스), M+2 익익월매출 Y열(24번 인덱스)로 정확히 수정
            t_next = clean_val(safe_get(row, 23))  
            t_next_next = clean_val(safe_get(row, 24))
            
            is_we = cur_dt.weekday() >= 5 if cur_dt != datetime.min.date() else False
            
            if cur_dt not in daily_data: daily_data[cur_dt] = {}
            if hc_name not in daily_data[cur_dt]: daily_data[cur_dt][hc_name] = {'amt':0, 'est':0, 'cnt':0, 'amt_we':0, 'amt_wd':0, 'amt_move':0}
            daily_data[cur_dt][hc_name]['amt'] += t_amt
            daily_data[cur_dt][hc_name]['est'] += t_est
            daily_data[cur_dt][hc_name]['cnt'] += t_cnt
            if is_we: daily_data[cur_dt][hc_name]['amt_we'] += t_amt
            else: daily_data[cur_dt][hc_name]['amt_wd'] += t_amt
                
            if cur_dt not in raw_snapshots: raw_snapshots[cur_dt] = {}
            if hc_name not in raw_snapshots[cur_dt]: raw_snapshots[cur_dt][hc_name] = {}
            
            raw_snapshots[cur_dt][hc_name]['sales'] = raw_snapshots[cur_dt][hc_name].get('sales', 0) + t_sales
            raw_snapshots[cur_dt][hc_name]['next'] = raw_snapshots[cur_dt][hc_name].get('next', 0) + t_next
            raw_snapshots[cur_dt][hc_name]['next_next'] = raw_snapshots[cur_dt][hc_name].get('next_next', 0) + t_next_next

            if cur_dt not in daily_raw_totals: daily_raw_totals[cur_dt] = {}
            if mapped_d not in daily_raw_totals[cur_dt]: daily_raw_totals[cur_dt][mapped_d] = {'has_normal': False, 'has_online': False, 'sales': 0, 'next': 0, 'next_next': 0, 'online': 0, 'cancel': 0}
            daily_raw_totals[cur_dt][mapped_d]['has_normal'] = True
            daily_raw_totals[cur_dt][mapped_d]['sales'] += t_sales
            daily_raw_totals[cur_dt][mapped_d]['next'] += t_next
            daily_raw_totals[cur_dt][mapped_d]['next_next'] += t_next_next

        elif curr_mode == "입주" and len(row) > 1:
            raw_dealer = safe_get(row, 1)
            raw_hc = safe_get(row, 1) 
            hc_name = clean_str(raw_hc.split('(')[0]) 
            hc_name = re.sub(r'\d+', '', hc_name) 
            
            is_dealer = get_mapped_dealer(hc_name) in dealer_names or hc_name in dealer_names
            if not hc_name or any(x in hc_name for x in sub_kw) or hc_name in exact_kw or is_dealer:
                continue
            
            if hc_name not in hc_to_dealer_master:
                hc_to_dealer_master[hc_name] = get_mapped_dealer(raw_dealer)
            if hc_name not in existing_hcs:
                existing_hcs.append(hc_name)
            
            dm = clean_val(safe_get(row, 12)) + clean_val(safe_get(row, 17))
            if cur_dt not in daily_data: daily_data[cur_dt] = {}
            if hc_name not in daily_data[cur_dt]: daily_data[cur_dt][hc_name] = {'amt':0, 'est':0, 'cnt':0, 'amt_we':0, 'amt_wd':0, 'amt_move':0}
            daily_data[cur_dt][hc_name]['amt_move'] += dm

        elif curr_mode == "점별" and len(row) > 1:
            raw_dealer = safe_get(row, 1)
            raw_hc = safe_get(row, 1) 
            hc_name = clean_str(raw_hc.split('(')[0]) 
            hc_name = re.sub(r'\d+', '', hc_name) 
            
            is_dealer = get_mapped_dealer(hc_name) in dealer_names or hc_name in dealer_names
            if not hc_name or any(x in hc_name for x in sub_kw) or hc_name in exact_kw or is_dealer:
                continue
            
            mapped_d = hc_to_dealer_master.get(hc_name, get_mapped_dealer(raw_dealer))
            if hc_name not in hc_to_dealer_master:
                hc_to_dealer_master[hc_name] = mapped_d
            if hc_name not in existing_hcs:
                existing_hcs.append(hc_name)
            
            t_online = clean_val(safe_get(row, 25)) 
            t_cancel = clean_val(safe_get(row, 37)) + clean_val(safe_get(row, 38)) 
            
            if cur_dt not in raw_snapshots: raw_snapshots[cur_dt] = {}
            if hc_name not in raw_snapshots[cur_dt]: raw_snapshots[cur_dt][hc_name] = {}
            
            raw_snapshots[cur_dt][hc_name]['online'] = raw_snapshots[cur_dt][hc_name].get('online', 0) + t_online
            raw_snapshots[cur_dt][hc_name]['cancel'] = raw_snapshots[cur_dt][hc_name].get('cancel', 0) + t_cancel

            if cur_dt not in daily_raw_totals: daily_raw_totals[cur_dt] = {}
            if mapped_d not in daily_raw_totals[cur_dt]: daily_raw_totals[cur_dt][mapped_d] = {'has_normal': False, 'has_online': False, 'sales': 0, 'next': 0, 'next_next': 0, 'online': 0, 'cancel': 0}
            daily_raw_totals[cur_dt][mapped_d]['has_online'] = True
            daily_raw_totals[cur_dt][mapped_d]['online'] += t_online
            daily_raw_totals[cur_dt][mapped_d]['cancel'] += t_cancel

    valid_dealers = list(set(hc_to_dealer_master.values()))
    av_dates = sorted(list(set(daily_data.keys()).union(set(raw_snapshots.keys()))))
    
    if selected_date not in av_dates:
        valid_dates = [d for d in av_dates if d <= selected_date]
        eff_selected_date = max(valid_dates) if valid_dates else max_date_in_sheet
    else:
        eff_selected_date = selected_date

    def get_snap(target_d, hc, min_d=None):
        res = {'sales':0, 'online':0, 'cancel':0, 'next':0, 'next_next':0}
        for metric in res.keys():
            valid = [d for d in raw_snapshots.keys() if d <= target_d and hc in raw_snapshots[d] and metric in raw_snapshots[d][hc]]
            if min_d: valid = [d for d in valid if d >= min_d]
            if valid:
                eff_d = max(valid)
                res[metric] = raw_snapshots[eff_d][hc][metric]
        return res

    def get_direct_group_snap(target_d, target_dealers, min_d=None):
        res = {'sales':0, 'online':0, 'cancel':0, 'next':0, 'next_next':0}
        
        valid_n_dates = [d for d, dlrs in daily_raw_totals.items() if d <= target_d and any(v['has_normal'] for v in dlrs.values())]
        valid_o_dates = [d for d, dlrs in daily_raw_totals.items() if d <= target_d and any(v['has_online'] for v in dlrs.values())]
        
        if min_d:
            valid_n_dates = [d for d in valid_n_dates if d >= min_d]
            valid_o_dates = [d for d in valid_o_dates if d >= min_d]
            
        eff_n = max(valid_n_dates) if valid_n_dates else None
        eff_o = max(valid_o_dates) if valid_o_dates else None
        
        if eff_n:
            for d_name, vals in daily_raw_totals[eff_n].items():
                if target_dealers is None or d_name in target_dealers:
                    res['sales'] += vals['sales']
                    res['next'] += vals['next']
                    res['next_next'] += vals['next_next']
        if eff_o:
            for d_name, vals in daily_raw_totals[eff_o].items():
                if target_dealers is None or d_name in target_dealers:
                    res['online'] += vals['online']
                    res['cancel'] += vals['cancel']
        return res

    def get_single_hc_snap(target_d, hc, min_d=None):
        res = {'sales':0, 'online':0, 'cancel':0, 'next':0, 'next_next':0}
        valid_n = [d for d, hcs in raw_snapshots.items() if d <= target_d and any('sales' in m for m in hcs.values())]
        valid_o = [d for d, hcs in raw_snapshots.items() if d <= target_d and any('online' in m for m in hcs.values())]
        if min_d:
            valid_n = [d for d in valid_n if d >= min_d]
            valid_o = [d for d in valid_o if d >= min_d]
        eff_n = max(valid_n) if valid_n else None
        eff_o = max(valid_o) if valid_o else None
        if eff_n and hc in raw_snapshots[eff_n]:
            res['sales'] = raw_snapshots[eff_n][hc].get('sales', 0)
            res['next'] = raw_snapshots[eff_n][hc].get('next', 0)
            res['next_next'] = raw_snapshots[eff_n][hc].get('next_next', 0)
        if eff_o and hc in raw_snapshots[eff_o]:
            res['online'] = raw_snapshots[eff_o][hc].get('online', 0)
            res['cancel'] = raw_snapshots[eff_o][hc].get('cancel', 0)
        return res

    def calc_weekly_net_increments(target_hcs, target_dealers=None, is_single_hc=False):
        w_res = [new_d() for _ in range(8)]
        for i in range(8):
            s_dt = trend_ranges[i][0].date()
            e_dt = trend_ranges[i][1].date()
            
            curr = s_dt
            while curr <= e_dt:
                if curr in daily_data:
                    for hc in target_hcs:
                        if hc in daily_data[curr]:
                            d_val = daily_data[curr][hc]
                            w_res[i]['amt'] += d_val['amt']
                            w_res[i]['est'] += d_val['est']
                            w_res[i]['cnt'] += d_val['cnt']
                            w_res[i]['amt_we'] += d_val['amt_we']
                            w_res[i]['amt_wd'] += d_val['amt_wd']
                            w_res[i]['amt_move'] += d_val['amt_move']
                curr += timedelta(days=1)
                
            snap_fn = (lambda d, md: get_single_hc_snap(d, target_hcs[0], md)) if is_single_hc else (lambda d, md: get_direct_group_snap(d, target_dealers, md))

            if s_dt.month == e_dt.month:
                m_start = s_dt.replace(day=1)
                snap_end = snap_fn(e_dt, m_start)
                snap_prev = snap_fn(s_dt - timedelta(days=1), m_start)
                
                w_res[i]['sales'] = snap_end['sales'] - snap_prev['sales']
                w_res[i]['online'] = snap_end['online'] - snap_prev['online']
                w_res[i]['cancel'] = snap_end['cancel'] - snap_prev['cancel']
                w_res[i]['next_sales'] = snap_end['next'] - snap_prev['next']
            else:
                m1_end = (s_dt.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                m1_start = s_dt.replace(day=1)
                m2_start = e_dt.replace(day=1)
                
                snap_m1_end = snap_fn(m1_end, m1_start)
                snap_m1_prev = snap_fn(s_dt - timedelta(days=1), m1_start)
                snap_m2_end = snap_fn(e_dt, m2_start)
                snap_m2_start = snap_fn(m2_start, m2_start)
                
                # [공식 1] 당월 매출 = (9.30 S총합 - 9.27 S총합) + (10.4 S총합 - 9.30 X총합(M+1))
                m1_sales = snap_m1_end['sales'] - snap_m1_prev['sales']
                m2_sales = snap_m2_end['sales'] - snap_m1_end['next']
                w_res[i]['sales'] = m1_sales + m2_sales
                
                # [공식 2] 온라인/취소 = (9.30 Z총합 - 9.27 Z총합) + (1일이 마지막날이면 0, 아니면 10.4 Z총합 - 10.1 Z총합)
                m1_online = snap_m1_end['online'] - snap_m1_prev['online']
                m1_cancel = snap_m1_end['cancel'] - snap_m1_prev['cancel']
                if e_dt.day == 1:
                    m2_online, m2_cancel = 0, 0
                else:
                    m2_online = snap_m2_end['online'] - snap_m2_start['online']
                    m2_cancel = snap_m2_end['cancel'] - snap_m2_start['cancel']
                w_res[i]['online'] = m1_online + m2_online
                w_res[i]['cancel'] = m1_cancel + m2_cancel
                
                # [공식 3] 이월매출 = (9.30 X총합 - 9.27 X총합) + (10.4 X총합 - 9.30 Y총합(M+2))
                m1_next = snap_m1_end['next'] - snap_m1_prev['next']
                m2_next = snap_m2_end['next'] - snap_m1_end['next_next']
                w_res[i]['next_sales'] = m1_next + m2_next
        return w_res

    def new_d(): return {'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0, 'online':0, 'cancel':0}
    
    month_labels = [f"📊 [월마감] {y%100}년 {m}월" for y, m in sorted(list(set((d.year, d.month) for d in av_dates)))]
    mtd_labels = ['🌟 [당일기준] 당월 누적', '🌟 [당일기준] 전월 누적', '🌟 [당일기준] 전전월 누적', '🌟 [당일기준] 전년 누적']
    
    trend_hc_w = {hc: calc_weekly_net_increments([hc], is_single_hc=True) for hc in existing_hcs}
    trend_dlr_w = {d: calc_weekly_net_increments([hc for hc in existing_hcs if hc_to_dealer_master.get(hc) == d], target_dealers=[d]) for d in valid_dealers}
    trend_reg_w = {reg: calc_weekly_net_increments([hc for hc in existing_hcs if hc_to_dealer_master.get(hc) in dlrs], target_dealers=dlrs) for reg, dlrs in REGION_MAP.items()}
    trend_tot_w = calc_weekly_net_increments(existing_hcs, target_dealers=None)

    trend_hc_m = {hc: {lbl: new_d() for lbl in month_labels} for hc in existing_hcs}
    trend_hc_mtd = {hc: {lbl: new_d() for lbl in mtd_labels} for hc in existing_hcs}

    t_mtd = eff_selected_date
    t_prev1 = get_prev_month_date(eff_selected_date, 1)
    t_prev2 = get_prev_month_date(eff_selected_date, 2)
    try: t_prev_y = datetime(eff_selected_date.year - 1, eff_selected_date.month, eff_selected_date.day).date()
    except: t_prev_y = datetime(eff_selected_date.year - 1, eff_selected_date.month, eff_selected_date.day - 1).date()
    
    mtd_target_dates = {
        '🌟 [당일기준] 당월 누적': t_mtd, '🌟 [당일기준] 전월 누적': t_prev1,
        '🌟 [당일기준] 전전월 누적': t_prev2, '🌟 [당일기준] 전년 누적': t_prev_y
    }
    
    for hc in existing_hcs:
        for lbl, t_date in mtd_target_dates.items():
            m_start = t_date.replace(day=1)
            snap = get_snap(t_date, hc, min_d=m_start)
            trend_hc_mtd[hc][lbl]['sales'] = snap['sales']
            trend_hc_mtd[hc][lbl]['online'] = snap['online']
            trend_hc_mtd[hc][lbl]['cancel'] = snap['cancel']
            trend_hc_mtd[hc][lbl]['next_sales'] = snap['next']
            
            curr = m_start
            while curr <= t_date:
                if curr in daily_data and hc in daily_data[curr]:
                    d_val = daily_data[curr]
                    trend_hc_mtd[hc][lbl]['amt'] += d_val[hc]['amt']
                    trend_hc_mtd[hc][lbl]['est'] += d_val[hc]['est']
                    trend_hc_mtd[hc][lbl]['cnt'] += d_val[hc]['cnt']
                    trend_hc_mtd[hc][lbl]['amt_we'] += d_val[hc]['amt_we']
                    trend_hc_mtd[hc][lbl]['amt_wd'] += d_val[hc]['amt_wd']
                    trend_hc_mtd[hc][lbl]['amt_move'] += d_val[hc]['amt_move']
                curr += timedelta(days=1)

    for hc in existing_hcs:
        for y, m in set((d.year, d.month) for d in av_dates):
            lbl = f"📊 [월마감] {y%100}년 {m}월"
            m_start = datetime(y, m, 1).date()
            m_end = (m_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            
            snap = get_snap(m_end, hc, min_d=m_start)
            trend_hc_m[hc][lbl]['sales'] = snap['sales']
            trend_hc_m[hc][lbl]['online'] = snap['online']
            trend_hc_m[hc][lbl]['cancel'] = snap['cancel']
            trend_hc_m[hc][lbl]['next_sales'] = snap['next']
            
            curr = m_start
            while curr <= m_end:
                if curr in daily_data and hc in daily_data[curr]:
                    d_val = daily_data[curr]
                    trend_hc_m[hc][lbl]['amt'] += d_val[hc]['amt']
                    trend_hc_m[hc][lbl]['est'] += d_val[hc]['est']
                    trend_hc_m[hc][lbl]['cnt'] += d_val[hc]['cnt']
                    trend_hc_m[hc][lbl]['amt_we'] += d_val[hc]['amt_we']
                    trend_hc_m[hc][lbl]['amt_wd'] += d_val[hc]['amt_wd']
                    trend_hc_m[hc][lbl]['amt_move'] += d_val[hc]['amt_move']
                curr += timedelta(days=1)

    trend_dlr_m = {d: {lbl: new_d() for lbl in month_labels} for d in valid_dealers}
    trend_dlr_mtd = {d: {lbl: new_d() for lbl in mtd_labels} for d in valid_dealers}
    trend_tot_m = {lbl: new_d() for lbl in month_labels}
    trend_tot_mtd = {lbl: new_d() for lbl in mtd_labels}
    
    keys_to_sum = ['sales', 'next_sales', 'est', 'cnt', 'amt', 'amt_we', 'amt_wd', 'amt_move', 'online', 'cancel']
    for hc in existing_hcs:
        md = hc_to_dealer_master.get(hc, "기타")
        if md in valid_dealers:
            for lbl in month_labels:
                for k in keys_to_sum:
                    trend_dlr_m[md][lbl][k] += trend_hc_m[hc][lbl][k]
                    trend_tot_m[lbl][k] += trend_hc_m[hc][lbl][k]
            for lbl in mtd_labels:
                for k in keys_to_sum:
                    trend_dlr_mtd[md][lbl][k] += trend_hc_mtd[hc][lbl][k]
                    trend_tot_mtd[lbl][k] += trend_hc_mtd[hc][lbl][k]

    trend_reg_m = {k: {lbl: new_d() for lbl in month_labels} for k in REGION_MAP.keys()}
    trend_reg_mtd = {k: {lbl: new_d() for lbl in mtd_labels} for k in REGION_MAP.keys()}
    
    for reg, dlrs in REGION_MAP.items():
        for d in dlrs:
            dm = trend_dlr_m.get(d, {lbl: new_d() for lbl in month_labels})
            dmtd = trend_dlr_mtd.get(d, {lbl: new_d() for lbl in mtd_labels})
            for lbl in month_labels:
                for k in keys_to_sum: trend_reg_m[reg][lbl][k] += dm[lbl][k]
            for lbl in mtd_labels:
                for k in keys_to_sum: trend_reg_mtd[reg][lbl][k] += dmtd[lbl][k]

    acts = {hc: {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for hc in existing_hcs}
    month_acts = {hc: {'amt': 0, 'est': 0, 'cnt': 0} for hc in existing_hcs}
    rdm = {d: {'amt': 0, 'est': 0, 'cnt': 0} for d in valid_dealers}
    rdw = {d: {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for d in valid_dealers}
    latest_sales_dict = {}

    for hc in existing_hcs:
        md = hc_to_dealer_master.get(hc, "기타")
        latest_sales_dict[hc] = get_snap(eff_selected_date, hc, min_d=eff_selected_date.replace(day=1)).get('sales', 0.0)
        
        for wk_lbl, d_str in date_headers.items():
            dt_match = re.findall(r'\d+', d_str)
            if len(dt_match) >= 4:
                try:
                    s_dt = datetime(cy, int(dt_match[0]), int(dt_match[1])).date()
                    e_dt = datetime(cy + (1 if int(dt_match[0])==12 and int(dt_match[2])==1 else 0), int(dt_match[2]), int(dt_match[3])).date()
                    curr = s_dt
                    while curr <= e_dt:
                        if curr in daily_data and hc in daily_data[curr]:
                            d_val = daily_data[curr][hc]
                            acts[hc][wk_lbl]['amt'] += d_val['amt']
                            acts[hc][wk_lbl]['est'] += d_val['est']
                            acts[hc][wk_lbl]['cnt'] += d_val['cnt']
                            if md in valid_dealers:
                                rdw[md][wk_lbl]['amt'] += d_val['amt']
                                rdw[md][wk_lbl]['est'] += d_val['est']
                                rdw[md][wk_lbl]['cnt'] += d_val['cnt']
                        curr += timedelta(days=1)
                except: pass
                
        m_start = eff_selected_date.replace(day=1)
        curr = m_start
        while curr <= eff_selected_date:
            if curr in daily_data and hc in daily_data[curr]:
                d_val = daily_data[curr][hc]
                month_acts[hc]['amt'] += d_val['amt']
                month_acts[hc]['est'] += d_val['est']
                month_acts[hc]['cnt'] += d_val['cnt']
                if md in valid_dealers:
                    rdm[md]['amt'] += d_val['amt']
                    rdm[md]['est'] += d_val['est']
                    rdm[md]['cnt'] += d_val['cnt']
            curr += timedelta(days=1)

    dealer_active_hcs, dealer_sales_sum_active = {}, {}
    for d, hc, tgt in hc_info_raw:
        hc_c = clean_str(hc)
        if hc_c not in EXCLUDED_HCS:
            if d not in dealer_active_hcs: dealer_active_hcs[d] = []
            dealer_active_hcs[d].append(hc_c)
            
    for d, hc, tgt in hc_info_raw:
        al = dealer_active_hcs.get(d, [])
        if not al or clean_str(hc) in al: dealer_sales_sum_active[d] = dealer_sales_sum_active.get(d, 0.0) + tgt

    final_hc_sales_tgt, targets = {}, {}
    for d, hc, tgt in hc_info_raw:
        hc_c = clean_str(hc)
        wt = (tgt / dealer_sales_sum_active.get(d, 1.0)) if hc_c not in EXCLUDED_HCS and dealer_sales_sum_active.get(d, 0) > 0 else 0.0
        final_hc_sales_tgt[hc_c] = dealer_sales_sum.get(d, 0.0) * wt
        
        targets[hc_c] = {}
        for wk in week_keys:
            d_amt = dealer_targets.get(d, {}).get(wk, {}).get('amt', 0) * wt
            d_est = dealer_targets.get(d, {}).get(wk, {}).get('est', 0) * wt
            d_cnt = dealer_targets.get(d, {}).get(wk, {}).get('cnt', 0) * wt
            targets[hc_c][wk] = {'amt': d_amt, 'est': d_est, 'cnt': d_cnt}

    col_tuples = [
        ('기본정보', '대리점', '대리점'), ('기본정보', 'HC명', 'HC명'), 
        ('🎯 당월매출', '인별매출(천)', '목표'), ('🎯 당월매출', '인별매출(천)', 'ACT'), ('🎯 당월매출', '인별매출(천)', '달성율(%)'), 
        ('🌟 당월 합계', '계약액(천)', '목표'), ('🌟 당월 합계', '계약액(천)', 'ACT'), ('🌟 당월 합계', '계약액(천)', '달성율(%)'), 
        ('🌟 당월 합계', '견적건', '목표'), ('🌟 당월 합계', '견적건', 'ACT'), ('🌟 당월 합계', '견적건', '달성율(%)'), 
        ('🌟 당월 합계', '계약건', '목표'), ('🌟 당월 합계', '계약건', 'ACT'), ('🌟 당월 합계', '계약건', '달성율(%)')
    ]
    
    for wk in week_keys:
        wl = f"{wk} ({date_headers.get(wk, '')})"
        for k in ['계약액(천)', '견적건', '계약건']:
            col_tuples.extend([(wl, k, '목표'), (wl, k, 'ACT'), (wl, k, '달성율(%)')])
        
    columns = pd.MultiIndex.from_tuples(col_tuples, names=['주차', '항목', '구분'])
    rows = []
    
    for hc_c in existing_hcs:
        if hc_c in EXCLUDED_HCS: continue
        d = hc_to_dealer_master.get(hc_c, "기타")
        tgt = final_hc_sales_tgt.get(hc_c, 0.0)
        ma = month_acts.get(hc_c, {'amt':0,'est':0,'cnt':0})
        sa = latest_sales_dict.get(hc_c, 0.0)
        
        if tgt == 0.0 and ma['amt'] == 0 and ma['est'] == 0 and ma['cnt'] == 0 and sa == 0: continue
        
        tgt_amt_sum = sum([targets.get(hc_c, {}).get(wk, {}).get('amt', 0) for wk in week_keys])
        tgt_est_sum = sum([targets.get(hc_c, {}).get(wk, {}).get('est', 0) for wk in week_keys])
        tgt_cnt_sum = sum([targets.get(hc_c, {}).get(wk, {}).get('cnt', 0) for wk in week_keys])
        
        r_d = [
            d, hc_c, tgt, sa, 0.0, 
            tgt_amt_sum, ma['amt'], 0.0, 
            tgt_est_sum, ma['est'], 0.0, 
            tgt_cnt_sum, ma['cnt'], 0.0
        ]
        
        for wk in week_keys:
            t = targets.get(hc_c, {}).get(wk, {'amt':0,'est':0,'cnt':0})
            a = acts.get(hc_c, {}).get(wk, {'amt':0,'est':0,'cnt':0})
            r_d.extend([t['amt'], a['amt'], 0.0, t['est'], a['est'], 0.0, t['cnt'], a['cnt'], 0.0])
        rows.append(r_d)

    df = pd.DataFrame(rows, columns=columns)
    
    for c in df.columns[2:]:
        if c[2] == '달성율(%)': 
            tgt_col = pd.to_numeric(df[(c[0], c[1], '목표')], errors='coerce').fillna(0)
            act_col = pd.to_numeric(df[(c[0], c[1], 'ACT')], errors='coerce').fillna(0)
            df[c] = np.where(tgt_col > 0, (act_col / tgt_col * 100).round(0), 0)
    
    tp = {'W': {'hc': trend_hc_w, 'dlr': trend_dlr_w, 'tot': trend_tot_w, 'reg': trend_reg_w}, 'M': {'hc': trend_hc_m, 'dlr': trend_dlr_m, 'tot': trend_tot_m, 'reg': trend_reg_m}, 'MTD': {'hc': trend_hc_mtd, 'dlr': trend_dlr_mtd, 'tot': trend_tot_mtd, 'reg': trend_reg_mtd}}
    ctw = date_to_target_week.get((eff_selected_date.month, eff_selected_date.day), week_keys[-1] if week_keys else '1주차')
    return df, date_headers, hc_to_dealer_master, rdm, rdw, week_keys, tp, ctw, month_labels, mtd_labels, eff_selected_date


if all_daily_data:
    (df_raw, date_headers, hc_to_dealer_master, rdm, rdw, 
     week_keys_list, trend_pack, CURRENT_TABLE_WEEK, month_labels, mtd_labels, eff_selected_date) = process_vdt_data(all_targets, all_daily_data, selected_date)

    def calc_subtotals(df, rdm, rdw):
        if df.empty: return df
        rr = []
        d_c, h_c = ('기본정보', '대리점', '대리점'), ('기본정보', 'HC명', 'HC명')
        for d, grp in df.groupby(d_c, sort=False):
            for _, r in grp.iterrows(): rr.append(r)
            stot = grp.select_dtypes(include=[np.number]).sum()
            stot[d_c], stot[h_c] = d, "합계"
            if d in rdm:
                stot[('🌟 당월 합계', '계약액(천)', 'ACT')] = rdm[d]['amt']
                stot[('🌟 당월 합계', '견적건', 'ACT')] = rdm[d]['est']
                stot[('🌟 당월 합계', '계약건', 'ACT')] = rdm[d]['cnt']
            if d in rdw:
                for wk, wd in rdw[d].items():
                    wc = [c[0] for c in df.columns if wk in c[0]]
                    if wc:
                        w = wc[0]
                        stot[(w, '계약액(천)', 'ACT')] = wd['amt']
                        stot[(w, '견적건', 'ACT')] = wd['est']
                        stot[(w, '계약건', 'ACT')] = wd['cnt']
            
            for c in df.columns[2:]:
                if c[2] == '달성율(%)': 
                    tgt_val = float(stot.get((c[0],c[1],'목표'), 0) or 0)
                    act_val = float(stot.get((c[0],c[1],'ACT'), 0) or 0)
                    stot[c] = round((act_val / tgt_val * 100), 0) if tgt_val > 0 else 0.0
            rr.append(pd.Series(stot))

        gt = df.select_dtypes(include=[np.number]).sum()
        gt[d_c], gt[h_c] = "🌟 총계", "🌟 총계"
        gt[('🌟 당월 합계', '계약액(천)', 'ACT')] = sum([rdm.get(d, {}).get('amt', 0) for d in df[d_c].unique()])
        gt[('🌟 당월 합계', '견적건', 'ACT')] = sum([rdm.get(d, {}).get('est', 0) for d in df[d_c].unique()])
        gt[('🌟 당월 합계', '계약건', 'ACT')] = sum([rdm.get(d, {}).get('cnt', 0) for d in df[d_c].unique()])
        
        sd = df[d_c].unique()[0] if not df.empty else None
        if sd and sd in rdw:
            for wk in rdw[sd].keys():
                wc = [c[0] for c in df.columns if wk in c[0]]
                if wc:
                    w = wc[0]
                    gt[(w, '계약액(천)', 'ACT')] = sum([rdw.get(d, {}).get(wk, {}).get('amt', 0) for d in df[d_c].unique()])
                    gt[(w, '견적건', 'ACT')] = sum([rdw.get(d, {}).get(wk, {}).get('est', 0) for d in df[d_c].unique()])
                    gt[(w, '계약건', 'ACT')] = sum([rdw.get(d, {}).get(wk, {}).get('cnt', 0) for d in df[d_c].unique()])

        for c in df.columns[2:]:
            if c[2] == '달성율(%)': 
                tgt_val = float(gt.get((c[0],c[1],'목표'), 0) or 0)
                act_val = float(gt.get((c[0],c[1],'ACT'), 0) or 0)
                gt[c] = round((act_val / tgt_val * 100), 0) if tgt_val > 0 else 0.0
        rr.append(pd.Series(gt))
        return pd.DataFrame(rr)

    if not df_raw.empty:
        final_df = calc_subtotals(df_raw, rdm, rdw)
        
        def set_view(target):
            st.session_state['view_target'] = target
            st.session_state['hc_selector'] = "✨ 인원별 상세 실적 (선택 시 우선 적용)"

        def on_hc_select():
            if st.session_state['hc_selector'] != "✨ 인원별 상세 실적 (선택 시 우선 적용)":
                st.session_state['view_target'] = st.session_state['hc_selector']

        def btn_type(t): return "primary" if st.session_state.get('view_target') == t else "secondary"
            
        vt = st.session_state['view_target']
        
        def get_period_data(label, hc_or_dlr_key):
            if label in trend_labels:
                idx = trend_labels.index(label)
                if vt == "충청호남팀 전체": return trend_pack['W']['tot'][idx]
                elif vt in ["충청팀 통합", "호남팀 통합"]: return trend_pack['W']['reg'][hc_or_dlr_key][idx]
                elif "대리점" in vt: return trend_pack['W']['dlr'].get(hc_or_dlr_key, [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for _ in range(8)])[idx]
                else: return trend_pack['W']['hc'].get(hc_or_dlr_key, [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for _ in range(8)])[idx]
            elif label in month_labels:
                if vt == "충청호남팀 전체": return trend_pack['M']['tot'][label]
                elif vt in ["충청팀 통합", "호남팀 통합"]: return trend_pack['M']['reg'][hc_or_dlr_key][label]
                elif "대리점" in vt: return trend_pack['M']['dlr'].get(hc_or_dlr_key, {lbl: {'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for lbl in month_labels})[label]
                else: return trend_pack['M']['hc'].get(hc_or_dlr_key, {lbl: {'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for lbl in month_labels})[label]
            elif label in mtd_labels:
                if vt == "충청호남팀 전체": return trend_pack['MTD']['tot'][label]
                elif vt in ["충청팀 통합", "호남팀 통합"]: return trend_pack['MTD']['reg'][hc_or_dlr_key][label]
                elif "대리점" in vt: return trend_pack['MTD']['dlr'].get(hc_or_dlr_key, {lbl: {'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for lbl in mtd_labels})[label]
                else: return trend_pack['MTD']['hc'].get(hc_or_dlr_key, {lbl: {'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for lbl in mtd_labels})[label]
            return {'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0}
        
        if vt == "충청호남팀 전체":
            ct, data_key = "충청호남팀 전체", "tot"
        elif vt in ["충청팀 통합", "호남팀 통합"]:
            ct, data_key = f"{vt}", "충청상권" if vt == "충청팀 통합" else "호남상권"
        elif "대리점" in vt: 
            td = vt.replace(" 대리점", "")
            ct, data_key = f"{td} 대리점", td
        else: 
            thc = vt.replace("👤 ", "").split(" - ")[1]
            ct, data_key = f"{thc} 님", thc

        st.markdown("#### 💡 **주/월 종합지표 비교**")
        
        c1, c2, c3 = st.columns([2.5, 4.5, 4.5])
        with c1: 
            st.markdown("<div style='text-align:center; padding-top:28px; font-weight:900; color:#1e293b; font-size:14px;'>데이터 비교 선택 ➡️</div>", unsafe_allow_html=True)
        with c3: 
            st.markdown("<div style='font-size:15px; font-weight:900; color:#dc2626; margin-bottom:4px;'>➡️ (조회 기준)</div>", unsafe_allow_html=True)
            sel_curr = st.selectbox("조회 기준", options=curr_options, index=curr_options.index(st.session_state.get('wow_curr', curr_options[0])) if st.session_state.get('wow_curr') in curr_options else 0, label_visibility="collapsed")
            st.session_state['wow_curr'] = sel_curr

        if sel_curr == '🌟 [당일기준] 당월 누적':
            prev_options = ['🌟 [당일기준] 전월 누적', '🌟 [당일기준] 전전월 누적', '🌟 [당일기준] 전년 누적']
        else:
            prev_options = all_normal_options

        if st.session_state.get('wow_prev') not in prev_options:
            st.session_state['wow_prev'] = prev_options[0]

        with c2: 
            st.markdown("<div style='font-size:15px; font-weight:900; color:#64748b; margin-bottom:4px;'>⬅️ (비교 대상)</div>", unsafe_allow_html=True)
            sel_prev = st.selectbox("비교 기준", options=prev_options, index=prev_options.index(st.session_state['wow_prev']), label_visibility="collapsed")
            st.session_state['wow_prev'] = sel_prev
            
        def td_cell(val, p_val, is_unit=False, is_rate=False):
            delta = val - p_val
            if is_rate: 
                v_s = f"+{delta:.1f}p%" if delta > 0 else f"{delta:.1f}p%"
            else:
                pct_str = ""
                if p_val != 0:
                    pct_val = (delta / abs(p_val)) * 100
                    pct_str = f" <span style='font-size:11px; letter-spacing:-0.5px;'>({'+' if pct_val>0 else ''}{pct_val:.0f}%)</span>"
                
                if is_unit: v_s = f"+{int(delta):,}만{pct_str}" if delta > 0 else f"{int(delta):,}만{pct_str}"
                else: v_s = f"+{delta:,.0f}{pct_str}" if delta > 0 else f"{delta:,.0f}{pct_str}"
                
            if delta > 0: return f"<td style='text-align:center; background-color:#f8fafc;'><span class='wow-up'>{v_s} 🔺</span></td>"
            elif delta < 0: return f"<td style='text-align:center; background-color:#f8fafc;'><span class='wow-down'>{v_s} 🔻</span></td>"
            return "<td style='text-align:center; background-color:#f8fafc;'><span class='wow-same'>-</span></td>"

        def td_val(v, is_pct=False, is_unit=False, is_tgt=False, bg=""):
            s = f"{v:.1f}%" if is_pct else (f"{int(v):,}" if is_unit else f"{v:,.0f}")
            c = "color: #1e3a8a; font-weight: 900;" if is_tgt else "font-weight: 600;"
            b = f"background-color:{bg};" if bg else ""
            return f"<td style='text-align:center; {c} {b}'>{s}</td>"
            
        def td_val_str(v_str, is_tgt=False, bg=""):
            c = "color: #1e3a8a; font-weight: 900;" if is_tgt else "font-weight: 600;"
            b = f"background-color:{bg};" if bg else ""
            return f"<td style='text-align:center; {c} {b}'>{v_str}</td>"

        pv = get_period_data(sel_prev, data_key)
        tv = get_period_data(sel_curr, data_key)
        
        pa, ta, ps, ts = pv.get('amt',0), tv.get('amt',0), pv.get('sales',0), tv.get('sales',0)
        po, to = pv.get('online',0), tv.get('online',0)
        pe, te, pc, tc = pv.get('est',0), tv.get('est',0), pv.get('cnt',0), tv.get('cnt',0)
        pm, tm = pv.get('amt_move',0), tv.get('amt_move',0)
        p_can, t_can = pv.get('cancel',0), tv.get('cancel',0)
        
        pw, tw = pa - pm, ta - tm
        pr, tr = (pc/pe*100) if pe>0 else 0, (tc/te*100) if te>0 else 0
        pu, tu = (pa/(pc*10)) if pc>0 else 0, (ta/(tc*10)) if tc>0 else 0
        
        po_pct = f" <span style='font-size:12px; font-weight:900; color:#0284c7;'>({po/ps*100:.0f}%)</span>" if ps > 0 else " <span style='font-size:12px; font-weight:900; color:#64748b;'>(0%)</span>"
        to_pct = f" <span style='font-size:12px; font-weight:900; color:#0284c7;'>({to/ts*100:.0f}%)</span>" if ts > 0 else " <span style='font-size:12px; font-weight:900; color:#64748b;'>(0%)</span>"

        curr_is_week = "▪️" in str(sel_curr)
        prev_is_week = "▪️" in str(sel_prev)

        disp_ps = "<td style='text-align:center; color:#94a3b8; background-color:#f1f5f9;'>-</td>" if prev_is_week else td_val(ps)
        disp_po = "<td style='text-align:center; color:#94a3b8; background-color:#f1f5f9;'>-</td>" if prev_is_week else td_val_str(f"{po:,.0f}{po_pct}")
        
        disp_ts = "<td style='text-align:center; color:#94a3b8; background-color:#f1f5f9;'>-</td>" if curr_is_week else td_val(ts, is_tgt=True)
        disp_to = "<td style='text-align:center; color:#94a3b8; background-color:#f1f5f9;'>-</td>" if curr_is_week else td_val_str(f"{to:,.0f}{to_pct}", is_tgt=True)
        
        disp_diff_s = "<td style='text-align:center; color:#94a3b8; background-color:#f1f5f9;'>-</td>" if (curr_is_week or prev_is_week) else td_cell(ts, ps)
        disp_diff_o = "<td style='text-align:center; color:#94a3b8; background-color:#f1f5f9;'>-</td>" if (curr_is_week or prev_is_week) else td_cell(to, po)

        html_wow = '''
        <table class="wow-table" style="width: 100%; border: 2px solid #94a3b8; border-radius: 8px; overflow: hidden; margin-top: 5px;">
            <thead><tr style="background-color: #1e293b; color: white;">
            <th style="padding: 10px; font-size: 13px; border-right: 2px solid #94a3b8; width:14%;">조직<br><span style="font-size:11px; color:#cbd5e1;">({CT})</span></th>
            <th style="padding: 10px;">💰 총 계약액<br>(천원)</th><th style="padding: 10px;">💰 총 매출액<br>(천원)</th><th style="padding: 10px;">💻 온라인매출<br>(천원)</th>
            <th style="padding: 10px;">📝 견적건<br>(건)</th><th style="padding: 10px;">🤝 계약건<br>(건)</th>
            <th style="padding: 10px; background-color:#334155;">🚶 워크인 계약액<br>(천원)</th><th style="padding: 10px; background-color:#334155;">🏠 입주 계약액<br>(천원)</th>
            <th style="padding: 10px;">📊 계약률<br>(%)</th><th style="padding: 10px;">💸 객단가<br>(만원)</th><th style="padding: 10px;">📉 총 취소액<br>(천원)</th></tr></thead><tbody>
            <tr style='background-color: #f8fafc;'><td style='text-align:center; font-weight:900; border-right:2px solid #94a3b8; color:#64748b;'>{SEL_PREV}</td>
            {TD_PA} {DISP_PS} {DISP_PO} {TD_PE} {TD_PC} {TD_PW} {TD_PM} {TD_PR} {TD_PU} {TD_PCAN} </tr>
            <tr style='background-color: white;'><td style='text-align:center; font-weight:900; color:#1e3a8a; border-right:2px solid #94a3b8;'>{SEL_CURR}</td>
            {TD_TA} {DISP_TS} {DISP_TO} {TD_TE} {TD_TC} {TD_TW} {TD_TM} {TD_TR} {TD_TU} {TD_TCAN} </tr>
            <tr style='background-color: #fef2f2;'><td style='text-align:center; font-weight:900; color:#b91c1c; border-right:2px solid #94a3b8;'>지표 간 증감</td>
            {DIFF_A} {DIFF_S} {DIFF_O} {DIFF_E} {DIFF_C} {DIFF_W} {DIFF_M} {DIFF_R} {DIFF_U} {DIFF_CAN} </tr></tbody></table>
        '''
        
        html_wow = html_wow.replace("{CT}", ct).replace("{SEL_PREV}", str(sel_prev)).replace("{SEL_CURR}", str(sel_curr))
        html_wow = html_wow.replace("{TD_PA}", td_val(pa)).replace("{DISP_PS}", disp_ps).replace("{DISP_PO}", disp_po).replace("{TD_PE}", td_val(pe)).replace("{TD_PC}", td_val(pc))
        html_wow = html_wow.replace("{TD_PW}", td_val(pw,bg='#f1f5f9')).replace("{TD_PM}", td_val(pm,bg='#f1f5f9')).replace("{TD_PR}", td_val(pr,True)).replace("{TD_PU}", td_val(pu,False,True)).replace("{TD_PCAN}", td_val(p_can))
        html_wow = html_wow.replace("{TD_TA}", td_val(ta,is_tgt=True)).replace("{DISP_TS}", disp_ts).replace("{DISP_TO}", disp_to).replace("{TD_TE}", td_val(te,is_tgt=True)).replace("{TD_TC}", td_val(tc,is_tgt=True))
        html_wow = html_wow.replace("{TD_TW}", td_val(tw,is_tgt=True,bg='#f1f5f9')).replace("{TD_TM}", td_val(tm,is_tgt=True,bg='#f1f5f9')).replace("{TD_TR}", td_val(tr,True,is_tgt=True)).replace("{TD_TU}", td_val(tu,False,True,is_tgt=True)).replace("{TD_TCAN}", td_val(t_can,is_tgt=True))
        html_wow = html_wow.replace("{DIFF_A}", td_cell(ta,pa)).replace("{DIFF_S}", disp_diff_s).replace("{DIFF_O}", disp_diff_o).replace("{DIFF_E}", td_cell(te,pe)).replace("{DIFF_C}", td_cell(tc,pc))
        html_wow = html_wow.replace("{DIFF_W}", td_cell(tw,pw)).replace("{DIFF_M}", td_cell(tm,pm)).replace("{DIFF_R}", td_cell(tr,pr,is_rate=True)).replace("{DIFF_U}", td_cell(tu,pu,is_unit=True)).replace("{DIFF_CAN}", td_cell(t_can,p_can))
        
        st.markdown(html_wow, unsafe_allow_html=True)
        st.markdown("---")

        st.markdown("#### 🔎 **실적 조회 (조직 및 인원 선택)**")
        st.markdown('<div id="org-buttons"></div>', unsafe_allow_html=True)
        
        c_o = st.columns([12, 2, 12, 9, 9, 9, 9, 2, 12, 9, 9, 9, 30])
        
        with c_o[0]: 
            st.button("I 전체통합" if vt != "충청호남팀 전체" else "✅ 전체통합", type=btn_type("충청호남팀 전체"), on_click=set_view, args=("충청호남팀 전체",), use_container_width=True)
        with c_o[1]: 
            st.markdown("<div style='text-align:center; padding-top:5px; color:#cbd5e1; font-weight:bold; font-size:16px;'>|</div>", unsafe_allow_html=True)
        with c_o[2]: 
            st.button("I 충청통합" if vt != "충청팀 통합" else "✅ 충청통합", type=btn_type("충청팀 통합"), on_click=set_view, args=("충청팀 통합",), use_container_width=True)
        with c_o[3]: 
            st.button("둔산" if vt != "둔산 대리점" else "✅ 둔산", type=btn_type("둔산 대리점"), on_click=set_view, args=("둔산 대리점",), use_container_width=True)
        with c_o[4]: 
            st.button("세종" if vt != "세종 대리점" else "✅ 세종", type=btn_type("세종 대리점"), on_click=set_view, args=("세종 대리점",), use_container_width=True)
        with c_o[5]: 
            st.button("목포" if vt != "목포 대리점" else "✅ 목포", type=btn_type("목포 대리점"), on_click=set_view, args=("목포 대리점",), use_container_width=True)
        with c_o[6]: 
            st.button("충주" if vt != "충주 대리점" else "✅ 충주", type=btn_type("충주 대리점"), on_click=set_view, args=("충주 대리점",), use_container_width=True)
        with c_o[7]: 
            st.markdown("<div style='text-align:center; padding-top:5px; color:#cbd5e1; font-weight:bold; font-size:16px;'>|</div>", unsafe_allow_html=True)
        with c_o[8]: 
            st.button("I 호남통합" if vt != "호남팀 통합" else "✅ 호남통합", type=btn_type("호남팀 통합"), on_click=set_view, args=("호남팀 통합",), use_container_width=True)
        with c_o[9]: 
            st.button("광양" if vt != "광양 대리점" else "✅ 광양", type=btn_type("광양 대리점"), on_click=set_view, args=("광양 대리점",), use_container_width=True)
        with c_o[10]: 
            st.button("익산" if vt != "익산 대리점" else "✅ 익산", type=btn_type("익산 대리점"), on_click=set_view, args=("익산 대리점",), use_container_width=True)
        with c_o[11]: 
            st.button("여수" if vt != "여수 대리점" else "✅ 여수", type=btn_type("여수 대리점"), on_click=set_view, args=("여수 대리점",), use_container_width=True)
        with c_o[12]:
            hl = ["✨ 인원별 상세 실적 (선택 시 우선 적용)"] + [f"👤 {r[('기본정보','대리점','대리점')]} - {r[('기본정보','HC명','HC명')]}" for _, r in final_df.iterrows() if r[('기본정보','HC명','HC명')] not in ["🌟 총계","합계","상권합계"] and r[('기본정보','HC명','HC명')] not in EXCLUDED_HCS]
            st.selectbox("인원선택", options=hl, key='hc_selector', on_change=on_hc_select, label_visibility="collapsed")
        st.markdown("---")
                
        def toggle_state(key): st.session_state[key] = not st.session_state[key]

        t_c1, t_c2 = st.columns([6, 4])
        with t_c1: st.markdown(f"#### 📈 {ct} 실적 추이 그래프")
        with t_c2:
            st.markdown("<div class='mode-toggle'>", unsafe_allow_html=True)
            vm = st.radio("보기 기준", ["주간 추이 (최근 8주)", "월간 누적 추이 (자동갱신)", "🔥 최근 4주 목표 vs 실적"], horizontal=True, label_visibility="collapsed", key='view_mode_selector')
            st.markdown("</div>", unsafe_allow_html=True)
            
        is_m = "월간" in vm
        
        if "최근 4주" in vm:
            last_4_keys = week_keys_list[-4:] if len(week_keys_list) >= 4 else week_keys_list
            
            t_amts, a_amts = [], []
            search_key = "🌟 총계" if "전체" in vt else ("합계" if "통합" in vt or "대리점" in vt else data_key)
            
            for wk in last_4_keys:
                if "전체" in vt: row_data = final_df[final_df[('기본정보', 'HC명', 'HC명')] == search_key]
                elif "통합" in vt: 
                    d_list = REGION_MAP["충청상권" if "충청" in vt else "호남상권"]
                    row_data = final_df[(final_df[('기본정보', '대리점', '대리점')].isin(d_list)) & (final_df[('기본정보', 'HC명', 'HC명')] == "합계")].sum(numeric_only=True).to_frame().T
                elif "대리점" in vt: row_data = final_df[(final_df[('기본정보', '대리점', '대리점')] == data_key) & (final_df[('기본정보', 'HC명', 'HC명')] == "합계")]
                else: row_data = final_df[final_df[('기본정보', 'HC명', 'HC명')] == search_key]

                if not row_data.empty:
                    exact_col_name = f"{wk} ({date_headers.get(wk, '')})"
                    t_amts.append(row_data[(exact_col_name, '계약액(천)', '목표')].values[0] / 100000.0)
                    a_amts.append(row_data[(exact_col_name, '계약액(천)', 'ACT')].values[0] / 100000.0)
                else:
                    t_amts.append(0); a_amts.append(0)

            x_lbls = [f"<b>{wk} ({date_headers.get(wk, '')})</b>" for wk in last_4_keys]

            fig = go.Figure()
            fig.add_trace(go.Bar(name='목표 계약액', x=x_lbls, y=t_amts, marker_color='#94a3b8', text=[f"{v:.1f}억" for v in t_amts], textposition='auto'))
            fig.add_trace(go.Bar(name='실제 계약액', x=x_lbls, y=a_amts, marker_color='#2563eb', text=[f"<b>{v:.1f}억</b>" for v in a_amts], textposition='auto'))
            fig.update_layout(barmode='group', height=450, margin=dict(l=20, r=20, t=60, b=20), plot_bgcolor='white', legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1))
            fig.update_yaxes(title="금액 (억)", gridcolor='#f1f5f9')
            fig.update_xaxes(showgrid=True, gridcolor='#f1f5f9', tickfont=dict(size=14, color='black'))
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            la = month_labels if is_m else trend_labels
            la_chart = [f"<b>{l}</b>" for l in la] 
            
            if vt == "충청호남팀 전체": sd = [trend_pack['M' if is_m else 'W']['tot'][l if is_m else trend_labels.index(l)] for l in la]
            elif vt in ["충청팀 통합", "호남팀 통합"]: sd = [trend_pack['M' if is_m else 'W']['reg'][data_key][l if is_m else trend_labels.index(l)] for l in la]
            elif "대리점" in vt: sd = [trend_pack['M' if is_m else 'W']['dlr'].get(data_key, {lbl: {'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for lbl in la} if is_m else [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for _ in range(8)])[l if is_m else trend_labels.index(l)] for l in la]
            else: sd = [trend_pack['M' if is_m else 'W']['hc'].get(data_key, {lbl: {'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for lbl in la} if is_m else [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0,'online':0,'cancel':0} for _ in range(8)])[l if is_m else trend_labels.index(l)] for l in la]
            
            g_c1, g_c2, g_c3, g_c4 = st.columns([5, 3, 2, 2])
            with g_c1:
                st.markdown("<div class='chart-btn-group'>💰 재무 지표</div>", unsafe_allow_html=True)
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1: st.button("✅ 계약액" if st.session_state['t_amt'] else "계약액", on_click=toggle_state, args=('t_amt',), use_container_width=True, type="primary" if st.session_state['t_amt'] else "secondary")
                with c2: st.button("✅ 매출액(순증분)" if st.session_state['t_sales'] else "매출액(순증분)", on_click=toggle_state, args=('t_sales',), use_container_width=True, type="primary" if st.session_state['t_sales'] else "secondary")
                with c3: st.button("✅ 이월매출(순증분)" if st.session_state['t_next'] else "이월매출(순증분)", on_click=toggle_state, args=('t_next',), use_container_width=True, type="primary" if st.session_state['t_next'] else "secondary")
                with c4: st.button("✅ 온라인(순증분)" if st.session_state['t_onl'] else "온라인(순증분)", on_click=toggle_state, args=('t_onl',), use_container_width=True, type="primary" if st.session_state['t_onl'] else "secondary")
                with c5: st.button("✅ 평균(계약)" if st.session_state['t_avg'] else "평균(계약)", on_click=toggle_state, args=('t_avg',), use_container_width=True, type="primary" if st.session_state['t_avg'] else "secondary")
            with g_c2:
                st.markdown("<div class='chart-btn-group'>🏢 분류 지표 (계약액)</div>", unsafe_allow_html=True)
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.button("✅ 주중" if st.session_state['t_wd'] else "주중", on_click=toggle_state, args=('t_wd',), use_container_width=True, type="primary" if st.session_state['t_wd'] else "secondary")
                with c2: st.button("✅ 주말" if st.session_state['t_we'] else "주말", on_click=toggle_state, args=('t_we',), use_container_width=True, type="primary" if st.session_state['t_we'] else "secondary")
                with c3: st.button("✅ 워크인" if st.session_state['t_walk'] else "워크인", on_click=toggle_state, args=('t_walk',), use_container_width=True, type="primary" if st.session_state['t_walk'] else "secondary")
                with c4: st.button("✅ 입주" if st.session_state['t_move'] else "입주", on_click=toggle_state, args=('t_move',), use_container_width=True, type="primary" if st.session_state['t_move'] else "secondary")
            with g_c3:
                st.markdown("<div class='chart-btn-group'>📝 건수 지표</div>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1: st.button("✅ 견적건" if st.session_state['t_est'] else "견적건", on_click=toggle_state, args=('t_est',), use_container_width=True, type="primary" if st.session_state['t_est'] else "secondary")
                with c2: st.button("✅ 계약건" if st.session_state['t_cnt'] else "계약건", on_click=toggle_state, args=('t_cnt',), use_container_width=True, type="primary" if st.session_state['t_cnt'] else "secondary")
            with g_c4:
                st.markdown("<div class='chart-btn-group'>📊 효율 지표</div>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                with c1: st.button("✅ 계약률" if st.session_state['t_rate'] else "계약률", on_click=toggle_state, args=('t_rate',), use_container_width=True, type="primary" if st.session_state['t_rate'] else "secondary")
                with c2: st.button("✅ 객단가" if st.session_state['t_unit'] else "객단가", on_click=toggle_state, args=('t_unit',), use_container_width=True, type="primary" if st.session_state['t_unit'] else "secondary")
                with c3: st.button("✅ 취소액" if st.session_state['t_can'] else "취소액", on_click=toggle_state, args=('t_can',), use_container_width=True, type="primary" if st.session_state['t_can'] else "secondary")
            
            y_a = [(w.get('amt', 0)/100000) for w in sd]
            y_s = [(w.get('sales', 0)/100000) for w in sd]
            y_n = [(w.get('next_sales', 0)/100000) for w in sd]
            y_onl = [(w.get('online', 0)/100000) for w in sd]
            y_can = [(w.get('cancel', 0)/100000) for w in sd]
            y_av = [sum(y_a)/len(y_a) if y_a else 0] * len(y_a)
            y_wd = [(w.get('amt_wd', 0)/100000) for w in sd]
            y_we = [(w.get('amt_we', 0)/100000) for w in sd]
            y_m = [(w.get('amt_move', 0)/100000) for w in sd]
            y_wk = [a - m for a, m in zip(y_a, y_m)]
            
            ym_txt, yw_txt, y_onl_txt = [], [], []
            for w, m, a, o, s in zip(y_wk, y_m, y_a, y_onl, y_s):
                if a != 0:
                    ym_txt.append(f"<b>{m:.2f}억</b><br><span style='font-size:11px'>({(m/a*100):.0f}%)</span>")
                    yw_txt.append(f"<b>{w:.2f}억</b><br><span style='font-size:11px'>({(w/a*100):.0f}%)</span>")
                else:
                    ym_txt.append(f"<b>{m:.2f}억</b>")
                    yw_txt.append(f"<b>{w:.2f}억</b>")
                    
                if s > 0:
                    y_onl_txt.append(f"<b>{o:.2f}억</b><br><span style='font-size:12px; font-weight:900;'>({(o/s*100):.0f}%)</span>")
                else:
                    y_onl_txt.append(f"<b>{o:.2f}억</b>")
            
            y_e = [w.get('est', 0) for w in sd]
            y_c = [w.get('cnt', 0) for w in sd]
            y_r = [(c/e*100) if e>0 else 0 for e, c in zip(y_e, y_c)]
            y_u = [(a*100000/(c*10)) if c>0 else 0 for a, c in zip(y_a, y_c)] 
                    
            if any([st.session_state[k] for k in toggle_keys]):
                fig = go.Figure()
                ms = [10] * (len(la)-1) + [20]
                
                if st.session_state['t_amt']: fig.add_trace(go.Scatter(x=la_chart, y=y_a, mode='lines+markers+text', name='계약액', text=[f"<b>{v:.2f}억</b>" for v in y_a], textposition='top center', textfont=dict(size=15, color='black'), line=dict(color='#0f172a', width=4), marker=dict(size=ms, color=['#0f172a'] * (len(la)-1) + ['#dc2626'], line=dict(width=2, color='white'))))
                if st.session_state['t_sales']: fig.add_trace(go.Scatter(x=la_chart, y=y_s, mode='lines+markers+text', name='매출액(순증분)', text=[f"<b>{v:.2f}억</b>" for v in y_s], textposition='bottom right', textfont=dict(size=15, color='#0d9488'), line=dict(color='#14b8a6', width=3), marker=dict(size=ms, line=dict(width=2, color='white'))))
                if st.session_state['t_next']: fig.add_trace(go.Scatter(x=la_chart, y=y_n, mode='lines+markers+text', name='이월매출(순증분)', text=[f"<b>{v:.2f}억</b>" for v in y_n], textposition='top left', textfont=dict(size=15, color='#d97706'), line=dict(color='#f59e0b', width=3), marker=dict(size=ms, line=dict(width=2, color='white'))))
                if st.session_state['t_onl']: fig.add_trace(go.Scatter(x=la_chart, y=y_onl, mode='lines+markers+text', name='온라인매출(순증분)', text=y_onl_txt, textposition='top right', textfont=dict(size=14, color='#0284c7'), line=dict(color='#38bdf8', width=3), marker=dict(size=ms, line=dict(width=2, color='white'))))
                
                if st.session_state['t_avg']: 
                    avg_txt = [""] * len(la)
                    mid_idx = len(la) // 2
                    avg_txt[mid_idx] = f"<b>평균 {y_av[-1]:.2f}억</b>"
                    fig.add_trace(go.Scatter(x=la_chart, y=y_av, mode='lines+text', name='평균선', text=avg_txt, textposition='top center', textfont=dict(size=18, color='#0f172a'), line=dict(color='#94a3b8', width=2, dash='dash')))
                    
                if st.session_state['t_wd']: fig.add_trace(go.Scatter(x=la_chart, y=y_wd, mode='lines+markers+text', name='주중', text=[f"<b>{v:.2f}억</b>" for v in y_wd], textposition='bottom center', textfont=dict(size=15, color='#0ea5e9'), line=dict(color='#0ea5e9', width=3), marker=dict(size=ms, line=dict(width=2, color='white'))))
                if st.session_state['t_we']: fig.add_trace(go.Scatter(x=la_chart, y=y_we, mode='lines+markers+text', name='주말', text=[f"<b>{v:.2f}억</b>" for v in y_we], textposition='top right', textfont=dict(size=15, color='#ef4444'), line=dict(color='#ef4444', width=3), marker=dict(size=ms, line=dict(width=2, color='white'))))
                if st.session_state['t_walk']: fig.add_trace(go.Scatter(x=la_chart, y=y_wk, mode='lines+markers+text', name='워크인', text=yw_txt, textposition='top left', textfont=dict(size=15, color='#f97316'), line=dict(color='#f97316', width=3, dash='dot')))
                if st.session_state['t_move']: fig.add_trace(go.Scatter(x=la_chart, y=y_m, mode='lines+markers+text', name='입주', text=ym_txt, textposition='bottom right', textfont=dict(size=15, color='#a855f7'), line=dict(color='#a855f7', width=3, dash='dot')))
                if st.session_state['t_est']: fig.add_trace(go.Scatter(x=la_chart, y=y_e, mode='lines+markers+text', name='견적건', text=[f"<b>{v:,.0f}건</b>" for v in y_e], textposition='top center', textfont=dict(size=15, color='#4338ca'), line=dict(color='#4338ca', width=3), marker=dict(size=ms, line=dict(width=2, color='white')), yaxis='y2'))
                if st.session_state['t_cnt']: fig.add_trace(go.Scatter(x=la_chart, y=y_c, mode='lines+markers+text', name='계약건', text=[f"<b>{v:,.0f}건</b>" for v in y_c], textposition='bottom center', textfont=dict(size=15, color='#10b981'), line=dict(color='#10b981', width=3), marker=dict(size=ms, line=dict(width=2, color='white')), yaxis='y2'))
                if st.session_state['t_rate']: fig.add_trace(go.Scatter(x=la_chart, y=y_r, mode='lines+markers+text', name='계약률', text=[f"<b>{v:.1f}%</b>" for v in y_r], textposition='top right', textfont=dict(size=15, color='#ca8a04'), line=dict(color='#ca8a04', width=3), marker=dict(size=ms, line=dict(width=2, color='white')), yaxis='y3'))
                if st.session_state['t_unit']: fig.add_trace(go.Scatter(x=la_chart, y=y_u, mode='lines+markers+text', name='객단가', text=[f"<b>{int(v):,}만</b>" for v in y_u], textposition='bottom left', textfont=dict(size=15, color='#ec4899'), line=dict(color='#ec4899', width=3), marker=dict(size=ms, line=dict(width=2, color='white')), yaxis='y4'))
                if st.session_state['t_can']: fig.add_trace(go.Scatter(x=la_chart, y=y_can, mode='lines+markers+text', name='취소액', text=[f"<b>{v:.2f}억</b>" for v in y_can], textposition='bottom left', textfont=dict(size=14, color='#9f1239'), line=dict(color='#e11d48', width=3, dash='dot'), marker=dict(size=ms, line=dict(width=2, color='white'))))
                    
                fig.update_layout(
                    height=450, margin=dict(l=20, r=20, t=60, b=20), plot_bgcolor='white', 
                    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1), 
                    annotations=[dict(xref='paper', yref='paper', x=0, y=1.1, xanchor='left', yanchor='bottom', text='<b>금액 (억)</b>', font=dict(size=13, color='#1e3a8a'), showarrow=False)], 
                    yaxis=dict(title="", tickformat=".1f", ticksuffix="억", dtick=0.5, gridcolor='#f1f5f9'), 
                    yaxis2=dict(title=dict(text="<b>건수 (건)</b>", font=dict(size=13, color='#ea580c')), overlaying='y', side='right', showgrid=False), 
                    yaxis3=dict(overlaying='y', visible=False), 
                    yaxis4=dict(overlaying='y', visible=False)
                )
                fig.update_xaxes(showgrid=True, gridcolor='#f1f5f9', tickfont=dict(size=14, color='black'))
                st.plotly_chart(fig, use_container_width=True)
            else: st.info("👆 위 세부 지표 버튼을 클릭하시면 실시간 꺾은선 그래프가 나타납니다.")
            
        st.markdown("---")
        
        st.markdown("#### 🏆 **대리점별 당월 매출 달성률 랭킹**")
        
        dealer_rank_data = []
        for _, r in final_df.iterrows():
            d_name = r[('기본정보', '대리점', '대리점')]
            hc_name = r[('기본정보', 'HC명', 'HC명')]
            
            if hc_name == "합계" and d_name not in ["🌟 총계", "충청상권", "호남상권"]:
                tgt = r[('🎯 당월매출', '인별매출(천)', '목표')]
                act = r[('🎯 당월매출', '인별매출(천)', 'ACT')]
                rate = r[('🎯 당월매출', '인별매출(천)', '달성율(%)')]
                dealer_rank_data.append({'Dealer': d_name, 'Target': tgt, 'Actual': act, 'Rate': rate})
                
        if dealer_rank_data:
            df_rank = pd.DataFrame(dealer_rank_data)
            df_rank = df_rank.sort_values(by='Rate', ascending=True)
            
            colors = ['#10b981' if rate >= 100 else '#3b82f6' for rate in df_rank['Rate']]
            texts = [f"<b>{r:.0f}%</b> ({a/100000:.1f}억 / {t/100000:.1f}억)" if t > 0 else f"<b>{r:.0f}%</b> ({a/100000:.1f}억 / 0억)" for r, a, t in zip(df_rank['Rate'], df_rank['Actual'], df_rank['Target'])]
            
            fig_rank = go.Figure(go.Bar(
                x=df_rank['Rate'],
                y=df_rank['Dealer'],
                orientation='h',
                marker_color=colors,
                text=texts,
                textposition='auto',
                textfont=dict(size=14, color='white')
            ))
            
            fig_rank.update_layout(
                height=300 + (len(df_rank) * 30),
                margin=dict(l=20, r=20, t=30, b=20),
                plot_bgcolor='white',
                xaxis=dict(showgrid=True, gridcolor='#f1f5f9', title="달성률 (%)"),
                yaxis=dict(showgrid=False, tickfont=dict(size=14, color='black', weight='bold'))
            )
            st.plotly_chart(fig_rank, use_container_width=True)
        
        st.markdown("---")

        tdr = date_headers.get(CURRENT_TABLE_WEEK, "")
        
        if "님" in ct:
            r_data = final_df[final_df[('기본정보', 'HC명', 'HC명')] == data_key]
            if not r_data.empty:
                t_amt = r_data[('🌟 당월 합계', '계약액(천)', '목표')].values[0]
                a_amt = r_data[('🌟 당월 합계', '계약액(천)', 'ACT')].values[0]
                pct_amt = r_data[('🌟 당월 합계', '계약액(천)', '달성율(%)')].values[0]
                
                t_c = '#047857' if pct_amt >= 100 else ('#ef4444' if pct_amt < 50 else '#ea580c')
                b_c = '#10b981' if pct_amt >= 100 else ('#ef4444' if pct_amt < 50 else '#f97316')
                b_w = min(pct_amt, 100)
                
                html_card = '''
                <div style="display:flex; gap:15px; margin-bottom:20px;">
                    <div style="flex:1; background:white; padding:15px; border-radius:10px; border:2px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="font-size:13px; color:#64748b; font-weight:bold;">🎯 당월 계약액 목표 (천원)</div>
                        <div style="font-size:22px; font-weight:900; color:#0f172a;">{T_AMT}</div>
                    </div>
                    <div style="flex:1; background:white; padding:15px; border-radius:10px; border:2px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="font-size:13px; color:#64748b; font-weight:bold;">🏆 현재 계약액 실적 (천원)</div>
                        <div style="font-size:22px; font-weight:900; color:#1d4ed8;">{A_AMT}</div>
                    </div>
                    <div style="flex:1; background:white; padding:15px; border-radius:10px; border:2px solid #e2e8f0; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
                        <div style="font-size:13px; color:#64748b; font-weight:bold;">🔥 목표 달성율 (%)</div>
                        <div style="font-size:22px; font-weight:900; color:{T_C};">{PCT_AMT}%</div>
                        <div style="width:100%; background-color:#e2e8f0; height:6px; border-radius:3px; margin-top:5px;">
                            <div style="width:{B_W}%; background-color:{B_C}; height:100%; border-radius:3px;"></div>
                        </div>
                    </div>
                </div>
                '''
                
                html_card = html_card.replace("{T_AMT}", f"{t_amt:,.0f}").replace("{A_AMT}", f"{a_amt:,.0f}")
                html_card = html_card.replace("{PCT_AMT}", f"{pct_amt:,.0f}").replace("{T_C}", t_c)
                html_card = html_card.replace("{B_W}", str(b_w)).replace("{B_C}", b_c)
                
                st.markdown(html_card, unsafe_allow_html=True)

        st.markdown(f"<div style='background-color: #f8fafc; padding: 15px; border-left: 5px solid #3b82f6; border-radius: 5px; margin-bottom: 20px;'><h4 style='margin:0; color: #1e3a8a;'>📌 {current_month}월 {CURRENT_TABLE_WEEK} {tdr} 전체 VDT 현황 표 (기준일: {eff_selected_date})</h4></div>", unsafe_allow_html=True)
        
        uds = [d for d in final_df[('기본정보', '대리점', '대리점')].unique() if d not in ["🌟 총계", "충청상권", "호남상권"]]
        dcs = {d: ['#f8fafc', '#ffffff'][i%2] for i, d in enumerate(uds)}
        
        cws_s = [50, 70, 55, 55, 55, 55, 55, 55, 45, 45, 45, 45, 45, 45]
        cls_s = [sum(cws_s[:i]) for i in range(len(cws_s))]
        
        tab1, tab2 = st.tabs(["📊 핵심 요약 뷰 (달성률 게이지 적용)", "📆 주차별 상세 뷰 (필터 조회 기능)"])

        with tab1:
            hl_sum = ["<div class='vdt-table-container'><table class='vdt-table'><thead><tr>"]
            
            w_css = f"min-width:{cws_s[0]}px; max-width:{cws_s[0]}px;"
            hl_sum.append(f"<th rowspan='3' style='position:sticky; top:0; left:0; z-index:20; background-color:#0f172a; border-right:1px solid #cbd5e1; {w_css}'>대리점</th>")
            w_css = f"min-width:{cws_s[1]}px; max-width:{cws_s[1]}px;"
            hl_sum.append(f"<th rowspan='3' style='position:sticky; top:0; left:{cls_s[1]}px; z-index:20; background-color:#0f172a; border-right:2px solid #94a3b8; {w_css}'>HC명</th>")
            
            h1_list_sum = []
            for c in final_df.columns[2:14]:
                if c[0] not in h1_list_sum: h1_list_sum.append(c[0])
                    
            for h1 in h1_list_sum:
                sp = "position:sticky; top:0; background-color:#064e3b; color:#a7f3d0; border-top:2px solid #047857;"
                if h1 == '🎯 당월매출': hl_sum.append(f"<th colspan='3' style='{sp} left:{cls_s[2]}px; z-index:15; border-right:3px solid #1e293b;'>{h1}</th>")
                elif "🌟 당월 합계" in h1: hl_sum.append(f"<th colspan='9' style='{sp} left:{cls_s[5]}px; z-index:15; border-right:4px solid #94a3b8;'>{h1}</th>")
            hl_sum.append("</tr><tr>")
            
            for h1 in h1_list_sum:
                sp = "position:sticky; top:33px; background-color:#065f46; color:#a7f3d0;"
                if h1 == '🎯 당월매출': hl_sum.append(f"<th colspan='3' style='{sp} left:{cls_s[2]}px; z-index:15; border-right:3px solid #1e293b;'>인별매출(천)</th>")
                elif "🌟 당월 합계" in h1: hl_sum.append(f"<th colspan='3' style='{sp} left:{cls_s[5]}px; z-index:15;'>계약액(천)</th><th colspan='3' style='{sp} left:{cls_s[8]}px; z-index:15;'>견적건</th><th colspan='3' style='{sp} left:{cls_s[11]}px; z-index:15; border-right:4px solid #94a3b8;'>계약건</th>")
            hl_sum.append("</tr><tr>")
            
            for i, c in enumerate(final_df.columns[2:14]):
                ai = i + 2
                w_css = f"min-width:{cws_s[ai]}px; max-width:{cws_s[ai]}px;"
                sp = f"position:sticky; top:66px; background-color:#047857; color:#a7f3d0; left:{cls_s[ai]}px; z-index:15; {w_css}"
                if c[0]=='🎯 당월매출' and c[2]=='달성율(%)': sp += " border-right:3px solid #1e293b;"
                if "🌟 당월 합계" in c[0] and c[1]=='계약건' and c[2]=='달성율(%)': sp += " border-right:4px solid #94a3b8;"
                hl_sum.append(f"<th style='{sp}'>{c[2]}</th>")
            hl_sum.append("</tr></thead><tbody>")
            
            for _, r in final_df.iterrows():
                d, hc = r[('기본정보', '대리점', '대리점')], r[('기본정보', 'HC명', 'HC명')]
                bg, rb = ("#e2e8f0", "style='background-color:#e2e8f0;'") if hc in ["합계","상권합계"] else (("#cbd5e1", "style='background-color:#cbd5e1;'") if "🌟" in str(hc) else (dcs.get(d, '#ffffff'), f"style='background-color:{dcs.get(d, '#ffffff')};'"))
                
                w_css = f"min-width:{cws_s[0]}px; max-width:{cws_s[0]}px;"
                hl_sum.append(f"<tr {rb}><td class='text-center' style='position:sticky; left:0; z-index:6; border-right:1px solid #cbd5e1; {w_css}'>{d}</td>")
                w_css = f"min-width:{cws_s[1]}px; max-width:{cws_s[1]}px;"
                hl_sum.append(f"<td class='text-center' style='position:sticky; left:{cls_s[1]}px; z-index:6; border-right:2px solid #94a3b8; {w_css}'>{hc}</td>")
                
                for i, v in enumerate(r[2:14]):
                    ai, c = i + 2, final_df.columns[i + 2]
                    
                    if c[2] == '달성율(%)':
                        pct = min(max(v, 0), 100)
                        act_val = r.iloc[ai - 1] 
                        tgt_val = r.iloc[ai - 2]
                        
                        if hc in ["합계","상권합계"] or "🌟" in str(hc):
                            if v >= 100: bar_col = "rgba(139, 92, 246, 0.85)"
                            elif v < 50: bar_col = "rgba(225, 29, 72, 0.8)"
                            else: bar_col = "rgba(168, 85, 247, 0.75)"
                        else:
                            if v >= 100: bar_col = "rgba(5, 150, 105, 0.85)"
                            elif v < 50: bar_col = "rgba(220, 38, 38, 0.8)"
                            else: bar_col = "rgba(37, 99, 235, 0.75)"
                            
                        if v > 0:
                            txt_display = f"<span style='font-size:11px; color:#0f172a; font-weight:900;'>{act_val:,.0f} / {tgt_val:,.0f}</span> <span style='color:#000000; font-weight:900; margin-left:4px; font-size:13px;'>{v:.0f}%</span>"
                        else:
                            txt_display = f"<span style='font-size:12px; color:#0f172a; font-weight:900;'>0%</span>"
                            
                        sp = f"background: linear-gradient(90deg, {bar_col} {pct}%, transparent {pct}%);"
                    else:
                        sp = ""
                        txt_display = f"{v:,.0f}"
                        
                    w_css = f"min-width:{cws_s[ai]}px; max-width:{cws_s[ai]}px;"
                    sp += f" position:sticky; left:{cls_s[ai]}px; z-index:5; {w_css}"
                    if c[0]=='🎯 당월매출' and c[2]=='달성율(%)': sp += " border-right:3px solid #1e293b;"
                    if "🌟 당월 합계" in c[0] and c[1]=='계약건' and c[2]=='달성율(%)': sp += " border-right:4px solid #94a3b8;"
                    
                    hl_sum.append(f"<td style='{sp}'>{txt_display}</td>")
                hl_sum.append("</tr>")
            hl_sum.append("</tbody></table></div>")
            st.markdown("".join(hl_sum), unsafe_allow_html=True)

        with tab2:
            st.markdown("<div style='margin-bottom:10px; font-weight:bold; color:#475569;'>🔎 확인하고 싶은 주차를 선택하세요 (기본: 전체보기)</div>", unsafe_allow_html=True)
            wk_filter_options = ["전체 보기"] + [f"{wk} ({date_headers.get(wk, '')})" for wk in week_keys_list]
            wk_filter_sel = st.radio("주차별 필터", wk_filter_options, horizontal=True, label_visibility="collapsed")
            
            wk_filter = wk_filter_sel.split(" (")[0] if wk_filter_sel != "전체 보기" else "전체 보기"
            
            cws = [60,75,55,55,55,55,55,55,45,45,45,45,45,45]
            cls = [sum(cws[:i]) for i in range(len(cws))]
            
            hl = ["<div class='vdt-table-container'><table class='vdt-table'><thead><tr>"]
            
            w_css = f"min-width:{cws[0]}px; max-width:{cws[0]}px;"
            hl.append(f"<th rowspan='3' style='position:sticky; top:0; left:0; z-index:20; background-color:#0f172a; border-right:1px solid #cbd5e1; {w_css}'>대리점</th>")
            w_css = f"min-width:{cws[1]}px; max-width:{cws[1]}px;"
            hl.append(f"<th rowspan='3' style='position:sticky; top:0; left:{cls[1]}px; z-index:20; background-color:#0f172a; border-right:2px solid #94a3b8; {w_css}'>HC명</th>")
            
            h1_list = []
            for c in final_df.columns[2:]:
                if c[0] not in h1_list: h1_list.append(c[0])
                    
            for h1 in h1_list:
                if h1 not in ['🎯 당월매출', '🌟 당월 합계'] and wk_filter != "전체 보기" and wk_filter not in h1: continue
                    
                ic, im = CURRENT_TABLE_WEEK in h1, "당월" in h1
                sp = "position:sticky; top:0; " + ("background-color:#1e3a8a; border:3px solid #60a5fa;" if ic else ("background-color:#064e3b; color:#a7f3d0; border-top:2px solid #047857;" if im else "background-color:#0f172a;"))
                if h1 == '🎯 당월매출': hl.append(f"<th colspan='3' style='{sp} left:{cls[2]}px; z-index:15; border-right:3px solid #1e293b;'>{h1}</th>")
                elif "🌟 당월 합계" in h1: hl.append(f"<th colspan='9' style='{sp} left:{cls[5]}px; z-index:15; border-right:4px solid #94a3b8;'>{h1}</th>")
                else: hl.append(f"<th colspan='9' style='{sp} z-index:10;'>{h1}</th>")
            hl.append("</tr><tr>")
            
            for h1 in h1_list:
                if h1 not in ['🎯 당월매출', '🌟 당월 합계'] and wk_filter != "전체 보기" and wk_filter not in h1: continue
                    
                ic, im = CURRENT_TABLE_WEEK in h1, "당월" in h1
                sp = "position:sticky; top:33px; " + ("background-color:#1e40af; border-left:3px solid #60a5fa; border-right:3px solid #60a5fa;" if ic else ("background-color:#065f46; color:#a7f3d0;" if im else "background-color:#0f172a;"))
                if h1 == '🎯 당월매출': hl.append(f"<th colspan='3' style='{sp} left:{cls[2]}px; z-index:15; border-right:3px solid #1e293b;'>인별매출(천)</th>")
                elif "🌟 당월 합계" in h1: hl.append(f"<th colspan='3' style='{sp} left:{cls[5]}px; z-index:15;'>계약액(천)</th><th colspan='3' style='{sp} left:{cls[8]}px; z-index:15;'>견적건</th><th colspan='3' style='{sp} left:{cls[11]}px; z-index:15; border-right:4px solid #94a3b8;'>계약건</th>")
                else: hl.append(f"<th colspan='3' style='{sp} z-index:10;'>계약액(천)</th><th colspan='3' style='{sp} z-index:10;'>견적건</th><th colspan='3' style='{sp} z-index:10;'>계약건</th>")
            hl.append("</tr><tr>")
            
            for i, c in enumerate(final_df.columns[2:]):
                if c[0] not in ['🎯 당월매출', '🌟 당월 합계'] and wk_filter != "전체 보기" and wk_filter not in c[0]: continue
                    
                ai = i + 2
                ic, im = CURRENT_TABLE_WEEK in c[0], "당월" in c[0]
                sp = "position:sticky; top:66px; " + ("background-color:#1d4ed8; border-bottom:3px solid #60a5fa;" + ("border-left:3px solid #60a5fa;" if c[1]=='계약액(천)' and c[2]=='목표' else "") + ("border-right:3px solid #60a5fa;" if c[1]=='계약건' and c[2]=='달성율(%)' else "") if ic else ("background-color:#047857; color:#a7f3d0;" if im else "background-color:#0f172a;"))
                
                if ai <= 13:
                    w_css = f"min-width:{cws[ai]}px; max-width:{cws[ai]}px;"
                    sp += f" left:{cls[ai]}px; z-index:15; {w_css}"
                else:
                    sp += " z-index:10; min-width:50px; max-width:50px;"
                    
                if c[0]=='🎯 당월매출' and c[2]=='달성율(%)': sp += " border-right:3px solid #1e293b;"
                if "🌟 당월 합계" in c[0] and c[1]=='계약건' and c[2]=='달성율(%)': sp += " border-right:4px solid #94a3b8;"
                hl.append(f"<th style='{sp}'>{c[2]}</th>")
            hl.append("</tr></thead><tbody>")
            
            for _, r in final_df.iterrows():
                d, hc = r[('기본정보', '대리점', '대리점')], r[('기본정보', 'HC명', 'HC명')]
                bg, rb = ("#e2e8f0", "style='background-color:#e2e8f0;'") if hc in ["합계","상권합계"] else (("#cbd5e1", "style='background-color:#cbd5e1;'") if "🌟" in str(hc) else (dcs.get(d, '#ffffff'), f"style='background-color:{dcs.get(d, '#ffffff')};'"))
                
                w_css = f"min-width:{cws[0]}px; max-width:{cws[0]}px;"
                hl.append(f"<tr {rb}><td class='text-center' style='position:sticky; left:0; z-index:6; border-right:1px solid #cbd5e1; {w_css}'>{d}</td>")
                w_css = f"min-width:{cws[1]}px; max-width:{cws[1]}px;"
                hl.append(f"<td class='text-center' style='position:sticky; left:{cls[1]}px; z-index:6; border-right:2px solid #94a3b8; {w_css}'>{hc}</td>")
                
                for i, v in enumerate(r[2:]):
                    c = final_df.columns[i + 2]
                    if c[0] not in ['🎯 당월매출', '🌟 당월 합계'] and wk_filter != "전체 보기" and wk_filter not in c[0]: continue
                        
                    ai = i + 2
                    ic, im = CURRENT_TABLE_WEEK in c[0], "당월" in c[0]
                    sp = ("border-left:3px solid #3b82f6;" if c[1]=='계약액(천)' and c[2]=='목표' else "") + ("border-right:3px solid #3b82f6;" if c[1]=='계약건' and c[2]=='달성율(%)' else "") if ic else ""
                    
                    if wk_filter != "전체 보기" and c[2] == '달성율(%)' and c[0] not in ['🎯 당월매출', '🌟 당월 합계']:
                        pct = min(max(v, 0), 100)
                        act_val = r.iloc[ai - 1] 
                        tgt_val = r.iloc[ai - 2]
                        
                        if hc in ["합계","상권합계"] or "🌟" in str(hc):
                            if v >= 100: bar_col = "rgba(139, 92, 246, 0.85)"
                            elif v < 50: bar_col = "rgba(225, 29, 72, 0.8)"
                            else: bar_col = "rgba(168, 85, 247, 0.75)"
                        else:
                            if v >= 100: bar_col = "rgba(5, 150, 105, 0.85)"
                            elif v < 50: bar_col = "rgba(220, 38, 38, 0.8)"
                            else: bar_col = "rgba(37, 99, 235, 0.75)"
                            
                        if v > 0:
                            vs = f"<span style='font-size:11px; color:#0f172a; font-weight:900;'>{act_val:,.0f} / {tgt_val:,.0f}</span> <span style='color:#000000; font-weight:900; margin-left:4px; font-size:13px;'>{v:.0f}%</span>"
                        else:
                            vs = f"<span style='font-size:12px; color:#0f172a; font-weight:900;'>0%</span>"
                            
                        sp += f" background: linear-gradient(90deg, {bar_col} {pct}%, transparent {pct}%);"
                    else:
                        if c[2] == '달성율(%)':
                            vs = f"<span style='color:{'#047857' if im else '#1d4ed8'}; font-weight:900;'>{v:.0f}%</span>" if v>=100 else (f"<span style='font-weight:600;'>{v:.0f}%</span>" if v>0 else "0%")
                        else:
                            vs = f"{v:,.0f}"

                    if ai <= 13:
                        w_css = f"min-width:{cws[ai]}px; max-width:{cws[ai]}px;"
                        sp += f" position:sticky; left:{cls[ai]}px; z-index:5; {w_css}" 
                    else:
                        sp += " min-width:50px; max-width:50px;"
                        
                    if c[0]=='🎯 당월매출' and c[2]=='달성율(%)': sp += " border-right:3px solid #1e293b;"
                    if "🌟 당월 합계" in c[0] and c[1]=='계약건' and c[2]=='달성율(%)': sp += " border-right:4px solid #94a3b8;"
                    
                    hl.append(f"<td style='{sp}'>{vs}</td>")
                hl.append("</tr>")
            hl.append("</tbody></table></div>")
            
            st.markdown("".join(hl), unsafe_allow_html=True)
