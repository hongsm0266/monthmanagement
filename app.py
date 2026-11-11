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

st.set_page_config(page_title="충청호남팀 영업사원 주차별 VDT 목표 관리", layout="wide")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1yZdc4BL5CHLwBQ2QGp8zD5_ov7LDKsEcnrONdQvDyHI/edit?gid=1748736055#gid=1748736055"

if 'init_v22' not in st.session_state:
    st.session_state.update({'view_target': "충청호남팀 전체", 'hc_selector': "✨ 인원별 상세 실적 (선택 시 우선 적용)", 
                             'view_mode': "주간 추이 (최근 8주)", 't_amt': True, 't_sales': False, 't_next': False,
                             't_avg': False, 't_wd': False, 't_we': False, 't_walk': False, 't_move': False,
                             't_est': False, 't_cnt': False, 't_rate': False, 't_unit': False, 
                             'wow_prev': None, 'wow_curr': None, 'init_v22': True})

toggle_keys = ['t_amt', 't_sales', 't_next', 't_avg', 't_wd', 't_we', 't_walk', 't_move', 't_est', 't_cnt', 't_rate', 't_unit']
EXCLUDED_HCS = ["장재형", "강지인", "신재민"]

@st.cache_resource
def init_connection():
    try:
        creds_dict = json.loads(st.secrets["gcp"]["key"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"구글 API 키 오류: {e}")
        return None

client = init_connection()

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
    html, body, [class*="css"], [class*="st-"], th, td { font-family: 'Noto Sans KR', sans-serif !important; }
    .vdt-table-container { width: 100%; max-height: 65vh; overflow: auto; border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 10px; }
    .vdt-table-container::-webkit-scrollbar { width: 14px; height: 14px; }
    .vdt-table-container::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 8px; }
    .vdt-table-container::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 8px; border: 3px solid #f1f5f9; }
    .vdt-table { width: 100%; border-collapse: collapse; font-size: 12px; white-space: nowrap; }
    .vdt-table thead th { height: 34px; position: sticky; z-index: 10; }
    .vdt-table thead tr:nth-child(1) th { top: 0; }
    .vdt-table thead tr:nth-child(2) th { top: 33px; }
    .vdt-table thead tr:nth-child(3) th { top: 66px; }
    .vdt-table th { background-color: #0f172a; color: white; padding: 8px 10px; text-align: center; border: 1px solid #334155; font-weight: 600; }
    .vdt-table td { padding: 6px 10px; text-align: right; border: 1px solid #e2e8f0; }
    .title-box { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 12px; border-radius: 8px; margin-bottom: 12px; }
    h1, h3, h4 { font-weight: 900 !important; margin: 0; }
    h1 { font-size: 14px !important; color: white !important; }
    h4 { font-size: 14px !important; color: #1e293b !important; }
    .wow-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .wow-table th { background-color: #1e293b; color: white; padding: 6px; text-align: center; border: 1px solid #334155; font-weight: 900; font-size: 12px;}
    .wow-table td { padding: 6px; text-align: right; border: 1px solid #cbd5e1; background-color: white; font-size: 13px;}
    .wow-table td.name-col { text-align: center; font-weight: 900; background-color: #f8fafc; color: #0f172a; }
    .wow-up { color: #dc2626; font-weight: 900; }
    .wow-down { color: #2563eb; font-weight: 900; }
    .wow-same { color: #64748b; font-weight: 600; }
    div.stButton > button { background: #f8fafc !important; color: #020617 !important; font-size: 12px !important; font-weight: 900 !important; border-radius: 6px !important; padding: 4px 6px !important; border: 1px solid #94a3b8 !important; height: auto !important; min-height: 32px; border-bottom: 2px solid #64748b !important; transition: all 0.1s ease !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(180deg, #fee2e2 0%, #fecaca 100%) !important; color: #991b1b !important; border: 1px solid #f87171 !important; border-bottom: 2px solid #ef4444 !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(1) button { background-color: #faf5ff !important; border-color: #e9d5ff !important; color: #9333ea !important; border-bottom: 2px solid #d8b4fe !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(1) button[kind="primary"] { background: linear-gradient(180deg, #f3e8ff 0%, #e9d5ff 100%) !important; color: #3b0764 !important; border-bottom: 2px solid #7e22ce !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(3) button { background-color: #f0f9ff !important; border-color: #bae6fd !important; color: #0284c7 !important; border-bottom: 2px solid #7dd3fc !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(3) button[kind="primary"] { background: linear-gradient(180deg, #e0f2fe 0%, #bae6fd 100%) !important; color: #082f49 !important; border-bottom: 2px solid #0284c7 !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(9) button { background-color: #f0fdf4 !important; border-color: #bbf7d0 !important; color: #16a34a !important; border-bottom: 2px solid #86efac !important; }
    #org-buttons + div[data-testid="stHorizontalBlock"] > div:nth-child(9) button[kind="primary"] { background: linear-gradient(180deg, #dcfce7 0%, #bbf7d0 100%) !important; color: #052e16 !important; border-bottom: 2px solid #16a34a !important; }
    .chart-btn-group { font-size: 11px; font-weight: 800; color: #475569; background: #e2e8f0; border-radius: 4px; padding: 2px 0; text-align: center; margin-bottom: 4px; border: 1px solid #cbd5e1;}
</style>
""", unsafe_allow_html=True)

current_date = datetime.now()
current_month = current_date.month
st.markdown(f"<div class='title-box'><h1>📊 충청호남팀 영업사원 주차별 VDT 목표 관리 ({current_month}월)</h1></div>", unsafe_allow_html=True)

def clean_str(val): return re.sub(r'\s+', '', str(val))
def safe_get(row, idx): return str(row[idx]).strip() if len(row) > idx else ""
def clean_val(v):
    if not v or pd.isna(v): return 0.0
    v_str = str(v).replace('%', '').replace(',', '').replace('원', '').replace('건', '').strip()
    m = 100000000 if '억' in v_str else (10000 if '만' in v_str else 1)
    v_str = re.sub(r'[^\d\.-]', '', v_str)
    return float(v_str) * m if v_str else 0.0

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
    trend_labels.append(f"{iso_week}주 ({w_start.strftime('%m.%d')}~{w_end.strftime('%m.%d')})")

def get_trend_week_idx(m, d):
    try:
        t_d = datetime(current_date.year, m, d).date()
        for i, (s, e) in enumerate(trend_ranges):
            if s.date() <= t_d <= e.date(): return i
    except: pass
    return -1

month_list, month_labels = [8, 9, 10, 11], ["8월", "9월", "10월", "11월"]

def safe_api_call(func, *args, **kwargs):
    for attempt in range(6):
        try: return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and attempt < 5:
                time.sleep(15 * (attempt + 1))
                continue
            raise e

@st.cache_data(ttl=600, show_spinner=False)
def load_vdt_data():
    if not client: return pd.DataFrame(), {}, {}, {}, {}, [], {}, ""
    try:
        sh = safe_api_call(client.open_by_url, SHEET_URL)
        all_ws_objs = safe_api_call(sh.worksheets)
        all_ws = [ws.title for ws in all_ws_objs]
        if "주차별 목표 세팅" not in all_ws: return pd.DataFrame(), {}, {}, {}, {}, [], {}, ""
        
        target_ws = sh.worksheet("주차별 목표 세팅")
        all_targets = safe_api_call(target_ws.get_all_values)
        
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
        valid_dealers = list(set(d for d, _, _ in hc_info_raw))
        
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
        
        daily_ws = None
        for ws in all_ws_objs:
            if "모음" in ws.title or "통합" in ws.title:
                daily_ws = ws
                break
        
        if not daily_ws: return pd.DataFrame(), {}, {}, {}, {}, [], {}, ""
            
        all_daily_data = safe_api_call(daily_ws.get_all_values)
        
        acts = {clean_str(hc): {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for _, hc, _ in hc_info_raw}
        month_acts = {clean_str(hc): {'amt': 0, 'est': 0, 'cnt': 0} for _, hc, _ in hc_info_raw}
        
        rdm = {d: {'amt': 0, 'est': 0, 'cnt': 0} for d in valid_dealers}
        rdw = {d: {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for d in valid_dealers}
        
        def new_d(): return [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(8)]
        def new_m(): return [{'amt':0, 'est':0, 'cnt':0, 'amt_wd':0, 'amt_we':0, 'sales':0, 'next_sales':0, 'amt_move':0} for _ in range(4)]
        
        trend_hc_w = {clean_str(hc): new_d() for _, hc, _ in hc_info_raw}
        trend_dlr_w = {d: new_d() for d in valid_dealers}
        trend_tot_w = new_d()
        
        trend_hc_m = {clean_str(hc): new_m() for _, hc, _ in hc_info_raw}
        trend_dlr_m = {d: new_m() for d in valid_dealers}
        trend_tot_m = new_m()
        existing_hcs = [clean_str(h) for d, h, t in hc_info_raw]
        
        latest_sales_dict = {} 

        curr_m, curr_d = -1, -1
        curr_mode = ""
        wk_info, tr_idx, mo_idx, is_we = None, -1, -1, False

        for r_idx, row in enumerate(all_daily_data):
            # 🚀 날짜 및 이정표 파싱 로직 초강력 보강! (연도 무시하고 정확히 달/일 추출)
            row_header = clean_str("".join([safe_get(row, i) for i in range(min(5, len(row)))]))
            
            if "일반" in row_header or "입주" in row_header:
                date_match = re.search(r'(?:20\d{2}[년/.-]\s*)?([01]?\d)[월/.-]\s*([0-3]?\d)일?', row_header)
                if date_match:
                    curr_m, curr_d = int(date_match.group(1)), int(date_match.group(2))
                    wk_info = date_to_target_week.get((curr_m, curr_d))
                    tr_idx = get_trend_week_idx(curr_m, curr_d)
                    mo_idx = month_list.index(curr_m) if curr_m in month_list else -1
                    try: is_we = datetime(current_date.year, curr_m, curr_d).weekday() >= 5
                    except: is_we = False
                    
                if "일반" in row_header: curr_mode = "일반"
                elif "입주" in row_header: curr_mode = "입주"
                continue
                
            if curr_mode == "일반" and len(row) > 3:
                t_est, t_cnt = clean_val(safe_get(row, 4)), clean_val(safe_get(row, 5))
                t_amt = clean_val(safe_get(row, 15)) 
                t_sales = clean_val(safe_get(row, 18)) 
                t_next = clean_val(safe_get(row, 24))  
                
                hc_name = clean_str(safe_get(row, 3)) 
                if not hc_name and len(row) > 1: hc_name = clean_str(safe_get(row, 1)) 
                
                if any(x in hc_name for x in ['합계', '소계', '총계', '목표', '사번', '비고', '계']): continue
                dc = hc_name.replace("팀", "").replace("대리점", "").strip()
                if dc in valid_dealers or dc in ["충청상권", "호남상권", "세종2"]: continue
                if not hc_name: continue 
                    
                md = hc_to_dealer_master.get(hc_name)
                if not md:
                    md = get_mapped_dealer(clean_str("".join([safe_get(row, i) for i in range(4)])))
                    if not md or md not in valid_dealers: md = "기타"
                    
                if hc_name not in existing_hcs:
                    hc_info_raw.append((md, hc_name, 0.0))
                    existing_hcs.append(hc_name)
                    acts[hc_name] = {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys}
                    month_acts[hc_name] = {'amt': 0, 'est': 0, 'cnt': 0}
                    hc_to_dealer_master[hc_name] = md
                    trend_hc_w[hc_name], trend_hc_m[hc_name] = new_d(), new_m()
                    if md not in valid_dealers:
                        valid_dealers.append(md)
                        rdm[md], rdw[md] = {'amt': 0, 'est': 0, 'cnt': 0}, {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys}
                        trend_dlr_w[md], trend_dlr_m[md] = new_d(), new_m()

                if wk_info:
                    acts[hc_name][wk_info]['est'] += t_est
                    acts[hc_name][wk_info]['cnt'] += t_cnt
                    acts[hc_name][wk_info]['amt'] += t_amt
                    if curr_m == current_month:
                        month_acts[hc_name]['est'] += t_est
                        month_acts[hc_name]['cnt'] += t_cnt
                        month_acts[hc_name]['amt'] += t_amt
                            
                    if md in valid_dealers:
                        if wk_info in rdw[md]:
                            rdw[md][wk_info]['est'] += t_est
                            rdw[md][wk_info]['cnt'] += t_cnt
                            rdw[md][wk_info]['amt'] += t_amt
                        if curr_m == current_month:
                            rdm[md]['est'] += t_est
                            rdm[md]['cnt'] += t_cnt
                            rdm[md]['amt'] += t_amt

                if tr_idx != -1:
                    trend_hc_w[hc_name][tr_idx]['est'] += t_est
                    trend_hc_w[hc_name][tr_idx]['cnt'] += t_cnt
                    trend_hc_w[hc_name][tr_idx]['amt'] += t_amt
                    trend_hc_w[hc_name][tr_idx]['sales'] = t_sales
                    trend_hc_w[hc_name][tr_idx]['next_sales'] = t_next
                    if is_we: trend_hc_w[hc_name][tr_idx]['amt_we'] += t_amt
                    else: trend_hc_w[hc_name][tr_idx]['amt_wd'] += t_amt
                        
                if mo_idx != -1:
                    trend_hc_m[hc_name][mo_idx]['est'] += t_est
                    trend_hc_m[hc_name][mo_idx]['cnt'] += t_cnt
                    trend_hc_m[hc_name][mo_idx]['amt'] += t_amt
                    trend_hc_m[hc_name][mo_idx]['sales'] = t_sales
                    trend_hc_m[hc_name][mo_idx]['next_sales'] = t_next
                    if is_we: trend_hc_m[hc_name][mo_idx]['amt_we'] += t_amt
                    else: trend_hc_m[hc_name][mo_idx]['amt_wd'] += t_amt
                        
                if t_sales > 0: latest_sales_dict[hc_name] = t_sales

            elif curr_mode == "입주" and len(row) > 3:
                hc_name = clean_str(safe_get(row, 1)) 
                if not hc_name: hc_name = clean_str(safe_get(row, 3))
                
                if not hc_name or any(x in hc_name for x in ['합계', '소계', '총계', '목표', '대리점', '계']): continue
                dc = hc_name.replace("팀", "").replace("대리점", "").strip()
                if dc in valid_dealers or dc in ["충청상권", "호남상권", "세종2"]: continue
                
                m_m, m_r = clean_val(safe_get(row, 12)), clean_val(safe_get(row, 17))
                dm = m_m + m_r
                md = hc_to_dealer_master.get(hc_name)
                
                if not md or md not in valid_dealers: continue
                if tr_idx != -1: trend_hc_w[hc_name][tr_idx]['amt_move'] += dm
                if mo_idx != -1: trend_hc_m[hc_name][mo_idx]['amt_move'] += dm

        for hc in existing_hcs:
            md = hc_to_dealer_master.get(hc, "기타")
            if md in valid_dealers:
                for i in range(8):
                    for k in ['sales', 'next_sales', 'est', 'cnt', 'amt', 'amt_we', 'amt_wd', 'amt_move']:
                        trend_dlr_w[md][i][k] += trend_hc_w[hc][i][k]
                        trend_tot_w[i][k] += trend_hc_w[hc][i][k]
                for i in range(4):
                    for k in ['sales', 'next_sales', 'est', 'cnt', 'amt', 'amt_we', 'amt_wd', 'amt_move']:
                        trend_dlr_m[md][i][k] += trend_hc_m[hc][i][k]
                        trend_tot_m[i][k] += trend_hc_m[hc][i][k]

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
            targets[hc_c] = {wk: {'amt': dealer_targets.get(d, {}).get(wk, {}).get('amt', 0) * wt, 'est': dealer_targets.get(d, {}).get(wk, {}).get('est', 0) * wt, 'cnt': dealer_targets.get(d, {}).get(wk, {}).get('cnt', 0) * wt} for wk in week_keys}

        col_tuples = [('기본정보', '대리점', '대리점'), ('기본정보', 'HC명', 'HC명'), ('🎯 당월매출', '인별매출(천)', '목표'), ('🎯 당월매출', '인별매출(천)', 'ACT'), ('🎯 당월매출', '인별매출(천)', '달성율(%)'), ('🌟 당월 합계', '계약액(천)', '목표'), ('🌟 당월 합계', '계약액(천)', 'ACT'), ('🌟 당월 합계', '계약액(천)', '달성율(%)'), ('🌟 당월 합계', '견적건', '목표'), ('🌟 당월 합계', '견적건', 'ACT'), ('🌟 당월 합계', '견적건', '달성율(%)'), ('🌟 당월 합계', '계약건', '목표'), ('🌟 당월 합계', '계약건', 'ACT'), ('🌟 당월 합계', '계약건', '달성율(%)')]
        for wk in week_keys:
            wl = f"{wk} ({date_headers.get(wk, '')})"
            for k in ['계약액(천)', '견적건', '계약건']:
                col_tuples.extend([(wl, k, '목표'), (wl, k, 'ACT'), (wl, k, '달성율(%)')])
            
        columns = pd.MultiIndex.from_tuples(col_tuples, names=['주차', '항목', '구분'])
        rows = []
        for d, hc, _ in hc_info_raw:
            hc_c = clean_str(hc)
            if hc_c in EXCLUDED_HCS: continue
            tgt, ma, sa = final_hc_sales_tgt.get(hc_c, 0.0), month_acts.get(hc_c, {'amt':0,'est':0,'cnt':0}), latest_sales_dict.get(hc_c, 0.0)
            if tgt == 0.0 and ma['amt'] == 0 and ma['est'] == 0 and ma['cnt'] == 0 and sa == 0: continue
            
            r_d = [d, hc, tgt, sa, 0.0, sum([targets.get(hc_c, {}).get(wk, {}).get('amt', 0) for wk in week_keys]), ma['amt'], 0.0, sum([targets.get(hc_c, {}).get(wk, {}).get('est', 0) for wk in week_keys]), ma['est'], 0.0, sum([targets.get(hc_c, {}).get(wk, {}).get('cnt', 0) for wk in week_keys]), ma['cnt'], 0.0]
            for wk in week_keys:
                t, a = targets.get(hc_c, {}).get(wk, {'amt':0,'est':0,'cnt':0}), acts.get(hc_c, {}).get(wk, {'amt':0,'est':0,'cnt':0})
                r_d.extend([t['amt'], a['amt'], 0.0, t['est'], a['est'], 0.0, t['cnt'], a['cnt'], 0.0])
            rows.append(r_d)

        df = pd.DataFrame(rows, columns=columns)
        for c in df.columns[2:]:
            if c[2] == '달성율(%)': df[c] = np.where(df[(c[0], c[1], '목표')] > 0, (df[(c[0], c[1], 'ACT')] / df[(c[0], c[1], '목표')] * 100).round(0), 0)
        
        trend_reg_w = {k: new_d() for k in REGION_MAP.keys()}
        trend_reg_m = {k: new_m() for k in REGION_MAP.keys()}
        
        for reg, dlrs in REGION_MAP.items():
            for d in dlrs:
                dw, dm = trend_dlr_w.get(d, new_d()), trend_dlr_m.get(d, new_m())
                for i in range(8):
                    for k in ['sales', 'next_sales', 'est', 'cnt', 'amt', 'amt_we', 'amt_wd', 'amt_move']: trend_reg_w[reg][i][k] += dw[i][k]
                for i in range(4):
                    for k in ['sales', 'next_sales', 'est', 'cnt', 'amt', 'amt_we', 'amt_wd', 'amt_move']: trend_reg_m[reg][i][k] += dm[i][k]

        ctw = date_to_target_week.get((curr_m if curr_m != -1 else current_date.month, curr_d if curr_d != -1 else current_date.day), week_keys[-1] if week_keys else '1주차')
        tp = {'W': {'hc': trend_hc_w, 'dlr': trend_dlr_w, 'tot': trend_tot_w, 'reg': trend_reg_w}, 'M': {'hc': trend_hc_m, 'dlr': trend_dlr_m, 'tot': trend_tot_m, 'reg': trend_reg_m}}
        
        return df, date_headers, hc_to_dealer_master, rdm, rdw, week_keys, tp, ctw

    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame(), {}, {}, {}, {}, [], {}, ""

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
            if c[2] == '달성율(%)': stot[c] = round((stot[(c[0],c[1],'ACT')] / stot[(c[0],c[1],'목표')] * 100), 0) if stot[(c[0],c[1],'목표')] > 0 else 0.0
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
        if c[2] == '달성율(%)': gt[c] = round((gt[(c[0],c[1],'ACT')] / gt[(c[0],c[1],'목표')] * 100), 0) if gt[(c[0],c[1],'목표')] > 0 else 0.0
    rr.append(pd.Series(gt))
    return pd.DataFrame(rr)

with st.spinner("🚀 최신 일보 데이터를 초고속으로 스캔하고 있습니다..."):
    df_raw, date_headers, hc_to_dealer_master, rdm, rdw, week_keys_list, trend_pack, CURRENT_TABLE_WEEK = load_vdt_data()

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
            elif "대리점" in vt: return trend_pack['W']['dlr'].get(hc_or_dlr_key, [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0} for _ in range(8)])[idx]
            else: return trend_pack['W']['hc'].get(hc_or_dlr_key, [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0} for _ in range(8)])[idx]
        elif label in month_labels:
            idx = month_labels.index(label)
            if vt == "충청호남팀 전체": return trend_pack['M']['tot'][idx]
            elif vt in ["충청팀 통합", "호남팀 통합"]: return trend_pack['M']['reg'][hc_or_dlr_key][idx]
            elif "대리점" in vt: return trend_pack['M']['dlr'].get(hc_or_dlr_key, [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0} for _ in range(4)])[idx]
            else: return trend_pack['M']['hc'].get(hc_or_dlr_key, [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0} for _ in range(4)])[idx]
        return {'amt':0,'est':0,'cnt':0,'sales':0,'amt_move':0}
    
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

    # 🚀 1. 브리핑 보드
    st.markdown("#### 💡 **주/월 종합지표 비교**")
    all_options = list(reversed(trend_labels)) + list(reversed(month_labels))
    
    if st.session_state.get('wow_curr') not in all_options: 
        st.session_state['wow_curr'] = all_options[0]
    if st.session_state.get('wow_prev') not in all_options: 
        st.session_state['wow_prev'] = all_options[1] if len(all_options)>1 else all_options[0]
        
    w1, w2 = st.columns([1, 1])
    with w1: 
        st.markdown("<div style='font-size:14px; font-weight:900; color:#1e293b; margin-bottom:5px;'>⬅️ 비교 기준 주/월 (과거)</div>", unsafe_allow_html=True)
        sel_prev = st.selectbox("비교 기준", options=all_options, key="wow_prev", label_visibility="collapsed")
    with w2: 
        st.markdown("<div style='font-size:14px; font-weight:900; color:#dc2626; margin-bottom:5px;'>➡️ 회의 조회 주/월 (현재)</div>", unsafe_allow_html=True)
        sel_curr = st.selectbox("조회 기준", options=all_options, key="wow_curr", label_visibility="collapsed")
        
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

    pv = get_period_data(sel_prev, data_key)
    tv = get_period_data(sel_curr, data_key)
    
    pa, ta, ps, ts = pv.get('amt',0), tv.get('amt',0), pv.get('sales',0), tv.get('sales',0)
    pe, te, pc, tc = pv.get('est',0), tv.get('est',0), pv.get('cnt',0), tv.get('cnt',0)
    pm, tm = pv.get('amt_move',0), tv.get('amt_move',0)
    pw, tw = pa - pm, ta - tm
    pr, tr = (pc/pe*100) if pe>0 else 0, (tc/te*100) if te>0 else 0
    pu, tu = (pa/(pc*10)) if pc>0 else 0, (ta/(tc*10)) if tc>0 else 0

    html_wow = [
        '<table class="wow-table" style="width: 100%; border: 2px solid #94a3b8; border-radius: 8px; overflow: hidden;">',
        '<thead><tr style="background-color: #1e293b; color: white;">',
        f'<th style="padding: 10px; font-size: 13px; border-right: 2px solid #94a3b8;">주차/월 구분<br><span style="font-size:11px; color:#cbd5e1;">({ct})</span></th>',
        '<th style="padding: 10px;">💰 총 계약액<br>(천원)</th><th style="padding: 10px;">💰 총 매출액<br>(천원)</th><th style="padding: 10px;">📝 견적건<br>(건)</th><th style="padding: 10px;">🤝 계약건<br>(건)</th>',
        '<th style="padding: 10px; background-color:#334155;">🚶 워크인 계약액<br>(천원)</th><th style="padding: 10px; background-color:#334155;">🏠 입주 계약액<br>(천원)</th>',
        '<th style="padding: 10px;">📊 계약률<br>(%)</th><th style="padding: 10px;">💸 객단가<br>(만원)</th></tr></thead><tbody>'
    ]
    html_wow.append(f"<tr style='background-color: #f8fafc;'><td style='text-align:center; font-weight:900; border-right:2px solid #94a3b8;'>{sel_prev}<br><span style='font-size:11px; color:#64748b;'>(비교 대상)</span></td>" + td_val(pa)+td_val(ps)+td_val(pe)+td_val(pc)+td_val(pw,bg='#f1f5f9')+td_val(pm,bg='#f1f5f9')+td_val(pr,True)+td_val(pu,False,True) + "</tr>")
    html_wow.append(f"<tr style='background-color: white;'><td style='text-align:center; font-weight:900; color:#1e3a8a; border-right:2px solid #94a3b8;'>{sel_curr}<br><span style='font-size:11px; color:#64748b;'>(조회 기준)</span></td>" + td_val(ta,is_tgt=True)+td_val(ts,is_tgt=True)+td_val(te,is_tgt=True)+td_val(tc,is_tgt=True)+td_val(tw,is_tgt=True,bg='#f1f5f9')+td_val(tm,is_tgt=True,bg='#f1f5f9')+td_val(tr,True,is_tgt=True)+td_val(tu,False,True,is_tgt=True) + "</tr>")
    html_wow.append(f"<tr style='background-color: #fef2f2;'><td style='text-align:center; font-weight:900; color:#b91c1c; border-right:2px solid #94a3b8;'>지표 간 증감</td>" + td_cell(ta,pa)+td_cell(ts,ps)+td_cell(te,pe)+td_cell(tc,pc)+td_cell(tw,pw)+td_cell(tm,pm)+td_cell(tr,pr,is_rate=True)+td_cell(tu,pu,is_unit=True) + "</tr></tbody></table>")
    
    st.markdown("".join(html_wow), unsafe_allow_html=True)
    st.markdown("---")

    # 🚀 2. 조직 선택
    st.markdown("#### 🔎 **실적 조회 (조직 및 인원 선택)**")
    st.markdown('<div id="org-buttons"></div>', unsafe_allow_html=True)
    c_o = st.columns([12, 2, 12, 9, 9, 9, 9, 2, 12, 9, 9, 9, 30])
    with c_o[0]: st.button("I 전체통합" if vt != "충청호남팀 전체" else "✅ 전체통합", type=btn_type("충청호남팀 전체"), on_click=set_view, args=("충청호남팀 전체",), use_container_width=True)
    with c_o[1]: st.markdown("<div style='text-align:center; padding-top:5px; color:#cbd5e1; font-weight:bold; font-size:16px;'>|</div>", unsafe_allow_html=True)
    with c_o[2]: st.button("I 충청통합" if vt != "충청팀 통합" else "✅ 충청통합", type=btn_type("충청팀 통합"), on_click=set_view, args=("충청팀 통합",), use_container_width=True)
    with c_o[3]: st.button("둔산" if vt != "둔산 대리점" else "✅ 둔산", type=btn_type("둔산 대리점"), on_click=set_view, args=("둔산 대리점",), use_container_width=True)
    with c_o[4]: st.button("세종" if vt != "세종 대리점" else "✅ 세종", type=btn_type("세종 대리점"), on_click=set_view, args=("세종 대리점",), use_container_width=True)
    with c_o[5]: st.button("목포" if vt != "목포 대리점" else "✅ 목포", type=btn_type("목포 대리점"), on_click=set_view, args=("목포 대리점",), use_container_width=True)
    with c_o[6]: st.button("충주" if vt != "충주 대리점" else "✅ 충주", type=btn_type("충주 대리점"), on_click=set_view, args=("충주 대리점",), use_container_width=True)
    with c_o[7]: st.markdown("<div style='text-align:center; padding-top:5px; color:#cbd5e1; font-weight:bold; font-size:16px;'>|</div>", unsafe_allow_html=True)
    with c_o[8]: st.button("I 호남통합" if vt != "호남팀 통합" else "✅ 호남통합", type=btn_type("호남팀 통합"), on_click=set_view, args=("호남팀 통합",), use_container_width=True)
    with c_o[9]: st.button("광양" if vt != "광양 대리점" else "✅ 광양", type=btn_type("광양 대리점"), on_click=set_view, args=("광양 대리점",), use_container_width=True)
    with c_o[10]: st.button("익산" if vt != "익산 대리점" else "✅ 익산", type=btn_type("익산 대리점"), on_click=set_view, args=("익산 대리점",), use_container_width=True)
    with c_o[11]: st.button("여수" if vt != "여수 대리점" else "✅ 여수", type=btn_type("여수 대리점"), on_click=set_view, args=("여수 대리점",), use_container_width=True)
    with c_o[12]:
        hl = ["✨ 인원별 상세 실적 (선택 시 우선 적용)"] + [f"👤 {r[('기본정보','대리점','대리점')]} - {r[('기본정보','HC명','HC명')]}" for _, r in final_df.iterrows() if r[('기본정보','HC명','HC명')] not in ["🌟 총계","합계","상권합계"] and r[('기본정보','HC명','HC명')] not in EXCLUDED_HCS]
        st.selectbox("인원선택", options=hl, key='hc_selector', on_change=on_hc_select, label_visibility="collapsed")
    st.markdown("---")
            
    def toggle_state(key): st.session_state[key] = not st.session_state[key]

    # 🚀 3. 트렌드 그래프
    t_c1, t_c2 = st.columns([7, 3])
    with t_c1: st.markdown(f"#### 📈 {ct} 실적 추이 그래프")
    with t_c2:
        st.markdown("<div class='mode-toggle'>", unsafe_allow_html=True)
        vm = st.radio("보기 기준", ["주간 추이 (최근 8주)", "월간 누적 추이 (8~11월)"], horizontal=True, label_visibility="collapsed", key='view_mode_selector')
        st.markdown("</div>", unsafe_allow_html=True)
        
    is_m = "월간" in vm
    la = month_labels if is_m else trend_labels
    pk = trend_pack['M'] if is_m else trend_pack['W']

    if vt == "충청호남팀 전체": sd = pk['tot']
    elif vt in ["충청팀 통합", "호남팀 통합"]: sd = pk['reg']["충청상권" if vt == "충청팀 통합" else "호남상권"]
    elif "대리점" in vt: sd = pk['dlr'].get(vt.replace(" 대리점", ""), [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_wd':0,'amt_we':0,'amt_move':0} for _ in la])
    else: sd = pk['hc'].get(vt.replace("👤 ", "").split(" - ")[1], [{'amt':0,'est':0,'cnt':0,'sales':0,'amt_wd':0,'amt_we':0,'amt_move':0} for _ in la])
    
    g_c1, g_c2, g_c3, g_c4 = st.columns([5, 3, 2, 2])
    with g_c1:
        st.markdown("<div class='chart-btn-group'>💰 재무 지표</div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.button("✅ 계약액" if st.session_state['t_amt'] else "계약액", on_click=toggle_state, args=('t_amt',), use_container_width=True, type="primary" if st.session_state['t_amt'] else "secondary")
        with c2: st.button("✅ 매출액" if st.session_state['t_sales'] else "매출액", on_click=toggle_state, args=('t_sales',), use_container_width=True, type="primary" if st.session_state['t_sales'] else "secondary")
        with c3: st.button("✅ 이월매출" if st.session_state['t_next'] else "이월매출", on_click=toggle_state, args=('t_next',), use_container_width=True, type="primary" if st.session_state['t_next'] else "secondary")
        with c4: st.button("✅ 평균(계약)" if st.session_state['t_avg'] else "평균(계약)", on_click=toggle_state, args=('t_avg',), use_container_width=True, type="primary" if st.session_state['t_avg'] else "secondary")
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
        c1, c2 = st.columns(2)
        with c1: st.button("✅ 계약률" if st.session_state['t_rate'] else "계약률", on_click=toggle_state, args=('t_rate',), use_container_width=True, type="primary" if st.session_state['t_rate'] else "secondary")
        with c2: st.button("✅ 객단가" if st.session_state['t_unit'] else "객단가", on_click=toggle_state, args=('t_unit',), use_container_width=True, type="primary" if st.session_state['t_unit'] else "secondary")
    
    y_a = [(w.get('amt', 0)/100000) for w in sd]
    y_s = [(w.get('sales', 0)/100000) for w in sd]
    y_n = [(w.get('next_sales', 0)/100000) for w in sd]
    y_av = [sum(y_a)/len(y_a) if y_a else 0] * len(y_a)
    y_wd = [(w.get('amt_wd', 0)/100000) for w in sd]
    y_we = [(w.get('amt_we', 0)/100000) for w in sd]
    y_m = [(w.get('amt_move', 0)/100000) for w in sd]
    y_wk = [a - m for a, m in zip(y_a, y_m)]
    
    ym_txt, yw_txt = [], []
    for w, m, a in zip(y_wk, y_m, y_a):
        if a > 0:
            ym_txt.append(f"<b>{m:.2f}억</b><br><span style='font-size:11px'>({(m/a*100):.0f}%)</span>")
            yw_txt.append(f"<b>{w:.2f}억</b><br><span style='font-size:11px'>({(w/a*100):.0f}%)</span>")
        else:
            ym_txt.append(f"<b>{m:.2f}억</b>")
            yw_txt.append(f"<b>{w:.2f}억</b>")
    
    y_e = [w.get('est', 0) for w in sd]
    y_c = [w.get('cnt', 0) for w in sd]
    y_r = [(c/e*100) if e>0 else 0 for e, c in zip(y_e, y_c)]
    y_u = [(a*100000/(c*10)) if c>0 else 0 for a, c in zip(y_a, y_c)] 
            
    if any([st.session_state[k] for k in toggle_keys]):
        fig = go.Figure()
        ms = [10] * (len(la)-1) + [20]
        
        if st.session_state['t_amt']: fig.add_trace(go.Scatter(x=la, y=y_a, mode='lines+markers+text', name='계약액', text=[f"<b>{v:.2f}억</b>" for v in y_a], textposition='top center', textfont=dict(size=15, color='black'), line=dict(color='#0f172a', width=4), marker=dict(size=ms, color=['#0f172a'] * (len(la)-1) + ['#dc2626'], line=dict(width=2, color='white'))))
        if st.session_state['t_sales']: fig.add_trace(go.Scatter(x=la, y=y_s, mode='lines+markers+text', name='매출액', text=[f"<b>{v:.2f}억</b>" for v in y_s], textposition='bottom right', textfont=dict(size=15, color='#0d9488'), line=dict(color='#14b8a6', width=3), marker=dict(size=ms, line=dict(width=2, color='white'))))
        if st.session_state['t_next']: fig.add_trace(go.Scatter(x=la, y=y_n, mode='lines+markers+text', name='이월매출', text=[f"<b>{v:.2f}억</b>" for v in y_n], textposition='top left', textfont=dict(size=15, color='#d97706'), line=dict(color='#f59e0b', width=3), marker=dict(size=ms, line=dict(width=2, color='white'))))
        if st.session_state['t_avg']: fig.add_trace(go.Scatter(x=la, y=y_av, mode='lines+text', name='평균선', text=[""] * (len(la)-1) + [f"<b>평균 {y_av[-1]:.2f}억</b>"], textposition='top right', textfont=dict(size=15, color='#475569'), line=dict(color='#94a3b8', width=2, dash='dash')))
        if st.session_state['t_wd']: fig.add_trace(go.Scatter(x=la, y=y_wd, mode='lines+markers+text', name='주중', text=[f"<b>{v:.2f}억</b>" for v in y_wd], textposition='bottom center', textfont=dict(size=15, color='#0ea5e9'), line=dict(color='#0ea5e9', width=3), marker=dict(size=ms, line=dict(width=2, color='white'))))
        if st.session_state['t_we']: fig.add_trace(go.Scatter(x=la, y=y_we, mode='lines+markers+text', name='주말', text=[f"<b>{v:.2f}억</b>" for v in y_we], textposition='top right', textfont=dict(size=15, color='#ef4444'), line=dict(color='#ef4444', width=3), marker=dict(size=ms, line=dict(width=2, color='white'))))
        if st.session_state['t_walk']: fig.add_trace(go.Scatter(x=la, y=y_wk, mode='lines+markers+text', name='워크인', text=yw_txt, textposition='top left', textfont=dict(size=15, color='#f97316'), line=dict(color='#f97316', width=3, dash='dot')))
        if st.session_state['t_move']: fig.add_trace(go.Scatter(x=la, y=y_m, mode='lines+markers+text', name='입주', text=ym_txt, textposition='bottom right', textfont=dict(size=15, color='#a855f7'), line=dict(color='#a855f7', width=3, dash='dot')))
        if st.session_state['t_est']: fig.add_trace(go.Scatter(x=la, y=y_e, mode='lines+markers+text', name='견적건', text=[f"<b>{v:,.0f}건</b>" for v in y_e], textposition='top center', textfont=dict(size=15, color='#4338ca'), line=dict(color='#4338ca', width=3), marker=dict(size=ms, line=dict(width=2, color='white')), yaxis='y2'))
        if st.session_state['t_cnt']: fig.add_trace(go.Scatter(x=la, y=y_c, mode='lines+markers+text', name='계약건', text=[f"<b>{v:,.0f}건</b>" for v in y_c], textposition='bottom center', textfont=dict(size=15, color='#10b981'), line=dict(color='#10b981', width=3), marker=dict(size=ms, line=dict(width=2, color='white')), yaxis='y2'))
        if st.session_state['t_rate']: fig.add_trace(go.Scatter(x=la, y=y_r, mode='lines+markers+text', name='계약률', text=[f"<b>{v:.1f}%</b>" for v in y_r], textposition='top right', textfont=dict(size=15, color='#ca8a04'), line=dict(color='#ca8a04', width=3), marker=dict(size=ms, line=dict(width=2, color='white')), yaxis='y3'))
        if st.session_state['t_unit']: fig.add_trace(go.Scatter(x=la, y=y_u, mode='lines+markers+text', name='객단가', text=[f"<b>{int(v):,}만</b>" for v in y_u], textposition='bottom left', textfont=dict(size=15, color='#ec4899'), line=dict(color='#ec4899', width=3), marker=dict(size=ms, line=dict(width=2, color='white')), yaxis='y4'))
            
        fig.update_layout(
            height=450, margin=dict(l=20, r=20, t=60, b=20), plot_bgcolor='white', 
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1), 
            annotations=[dict(xref='paper', yref='paper', x=0, y=1.1, xanchor='left', yanchor='bottom', text='<b>금액 (억)</b>', font=dict(size=13, color='#1e3a8a'), showarrow=False)], 
            yaxis=dict(title="", tickformat=".1f", ticksuffix="억", dtick=0.5, gridcolor='#f1f5f9'), 
            yaxis2=dict(title=dict(text="<b>건수 (건)</b>", font=dict(size=13, color='#ea580c')), overlaying='y', side='right', showgrid=False), 
            yaxis3=dict(overlaying='y', visible=False), 
            yaxis4=dict(overlaying='y', visible=False)
        )
        fig.update_xaxes(showgrid=True, gridcolor='#f1f5f9', tickfont=dict(size=12, color='black'))
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("👆 위 세부 지표 버튼을 클릭하시면 실시간 꺾은선 그래프가 나타납니다.")
    st.markdown("---")

    # 🚀 4. 하단 전체 상세 표 출력
    tdr = date_headers.get(CURRENT_TABLE_WEEK, "")
    st.markdown(f"<div style='background-color: #f8fafc; padding: 15px; border-left: 5px solid #3b82f6; border-radius: 5px; margin-bottom: 20px;'><h4 style='margin:0; color: #1e3a8a;'>📌 {current_month}월 {CURRENT_TABLE_WEEK} {tdr} 전체 VDT 현황 표</h4></div>", unsafe_allow_html=True)
    
    uds = [d for d in final_df[('기본정보', '대리점', '대리점')].unique() if d not in ["🌟 총계", "충청상권", "호남상권"]]
    dcs = {d: ['#f8fafc', '#ffffff'][i%2] for i, d in enumerate(uds)}
    cws, cls = [80,90,70,70,70,70,70,70,55,55,55,55,55,55], [0,80,170,240,310,380,450,520,590,645,700,755,810,865]
    
    hl = ["<div class='vdt-table-container'><table class='vdt-table'><thead><tr>"]
    hl.append(f"<th rowspan='3' style='position:sticky; top:0; left:0; z-index:20; background-color:#0f172a; min-width:{cws[0]}px; max-width:{cws[0]}px; border-right:1px solid #cbd5e1;'>대리점</th>")
    hl.append(f"<th rowspan='3' style='position:sticky; top:0; left:{cls[1]}px; z-index:20; background-color:#0f172a; min-width:{cws[1]}px; max-width:{cws[1]}px; border-right:2px solid #94a3b8;'>HC명</th>")
    
    h1_list = []
    for c in final_df.columns[2:]:
        if c[0] not in h1_list: h1_list.append(c[0])
            
    for h1 in h1_list:
        ic, im = CURRENT_TABLE_WEEK in h1, "당월" in h1
        sp = "position:sticky; top:0; " + ("background-color:#1e3a8a; border:3px solid #60a5fa;" if ic else ("background-color:#064e3b; color:#a7f3d0; border-top:2px solid #047857;" if im else "background-color:#0f172a;"))
        if h1 == '🎯 당월매출': hl.append(f"<th colspan='3' style='{sp} left:{cls[2]}px; z-index:15; border-right:3px solid #1e293b;'>{h1}</th>")
        elif "🌟 당월 합계" in h1: hl.append(f"<th colspan='9' style='{sp} left:{cls[5]}px; z-index:15; border-right:4px solid #94a3b8;'>{h1}</th>")
        else: hl.append(f"<th colspan='9' style='{sp} z-index:10;'>{h1}</th>")
    hl.append("</tr><tr>")
    
    for h1 in h1_list:
        ic, im = CURRENT_TABLE_WEEK in h1, "당월" in h1
        sp = "position:sticky; top:33px; " + ("background-color:#1e40af; border-left:3px solid #60a5fa; border-right:3px solid #60a5fa;" if ic else ("background-color:#065f46; color:#a7f3d0;" if im else "background-color:#0f172a;"))
        if h1 == '🎯 당월매출': hl.append(f"<th colspan='3' style='{sp} left:{cls[2]}px; z-index:15; border-right:3px solid #1e293b;'>인별매출(천)</th>")
        elif "🌟 당월 합계" in h1: hl.append(f"<th colspan='3' style='{sp} left:{cls[5]}px; z-index:15;'>계약액(천)</th><th colspan='3' style='{sp} left:{cls[8]}px; z-index:15;'>견적건</th><th colspan='3' style='{sp} left:{cls[11]}px; z-index:15; border-right:4px solid #94a3b8;'>계약건</th>")
        else: hl.append(f"<th colspan='3' style='{sp} z-index:10;'>계약액(천)</th><th colspan='3' style='{sp} z-index:10;'>견적건</th><th colspan='3' style='{sp} z-index:10;'>계약건</th>")
    hl.append("</tr><tr>")
    
    for i, c in enumerate(final_df.columns[2:]):
        ai = i + 2
        ic, im = CURRENT_TABLE_WEEK in c[0], "당월" in c[0]
        sp = "position:sticky; top:66px; " + ("background-color:#1d4ed8; border-bottom:3px solid #60a5fa;" + ("border-left:3px solid #60a5fa;" if c[1]=='계약액(천)' and c[2]=='목표' else "") + ("border-right:3px solid #60a5fa;" if c[1]=='계약건' and c[2]=='달성율(%)' else "") if ic else ("background-color:#047857; color:#a7f3d0;" if im else "background-color:#0f172a;"))
        sp += f" left:{cls[ai]}px; z-index:15; min-width:{cws[ai]}px; max-width:{cws[ai]}px;" if ai<=13 else " z-index:10; min-width:60px;"
        if c[0]=='🎯 당월매출' and c[2]=='달성율(%)': sp += " border-right:3px solid #1e293b;"
        if "🌟 당월 합계" in c[0] and c[1]=='계약건' and c[2]=='달성율(%)': sp += " border-right:4px solid #94a3b8;"
        hl.append(f"<th style='{sp}'>{c[2]}</th>")
    hl.append("</tr></thead><tbody>")
    
    for _, r in final_df.iterrows():
        d, hc = r[('기본정보', '대리점', '대리점')], r[('기본정보', 'HC명', 'HC명')]
        bg, rb = ("#e2e8f0", "style='background-color:#e2e8f0; font-weight:bold;'") if hc in ["합계","상권합계"] else (("#cbd5e1", "style='background-color:#cbd5e1; font-weight:bold;'") if "🌟" in str(hc) else (dcs.get(d, '#ffffff'), f"style='background-color:{dcs.get(d, '#ffffff')};'"))
        hl.append(f"<tr {rb}><td class='text-center' style='position:sticky; left:0; z-index:6; background-color:{bg}; min-width:{cws[0]}px; max-width:{cws[0]}px; border-right:1px solid #cbd5e1;'>{d}</td>")
        hl.append(f"<td class='text-center' style='position:sticky; left:{cls[1]}px; z-index:6; background-color:{bg}; min-width:{cws[1]}px; max-width:{cws[1]}px; border-right:2px solid #94a3b8;'>{hc}</td>")
        
        for i, v in enumerate(r[2:]):
            ai, c = i + 2, final_df.columns[i + 2]
            ic, im = CURRENT_TABLE_WEEK in c[0], "당월" in c[0]
            sp = "background-color:rgba(37,99,235,0.12);" + ("border-left:3px solid #3b82f6;" if c[1]=='계약액(천)' and c[2]=='목표' else "") + ("border-right:3px solid #3b82f6;" if c[1]=='계약건' and c[2]=='달성율(%)' else "") if ic else ("background-color:" + ({'#f8fafc':'#e4f1ef', '#e2e8f0':'#d1dbda', '#cbd5e1':'#bcc7c7'}.get(bg, '#ebf6f2') if ai<=13 else "rgba(5,150,105,0.08)") + ";" if im else f"background-color:{bg};")
            sp += f" position:sticky; left:{cls[ai]}px; z-index:5; min-width:{cws[ai]}px; max-width:{cws[ai]}px;" if ai<=13 else ""
            if c[0]=='🎯 당월매출' and c[2]=='달성율(%)': sp += " border-right:3px solid #1e293b;"
            if "🌟 당월 합계" in c[0] and c[1]=='계약건' and c[2]=='달성율(%)': sp += " border-right:4px solid #94a3b8;"
            
            vs = f"<span style='color:{'#047857' if im else '#1d4ed8'}; font-weight:900;'>{v:.0f}%</span>" if c[2]=='달성율(%)' and v>=100 else (f"<span style='font-weight:600;'>{v:.0f}%</span>" if c[2]=='달성율(%)' and v>0 else (f"{v:.0f}%" if c[2]=='달성율(%)' else f"{v:,.0f}"))
            hl.append(f"<td style='{sp}'>{vs}</td>")
        hl.append("</tr>")
    hl.append("</tbody></table></div>")
    
    st.markdown("".join(hl), unsafe_allow_html=True)
