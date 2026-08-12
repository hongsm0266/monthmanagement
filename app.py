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

# --- 커스텀 CSS ---
st.markdown("""
<style>
    @font-face { font-family: 'Paperlogy'; src: url('https://cdn.jsdelivr.net/gh/projectnoonnu/2408-3@1.0/Paperlogy-8Bold.woff2') format('woff2'); font-weight: 700; font-display: swap; }
    html, body, [class*="css"], [class*="st-"], th, td { font-family: 'Paperlogy', sans-serif !important; }
    
    .vdt-table-container {
        width: 100%;
        max-height: 65vh; 
        overflow: auto;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        margin-top: 10px;
    }
    
    .vdt-table-container::-webkit-scrollbar { width: 14px; height: 14px; }
    .vdt-table-container::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 8px; }
    .vdt-table-container::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 8px; border: 3px solid #f1f5f9; }
    .vdt-table-container::-webkit-scrollbar-thumb:hover { background: #64748b; }

    .vdt-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
        white-space: nowrap;
    }
    
    .vdt-table thead th {
        height: 34px;
        box-sizing: border-box;
        position: sticky;
        z-index: 10;
        background-clip: padding-box; 
    }
    .vdt-table thead tr:nth-child(1) th { top: 0; }
    .vdt-table thead tr:nth-child(2) th { top: 33px; }
    .vdt-table thead tr:nth-child(3) th { top: 66px; }

    .vdt-table th {
        background-color: #0f172a;
        color: white;
        padding: 8px 10px;
        text-align: center;
        border: 1px solid #334155;
        font-weight: 600;
    }
    .vdt-table td {
        padding: 6px 10px;
        text-align: right;
        border: 1px solid #e2e8f0;
    }
    .vdt-table td.text-center { text-align: center; }
    .title-box { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
    h1 { font-weight: 900 !important; color: white !important; font-size: 24px !important; margin: 0; }
    
    div[data-testid="metric-container"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

current_month = datetime.now().month
st.markdown(f"<div class='title-box'><h1>📊 충청호남팀 영업사원 주차별 VDT 목표 관리 ({current_month}월)</h1></div>", unsafe_allow_html=True)

def clean_str(val):
    return re.sub(r'\s+', '', str(val))

def safe_get(row, idx):
    return str(row[idx]).strip() if len(row) > idx else ""

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
            if m_val == 7 and d_val >= 27: return '0주차'
            if m_val == 8:
                if d_val <= 2: return '0주차'
                elif d_val <= 9: return '1주차'
                elif d_val <= 16: return '2주차'
                elif d_val <= 23: return '3주차'
                elif d_val <= 30: return '4주차'
                else: return '5주차'
    except:
        pass
    return None

def get_mapped_dealer(raw_d):
    c_d = clean_str(raw_d)
    if any(k in c_d for k in ["한밭", "INT충청", "701347", "세종2"]):
        return "세종"
    return raw_d.strip()

now = datetime.now()
CURRENT_WEEK = get_week_name(f"{now.month}/{now.day}") 
if not CURRENT_WEEK: CURRENT_WEEK = '1주차'

PREV_WEEK = None
if CURRENT_WEEK:
    try:
        curr_num = int(CURRENT_WEEK.replace("주차", ""))
        if curr_num > 0:
            PREV_WEEK = f"{curr_num - 1}주차"
    except:
        pass

@st.cache_data(ttl=60)
def load_vdt_data():
    if not client: return pd.DataFrame(), {}, {}, {}, {}
    
    status_box = st.empty()
    try:
        status_box.info("🔍 0단계: 구글 시트 연결 중...")
        sh = client.open_by_url(SHEET_URL)
        all_worksheets = [ws.title for ws in sh.worksheets()]
        
        target_sheet_name = "주차별 목표 세팅"
        if target_sheet_name not in all_worksheets: 
            st.error(f"🚨 '{target_sheet_name}' 탭을 찾을 수 없습니다.")
            return pd.DataFrame(), {}, {}, {}, {}
        
        target_ws = sh.worksheet(target_sheet_name)
        
        status_box.info("📊 1단계: 인별 매출목표 및 비중 계산 중...")
        all_targets = target_ws.get_all_values()
        
        split_idx = 15
        for i, row in enumerate(all_targets):
            if len(row) > 1 and clean_str(row[1]) in ['HC', 'HC명', '영업사원', '이름']:
                split_idx = i
                break
                
        target_data = all_targets[:split_idx]
        hc_target_data = all_targets[split_idx:]
        
        hc_info_dict = {}         
        dealer_sales_sum = {} 
        
        for row in hc_target_data:
            if len(row) >= 4 and str(row[0]).strip() and str(row[1]).strip():
                raw_dealer = str(row[0]).strip()
                hc_name = clean_str(row[1]) 
                
                if raw_dealer in ['대리점', '대리점명', '구분'] or hc_name in ['HC', 'HC명', '영업사원', '이름']:
                    continue
                    
                if hc_name.isdigit(): continue
                
                dealer = get_mapped_dealer(raw_dealer)
                sales_target = clean_val(row[3]) / 1000.0
                
                key = (dealer, hc_name)
                hc_info_dict[key] = hc_info_dict.get(key, 0.0) + sales_target
                dealer_sales_sum[dealer] = dealer_sales_sum.get(dealer, 0.0) + sales_target

        hc_info = [(d, h, t) for (d, h), t in hc_info_dict.items()]

        status_box.info("🎯 2단계: 대리점 주차별 목표 스캔 중...")
        
        date_headers = {
            '0주차': '7/27~8/2',
            '1주차': '8/3~8/9',
            '2주차': '8/10~8/16',
            '3주차': '8/17~8/23',
            '4주차': '8/24~8/30',
            '5주차': '8/31'
        }
        
        week_cols = {
            '0주차': {'amt': 1, 'est': 2, 'cnt': 3},   
            '1주차': {'amt': 4, 'est': 5, 'cnt': 6},   
            '2주차': {'amt': 7, 'est': 8, 'cnt': 9},   
            '3주차': {'amt': 10, 'est': 11, 'cnt': 12}, 
            '4주차': {'amt': 13, 'est': 14, 'cnt': 15}, 
            '5주차': {'amt': 16, 'est': 17, 'cnt': 18}, 
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

        status_box.info("📈 3단계: 일별 실적(ACT) 스캔 및 누적 취합 중...")
        
        raw_daily_sheets = [ws for ws in sh.worksheets() if "/" in ws.title or "일" in ws.title]
        
        def sort_key(ws):
            try:
                nums = re.findall(r'\d+', ws.title)
                if len(nums) >= 2:
                    return int(nums[0]) * 100 + int(nums[1])
            except:
                pass
            return 0
                
        daily_sheets = sorted(raw_daily_sheets, key=sort_key)
        
        existing_hcs = [clean_str(h) for d, h, t in hc_info]
        valid_dealers = list(set([d for d, _, _ in hc_info]))
        
        # 🚀 [당월 범위에 해당하는 시트만 골라내기 + 월(Month) 추출]
        valid_daily_sheets = []
        for ws in daily_sheets:
            wk = get_week_name(ws.title)
            nums = re.findall(r'\d+', ws.title)
            if wk and len(nums) >= 2: 
                m_val = int(nums[0]) # 7월인지 8월인지 추출
                valid_daily_sheets.append((m_val, wk, ws))
        
        # 신규 인원 스캔 로직 (해당 범위 시트 한정)
        for m_val, wk, ws in valid_daily_sheets:
            d_data = ws.get_all_values()
            current_rem_dealer = ""
            for row in d_data:
                hc_name_raw = safe_get(row, 3)
                if not hc_name_raw: continue
                
                header_str = clean_str("".join([safe_get(row, i) for i in range(4)]))
                
                mapped_d = get_mapped_dealer(header_str)
                if mapped_d == "세종":
                    current_rem_dealer = "세종"
                else:
                    for vd in valid_dealers:
                        if clean_str(vd) in header_str:
                            current_rem_dealer = vd
                            break
                            
                hc_name = clean_str(hc_name_raw)
                if hc_name and not any(x in hc_name for x in ['HC', 'HC명', '영업사원', '이름', '합계', '소계', '총계', '목표', '대리점', '비고', '사번']):
                    if hc_name not in existing_hcs:
                        new_dealer = current_rem_dealer if current_rem_dealer else "기타"
                        hc_info.append((new_dealer, hc_name, 0.0))
                        existing_hcs.append(hc_name)
                        if new_dealer not in valid_dealers:
                            valid_dealers.append(new_dealer)

        hc_weights = {}
        for dealer, hc, target in hc_info:
            d_sum = dealer_sales_sum.get(dealer, 0.0)
            hc_weights[hc] = (target / d_sum) if d_sum > 0 else 0.0
            
        targets = {}
        for dealer, hc, _ in hc_info:
            targets[hc] = {}
            weight = hc_weights.get(hc, 0.0)
            d_t = dealer_targets.get(dealer, {})
            for wk in week_keys:
                targets[hc][wk] = {
                    'amt': d_t.get(wk, {}).get('amt', 0) * weight,
                    'est': d_t.get(wk, {}).get('est', 0) * weight,
                    'cnt': d_t.get(wk, {}).get('cnt', 0) * weight,
                }
                
        acts = {clean_str(hc): {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for _, hc, _ in hc_info}
        month_acts = {clean_str(hc): {'amt': 0, 'est': 0, 'cnt': 0} for _, hc, _ in hc_info}
        
        hc_to_dealer = {clean_str(hc): dealer for dealer, hc, _ in hc_info}
        valid_dealers = list(set([d for d, _, _ in hc_info]))
        
        real_dealer_monthly = {d: {'amt': 0, 'est': 0, 'cnt': 0} for d in valid_dealers}
        real_dealer_weekly = {d: {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for d in valid_dealers}
        
        # 1️⃣ 주차별 & 당월 실적 누적 (🚀 당월 합계는 무조건 "현재 월(8월)" 시트만 합산!)
        for m_val, wk, ws in valid_daily_sheets:
            d_data = ws.get_all_values()
            
            current_remembered_dealer = ""
            cached_est, cached_cnt, cached_amt = 0.0, 0.0, 0.0
            
            for row in d_data:
                if len(row) > 3: 
                    row_header_str = clean_str("".join([safe_get(row, i) for i in range(4)]))
                    
                    if get_mapped_dealer(row_header_str) == "세종":
                        current_remembered_dealer = "세종"
                    else:
                        for vd in valid_dealers:
                            if clean_str(vd) in row_header_str:
                                current_remembered_dealer = vd
                                break

                    temp_est = clean_val(safe_get(row, 4))
                    temp_cnt = clean_val(safe_get(row, 5))
                    temp_amt = clean_val(safe_get(row, 15))
                    
                    hc_name_raw = safe_get(row, 3)
                    hc_name = clean_str(hc_name_raw)
                    
                    if any(x in hc_name for x in ['합계', '소계', '총계', '목표', '대리점', '사번', '비고']):
                        cached_est, cached_cnt, cached_amt = 0.0, 0.0, 0.0
                        continue
                        
                    if not hc_name:
                        if temp_est > 0 or temp_cnt > 0 or temp_amt > 0:
                            cached_est, cached_cnt, cached_amt = temp_est, temp_cnt, temp_amt
                        continue
                        
                    if hc_name:
                        est_val = temp_est if temp_est > 0 else cached_est
                        cnt_val = temp_cnt if temp_cnt > 0 else cached_cnt
                        amt_val = temp_amt if temp_amt > 0 else cached_amt
                        
                        cached_est, cached_cnt, cached_amt = 0.0, 0.0, 0.0
                        
                        if hc_name in acts:
                            # [주차별 실적] 7월 27~31일이든 8월이든 주차(0주차)에 맞게 전부 더함
                            acts[hc_name][wk]['est'] += est_val
                            acts[hc_name][wk]['cnt'] += cnt_val
                            acts[hc_name][wk]['amt'] += amt_val
                            
                            # 🚀 [당월 합계 실적] 오직 이번 달(8월) 일보인 경우에만 더함!
                            if m_val == current_month:
                                month_acts[hc_name]['est'] += est_val
                                month_acts[hc_name]['cnt'] += cnt_val
                                month_acts[hc_name]['amt'] += amt_val
                        
                        matched_dealer = current_remembered_dealer
                        if not matched_dealer:
                            matched_dealer = hc_to_dealer.get(hc_name, "")
                            
                        if matched_dealer in valid_dealers:
                            if wk in real_dealer_weekly[matched_dealer]:
                                real_dealer_weekly[matched_dealer][wk]['est'] += est_val
                                real_dealer_weekly[matched_dealer][wk]['cnt'] += cnt_val
                                real_dealer_weekly[matched_dealer][wk]['amt'] += amt_val

                            # 🚀 대리점 당월 찐 합계도 8월 일보 실적만 더함!
                            if m_val == current_month:
                                real_dealer_monthly[matched_dealer]['est'] += est_val
                                real_dealer_monthly[matched_dealer]['cnt'] += cnt_val
                                real_dealer_monthly[matched_dealer]['amt'] += amt_val
                        
        # 2️⃣ 당월매출 S열 스캔
        acts_sales = {clean_str(hc): 0 for _, hc, _ in hc_info}
        real_dealer_sales = {d: 0 for d in valid_dealers}
        
        # 최신 시트 골라내기 (0~5주차 범위 안에서 가장 마지막 시트)
        if valid_daily_sheets:
            latest_m, latest_wk, latest_sheet = valid_daily_sheets[-1] 
            l_data = latest_sheet.get_all_values()
            
            current_remembered_dealer = ""
            cached_s = 0.0
            
            for row in l_data:
                if len(row) > 3:
                    row_header_str = clean_str("".join([safe_get(row, i) for i in range(4)]))
                    
                    if get_mapped_dealer(row_header_str) == "세종":
                        current_remembered_dealer = "세종"
                    else:
                        for vd in valid_dealers:
                            if clean_str(vd) in row_header_str:
                                current_remembered_dealer = vd
                                break
                                
                    hc_name_s = clean_str(safe_get(row, 3))
                    temp_s = clean_val(safe_get(row, 18))
                    
                    if any(x in hc_name_s for x in ['합계', '소계', '총계', '목표', '대리점', '사번', '비고']):
                        cached_s = 0.0
                        continue
                        
                    if not hc_name_s:
                        if temp_s > 0:
                            cached_s = temp_s
                        continue
                        
                    if hc_name_s:
                        s_val = temp_s if temp_s > 0 else cached_s
                        cached_s = 0.0 
                        
                        if s_val > 0:
                            if hc_name_s in acts_sales:
                                acts_sales[hc_name_s] += s_val
                                
                            matched_dealer = current_remembered_dealer
                            if not matched_dealer:
                                matched_dealer = hc_to_dealer.get(hc_name_s, "")
                                
                            if matched_dealer in real_dealer_sales:
                                real_dealer_sales[matched_dealer] += s_val

        status_box.info("✅ 데이터 구성 완료! 표 출력 중...")
        
        col_tuples = [
            ('기본정보', '대리점', '대리점'),
            ('기본정보', 'HC명', 'HC명'),
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
        for dealer, hc, sales_tgt in hc_info:
            hc_clean = clean_str(hc)
            m_act = month_acts.get(hc_clean, {'amt': 0, 'est': 0, 'cnt': 0})
            s_act = acts_sales.get(hc_clean, 0)

            # 0원 퇴사자 숨김 필터
            if sales_tgt == 0.0 and m_act['amt'] == 0 and m_act['est'] == 0 and m_act['cnt'] == 0 and s_act == 0:
                continue

            row_data = [dealer, hc]
            row_data.extend([sales_tgt, s_act, 0.0])
            
            m_tgt_amt = sum([targets.get(hc, {}).get(wk, {}).get('amt', 0) for wk in week_keys])
            m_tgt_est = sum([targets.get(hc, {}).get(wk, {}).get('est', 0) for wk in week_keys])
            m_tgt_cnt = sum([targets.get(hc, {}).get(wk, {}).get('cnt', 0) for wk in week_keys])
            
            row_data.extend([
                m_tgt_amt, m_act['amt'], 0.0,
                m_tgt_est, m_act['est'], 0.0,
                m_tgt_cnt, m_act['cnt'], 0.0
            ])
            
            for wk in week_keys:
                t = targets.get(hc, {}).get(wk, {'amt': 0, 'est': 0, 'cnt': 0})
                a = acts.get(hc_clean, {}).get(wk, {'amt': 0, 'est': 0, 'cnt': 0})
                row_data.extend([t['amt'], a['amt'], 0.0, t['est'], a['est'], 0.0, t['cnt'], a['cnt'], 0.0])
                
            rows.append(row_data)

        df = pd.DataFrame(rows, columns=columns)
        
        for col in df.columns[2:]:
            if col[2] == '달성율(%)':
                tgt_col = (col[0], col[1], '목표')
                act_col = (col[0], col[1], 'ACT')
                df[col] = np.where(df[tgt_col] > 0, (df[act_col] / df[tgt_col] * 100).round(1), 0)
        
        status_box.empty()
        return df, date_headers, real_dealer_sales, real_dealer_monthly, real_dealer_weekly 

    except Exception as e:
        status_box.empty()
        st.error("🚨 데이터 구성 중 에러가 발생했습니다!")
        with st.expander("🛠️ 상세 에러 보기"): st.code(traceback.format_exc())
        return pd.DataFrame(), {}, {}, {}, {}

def calculate_subtotals(df, real_dealer_sales, real_dealer_monthly, real_dealer_weekly):
    if df.empty: return df
    
    result_rows = []
    dealer_col = ('기본정보', '대리점', '대리점')
    hc_col = ('기본정보', 'HC명', 'HC명')
    
    for dealer, group in df.groupby(dealer_col, sort=False):
        for _, row in group.iterrows(): result_rows.append(row)
            
        subtotal = group.select_dtypes(include=[np.number]).sum()
        subtotal[dealer_col] = dealer
        subtotal[hc_col] = "합계"
        
        if dealer in real_dealer_sales:
            subtotal[('🎯 당월매출', '인별매출(천)', 'ACT')] = real_dealer_sales[dealer]
            
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
                tgt_col = (col[0], col[1], '목표')
                act_col = (col[0], col[1], 'ACT')
                subtotal[col] = round((subtotal[act_col] / subtotal[tgt_col] * 100), 1) if subtotal[tgt_col] > 0 else 0.0
        result_rows.append(pd.Series(subtotal))

    grand_total = df.select_dtypes(include=[np.number]).sum()
    grand_total[dealer_col] = "🌟 총계"
    grand_total[hc_col] = "🌟 총계"
    
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
            tgt_col = (col[0], col[1], '목표')
            act_col = (col[0], col[1], 'ACT')
            grand_total[col] = round((grand_total[act_col] / grand_total[tgt_col] * 100), 1) if grand_total[tgt_col] > 0 else 0.0
    result_rows.append(pd.Series(grand_total))
    
    return pd.DataFrame(result_rows)

df_raw, date_headers, real_dealer_sales, real_dealer_monthly, real_dealer_weekly = load_vdt_data()

if not df_raw.empty:
    final_df = calculate_subtotals(df_raw, real_dealer_sales, real_dealer_monthly, real_dealer_weekly)
    
    # ---------------------------------------------------------
    # 🚀 개인/대리점 선택 및 실적 차트 대시보드
    # ---------------------------------------------------------
    st.markdown("---")
    col_sel, col_btn = st.columns([7, 2]) 
    
    with col_sel:
        st.markdown("### 🔎 **인별 / 대리점별 상세 실적 확인**")
        valid_choices = ["✨ 여기를 클릭하여 인원 또는 대리점을 선택하세요 (전체 표만 보기)"]
        for r_idx in range(len(final_df)):
            dealer = final_df.iloc[r_idx][('기본정보', '대리점', '대리점')]
            hc = final_df.iloc[r_idx][('기본정보', 'HC명', 'HC명')]
            if hc == "🌟 총계": continue
            if hc == "합계":
                valid_choices.append(f"🏢 [{dealer}] 대리점 합계")
            else:
                valid_choices.append(f"👤 {dealer} - {hc}")
        
        selected_option = st.selectbox(
            "👇 아래 입력창을 클릭(선택)하면 해당 인원의 실적 차트가 나타납니다.", 
            options=valid_choices
        )
        
    with col_btn:
        st.write("") 
        st.write("") 
        st.write("") 
        if st.button("🔄 실적 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if selected_option != valid_choices[0]:
        st.markdown("---")
        
        is_dealer_total = "대리점 합계" in selected_option
        if is_dealer_total:
            target_dealer = selected_option.replace("🏢 [", "").replace("] 대리점 합계", "")
            target_hc = "합계"
            comp_df = final_df[final_df[('기본정보', 'HC명', 'HC명')] == "합계"]
            unit_str = "팀"
        else:
            parts = selected_option.replace("👤 ", "").split(" - ")
            target_dealer = parts[0]
            target_hc = parts[1]
            comp_df = final_df[~final_df[('기본정보', 'HC명', 'HC명')].str.contains("합계|총계", na=False)]
            unit_str = "명"
            
        t_row = final_df[(final_df[('기본정보', '대리점', '대리점')] == target_dealer) & (final_df[('기본정보', 'HC명', 'HC명')] == target_hc)].iloc[0]
        
        total_competitors = len(comp_df)
        def get_rank_str(col_tuple, val):
            if val == 0: return f"순위 제외"
            ranks = comp_df[col_tuple].rank(method='min', ascending=False)
            target_idx = comp_df[(comp_df[('기본정보', '대리점', '대리점')] == target_dealer) & (comp_df[('기본정보', 'HC명', 'HC명')] == target_hc)].index[0]
            return f"🏆 {int(ranks.loc[target_idx])}등 / {total_competitors}{unit_str}"

        curr_wk_cols = [c[0] for c in final_df.columns if CURRENT_WEEK in c[0]]
        cw_col = curr_wk_cols[0] if curr_wk_cols else None
        
        prev_wk_cols = [c[0] for c in final_df.columns if PREV_WEEK and PREV_WEEK in c[0]]
        pw_col = prev_wk_cols[0] if prev_wk_cols else None
        
        st.markdown(f"### ✨ **{selected_option.split(' ', 1)[1]}** 실적 요약 (당월 / 전주 / 당주)")
        
        act1 = t_row[('🎯 당월매출', '인별매출(천)', 'ACT')]
        pct1 = t_row[('🎯 당월매출', '인별매출(천)', '달성율(%)')]
        rk1 = get_rank_str(('🎯 당월매출', '인별매출(천)', '달성율(%)'), pct1)
        
        act2 = t_row[('🌟 당월 합계', '계약액(천)', 'ACT')]
        pct2 = t_row[('🌟 당월 합계', '계약액(천)', '달성율(%)')]
        rk2 = get_rank_str(('🌟 당월 합계', '계약액(천)', '달성율(%)'), pct2)
        
        act_m_est = t_row[('🌟 당월 합계', '견적건', 'ACT')]
        pct_m_est = t_row[('🌟 당월 합계', '견적건', '달성율(%)')]
        rk_m_est = get_rank_str(('🌟 당월 합계', '견적건', '달성율(%)'), pct_m_est)
        
        act_pw_amt = t_row[(pw_col, '계약액(천)', 'ACT')] if pw_col else 0
        pct_pw_amt = t_row[(pw_col, '계약액(천)', '달성율(%)')] if pw_col else 0
        rk_pw_amt = get_rank_str((pw_col, '계약액(천)', '달성율(%)'), pct_pw_amt) if pw_col else ""
        
        act_pw_cnt = t_row[(pw_col, '계약건', 'ACT')] if pw_col else 0
        pct_pw_cnt = t_row[(pw_col, '계약건', '달성율(%)')] if pw_col else 0
        rk_pw_cnt = get_rank_str((pw_col, '계약건', '달성율(%)'), pct_pw_cnt) if pw_col else ""
        
        act_pw_est = t_row[(pw_col, '견적건', 'ACT')] if pw_col else 0
        pct_pw_est = t_row[(pw_col, '견적건', '달성율(%)')] if pw_col else 0
        rk_pw_est = get_rank_str((pw_col, '견적건', '달성율(%)'), pct_pw_est) if pw_col else ""
        
        act3 = t_row[(cw_col, '계약액(천)', 'ACT')] if cw_col else 0
        pct3 = t_row[(cw_col, '계약액(천)', '달성율(%)')] if cw_col else 0
        rk3 = get_rank_str((cw_col, '계약액(천)', '달성율(%)'), pct3) if cw_col else ""
        
        act4 = t_row[(cw_col, '계약건', 'ACT')] if cw_col else 0
        pct4 = t_row[(cw_col, '계약건', '달성율(%)')] if cw_col else 0
        rk4 = get_rank_str((cw_col, '계약건', '달성율(%)'), pct4) if cw_col else ""
        
        act_cw_est = t_row[(cw_col, '견적건', 'ACT')] if cw_col else 0
        pct_cw_est = t_row[(cw_col, '견적건', '달성율(%)')] if cw_col else 0
        rk_cw_est = get_rank_str((cw_col, '견적건', '달성율(%)'), pct_cw_est) if cw_col else ""

        mc1, mc2, mc3 = st.columns(3)
        with mc1: 
            st.metric("🌲 당월매출 (천원)", f"{act1:,.0f}", f"{pct1:.1f}% 달성 | {rk1}", delta_color="off")
            st.metric("🌟 당월 합계 계약액 (천원)", f"{act2:,.0f}", f"{pct2:.1f}% 달성 | {rk2}", delta_color="off")
            st.metric("🌟 당월 합계 견적건 (건)", f"{act_m_est:,.0f}", f"{pct_m_est:.1f}% 달성 | {rk_m_est}", delta_color="off")
            
        with mc2: 
            if pw_col:
                st.metric(f"⏪ 전주({PREV_WEEK}) 계약액 (천원)", f"{act_pw_amt:,.0f}", f"{pct_pw_amt:.1f}% 달성 | {rk_pw_amt}", delta_color="off")
                st.metric(f"⏪ 전주({PREV_WEEK}) 계약건 (건)", f"{act_pw_cnt:,.0f}", f"{pct_pw_cnt:.1f}% 달성 | {rk_pw_cnt}", delta_color="off")
                st.metric(f"⏪ 전주({PREV_WEEK}) 견적건 (건)", f"{act_pw_est:,.0f}", f"{pct_pw_est:.1f}% 달성 | {rk_pw_est}", delta_color="off")
            else:
                st.metric("⏪ 전주 계약액 (천원)", "-", "해당 데이터 없음", delta_color="off")
                st.metric("⏪ 전주 계약건 (건)", "-", "해당 데이터 없음", delta_color="off")
                st.metric("⏪ 전주 견적건 (건)", "-", "해당 데이터 없음", delta_color="off")
                
        with mc3: 
            st.metric(f"🌊 당주({CURRENT_WEEK}) 계약액 (천원)", f"{act3:,.0f}", f"{pct3:.1f}% 달성 | {rk3}", delta_color="off")
            st.metric(f"🌊 당주({CURRENT_WEEK}) 계약건 (건)", f"{act4:,.0f}", f"{pct4:.1f}% 달성 | {rk4}", delta_color="off")
            st.metric(f"🌊 당주({CURRENT_WEEK}) 견적건 (건)", f"{act_cw_est:,.0f}", f"{pct_cw_est:.1f}% 달성 | {rk_cw_est}", delta_color="off")
            
        st.markdown("##### 📈 주요 항목 목표 대비 실적(ACT)")
        
        categories = [
            "당월매출", 
            "당월 합계 계약액", 
            f"{CURRENT_WEEK} 계약액", 
            f"{CURRENT_WEEK} 견적건", 
            f"{CURRENT_WEEK} 계약건"
        ]
        
        targets = [
            t_row[('🎯 당월매출', '인별매출(천)', '목표')],
            t_row[('🌟 당월 합계', '계약액(천)', '목표')],
            t_row[(cw_col, '계약액(천)', '목표')] if cw_col else 0,
            t_row[(cw_col, '견적건', '목표')] if cw_col else 0,
            t_row[(cw_col, '계약건', '목표')] if cw_col else 0
        ]
        
        acts = [
            t_row[('🎯 당월매출', '인별매출(천)', 'ACT')],
            t_row[('🌟 당월 합계', '계약액(천)', 'ACT')],
            t_row[(cw_col, '계약액(천)', 'ACT')] if cw_col else 0,
            t_row[(cw_col, '견적건', 'ACT')] if cw_col else 0,
            t_row[(cw_col, '계약건', 'ACT')] if cw_col else 0
        ]
        
        pcts = [pct1, pct2, pct3, t_row[(cw_col, '견적건', '달성율(%)')] if cw_col else 0, pct4]

        text_targets = [f"{v:,.0f}건" if "건" in c else f"{v:,.0f}" for v, c in zip(targets, categories)]
        text_acts = [f"{v:,.0f}건<br>({p:.1f}%)" if "건" in c else f"{v:,.0f}<br>({p:.1f}%)" for v, p, c in zip(acts, pcts, categories)]
        act_colors = ['#10b981' if p >= 100 else '#3b82f6' for p in pcts]

        cat_amt = categories[:3]
        tgt_amt = targets[:3]
        act_amt = acts[:3]
        tt_amt = text_targets[:3]
        ta_amt = text_acts[:3]
        ac_amt = act_colors[:3]
        
        cat_cnt = categories[3:]
        tgt_cnt = targets[3:]
        act_cnt = acts[3:]
        tt_cnt = text_targets[3:]
        ta_cnt = text_acts[3:]
        ac_cnt = act_colors[3:]

        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=cat_amt, y=tgt_amt, name='🎯 목표',
            marker_color='#cbd5e1', text=tt_amt, textposition='outside', 
            textfont=dict(size=14, color='#1e293b'), yaxis='y1'
        ))
        
        fig.add_trace(go.Bar(
            x=cat_amt, y=act_amt, name='🔥 실적(ACT)',
            marker_color=ac_amt, text=ta_amt, textposition='outside', 
            textfont=dict(size=15, color='#0f172a'), yaxis='y1'
        ))
        
        fig.add_trace(go.Bar(
            x=cat_cnt, y=tgt_cnt, name='🎯 목표(건수)',
            marker_color='#cbd5e1', text=tt_cnt, textposition='outside', 
            textfont=dict(size=14, color='#1e293b'), yaxis='y2', showlegend=False
        ))
        
        fig.add_trace(go.Bar(
            x=cat_cnt, y=act_cnt, name='🔥 실적(건수)',
            marker_color=ac_cnt, text=ta_cnt, textposition='outside', 
            textfont=dict(size=15, color='#0f172a'), yaxis='y2', showlegend=False
        ))
        
        fig.update_layout(
            barmode='group', height=450,
            xaxis=dict(tickangle=0, tickfont=dict(size=16, color='black')), 
            yaxis=dict(
                title=dict(text="<b>금액 (천원)</b>", font=dict(size=15, color='#1e3a8a')), 
                tickfont=dict(size=14, color='#1e3a8a')
            ),
            yaxis2=dict(
                title=dict(text="<b>건수 (건)</b>", font=dict(size=15, color='#ea580c')), 
                tickfont=dict(size=14, color='#ea580c'),
                overlaying='y', side='right'
            ),
            margin=dict(l=20, r=20, t=70, b=20),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(size=18, color='black') 
            ),
            plot_bgcolor='white'
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
    # ---------------------------------------------------------
    
    st.markdown(f"""
    <div style='background-color: #f8fafc; padding: 15px; border-left: 5px solid #3b82f6; border-radius: 5px; margin-bottom: 20px;'>
        <h2 style='margin:0; color: #1e3a8a;'>📌 {current_month}월 {CURRENT_WEEK} VDT 현황</h2>
    </div>
    """, unsafe_allow_html=True)
    
    def render_custom_html_table(df):
        dealer_col = ('기본정보', '대리점', '대리점')
        hc_col = ('기본정보', 'HC명', 'HC명')
        
        unique_dealers = [d for d in df[dealer_col].unique() if d not in ["🌟 총계"]]
        dealer_colors = {}
        colors = ['#f8fafc', '#ffffff']
        for idx, d in enumerate(unique_dealers):
            dealer_colors[d] = colors[idx % len(colors)]
            
        html = ["<div class='vdt-table-container'><table class='vdt-table'><thead>"]
        
        html.append("<tr><th rowspan='3' style='position: sticky; top: 0; left: 0; z-index: 15; background-color: #0f172a; min-width: 90px; max-width: 90px;'>대리점</th><th rowspan='3' style='position: sticky; top: 0; left: 90px; z-index: 15; background-color: #0f172a; min-width: 110px; max-width: 110px; border-right: 2px solid #94a3b8;'>HC명</th>")
        
        headers_l1 = []
        for col in df.columns[2:]:
            if col[0] not in headers_l1: headers_l1.append(col[0])
                
        for h1 in headers_l1:
            is_curr = CURRENT_WEEK in h1
            is_monthly = "당월" in h1
            
            style_parts = []
            if is_curr:
                style_parts.append("background-color: #1e3a8a")
                style_parts.append("border: 3px solid #60a5fa") 
            elif is_monthly:
                style_parts.append("background-color: #064e3b") 
                style_parts.append("color: #a7f3d0") 
                style_parts.append("border-top: 2px solid #047857")
            
            if h1 == '🎯 당월매출':
                style_parts.append("border-right: 3px solid #1e293b")
                
            if "🌟 당월 합계" in h1:
                style_parts.append("border-right: 4px solid #94a3b8")
                
            bg_style = f"style='{'; '.join(style_parts)}'" if style_parts else ""
            
            if "🎯" in h1: html.append(f"<th colspan='3' {bg_style}>{h1}</th>")
            else: html.append(f"<th colspan='9' {bg_style}>{h1}</th>")
        html.append("</tr>")
        
        html.append("<tr>")
        for h1 in headers_l1:
            is_curr = CURRENT_WEEK in h1
            is_monthly = "당월" in h1
            
            style_parts = []
            if is_curr:
                style_parts.append("background-color: #1e40af")
                style_parts.append("border-left: 3px solid #60a5fa")
                style_parts.append("border-right: 3px solid #60a5fa")
            elif is_monthly:
                style_parts.append("background-color: #065f46")
                style_parts.append("color: #a7f3d0")
            
            if h1 == '🎯 당월매출':
                style_parts.append("border-right: 3px solid #1e293b")
                
            if "🌟 당월 합계" in h1: style_parts.append("border-right: 4px solid #94a3b8")
                
            bg_style = f"style='{'; '.join(style_parts)}'" if style_parts else ""
            
            if "🎯" in h1: html.append(f"<th colspan='3' {bg_style}>인별매출(천)</th>")
            else:
                html.append(f"<th colspan='3' {bg_style}>계약액(천)</th>")
                html.append(f"<th colspan='3' {bg_style}>견적건</th>")
                html.append(f"<th colspan='3' {bg_style}>계약건</th>")
        html.append("</tr>")
        
        html.append("<tr>")
        for col in df.columns[2:]:
            is_curr = CURRENT_WEEK in col[0]
            is_monthly = "당월" in col[0]
            
            is_first_of_week = is_curr and col[1] == '계약액(천)' and col[2] == '목표'
            is_last_of_week = is_curr and col[1] == '계약건' and col[2] == '달성율(%)'
            is_last_of_sales = col[0] == '🎯 당월매출' and col[2] == '달성율(%)'
            is_last_monthly = "🌟 당월 합계" in col[0] and col[1] == '계약건' and col[2] == '달성율(%)'
            
            style_parts = []
            if is_curr:
                style_parts.append("background-color: #1d4ed8")
                style_parts.append("border-bottom: 3px solid #60a5fa")
                if is_first_of_week: style_parts.append("border-left: 3px solid #60a5fa")
                if is_last_of_week: style_parts.append("border-right: 3px solid #60a5fa")
            elif is_monthly:
                style_parts.append("background-color: #047857")
                style_parts.append("color: #a7f3d0")
            
            if is_last_of_sales:
                style_parts.append("border-right: 3px solid #1e293b")
                
            if is_last_monthly: style_parts.append("border-right: 4px solid #94a3b8")
                
            bg_style = f"style='{'; '.join(style_parts)}'" if style_parts else ""
            html.append(f"<th {bg_style}>{col[2]}</th>")
        html.append("</tr></thead><tbody>")
        
        for r_idx in range(len(df)):
            row = df.iloc[r_idx]
            dealer = row[dealer_col]
            hc = row[hc_col]
            
            if str(hc) == "합계": 
                bg_color = "#e2e8f0"
                row_bg = f"style='background-color: {bg_color}; font-weight: bold;'"
            elif "🌟" in str(hc): 
                bg_color = "#cbd5e1"
                row_bg = f"style='background-color: {bg_color}; font-weight: bold;'"
            else:
                bg_color = dealer_colors.get(dealer, '#ffffff')
                row_bg = f"style='background-color: {bg_color};'"
                
            html.append(f"<tr {row_bg}>")
            
            html.append(f"<td class='text-center' style='position: sticky; left: 0; z-index: 5; background-color: {bg_color}; min-width: 90px; max-width: 90px; border-right: 1px solid #cbd5e1;'>{dealer}</td>")
            html.append(f"<td class='text-center' style='position: sticky; left: 90px; z-index: 5; background-color: {bg_color}; min-width: 110px; max-width: 110px; border-right: 2px solid #94a3b8;'>{hc}</td>")
            
            for c_idx, val in enumerate(row[2:]):
                col_obj = df.columns[c_idx + 2]
                is_curr = CURRENT_WEEK in col_obj[0]
                is_monthly = "당월" in col_obj[0]
                
                is_first_of_week = is_curr and col[1] == '계약액(천)' and col[2] == '목표'
                is_last_of_week = is_curr and col[1] == '계약건' and col[2] == '달성율(%)'
                is_last_of_sales = col[0] == '🎯 당월매출' and col[obj[2] == '달성율(%)'
                is_last_monthly = "🌟 당월 합계" in col[0] and col_obj[1] == '계약건' and col_obj[2] == '달성율(%)'
                
                style_parts = []
                if is_curr:
                    style_parts.append("background-color: rgba(37, 99, 235, 0.12)") 
                    if is_first_of_week: style_parts.append("border-left: 3px solid #3b82f6")
                    if is_last_of_week: style_parts.append("border-right: 3px solid #3b82f6")
                elif is_monthly:
                    style_parts.append("background-color: rgba(5, 150, 105, 0.08)") 
                
                if is_last_of_sales:
                    style_parts.append("border-right: 3px solid #1e293b")
                    
                if is_last_monthly: style_parts.append("border-right: 4px solid #94a3b8")
                    
                if col_obj[2] == '달성율(%)':
                    val_str = f"{val:.1f}%"
                    if val >= 100:
                        val_str = f"<span style='color: #047857; font-weight: 900;'>{val_str}</span>" if is_monthly else f"<span style='color: #1d4ed8; font-weight: 900;'>{val_str}</span>"
                    elif val > 0:
                        val_str = f"<span style='font-weight: 600;'>{val_str}</span>"
                else:
                    val_str = f"{val:,.0f}"
                    
                border_style = f"{'; '.join(style_parts)}" if style_parts else ""
                html.append(f"<td style='{border_style}'>{val_str}</td>")
            html.append("</tr>")
            
        html.append("</tbody></table></div>")
        return "".join(html)
    
    table_html = render_custom_html_table(final_df)
    st.markdown(table_html, unsafe_allow_html=True)
