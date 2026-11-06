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
    .user-info-name { font-size: 18px !important; font-weight: 900 !important; color: #0369a1 !
