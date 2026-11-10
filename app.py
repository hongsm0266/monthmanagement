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

# 🚀 접속 시 초기값 (세션) 강력 강제 세팅 (과거 캐시 무시)
if 'init_v3' not in st.session_state:
    st.session_state['view_target'] = "충청호남팀 전체"
    st.session_state['hc_selector'] = "✨ 인원별 상세 실적 (선택 시 우선 적용)"
    st.session_state['t_amt'] = True  # 계약액 무조건 ON
    st.session_state['t_avg'] = False
    st.session_state['t_wd'] = False
    st.session_state['t_we'] = False
    st.session_state['t_walk'] = False
    st.session_state['t_move'] = False
    st.session_state['t_est'] = False
    st.session_state['t_cnt'] = False
    st.session_state['t_rate'] = False
    st.session_state['t_unit'] = False
    st.session_state['init_v3'] = True

toggle_keys = ['t_amt', 't_avg', 't_wd', 't_we', 't_walk', 't_move', 't_est', 't_cnt', 't_rate', 't_unit']

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
    
    div[data-testid="metric-container"] { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    [data-testid="stMetricLabel"] { background-color: #e2e8f0 !important; padding: 4px 10px !important; border-radius: 6px !important; border-left: 5px solid #3b82f6 !important; display: inline-block !important; margin-bottom: 6px !important; }
    [data-testid="stMetricLabel"] * { font-size: 12px !important; font-weight: 900 !important; color: #0f172a !important; letter-spacing: -0.3px; }
    [data-testid="stMetricValue"] > div { font-size: 20px !important; font-weight: 900 !important; color: #1e3a8a !important; margin-top: 5px; }
    
    /* 일반 탭 버튼 기본 스타일 */
    div.stButton > button { 
        background: #f8fafc !important; color: #475569 !important; font-size: 11.5px !important; font-weight: 800 !important; 
        border-radius: 6px !important; padding: 4px 6px !important; border: 1px solid #cbd5e1 !important; height: auto !important; min-height: 32px; 
        border-bottom: 2px solid #94a3b8 !important; transition: all 0.1s ease !important; letter-spacing: -0.5px !important;
    }
    div.stButton > button[kind="primary"] { 
        background: linear-gradient(180deg, #fef2f2 0%, #fee2e2 100%) !important; 
        color: #b91c1c !important; 
        border: 1px solid #fca5a5 !important; 
        border-bottom: 2px solid #f87171 !important; 
    }
    div.stButton > button:hover { transform: translateY(-1px) !important; }
    div.stButton > button:active { transform: translateY(1px) !important; border-bottom: 1px solid #cbd5e1 !important; margin-bottom: 1px !important; }
    
    /* 🚀 1열 탭 (조직 및 인원) 특정 버튼 컬러 커스텀 (전체통합, 충청통합, 호남통합 전용) */
    
    /* 전체통합 (1번째 자식) - 보라색 */
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(1) button {
        background-color: #faf5ff !important; border-color: #e9d5ff !important; color: #9333ea !important; border-bottom: 2px solid #d8b4fe !important;
    }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(1) button[kind="primary"] {
        background: linear-gradient(180deg, #f3e8ff 0%, #e9d5ff 100%) !important; color: #7e22ce !important; border-bottom: 2px solid #a855f7 !important;
    }

    /* 충청통합 (3번째 자식) - 파란색 */
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(3) button {
        background-color: #f0f9ff !important; border-color: #bae6fd !important; color: #0284c7 !important; border-bottom: 2px solid #7dd3fc !important;
    }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(3) button[kind="primary"] {
        background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%) !important; color: #0369a1 !important; border-bottom: 2px solid #0ea5e9 !important;
    }

    /* 호남통합 (9번째 자식) - 초록색 */
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(9) button {
        background-color: #f0fdf4 !important; border-color: #bbf7d0 !important; color: #16a34a !important; border-bottom: 2px solid #86efac !important;
    }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(9) button[kind="primary"] {
        background: linear-gradient(180deg, #dcfce7 0%, #bbf7d0 100%) !important; color: #15803d !important; border-bottom: 2px solid #22c55e !important;
    }

    .btn-group-title { font-size: 12px; font-weight: 900; color: #1e293b; background: #e2e8f0; border-radius: 4px; padding: 4px 10px; margin-bottom: 6px; border-left: 4px solid #3b82f6; }
    .chart-btn-group { font-size: 11px; font-weight: 800; color: #475569; background: #e2e8f0; border-radius: 4px; padding: 2px 0; text-align: center; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

current_month = datetime.now().month
st.markdown(f"<div class='title-box'><h1>📊 충청호남팀 영업사원 주차별 VDT 목표 관리 ({current_month}월)</h1></div>", unsafe_allow_html=True)

def clean_str(val): return re.sub(r'\s+', '', str(val))
def safe_get(row, idx): return str(row[idx]).strip() if len(row) > idx else ""
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

def get_week_name(sheet_title):
    try:
        nums = re.findall(r'\d+', sheet_title)
        if len(nums) >= 2:
            m_val, d_val = int(nums[0]), int(nums[1])
            if m_val == 11:
                if d_val <= 7: return '1주차'
                elif d_val <= 14: return '2주차'
                elif d_val <= 21: return '3주차'
                elif d_val <= 28: return '4주차'
                else: return '5주차'
            elif m_val == 10:
                if d_val <= 4: return '1주차'
                elif d_val <= 11: return '2주차'
                elif d_val <= 18: return '3주차'
                elif d_val <= 25: return '4주차'
                else: return '5주차'
            elif m_val == 9:
                if d_val <= 6: return '1주차'
                elif d_val <= 13: return '2주차'
                elif d_val <= 20: return '3주차'
                elif d_val <= 27: return '4주차'
                else: return '5주차'
    except: pass
    return None

def get_mapped_dealer(raw_d):
    c_d = clean_str(raw_d)
    if any(k in c_d for k in ["한밭", "INT충청", "701347", "세종2"]): return "세종"
    return raw_d.strip()

REGION_MAP = {
    "충청상권": ["둔산", "목포", "세종", "충주"], 
    "호남상권": ["광양", "여수", "익산"]
}

now = datetime.now()
current_monday = now - timedelta(days=now.weekday())

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
        target_date = datetime(now.year, m, d)
        for i, (start, end) in enumerate(trend_ranges):
            if start.date() <= target_date.date() <= end.date(): return i
    except: pass
    return -1

CURRENT_WEEK = get_week_name(f"{now.month}/{now.day}") 
if not CURRENT_WEEK: CURRENT_WEEK = '1주차'

PREV_WEEK = None
if CURRENT_WEEK:
    try:
        curr_num = int(CURRENT_WEEK.replace("주차", ""))
        if curr_num > 0: PREV_WEEK = f"{curr_num - 1}주차"
    except: pass

def safe_api_call(func, *args, **kwargs):
    max_retries = 4
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if "429" in str(e):
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 8
                    st.toast(f"⏳ 서버 요청 한도 도달. {wait_time}초 후 재시도...", icon="⚠️")
                    time.sleep(wait_time)
                    continue
            raise e

@st.cache_data(ttl=600)
def load_vdt_data():
    if not client: return pd.DataFrame(), {}, {}, {}, {}, [], {}, {}, {}, {}
    
    status_box = st.empty()
    try:
        status_box.info("🔍 0단계: 구글 시트 연결 중...")
        sh = safe_api_call(client.open_by_url, SHEET_URL)
        all_worksheets = [ws.title for ws in safe_api_call(sh.worksheets)]
        
        target_sheet_name = "주차별 목표 세팅"
        if target_sheet_name not in all_worksheets: 
            return pd.DataFrame(), {}, {}, {}, {}, [], {}, {}, {}, {}
        
        target_ws = sh.worksheet(target_sheet_name)
        status_box.info("📊 1단계: 인별 매출목표 계산 중...")
        all_targets = safe_api_call(target_ws.get_all_values)
        
        split_idx = 15
        for i, row in enumerate(all_targets):
            if len(row) > 1 and clean_str(row[1]) in ['HC', 'HC명', '영업사원', '이름']:
                split_idx = i
                break
                
        target_data = all_targets[:split_idx]
        hc_target_data = all_targets[split_idx:]
        
        hc_info_raw = []         
        dealer_sales_sum = {} 
        
        for row in hc_target_data:
            if len(row) >= 4 and str(row[0]).strip() and str(row[1]).strip():
                raw_dealer = str(row[0]).strip()
                hc_name = clean_str(row[1]) 
                if raw_dealer in ['대리점', '대리점명', '구분'] or hc_name in ['HC', 'HC명', '영업사원', '이름']: continue
                if hc_name.isdigit(): continue
                dealer = get_mapped_dealer(raw_dealer)
                sales_target = clean_val(row[3]) / 1000.0
                hc_info_raw.append((dealer, hc_name, sales_target))
                dealer_sales_sum[dealer] = dealer_sales_sum.get(dealer, 0.0) + sales_target

        status_box.info("🎯 2단계: 주차별 목표 스캔 중...")
        
        if current_month == 11:
            date_headers = {
                '1주차': '11/1~11/7', '2주차': '11/8~11/14', '3주차': '11/15~11/21',
                '4주차': '11/22~11/28', '5주차': '11/29~11/30'
            }
        elif current_month == 10:
            date_headers = {
                '1주차': '10/1~10/4', '2주차': '10/5~10/11', '3주차': '10/12~10/18',
                '4주차': '10/19~10/25', '5주차': '10/26~10/31'
            }
        else:
            date_headers = {
                '1주차': '1주차', '2주차': '2주차', '3주차': '3주차', '4주차': '4주차', '5주차': '5주차'
            }
            
        week_cols = {
            '1주차': {'amt': 1, 'est': 2, 'cnt': 3}, '2주차': {'amt': 4, 'est': 5, 'cnt': 6},   
            '3주차': {'amt': 7, 'est': 8, 'cnt': 9}, '4주차': {'amt': 10, 'est': 11, 'cnt': 12}, 
            '5주차': {'amt': 13, 'est': 14, 'cnt': 15}, 
        }
        week_keys = list(week_cols.keys())
        
        dealer_targets = {}
        for row in target_data:
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
        trend_sheets = []
        for ws in daily_sheets:
            wk = get_week_name(ws.title)
            nums = re.findall(r'\d+', ws.title)
            if len(nums) >= 2: 
                m_val, d_val = int(nums[0]), int(nums[1])
                if m_val == current_month and wk:
                    valid_daily_sheets.append((m_val, wk, ws))
                
                idx = get_trend_week_idx(m_val, d_val)
                if idx != -1:
                    trend_sheets.append((m_val, d_val, ws, idx))

        valid_map = {ws.id: (m_val, wk) for m_val, wk, ws in valid_daily_sheets}
        trend_map = {ws.id: idx for m_val, d_val, ws, idx in trend_sheets}
        all_sheet_ids = set(list(valid_map.keys()) + list(trend_map.keys()))
        
        status_box.info(f"📉 3단계: 일별 실적 스캔 및 최근 8주 트렌드 데이터 계산 중...")
        sheet_data_cache = {}
        id_to_ws = {ws.id: ws for _,_,ws in valid_daily_sheets}
        for _,_,ws,_ in trend_sheets: id_to_ws[ws.id] = ws
        
        for ws_id in all_sheet_ids:
            time.sleep(0.2) 
            sheet_data_cache[ws_id] = safe_api_call(id_to_ws[ws_id].get_all_values)
        
        existing_hcs = [clean_str(h) for d, h, t in hc_info_raw]
        valid_dealers = list(set([d for d, _, _ in hc_info_raw]))
        
        acts = {clean_str(hc): {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for _, hc, _ in hc_info_raw}
        month_acts = {clean_str(hc): {'amt': 0, 'est': 0, 'cnt': 0} for _, hc, _ in hc_info_raw}
        hc_to_dealer = {clean_str(hc): dealer for dealer, hc, _ in hc_info_raw}
        
        real_dealer_monthly = {d: {'amt': 0, 'est': 0, 'cnt': 0} for d in valid_dealers}
        real_dealer_weekly = {d: {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for d in valid_dealers}
        
        trend_hc_data = {clean_str(hc): [{'amt': 0, 'est': 0, 'cnt': 0, 'amt_wd': 0, 'amt_we': 0} for _ in range(8)] for _, hc, _ in hc_info_raw}
        trend_dealer_data = {d: [{'amt': 0, 'est': 0, 'cnt': 0, 'amt_wd': 0, 'amt_we': 0} for _ in range(8)] for d in valid_dealers}
        trend_total_data = [{'amt': 0, 'est': 0, 'cnt': 0, 'amt_wd': 0, 'amt_we': 0} for _ in range(8)]
        
        for ws_id in all_sheet_ids:
            d_data = sheet_data_cache[ws_id] 
            wk_info = valid_map.get(ws_id) 
            tr_idx = trend_map.get(ws_id, -1)
            
            is_weekend = False
            if tr_idx != -1:
                for m_val, d_val, ws, idx in trend_sheets:
                    if ws.id == ws_id:
                        try:
                            sheet_date = datetime(now.year, m_val, d_val)
                            is_weekend = sheet_date.weekday() >= 5 
                        except: pass
                        break

            current_rem_dealer = ""
            for row in d_data:
                if len(row) > 3: 
                    row_header_str = clean_str("".join([safe_get(row, i) for i in range(4)]))
                    if get_mapped_dealer(row_header_str) == "세종": current_rem_dealer = "세종"
                    else:
                        for vd in valid_dealers:
                            if clean_str(vd) in row_header_str:
                                current_rem_dealer = vd
                                break

                    temp_est, temp_cnt, temp_amt = clean_val(safe_get(row, 4)), clean_val(safe_get(row, 5)), clean_val(safe_get(row, 15))
                    hc_name = clean_str(safe_get(row, 3))
                    if any(x in hc_name for x in ['합계', '소계', '총계', '목표', '대리점', '사번', '비고']): continue
                    if not hc_name: continue 
                        
                    if hc_name and hc_name not in existing_hcs:
                        new_dealer = current_rem_dealer if current_rem_dealer else "기타"
                        hc_info_raw.append((new_dealer, hc_name, 0.0))
                        existing_hcs.append(hc_name)
                        acts[hc_name] = {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys}
                        month_acts[hc_name] = {'amt': 0, 'est': 0, 'cnt': 0}
                        hc_to_dealer[hc_name] = new_dealer
                        trend_hc_data[hc_name] = [{'amt': 0, 'est': 0, 'cnt': 0, 'amt_wd': 0, 'amt_we': 0} for _ in range(8)]
                        if new_dealer not in valid_dealers:
                            valid_dealers.append(new_dealer)
                            real_dealer_monthly[new_dealer] = {'amt': 0, 'est': 0, 'cnt': 0}
                            real_dealer_weekly[new_dealer] = {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys}
                            trend_dealer_data[new_dealer] = [{'amt': 0, 'est': 0, 'cnt': 0, 'amt_wd': 0, 'amt_we': 0} for _ in range(8)]

                    matched_dealer = current_rem_dealer
                    if not matched_dealer: matched_dealer = hc_to_dealer.get(hc_name, "")
                    
                    if wk_info:
                        m_val, wk = wk_info
                        acts[hc_name][wk]['est'] += temp_est
                        acts[hc_name][wk]['cnt'] += temp_cnt
                        acts[hc_name][wk]['amt'] += temp_amt
                        if m_val == current_month:
                            month_acts[hc_name]['est'] += temp_est
                            month_acts[hc_name]['cnt'] += temp_cnt
                            month_acts[hc_name]['amt'] += temp_amt
                                
                        if matched_dealer in valid_dealers:
                            real_dealer_weekly[matched_dealer][wk]['est'] += temp_est
                            real_dealer_weekly[matched_dealer][wk]['cnt'] += temp_cnt
                            real_dealer_weekly[matched_dealer][wk]['amt'] += temp_amt
                            if m_val == current_month:
                                real_dealer_monthly[matched_dealer]['est'] += temp_est
                                real_dealer_monthly[matched_dealer]['cnt'] += temp_cnt
                                real_dealer_monthly[matched_dealer]['amt'] += temp_amt

                    if tr_idx != -1:
                        trend_hc_data[hc_name][tr_idx]['est'] += temp_est
                        trend_hc_data[hc_name][tr_idx]['cnt'] += temp_cnt
                        trend_hc_data[hc_name][tr_idx]['amt'] += temp_amt
                        if is_weekend: trend_hc_data[hc_name][tr_idx]['amt_we'] += temp_amt
                        else: trend_hc_data[hc_name][tr_idx]['amt_wd'] += temp_amt
                        
                        if matched_dealer in valid_dealers:
                            trend_dealer_data[matched_dealer][tr_idx]['est'] += temp_est
                            trend_dealer_data[matched_dealer][tr_idx]['cnt'] += temp_cnt
                            trend_dealer_data[matched_dealer][tr_idx]['amt'] += temp_amt
                            if is_weekend: trend_dealer_data[matched_dealer][tr_idx]['amt_we'] += temp_amt
                            else: trend_dealer_data[matched_dealer][tr_idx]['amt_wd'] += temp_amt
                            
                            trend_total_data[tr_idx]['est'] += temp_est
                            trend_total_data[tr_idx]['cnt'] += temp_cnt
                            trend_total_data[tr_idx]['amt'] += temp_amt
                            if is_weekend: trend_total_data[tr_idx]['amt_we'] += temp_amt
                            else: trend_total_data[tr_idx]['amt_wd'] += temp_amt
                            
        acts_sales = {clean_str(hc): 0 for _, hc, _ in hc_info_raw}
        real_dealer_sales = {d: 0 for d in valid_dealers}
        
        if valid_daily_sheets:
            latest_m, latest_wk, latest_sheet = valid_daily_sheets[-1] 
            l_data = sheet_data_cache[latest_sheet.id] 
            current_remembered_dealer = ""
            for row in l_data:
                if len(row) > 3:
                    row_header_str = clean_str("".join([safe_get(row, i) for i in range(4)]))
                    if get_mapped_dealer(row_header_str) == "세종": current_remembered_dealer = "세종"
                    else:
                        for vd in valid_dealers:
                            if clean_str(vd) in row_header_str:
                                current_remembered_dealer = vd
                                break
                                
                    hc_name_s, temp_s = clean_str(safe_get(row, 3)), clean_val(safe_get(row, 18))
                    if any(x in hc_name_s for x in ['합계', '소계', '총계', '목표', '대리점', '사번', '비고']): continue
                    if not hc_name_s: continue 
                        
                    if hc_name_s:
                        if temp_s > 0:
                            if hc_name_s in acts_sales: acts_sales[hc_name_s] += temp_s
                            matched_dealer = current_remembered_dealer
                            if not matched_dealer: matched_dealer = hc_to_dealer.get(hc_name_s, "")
                            if matched_dealer in real_dealer_sales: real_dealer_sales[matched_dealer] += temp_s

        status_box.info("🎯 4단계: 실적 데이터 기반 목표 최적화 중...")
        
        EXCLUDED_HCS = ["장재형", "강지인", "신재민"]
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
            if active_list: 
                if hc_clean in active_list:
                    dealer_sales_sum_active[dealer] = dealer_sales_sum_active.get(dealer, 0.0) + tgt
            else: 
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

        status_box.info("✅ 데이터 구성 완료! 표 출력 중...")
        
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
            sales_tgt = final_hc_sales_tgt.get(hc_clean, 0.0) 
            m_act = month_acts.get(hc_clean, {'amt': 0, 'est': 0, 'cnt': 0})
            s_act = acts_sales.get(hc_clean, 0)

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
                df[col] = np.where(df[tgt_col] > 0, (df[act_col] / df[tgt_col] * 100).round(1), 0)
        
        trend_region_data = {"충청상권": [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0} for _ in range(8)],
                             "호남상권": [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0} for _ in range(8)]}
        for region, dealers in REGION_MAP.items():
            for d in dealers:
                d_data = trend_dealer_data.get(d, [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0} for _ in range(8)])
                for i in range(8):
                    trend_region_data[region][i]['amt'] += d_data[i]['amt']
                    trend_region_data[region][i]['est'] += d_data[i]['est']
                    trend_region_data[region][i]['cnt'] += d_data[i]['cnt']
                    trend_region_data[region][i]['amt_wd'] += d_data[i]['amt_wd']
                    trend_region_data[region][i]['amt_we'] += d_data[i]['amt_we']

        status_box.empty()
        return df, date_headers, real_dealer_sales, real_dealer_monthly, real_dealer_weekly, week_keys, trend_hc_data, trend_dealer_data, trend_total_data, trend_region_data

    except Exception as e:
        status_box.empty()
        st.error("🚨 데이터 구성 중 에러가 발생했습니다!")
        with st.expander("🛠️ 상세 에러 보기"): st.code(traceback.format_exc())
        return pd.DataFrame(), {}, {}, {}, {}, [], {}, {}, {}, {}

def calculate_subtotals(df, real_dealer_sales, real_dealer_monthly, real_dealer_weekly):
    if df.empty: return df
    
    result_rows = []
    dealer_col, hc_col = ('기본정보', '대리점', '대리점'), ('기본정보', 'HC명', 'HC명')
    
    for dealer, group in df.groupby(dealer_col, sort=False):
        for _, row in group.iterrows(): result_rows.append(row)
            
        subtotal = group.select_dtypes(include=[np.number]).sum()
        subtotal[dealer_col], subtotal[hc_col] = dealer, "합계"
        
        if dealer in real_dealer_sales: subtotal[('🎯 당월매출', '인별매출(천)', 'ACT')] = real_dealer_sales[dealer]
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
                subtotal[col] = round((subtotal[act_col] / subtotal[tgt_col] * 100), 1) if subtotal[tgt_col] > 0 else 0.0
        result_rows.append(pd.Series(subtotal))

    grand_total = df.select_dtypes(include=[np.number]).sum()
    grand_total[dealer_col], grand_total[hc_col] = "🌟 총계", "🌟 총계"
    
    grand_total[('🎯 당월매출', '인별매출(천)', 'ACT')] = sum([real_dealer_sales.get(d, 0) for d in df[dealer_col].unique()])
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
            grand_total[col] = round((grand_total[act_col] / grand_total[tgt_col] * 100), 1) if grand_total[tgt_col] > 0 else 0.0
    result_rows.append(pd.Series(grand_total))
    
    return pd.DataFrame(result_rows)

df_raw, date_headers, real_dealer_sales, real_dealer_monthly, real_dealer_weekly, week_keys_list, trend_hc_data, trend_dealer_data, trend_total_data, trend_region_data = load_vdt_data()

if not df_raw.empty:
    final_df = calculate_subtotals(df_raw, real_dealer_sales, real_dealer_monthly, real_dealer_weekly)
    
    def set_view(target):
        st.session_state['view_target'] = target
        st.session_state['hc_selector'] = "✨ 인원별 상세 실적 (선택 시 우선 적용)"

    def on_hc_select():
        if st.session_state['hc_selector'] != "✨ 인원별 상세 실적 (선택 시 우선 적용)":
            st.session_state['view_target'] = st.session_state['hc_selector']

    def btn_type(target):
        return "primary" if st.session_state.get('view_target') == target else "secondary"
        
    st.markdown("#### 🔎 **실적 조회 (조직 및 인원)**")
    
    st.markdown('<div id="org-buttons"></div>', unsafe_allow_html=True)
    c_org = st.columns([12, 2, 12, 9, 9, 9, 9, 2, 12, 9, 9, 9, 30])
    
    with c_org[0]: st.button("전체통합" if st.session_state['view_target'] != "충청호남팀 전체" else "✅ 전체통합", type=btn_type("충청호남팀 전체"), on_click=set_view, args=("충청호남팀 전체",), use_container_width=True)
    with c_org[1]: st.markdown("<div style='text-align:center; padding-top:5px; color:#cbd5e1; font-weight:bold; font-size:16px;'>|</div>", unsafe_allow_html=True)
    with c_org[2]: st.button("충청통합" if st.session_state['view_target'] != "충청팀 통합" else "✅ 충청통합", type=btn_type("충청팀 통합"), on_click=set_view, args=("충청팀 통합",), use_container_width=True)
    with c_org[3]: st.button("둔산" if st.session_state['view_target'] != "둔산 대리점" else "✅ 둔산", type=btn_type("둔산 대리점"), on_click=set_view, args=("둔산 대리점",), use_container_width=True)
    with c_org[4]: st.button("세종" if st.session_state['view_target'] != "세종 대리점" else "✅ 세종", type=btn_type("세종 대리점"), on_click=set_view, args=("세종 대리점",), use_container_width=True)
    with c_org[5]: st.button("목포" if st.session_state['view_target'] != "목포 대리점" else "✅ 목포", type=btn_type("목포 대리점"), on_click=set_view, args=("목포 대리점",), use_container_width=True)
    with c_org[6]: st.button("충주" if st.session_state['view_target'] != "충주 대리점" else "✅ 충주", type=btn_type("충주 대리점"), on_click=set_view, args=("충주 대리점",), use_container_width=True)
    with c_org[7]: st.markdown("<div style='text-align:center; padding-top:5px; color:#cbd5e1; font-weight:bold; font-size:16px;'>|</div>", unsafe_allow_html=True)
    with c_org[8]: st.button("호남통합" if st.session_state['view_target'] != "호남팀 통합" else "✅ 호남통합", type=btn_type("호남팀 통합"), on_click=set_view, args=("호남팀 통합",), use_container_width=True)
    with c_org[9]: st.button("광양" if st.session_state['view_target'] != "광양 대리점" else "✅ 광양", type=btn_type("광양 대리점"), on_click=set_view, args=("광양 대리점",), use_container_width=True)
    with c_org[10]: st.button("익산" if st.session_state['view_target'] != "익산 대리점" else "✅ 익산", type=btn_type("익산 대리점"), on_click=set_view, args=("익산 대리점",), use_container_width=True)
    with c_org[11]: st.button("여수" if st.session_state['view_target'] != "여수 대리점" else "✅ 여수", type=btn_type("여수 대리점"), on_click=set_view, args=("여수 대리점",), use_container_width=True)
    
    with c_org[12]:
        hc_list = ["✨ 인원별 상세 실적 (선택 시 우선 적용)"]
        for r_idx in range(len(final_df)):
            dealer = final_df.iloc[r_idx][('기본정보', '대리점', '대리점')]
            hc = final_df.iloc[r_idx][('기본정보', 'HC명', 'HC명')]
            if hc not in ["🌟 총계", "합계"]: hc_list.append(f"👤 {dealer} - {hc}")
            
        st.selectbox("인원선택", options=hc_list, key='hc_selector', on_change=on_hc_select, label_visibility="collapsed")

    vt = st.session_state['view_target']
    is_dealer_total = False
    is_region_total = False
    
    if vt == "충청호남팀 전체":
        target_row = final_df[final_df[('기본정보', 'HC명', 'HC명')] == '🌟 총계'].iloc[0]
        chart_title = "충청호남팀 전체"
        source_data = trend_total_data
    elif vt in ["충청팀 통합", "호남팀 통합"]:
        is_region_total = True
        region_key = "충청상권" if vt == "충청팀 통합" else "호남상권"
        dealers_in_region = REGION_MAP[region_key]
        
        region_rows = final_df[(final_df[('기본정보', '대리점', '대리점')].isin(dealers_in_region)) & (final_df[('기본정보', 'HC명', 'HC명')] == '합계')]
        target_row = region_rows.select_dtypes(include=[np.number]).sum()
        target_row[('기본정보', '대리점', '대리점')] = region_key
        target_row[('기본정보', 'HC명', 'HC명')] = '상권합계'
        
        for col in final_df.columns[2:]:
            if col[2] == '달성율(%)':
                tgt_col = (col[0], col[1], '목표')
                act_col = (col[0], col[1], 'ACT')
                target_row[col] = (target_row[act_col] / target_row[tgt_col] * 100) if target_row.get(tgt_col, 0) > 0 else 0.0
                
        chart_title = f"{vt} 전체"
        source_data = trend_region_data[region_key]
    elif "대리점" in vt: 
        is_dealer_total = True
        target_dealer = vt.replace(" 대리점", "")
        target_row = final_df[(final_df[('기본정보', '대리점', '대리점')] == target_dealer) & (final_df[('기본정보', 'HC명', 'HC명')] == '합계')].iloc[0]
        chart_title = f"{target_dealer} 대리점"
        source_data = trend_dealer_data.get(target_dealer, [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0} for _ in range(8)])
    else: 
        parts = vt.replace("👤 ", "").split(" - ")
        target_dealer, target_hc = parts[0], parts[1]
        target_row = final_df[(final_df[('기본정보', '대리점', '대리점')] == target_dealer) & (final_df[('기본정보', 'HC명', 'HC명')] == target_hc)].iloc[0]
        chart_title = f"{target_hc} 님"
        source_data = trend_hc_data.get(target_hc, [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0} for _ in range(8)])

    st.markdown("---")
            
    def toggle_state(key):
        st.session_state[key] = not st.session_state[key]

    g_col1, g_col2, g_col3, g_col4, g_col5 = st.columns([4, 2, 2, 2, 1])
    
    with g_col1:
        st.markdown("<div class='chart-btn-group'>💰 계약액 지표</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.button("계약액" if not st.session_state['t_amt'] else "✅ 계약액", on_click=toggle_state, args=('t_amt',), use_container_width=True, type="primary" if st.session_state['t_amt'] else "secondary")
        with c2: st.button("8주평균" if not st.session_state['t_avg'] else "✅ 8주평균", on_click=toggle_state, args=('t_avg',), use_container_width=True, type="primary" if st.session_state['t_avg'] else "secondary")
        with c3: st.button("계약(주중)" if not st.session_state['t_wd'] else "✅ 계약(주중)", on_click=toggle_state, args=('t_wd',), use_container_width=True, type="primary" if st.session_state['t_wd'] else "secondary")
        with c4: st.button("계약(주말)" if not st.session_state['t_we'] else "✅ 계약(주말)", on_click=toggle_state, args=('t_we',), use_container_width=True, type="primary" if st.session_state['t_we'] else "secondary")

    with g_col2:
        st.markdown("<div class='chart-btn-group'>🏢 분류 지표</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.button("워크인" if not st.session_state['t_walk'] else "✅ 워크인", on_click=toggle_state, args=('t_walk',), use_container_width=True, type="primary" if st.session_state['t_walk'] else "secondary")
        with c2: st.button("입주" if not st.session_state['t_move'] else "✅ 입주", on_click=toggle_state, args=('t_move',), use_container_width=True, type="primary" if st.session_state['t_move'] else "secondary")

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

    with g_col5:
        st.markdown("<div style='margin-bottom:4px;'>&nbsp;</div>", unsafe_allow_html=True)
        def reset_toggles():
            for tk in toggle_keys: st.session_state[tk] = False
        st.button("🔄 리셋", on_click=reset_toggles, use_container_width=True)
    
    y_amt = [w['amt'] for w in source_data]
    y_amt_억 = [v / 100000 for v in y_amt]
    y_avg_val = sum(y_amt) / len(y_amt) if y_amt else 0
    y_avg_억 = [y_avg_val / 100000] * 8
    
    y_wd = [w['amt_wd'] for w in source_data]
    y_wd_억 = [v / 100000 for v in y_wd]
    y_we = [w['amt_we'] for w in source_data]
    y_we_억 = [v / 100000 for v in y_we]
    
    y_est = [w['est'] for w in source_data]
    y_cnt = [w['cnt'] for w in source_data]
    y_rate = [(c / e * 100) if e > 0 else 0 for e, c in zip(y_est, y_cnt)]
    y_unit = [(a / (c * 10)) if c > 0 else 0 for a, c in zip(y_amt, y_cnt)] 
            
    y_walk_억 = [0] * len(trend_labels)
    y_move_억 = [0] * len(trend_labels)

    any_active = any([st.session_state[k] for k in toggle_keys])
    
    if any_active:
        fig_trend = go.Figure()
        marker_sizes = [10, 10, 10, 10, 10, 10, 10, 20]
        
        if st.session_state['t_amt']:
            marker_colors = ['#0f172a'] * 7 + ['#dc2626'] 
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_amt_억, mode='lines+markers+text', name='주간 계약액', text=[f"<b>{v:.2f}억</b>" for v in y_amt_억], textposition='top center', textfont=dict(size=15, color='black'), line=dict(color='#0f172a', width=4), marker=dict(size=marker_sizes, color=marker_colors, line=dict(width=2, color='white'))))
        
        if st.session_state['t_avg']:
            y_avg_text = [""] * 7 + [f"<b>평균 {y_avg_억[-1]:.2f}억</b>"]
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_avg_억, mode='lines+text', name='최근 8주 평균', text=y_avg_text, textposition='top right', textfont=dict(size=15, color='#475569'), line=dict(color='#94a3b8', width=2, dash='dash')))
        
        if st.session_state['t_wd']:
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_wd_억, mode='lines+markers+text', name='계약액(주중)', text=[f"<b>{v:.2f}억</b>" for v in y_wd_억], textposition='bottom center', textfont=dict(size=15, color='#0ea5e9'), line=dict(color='#0ea5e9', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white'))))
        
        if st.session_state['t_we']:
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_we_억, mode='lines+markers+text', name='계약액(주말)', text=[f"<b>{v:.2f}억</b>" for v in y_we_억], textposition='top right', textfont=dict(size=15, color='#ef4444'), line=dict(color='#ef4444', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white'))))
        
        if st.session_state['t_walk']:
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_walk_억, mode='lines+markers+text', name='워크인 계약액', text=[f"<b>{v:.2f}억</b>" for v in y_walk_억], textposition='top left', textfont=dict(size=15, color='#f97316'), line=dict(color='#f97316', width=3, dash='dot')))
        
        if st.session_state['t_move']:
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_move_억, mode='lines+markers+text', name='입주 계약액', text=[f"<b>{v:.2f}억</b>" for v in y_move_억], textposition='bottom right', textfont=dict(size=15, color='#a855f7'), line=dict(color='#a855f7', width=3, dash='dot')))

        if st.session_state['t_est']:
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_est, mode='lines+markers+text', name='견적건', text=[f"<b>{v:,.0f}건</b>" for v in y_est], textposition='top center', textfont=dict(size=15, color='#4338ca'), line=dict(color='#4338ca', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white')), yaxis='y2'))
        
        if st.session_state['t_cnt']:
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_cnt, mode='lines+markers+text', name='계약건', text=[f"<b>{v:,.0f}건</b>" for v in y_cnt], textposition='bottom center', textfont=dict(size=15, color='#10b981'), line=dict(color='#10b981', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white')), yaxis='y2'))

        if st.session_state['t_rate']:
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_rate, mode='lines+markers+text', name='계약률', text=[f"<b>{v:.1f}%</b>" for v in y_rate], textposition='top right', textfont=dict(size=15, color='#ca8a04'), line=dict(color='#ca8a04', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white')), yaxis='y3'))
        
        if st.session_state['t_unit']:
            fig_trend.add_trace(go.Scatter(x=trend_labels, y=y_unit, mode='lines+markers+text', name='객단가', text=[f"<b>{int(v):,}만</b>" for v in y_unit], textposition='bottom left', textfont=dict(size=15, color='#ec4899'), line=dict(color='#ec4899', width=3), marker=dict(size=marker_sizes, line=dict(width=2, color='white')), yaxis='y4'))
            
        fig_trend.update_layout(
            title=dict(text=f"<b>🎯 {chart_title} 실적 추이</b>", x=0.5, xanchor='center', font=dict(size=18, color='#0f172a')),
            height=520, margin=dict(l=20, r=20, t=100, b=20), plot_bgcolor='white', 
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
            annotations=[dict(xref='paper', yref='paper', x=0, y=1.08, xanchor='left', yanchor='bottom', text='<b>계약액 (억)</b>', font=dict(size=13, color='#1e3a8a'), showarrow=False)],
            yaxis=dict(title="", tickformat=".1f", ticksuffix="억", dtick=0.5, gridcolor='#f1f5f9'),
            yaxis2=dict(title=dict(text="<b>건수 (건)</b>", font=dict(size=13, color='#ea580c')), overlaying='y', side='right', showgrid=False),
            yaxis3=dict(overlaying='y', visible=False),
            yaxis4=dict(overlaying='y', visible=False),
        )
        fig_trend.update_xaxes(showgrid=True, gridcolor='#f1f5f9', tickfont=dict(size=12, color='black'))
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("👆 위 세부 지표 버튼을 클릭하시면 실시간 8주 추이 꺾은선 그래프가 나타납니다.")
    
    st.markdown("---")

    # 🚀 2. 선택 인원 상세 목표대비 실적 바 그래프
    if vt != "충청호남팀 전체":
        comp_df = final_df[~final_df[('기본정보', 'HC명', 'HC명')].str.contains("합계|총계|상권", na=False)]
        total_competitors = len(comp_df)
        unit_str = "팀" if (is_dealer_total or is_region_total) else "명"
        
        def get_rank_str(col_tuple, val):
            if val == 0 or is_region_total: return ""
            ranks = comp_df[col_tuple].rank(method='min', ascending=False)
            t_idx = comp_df[(comp_df[('기본정보', '대리점', '대리점')] == target_row.get(('기본정보', '대리점', '대리점'))) & (comp_df[('기본정보', 'HC명', 'HC명')] == target_row.get(('기본정보', 'HC명', 'HC명')))].index
            if not t_idx.empty:
                return f"🏆 {int(ranks.loc[t_idx[0]])}등 / {total_competitors}{unit_str}"
            return ""

        curr_wk_cols = [c[0] for c in final_df.columns if CURRENT_WEEK in c[0]]
        cw_col = curr_wk_cols[0] if curr_wk_cols else None
        prev_wk_cols = [c[0] for c in final_df.columns if PREV_WEEK and PREV_WEEK in c[0]]
        pw_col = prev_wk_cols[0] if prev_wk_cols else None
        
        st.markdown(f"#### ✨ **상세 목표 대비 실적 요약 (당월 / 전주 / 당주)**")
        
        act1, pct1 = target_row.get(('🎯 당월매출', '인별매출(천)', 'ACT'), 0), target_row.get(('🎯 당월매출', '인별매출(천)', '달성율(%)'), 0)
        rk1 = get_rank_str(('🎯 당월매출', '인별매출(천)', '달성율(%)'), pct1) if not is_dealer_total else ""
        
        act2, pct2 = target_row.get(('🌟 당월 합계', '계약액(천)', 'ACT'), 0), target_row.get(('🌟 당월 합계', '계약액(천)', '달성율(%)'), 0)
        rk2 = get_rank_str(('🌟 당월 합계', '계약액(천)', '달성율(%)'), pct2) if not is_dealer_total else ""
        
        act_m_est, pct_m_est = target_row.get(('🌟 당월 합계', '견적건', 'ACT'), 0), target_row.get(('🌟 당월 합계', '견적건', '달성율(%)'), 0)
        rk_m_est = get_rank_str(('🌟 당월 합계', '견적건', '달성율(%)'), pct_m_est) if not is_dealer_total else ""
        
        act_pw_amt, pct_pw_amt = (target_row.get((pw_col, '계약액(천)', 'ACT'), 0), target_row.get((pw_col, '계약액(천)', '달성율(%)'), 0)) if pw_col else (0, 0)
        rk_pw_amt = get_rank_str((pw_col, '계약액(천)', '달성율(%)'), pct_pw_amt) if pw_col and not is_dealer_total else ""
        
        act_pw_cnt, pct_pw_cnt = (target_row.get((pw_col, '계약건', 'ACT'), 0), target_row.get((pw_col, '계약건', '달성율(%)'), 0)) if pw_col else (0, 0)
        rk_pw_cnt = get_rank_str((pw_col, '계약건', '달성율(%)'), pct_pw_cnt) if pw_col and not is_dealer_total else ""
        
        act_pw_est, pct_pw_est = (target_row.get((pw_col, '견적건', 'ACT'), 0), target_row.get((pw_col, '견적건', '달성율(%)'), 0)) if pw_col else (0, 0)
        rk_pw_est = get_rank_str((pw_col, '견적건', '달성율(%)'), pct_pw_est) if pw_col and not is_dealer_total else ""
        
        act3, pct3 = (target_row.get((cw_col, '계약액(천)', 'ACT'), 0), target_row.get((cw_col, '계약액(천)', '달성율(%)'), 0)) if cw_col else (0, 0)
        rk3 = get_rank_str((cw_col, '계약액(천)', '달성율(%)'), pct3) if cw_col and not is_dealer_total else ""
        
        act4, pct4 = (target_row.get((cw_col, '계약건', 'ACT'), 0), target_row.get((cw_col, '계약건', '달성율(%)'), 0)) if cw_col else (0, 0)
        rk4 = get_rank_str((cw_col, '계약건', '달성율(%)'), pct4) if cw_col and not is_dealer_total else ""
        
        act_cw_est, pct_cw_est = (target_row.get((cw_col, '견적건', 'ACT'), 0), target_row.get((cw_col, '견적건', '달성율(%)'), 0)) if cw_col else (0, 0)
        rk_cw_est = get_rank_str((cw_col, '견적건', '달성율(%)'), pct_cw_est) if cw_col and not is_dealer_total else ""

        mc1, mc2, mc3 = st.columns(3)
        with mc1: 
            st.metric("🌲 당월매출 (천원)", f"{act1:,.0f}", f"{pct1:.1f}% 달성 | {rk1}" if rk1 else f"{pct1:.1f}% 달성", delta_color="off")
            st.metric("🌟 당월 합계 계약액 (천원)", f"{act2:,.0f}", f"{pct2:.1f}% 달성 | {rk2}" if rk2 else f"{pct2:.1f}% 달성", delta_color="off")
            st.metric("🌟 당월 합계 견적건 (건)", f"{act_m_est:,.0f}", f"{pct_m_est:.1f}% 달성 | {rk_m_est}" if rk_m_est else f"{pct_m_est:.1f}% 달성", delta_color="off")
            
        with mc2: 
            if pw_col:
                st.metric(f"⏪ 전주({PREV_WEEK}) 계약액 (천원)", f"{act_pw_amt:,.0f}", f"{pct_pw_amt:.1f}% 달성 | {rk_pw_amt}" if rk_pw_amt else f"{pct_pw_amt:.1f}% 달성", delta_color="off")
                st.metric(f"⏪ 전주({PREV_WEEK}) 계약건 (건)", f"{act_pw_cnt:,.0f}", f"{pct_pw_cnt:.1f}% 달성 | {rk_pw_cnt}" if rk_pw_cnt else f"{pct_pw_cnt:.1f}% 달성", delta_color="off")
                st.metric(f"⏪ 전주({PREV_WEEK}) 견적건 (건)", f"{act_pw_est:,.0f}", f"{pct_pw_est:.1f}% 달성 | {rk_pw_est}" if rk_pw_est else f"{pct_pw_est:.1f}% 달성", delta_color="off")
            else:
                st.metric("⏪ 전주 계약액 (천원)", "-", "해당 데이터 없음", delta_color="off")
                st.metric("⏪ 전주 계약건 (건)", "-", "해당 데이터 없음", delta_color="off")
                st.metric("⏪ 전주 견적건 (건)", "-", "해당 데이터 없음", delta_color="off")
                
        with mc3: 
            st.metric(f"🌊 당주({CURRENT_WEEK}) 계약액 (천원)", f"{act3:,.0f}", f"{pct3:.1f}% 달성 | {rk3}" if rk3 else f"{pct3:.1f}% 달성", delta_color="off")
            st.metric(f"🌊 당주({CURRENT_WEEK}) 계약건 (건)", f"{act4:,.0f}", f"{pct4:.1f}% 달성 | {rk4}" if rk4 else f"{pct4:.1f}% 달성", delta_color="off")
            st.metric(f"🌊 당주({CURRENT_WEEK}) 견적건 (건)", f"{act_cw_est:,.0f}", f"{pct_cw_est:.1f}% 달성 | {rk_cw_est}" if rk_cw_est else f"{pct_cw_est:.1f}% 달성", delta_color="off")
            
        categories = ["당월매출", "당월 합계 계약액", f"{CURRENT_WEEK} 계약액", f"{CURRENT_WEEK} 견적건", f"{CURRENT_WEEK} 계약건"]
        targets = [
            target_row.get(('🎯 당월매출', '인별매출(천)', '목표'), 0), target_row.get(('🌟 당월 합계', '계약액(천)', '목표'), 0),
            target_row.get((cw_col, '계약액(천)', '목표'), 0) if cw_col else 0, target_row.get((cw_col, '견적건', '목표'), 0) if cw_col else 0, target_row.get((cw_col, '계약건', '목표'), 0) if cw_col else 0
        ]
        acts = [
            target_row.get(('🎯 당월매출', '인별매출(천)', 'ACT'), 0), target_row.get(('🌟 당월 합계', '계약액(천)', 'ACT'), 0),
            target_row.get((cw_col, '계약액(천)', 'ACT'), 0) if cw_col else 0, target_row.get((cw_col, '견적건', 'ACT'), 0) if cw_col else 0, target_row.get((cw_col, '계약건', 'ACT'), 0) if cw_col else 0
        ]
        pcts = [pct1, pct2, pct3, target_row.get((cw_col, '견적건', '달성율(%)'), 0) if cw_col else 0, pct4]

        text_targets = [f"{v:,.0f}건" if "건" in c else f"{v:,.0f}" for v, c in zip(targets, categories)]
        text_acts = [f"<b>{v:,.0f}</b>건<br>({p:.1f}%)" if "건" in c else f"<b>{v:,.0f}</b><br>({p:.1f}%)" for v, p, c in zip(acts, pcts, categories)]
        act_colors = ['#10b981' if p >= 100 else '#3b82f6' for p in pcts]

        cat_amt, tgt_amt, act_amt, tt_amt, ta_amt, ac_amt = categories[:3], targets[:3], acts[:3], text_targets[:3], text_acts[:3], act_colors[:3]
        cat_cnt, tgt_cnt, act_cnt, tt_cnt, ta_cnt, ac_cnt = categories[3:], targets[3:], acts[3:], text_targets[3:], text_acts[3:], act_colors[3:]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=cat_amt, y=tgt_amt, name='🎯 목표', marker_color='#cbd5e1', text=tt_amt, textposition='outside', textfont=dict(size=14, color='#1e293b'), yaxis='y1'))
        fig.add_trace(go.Bar(x=cat_amt, y=act_amt, name='🔥 실적(ACT)', marker_color=ac_amt, text=ta_amt, textposition='outside', textfont=dict(size=15, color='#0f172a'), yaxis='y1'))
        fig.add_trace(go.Bar(x=cat_cnt, y=tgt_cnt, name='🎯 목표(건수)', marker_color='#cbd5e1', text=tt_cnt, textposition='outside', textfont=dict(size=14, color='#1e293b'), yaxis='y2', showlegend=False))
        fig.add_trace(go.Bar(x=cat_cnt, y=act_cnt, name='🔥 실적(건수)', marker_color=ac_cnt, text=ta_cnt, textposition='outside', textfont=dict(size=15, color='#0f172a'), yaxis='y2', showlegend=False))
        
        fig.update_layout(
            barmode='group', height=450, xaxis=dict(tickangle=0, tickfont=dict(size=14, color='black')), 
            yaxis=dict(title=dict(text="<b>금액 (천원)</b>", font=dict(size=13, color='#1e3a8a')), tickfont=dict(size=12, color='#1e3a8a')),
            yaxis2=dict(title=dict(text="<b>건수 (건)</b>", font=dict(size=13, color='#ea580c')), tickfont=dict(size=12, color='#ea580c'), overlaying='y', side='right'),
            margin=dict(l=20, r=20, t=70, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14, color='black')), plot_bgcolor='white'
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")

    # 🚀 3. 상세 표 출력
    st.markdown(f"""
    <div style='background-color: #f8fafc; padding: 15px; border-left: 5px solid #3b82f6; border-radius: 5px; margin-bottom: 20px;'>
        <h4 style='margin:0; color: #1e3a8a;'>📌 {current_month}월 {CURRENT_WEEK} VDT 현황 표</h4>
    </div>
    """, unsafe_allow_html=True)
    
    def render_custom_html_table(df):
        dealer_col, hc_col = ('기본정보', '대리점', '대리점'), ('기본정보', 'HC명', 'HC명')
        unique_dealers = [d for d in df[dealer_col].unique() if d not in ["🌟 총계"]]
        dealer_colors = {}
        colors = ['#f8fafc', '#ffffff']
        for idx, d in enumerate(unique_dealers): dealer_colors[d] = colors[idx % len(colors)]
            
        col_widths = [80, 90, 70, 70, 70, 70, 70, 70, 55, 55, 55, 55, 55, 55]
        col_lefts = [0, 80, 170, 240, 310, 380, 450, 520, 590, 645, 700, 755, 810, 865]
        html = ["<div class='vdt-table-container'><table class='vdt-table'><thead>"]
        
        html.append("<tr>")
        html.append(f"<th rowspan='3' style='position: sticky; top: 0; left: 0; z-index: 20; background-color: #0f172a; min-width: {col_widths[0]}px; max-width: {col_widths[0]}px; border-right: 1px solid #cbd5e1;'>대리점</th>")
        html.append(f"<th rowspan='3' style='position: sticky; top: 0; left: {col_lefts[1]}px; z-index: 20; background-color: #0f172a; min-width: {col_widths[1]}px; max-width: {col_widths[1]}px; border-right: 2px solid #94a3b8;'>HC명</th>")
        
        headers_l1 = []
        for col in df.columns[2:]:
            if col[0] not in headers_l1: headers_l1.append(col[0])
                
        for h1 in headers_l1:
            is_curr, is_monthly = CURRENT_WEEK in h1, "당월" in h1
            style_parts = ["position: sticky; top: 0;"]
            
            if is_curr: style_parts.extend(["background-color: #1e3a8a;", "border: 3px solid #60a5fa;"])
            elif is_monthly: style_parts.extend(["background-color: #064e3b;", "color: #a7f3d0;", "border-top: 2px solid #047857;"])
            else: style_parts.append("background-color: #0f172a;")
                
            if h1 == '🎯 당월매출':
                style_parts.extend([f"left: {col_lefts[2]}px;", "z-index: 15;", "border-right: 3px solid #1e293b;"])
                html.append(f"<th colspan='3' style='{'; '.join(style_parts)}'>{h1}</th>")
            elif "🌟 당월 합계" in h1:
                style_parts.extend([f"left: {col_lefts[5]}px;", "z-index: 15;", "border-right: 4px solid #94a3b8;"])
                html.append(f"<th colspan='9' style='{'; '.join(style_parts)}'>{h1}</th>")
            else:
                style_parts.append("z-index: 10;")
                html.append(f"<th colspan='9' style='{'; '.join(style_parts)}'>{h1}</th>")
        html.append("</tr>")
        
        html.append("<tr>")
        for h1 in headers_l1:
            is_curr, is_monthly = CURRENT_WEEK in h1, "당월" in h1
            base_styles = ["position: sticky; top: 33px;"]
            if is_curr: base_styles.extend(["background-color: #1e40af;", "border-left: 3px solid #60a5fa;", "border-right: 3px solid #60a5fa;"])
            elif is_monthly: base_styles.extend(["background-color: #065f46;", "color: #a7f3d0;"])
            else: base_styles.append("background-color: #0f172a;")
            
            if h1 == '🎯 당월매출':
                s_parts = base_styles.copy() + [f"left: {col_lefts[2]}px;", "z-index: 15;", "border-right: 3px solid #1e293b;"]
                html.append(f"<th colspan='3' style='{'; '.join(s_parts)}'>인별매출(천)</th>")
            elif "🌟 당월 합계" in h1:
                s1, s2, s3 = base_styles.copy() + [f"left: {col_lefts[5]}px;", "z-index: 15;"], base_styles.copy() + [f"left: {col_lefts[8]}px;", "z-index: 15;"], base_styles.copy() + [f"left: {col_lefts[11]}px;", "z-index: 15;", "border-right: 4px solid #94a3b8;"]
                html.append(f"<th colspan='3' style='{'; '.join(s1)}'>계약액(천)</th><th colspan='3' style='{'; '.join(s2)}'>견적건</th><th colspan='3' style='{'; '.join(s3)}'>계약건</th>")
            else:
                bg_style = f"style='{'; '.join(base_styles + ['z-index: 10;'])}'"
                html.append(f"<th colspan='3' {bg_style}>계약액(천)</th><th colspan='3' {bg_style}>견적건</th><th colspan='3' {bg_style}>계약건</th>")
        html.append("</tr>")
        
        html.append("<tr>")
        for c_idx, col in enumerate(df.columns[2:]):
            abs_idx = c_idx + 2
            is_curr, is_monthly = CURRENT_WEEK in col[0], "당월" in col[0]
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
            html.append(f"<th {bg_style}>{col[2]}</th>")
        html.append("</tr></thead><tbody>")
        
        for r_idx in range(len(df)):
            row = df.iloc[r_idx]
            dealer, hc = row[dealer_col], row[hc_col]
            
            if str(hc) == "합계": bg_color, row_bg = "#e2e8f0", "style='background-color: #e2e8f0; font-weight: bold;'"
            elif "🌟" in str(hc): bg_color, row_bg = "#cbd5e1", "style='background-color: #cbd5e1; font-weight: bold;'"
            else: bg_color, row_bg = dealer_colors.get(dealer, '#ffffff'), f"style='background-color: {dealer_colors.get(dealer, '#ffffff')};'"
                
            html.append(f"<tr {row_bg}>")
            html.append(f"<td class='text-center' style='position: sticky; left: 0; z-index: 6; background-color: {bg_color}; min-width: {col_widths[0]}px; max-width: {col_widths[0]}px; border-right: 1px solid #cbd5e1;'>{dealer}</td>")
            html.append(f"<td class='text-center' style='position: sticky; left: {col_lefts[1]}px; z-index: 6; background-color: {bg_color}; min-width: {col_widths[1]}px; max-width: {col_widths[1]}px; border-right: 2px solid #94a3b8;'>{hc}</td>")
            
            for c_idx, val in enumerate(row[2:]):
                abs_idx = c_idx + 2
                col_obj = df.columns[c_idx + 2]
                is_curr, is_monthly = CURRENT_WEEK in col_obj[0], "당월" in col_obj[0]
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
                    val_str = f"{val:.1f}%"
                    if val >= 100: val_str = f"<span style='color: #047857; font-weight: 900;'>{val_str}</span>" if is_monthly else f"<span style='color: #1d4ed8; font-weight: 900;'>{val_str}</span>"
                    elif val > 0: val_str = f"<span style='font-weight: 600;'>{val_str}</span>"
                else: val_str = f"{val:,.0f}"
                    
                border_style = f"{'; '.join(style_parts)}" if style_parts else ""
                html.append(f"<td style='{border_style}'>{val_str}</td>")
            html.append("</tr>")
            
        html.append("</tbody></table></div>")
        return "".join(html)
    
    table_html = render_custom_html_table(final_df)
    st.markdown(table_html, unsafe_allow_html=True)
