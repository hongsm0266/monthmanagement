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
import plotly.graph_objects as go # 🚀 고급 차트를 위한 라이브러리 추가

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
        overflow-x: auto;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        margin-top: 10px;
    }
    .vdt-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
        white-space: nowrap;
    }
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
    
    /* 요약 지표 카드 스타일 */
    div[data-testid="metric-container"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# 메인 제목
current_month = datetime.now().month
st.markdown(f"<div class='title-box'><h1>📊 충청호남팀 영업사원 주차별 VDT 목표 관리 ({current_month}월)</h1></div>", unsafe_allow_html=True)

def clean_val(v):
    if not v or pd.isna(v) or str(v).strip() == '': return 0.0
    v_str = str(v).replace('%', '').replace(',', '').replace('원', '').replace('건', '').strip()
    multiplier = 1
    if '억' in v_str:
        v_str = v_str.replace('억', '')
        multiplier = 100000000
    elif '만' in v_str:
        v_str = v_str.replace('만', '')
        multiplier = 10000
    try: return float(v_str) * multiplier
    except: return 0.0

def get_week_name(sheet_title):
    try:
        parts = sheet_title.replace('일','').split('/') 
        if len(parts) != 2: return None
        m, d = int(parts[0]), int(parts[1])
        if m == 7 and d >= 27: return '0주차'
        if m == 8:
            if d <= 2: return '0주차'
            elif d <= 9: return '1주차'
            elif d <= 16: return '2주차'
            elif d <= 23: return '3주차'
            elif d <= 30: return '4주차'
            else: return '5주차'
    except:
        pass
    return None

now = datetime.now()
CURRENT_WEEK = get_week_name(f"{now.month}/{now.day}") 
if not CURRENT_WEEK: CURRENT_WEEK = '1주차'

@st.cache_data(ttl=60)
def load_vdt_data():
    if not client: return pd.DataFrame(), {}
    
    status_box = st.empty()
    try:
        status_box.info("🔍 0단계: 구글 시트 연결 중...")
        sh = client.open_by_url(SHEET_URL)
        all_worksheets = [ws.title for ws in sh.worksheets()]
        
        target_sheet_name = "주차별 목표 세팅"
        if target_sheet_name not in all_worksheets: 
            st.error(f"🚨 '{target_sheet_name}' 탭을 찾을 수 없습니다.")
            return pd.DataFrame(), {}
        
        target_ws = sh.worksheet(target_sheet_name)
        
        status_box.info("📊 1단계: 인별 매출목표 및 비중 계산 중...")
        hc_target_data = target_ws.get("A16:D48")
        
        hc_info = []         
        dealer_sales_sum = {} 
        
        for row in hc_target_data:
            if len(row) >= 4 and str(row[0]).strip() and str(row[1]).strip():
                dealer = str(row[0]).strip()
                hc_name = str(row[1]).strip()
                
                if dealer in ['대리점', '대리점명', '구분'] or hc_name in ['HC', 'HC명', '영업사원', '이름']:
                    continue
                    
                sales_target = clean_val(row[3]) / 1000.0
                
                if (dealer, hc_name) not in [(d, h) for d, h, _ in hc_info]:
                    hc_info.append((dealer, hc_name, sales_target))
                    dealer_sales_sum[dealer] = dealer_sales_sum.get(dealer, 0.0) + sales_target

        hc_weights = {}
        for dealer, hc, target in hc_info:
            d_sum = dealer_sales_sum.get(dealer, 0.0)
            hc_weights[hc] = (target / d_sum) if d_sum > 0 else 0.0

        status_box.info("🎯 2단계: 대리점 주차별 목표 스캔 중...")
        target_data = target_ws.get("A1:T15")
        
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
                d_name = str(row[0]).strip()
                dealer_targets[d_name] = {}
                for wk, cols in week_cols.items():
                    t_amt = (clean_val(row[cols['amt']]) / 1000.0) if len(row) > cols['amt'] else 0.0 
                    t_est = clean_val(row[cols['est']]) if len(row) > cols['est'] else 0.0
                    t_cnt = clean_val(row[cols['cnt']]) if len(row) > cols['cnt'] else 0.0
                    dealer_targets[d_name][wk] = {'amt': t_amt, 'est': t_est, 'cnt': t_cnt}

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

        status_box.info("📈 3단계: 일별 실적(ACT) 스캔 및 누적 취합 중...")
        daily_sheets = [ws for ws in sh.worksheets() if "/" in ws.title]
        
        acts = {hc: {wk: {'amt': 0, 'est': 0, 'cnt': 0} for wk in week_keys} for _, hc, _ in hc_info}
        month_acts = {hc: {'amt': 0, 'est': 0, 'cnt': 0} for _, hc, _ in hc_info}
        acts_sales = {hc: 0 for _, hc, _ in hc_info}
        latest_sheet = None
        
        for ws in daily_sheets:
            wk = get_week_name(ws.title)
            latest_sheet = ws
            d_data = ws.get_all_values()
            
            for row in d_data:
                if len(row) > 15: 
                    hc_name = str(row[3]).strip()
                    if hc_name in acts:
                        est_val = clean_val(row[4])
                        cnt_val = clean_val(row[5])
                        amt_val = clean_val(row[15])
                        
                        if wk:
                            acts[hc_name][wk]['est'] += est_val
                            acts[hc_name][wk]['cnt'] += cnt_val
                            acts[hc_name][wk]['amt'] += amt_val
                        
                        month_acts[hc_name]['est'] += est_val
                        month_acts[hc_name]['cnt'] += cnt_val
                        month_acts[hc_name]['amt'] += amt_val

        if latest_sheet:
            l_data = latest_sheet.get_all_values() 
            for row in l_data:
                if len(row) > 18:
                    hc_name = str(row[3]).strip()
                    if hc_name in acts_sales:
                        acts_sales[hc_name] = clean_val(row[18])

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
            row_data = [dealer, hc]
            row_data.extend([sales_tgt, acts_sales.get(hc, 0), 0.0])
            
            m_tgt_amt = sum([targets.get(hc, {}).get(wk, {}).get('amt', 0) for wk in week_keys])
            m_tgt_est = sum([targets.get(hc, {}).get(wk, {}).get('est', 0) for wk in week_keys])
            m_tgt_cnt = sum([targets.get(hc, {}).get(wk, {}).get('cnt', 0) for wk in week_keys])
            
            m_act = month_acts.get(hc, {'amt': 0, 'est': 0, 'cnt': 0})
            
            row_data.extend([
                m_tgt_amt, m_act['amt'], 0.0,
                m_tgt_est, m_act['est'], 0.0,
                m_tgt_cnt, m_act['cnt'], 0.0
            ])
            
            for wk in week_keys:
                t = targets.get(hc, {}).get(wk, {'amt': 0, 'est': 0, 'cnt': 0})
                a = acts.get(hc, {}).get(wk, {'amt': 0, 'est': 0, 'cnt': 0})
                row_data.extend([t['amt'], a['amt'], 0.0, t['est'], a['est'], 0.0, t['cnt'], a['cnt'], 0.0])
                
            rows.append(row_data)

        df = pd.DataFrame(rows, columns=columns)
        
        for col in df.columns[2:]:
            if col[2] == '달성율(%)':
                tgt_col = (col[0], col[1], '목표')
                act_col = (col[0], col[1], 'ACT')
                df[col] = np.where(df[tgt_col] > 0, (df[act_col] / df[tgt_col] * 100).round(1), 0)
        
        status_box.empty()
        return df, date_headers

    except Exception as e:
        status_box.empty()
        st.error("🚨 데이터 구성 중 에러가 발생했습니다!")
        with st.expander("🛠️ 상세 에러 보기"): st.code(traceback.format_exc())
        return pd.DataFrame(), {}

def calculate_subtotals(df):
    if df.empty: return df
    
    result_rows = []
    dealer_col = ('기본정보', '대리점', '대리점')
    hc_col = ('기본정보', 'HC명', 'HC명')
    
    for dealer, group in df.groupby(dealer_col, sort=False):
        for _, row in group.iterrows(): result_rows.append(row)
            
        subtotal = group.select_dtypes(include=[np.number]).sum()
        subtotal[dealer_col] = dealer
        subtotal[hc_col] = "합계"
        
        for col in df.columns[2:]:
            if col[2] == '달성율(%)':
                tgt_col = (col[0], col[1], '목표')
                act_col = (col[0], col[1], 'ACT')
                subtotal[col] = round((subtotal[act_col] / subtotal[tgt_col] * 100), 1) if subtotal[tgt_col] > 0 else 0.0
        result_rows.append(pd.Series(subtotal))

    grand_total = df.select_dtypes(include=[np.number]).sum()
    grand_total[dealer_col] = "🌟 총계"
    grand_total[hc_col] = "🌟 총계"
    
    for col in df.columns[2:]:
        if col[2] == '달성율(%)':
            tgt_col = (col[0], col[1], '목표')
            act_col = (col[0], col[1], 'ACT')
            grand_total[col] = round((grand_total[act_col] / grand_total[tgt_col] * 100), 1) if grand_total[tgt_col] > 0 else 0.0
    result_rows.append(pd.Series(grand_total))
    
    return pd.DataFrame(result_rows)


df_raw, date_headers = load_vdt_data()

if not df_raw.empty:
    final_df = calculate_subtotals(df_raw)
    
    # ---------------------------------------------------------
    # 🚀 개인/대리점 선택 및 실적 차트 대시보드
    # ---------------------------------------------------------
    col_blank, col_sel, col_btn = st.columns([3, 4, 2])
    
    with col_sel:
        valid_choices = ["🔍 선택 안함 (전체 표만 보기)"]
        for r_idx in range(len(final_df)):
            dealer = final_df.iloc[r_idx][('기본정보', '대리점', '대리점')]
            hc = final_df.iloc[r_idx][('기본정보', 'HC명', 'HC명')]
            if hc == "🌟 총계": continue
            if hc == "합계":
                valid_choices.append(f"🏢 [{dealer}] 대리점 합계")
            else:
                valid_choices.append(f"👤 {dealer} - {hc}")
        
        selected_option = st.selectbox("🎯 개별 인원 및 대리점 요약 보기", options=valid_choices)
        
    with col_btn:
        st.write("") # 버튼 줄맞춤용 공백
        if st.button("🔄 실적 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if selected_option != "🔍 선택 안함 (전체 표만 보기)":
        st.markdown("---")
        st.markdown(f"### ✨ **{selected_option.split(' ', 1)[1]}** 실적 요약 (당월 & {CURRENT_WEEK})")
        
        if "대리점 합계" in selected_option:
            target_dealer = selected_option.replace("🏢 [", "").replace("] 대리점 합계", "")
            target_hc = "합계"
        else:
            parts = selected_option.replace("👤 ", "").split(" - ")
            target_dealer = parts[0]
            target_hc = parts[1]
            
        t_row = final_df[(final_df[('기본정보', '대리점', '대리점')] == target_dealer) & (final_df[('기본정보', 'HC명', 'HC명')] == target_hc)].iloc[0]
        
        curr_wk_cols = [c[0] for c in final_df.columns if CURRENT_WEEK in c[0]]
        cw_col = curr_wk_cols[0] if curr_wk_cols else None
        
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            act1 = t_row[('🎯 당월매출', '인별매출(천)', 'ACT')]
            pct1 = t_row[('🎯 당월매출', '인별매출(천)', '달성율(%)')]
            st.metric("🌲 당월매출 (천원)", f"{act1:,.0f}", f"{pct1:.1f}% 달성")
        with mc2:
            act2 = t_row[('🌟 당월 합계', '계약액(천)', 'ACT')]
            pct2 = t_row[('🌟 당월 합계', '계약액(천)', '달성율(%)')]
            st.metric("🌟 당월 전체 계약액 (천원)", f"{act2:,.0f}", f"{pct2:.1f}% 달성")
        with mc3:
            act3 = t_row[(cw_col, '계약액(천)', 'ACT')] if cw_col else 0
            pct3 = t_row[(cw_col, '계약액(천)', '달성율(%)')] if cw_col else 0
            st.metric(f"🌊 {CURRENT_WEEK} 계약액 (천원)", f"{act3:,.0f}", f"{pct3:.1f}% 달성")
        with mc4:
            act4 = t_row[(cw_col, '계약건', 'ACT')] if cw_col else 0
            pct4 = t_row[(cw_col, '계약건', '달성율(%)')] if cw_col else 0
            st.metric(f"🌊 {CURRENT_WEEK} 계약건 (건)", f"{act4:,.0f}", f"{pct4:.1f}% 달성")
            
        # 📈 고급 Plotly 차트 적용 부분
        st.markdown("##### 📈 주요 항목 목표 대비 실적(ACT)")
        
        categories = ["당월매출", "당월 합계 계약액", f"{CURRENT_WEEK} 계약액"]
        targets = [
            t_row[('🎯 당월매출', '인별매출(천)', '목표')],
            t_row[('🌟 당월 합계', '계약액(천)', '목표')],
            t_row[(cw_col, '계약액(천)', '목표')] if cw_col else 0
        ]
        acts = [
            t_row[('🎯 당월매출', '인별매출(천)', 'ACT')],
            t_row[('🌟 당월 합계', '계약액(천)', 'ACT')],
            t_row[(cw_col, '계약액(천)', 'ACT')] if cw_col else 0
        ]
        pcts = [
            t_row[('🎯 당월매출', '인별매출(천)', '달성율(%)')],
            t_row[('🌟 당월 합계', '계약액(천)', '달성율(%)')],
            t_row[(cw_col, '계약액(천)', '달성율(%)')] if cw_col else 0
        ]

        fig = go.Figure()
        
        # 목표 막대
        fig.add_trace(go.Bar(
            x=categories, y=targets, name='🎯 목표',
            marker_color='#cbd5e1',
            text=[f"{v:,.0f}" for v in targets],
            textposition='auto',
            textfont=dict(size=13, color='#475569')
        ))
        
        # 실적 막대 (100% 이상 달성 시 초록색, 미만 시 파란색)
        act_colors = ['#10b981' if p >= 100 else '#3b82f6' for p in pcts]
        fig.add_trace(go.Bar(
            x=categories, y=acts, name='🔥 실적(ACT)',
            marker_color=act_colors,
            text=[f"{v:,.0f}<br>({p:.1f}%)" for v, p in zip(acts, pcts)],
            textposition='auto',
            textfont=dict(size=14, color='white', weight='bold')
        ))
        
        fig.update_layout(
            barmode='group', height=400,
            xaxis=dict(tickangle=0, tickfont=dict(size=15, weight='bold')), # 가로축 글씨 크게 및 수평 정렬
            yaxis=dict(title="금액 (천원)"),
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor='white'
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
    # ---------------------------------------------------------
    
    def render_custom_html_table(df):
        dealer_col = ('기본정보', '대리점', '대리점')
        hc_col = ('기본정보', 'HC명', 'HC명')
        
        unique_dealers = [d for d in df[dealer_col].unique() if d not in ["🌟 총계"]]
        dealer_colors = {}
        colors = ['#f8fafc', '#ffffff']
        for idx, d in enumerate(unique_dealers):
            dealer_colors[d] = colors[idx % len(colors)]
            
        html = ["<div class='vdt-table-container'><table class='vdt-table'><thead>"]
        
        # --- 헤더 1열 ---
        html.append("<tr><th rowspan='3'>대리점</th><th rowspan='3' style='border-right: 2px solid #94a3b8;'>HC명</th>")
        
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
                
            if "🌟 당월 합계" in h1:
                style_parts.append("border-right: 4px solid #94a3b8")
                
            bg_style = f"style='{'; '.join(style_parts)}'" if style_parts else ""
            
            if "🎯" in h1: html.append(f"<th colspan='3' {bg_style}>{h1}</th>")
            else: html.append(f"<th colspan='9' {bg_style}>{h1}</th>")
        html.append("</tr>")
        
        # --- 헤더 2열 ---
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
                
            if "🌟 당월 합계" in h1: style_parts.append("border-right: 4px solid #94a3b8")
                
            bg_style = f"style='{'; '.join(style_parts)}'" if style_parts else ""
            
            if "🎯" in h1: html.append(f"<th colspan='3' {bg_style}>인별매출(천)</th>")
            else:
                html.append(f"<th colspan='3' {bg_style}>계약액(천)</th>")
                html.append(f"<th colspan='3' {bg_style}>견적건</th>")
                html.append(f"<th colspan='3' {bg_style}>계약건</th>")
        html.append("</tr>")
        
        # --- 헤더 3열 ---
        html.append("<tr>")
        for col in df.columns[2:]:
            is_curr = CURRENT_WEEK in col[0]
            is_monthly = "당월" in col[0]
            
            is_first_of_week = is_curr and col[1] == '계약액(천)' and col[2] == '목표'
            is_last_of_week = is_curr and col[1] == '계약건' and col[2] == '달성율(%)'
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
                
            if is_last_monthly: style_parts.append("border-right: 4px solid #94a3b8")
                
            bg_style = f"style='{'; '.join(style_parts)}'" if style_parts else ""
            html.append(f"<th {bg_style}>{col[2]}</th>")
        html.append("</tr></thead><tbody>")
        
        # --- 데이터 내용 생성 ---
        for r_idx in range(len(df)):
            row = df.iloc[r_idx]
            dealer = row[dealer_col]
            hc = row[hc_col]
            
            if str(hc) == "합계": row_bg = "style='background-color: #e2e8f0; font-weight: bold;'"
            elif "🌟" in str(hc): row_bg = "style='background-color: #cbd5e1; font-weight: bold;'"
            else:
                bg = dealer_colors.get(dealer, '#ffffff')
                row_bg = f"style='background-color: {bg};'"
                
            html.append(f"<tr {row_bg}>")
            html.append(f"<td class='text-center' style='border-right: 1px solid #cbd5e1;'>{dealer}</td>")
            html.append(f"<td class='text-center' style='border-right: 2px solid #94a3b8;'>{hc}</td>")
            
            for c_idx, val in enumerate(row[2:]):
                col_obj = df.columns[c_idx + 2]
                is_curr = CURRENT_WEEK in col_obj[0]
                is_monthly = "당월" in col_obj[0]
                
                is_first_of_week = is_curr and col_obj[1] == '계약액(천)' and col_obj[2] == '목표'
                is_last_of_week = is_curr and col_obj[1] == '계약건' and col_obj[2] == '달성율(%)'
                is_last_monthly = "🌟 당월 합계" in col_obj[0] and col_obj[1] == '계약건' and col_obj[2] == '달성율(%)'
                
                style_parts = []
                if is_curr:
                    style_parts.append("background-color: rgba(37, 99, 235, 0.12)") 
                    if is_first_of_week: style_parts.append("border-left: 3px solid #3b82f6")
                    if is_last_of_week: style_parts.append("border-right: 3px solid #3b82f6")
                elif is_monthly:
                    style_parts.append("background-color: rgba(5, 150, 105, 0.08)") 
                    
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

    st.info(f"💡 현재 진행 주차: **'{CURRENT_WEEK}'** (해당 주차 두꺼운 테두리 및 배경 음영 강조 적용 완료)")
    
    table_html = render_custom_html_table(final_df)
    st.markdown(table_html, unsafe_allow_html=True)
