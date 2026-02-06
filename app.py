import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- 1. เชื่อมต่อระบบ ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_clean_df(sheet_name):
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"])
        creds = Credentials.from_service_account_info(info, scopes=scope)
        gc = gspread.authorize(creds)
        sh = gc.open(sheet_name)
        worksheet = sh.get_worksheet(0)
        
        # อ่านข้อมูลทั้งหมดมาเป็นลิสต์
        data = worksheet.get_all_values()
        if not data:
            return pd.DataFrame()
            
        # สร้าง DataFrame โดยใช้แถวแรกเป็นหัวข้อ
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # ลบคอลัมน์ที่ไม่มีชื่อ (ป้องกัน Error Duplicate)
        df = df.loc[:, df.columns != ""]
        # ลบคอลัมน์ที่ชื่อซ้ำ (ถ้ามี)
        df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    except Exception as e:
        st.error(f"ไม่สามารถโหลดไฟล์ {sheet_name} ได้: {e}")
        return pd.DataFrame()

# --- 2. หน้าตาเว็บ (แบบที่คุณสร้างไว้) ---
st.set_page_config(page_title="TP2025 Dashboard", layout="wide")

st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

if page == "📊 วิเคราะห์ยอดขาย":
    st.title("📊 ระบบวิเคราะห์ยอดขาย ทีพี2025")
    df = get_clean_df("ทีพี2025")
    if not df.empty:
        st.write("### ข้อมูลยอดขายล่าสุด")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("กำลังรอข้อมูลจาก Google Sheets...")

elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้าคงเหลือ")
    df = get_clean_df("สต็อกสินค้า")
    if not df.empty:
        st.write("### รายการสินค้าในสต็อก")
        st.dataframe(df, use_container_width=True)
