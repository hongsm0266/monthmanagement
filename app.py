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

# --- 커스텀 CSS (Noto Sans KR 폰트 적용 완료) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
    
    html, body, [class*="css"], [class*="st-"], th, td { font-family: 'Noto Sans KR', sans-serif !important; }
    
    .vdt-table-container { width: 100%; max-height: 65vh; overflow: auto; border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 10px; }
    .vdt-table-container::-webkit-scrollbar { width: 14px; height: 14px; }
    .vdt-table-container::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 8px; }
    .vdt-table-container::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 8px; border: 3px solid #f1f5f9; }
    .vdt-table-container::-webkit-scrollbar-thumb:hover { background: #64748b; }

    .vdt-table { width: 100%; border-collapse: collapse; font-size: 12px; white-space: nowrap; }
    .vdt-table thead th { height: 34px; box-sizing: border-box; position: sticky; z-index: 10; background-clip: padding-box; }
    .vdt-table thead tr:nth-child(1) th { top: 0; }
    .vdt-table thead tr:nth-child(2) th { top: 33px; }
    .vdt-table thead tr:nth-child(3) th { top: 66px; }

    .vdt-table th { background-color: #0f172a; color: white; padding: 8px 10px; text-align: center; border: 1px solid #334155; font-weight: 600; }
    .vdt-table td { padding: 6px 10px; text-align: right; border: 1px solid #e2e8f0; }
    .vdt-table td.text-center { text-align: center; }
    .title-box { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
    h1 { font-weight: 900 !important; color: white !important; font-size: 24px !important; margin: 0; }
    
    div[data-testid="metric-container"] { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    [data-testid="stMetricLabel"] { background-color: #e2e8f0 !important; padding: 6px 12px !important; border-radius: 6px !important; border-left: 5px solid #3b82f6 !important; display: inline-block !important; margin-bottom: 8px !important; box-shadow: 1px 2px 4px rgba(0,0,0,0.08) !important; }
    [data-testid="stMetricLabel"] * { font-size: 15px !important; font-weight: 900 !important; color: #0f172a !important; letter-spacing: -0.3px; }
    [data-testid="stMetricValue"] > div { font-size: 28px !important; font-weight: 900 !important; color: #1e3a8a !important; margin-top: 5px; }
    [data-testid="stMetricDelta"] * { font-size: 14px !important; font-weight: 800 !important; }
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

now = datetime.now()
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
                    st.toast(f"⏳ 서버 요청 한도 도달. {wait_time}초 후 자동으로 재시도합니다... (새로고침 하지 마세요!)", icon="⚠️")
                    time.sleep(wait_time)
                    continue
            raise e

@st.cache_data(ttl=600)
def load_vdt_data():
    if not client: return pd.DataFrame(), {}, {}, {}, {}, []
    
    status_box = st.empty()
    try:
        status_box.info("🔍 0단계: 구글 시트 연결 중...")
        sh = safe_api_call(client.open_by_url, SHEET_URL)
        all_worksheets = [ws.title for ws in safe_api_call(sh.worksheets)]
        
        target_sheet_name = "주차별 목표 세팅"
        if target_sheet_name not in all_worksheets: 
            st.error(f"🚨 '{target_sheet_name}' 탭을 찾을 수 없습니다.")
            return pd.DataFrame(), {}, {}, {}, {}, []
        
        target_ws = sh.worksheet(target_sheet_name)
        status_box.info("📊 1단계: 인별 매출목표 및 비중 계산 중...")
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

        status_box.info("🎯 2단계: 대리점 주차별 목표 스캔 중...")
        
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
            '5주차': {'amt':
