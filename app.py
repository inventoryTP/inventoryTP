import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- 1. เชื่อมต่อระบบ ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    info = json.loads(st.secrets["gcp_service_account"]["json_data"])
    creds = Credentials.from_service_account_info(info, scopes=scope)
    gc = gspread.authorize(creds)

    # --- 2. ตั้งค่าหน้าเว็บ ---
    st.set_page_config(page_title="TP2025 Dashboard", layout="wide")
    st.sidebar.title("🚀 เมนูหลัก")
    page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

    if page == "📊 วิเคราะห์ยอดขาย":
        st.title("📊 ระบบวิเคราะห์ยอดขาย ทีพี2025")
        sh = gc.open("ทีพี2025")
        worksheet = sh.get_worksheet(0)
        
        # แก้ปัญหา Duplicates: ดึงข้อมูลมาเป็นลิสต์ก่อนแล้วเลือกแค่ 5 คอลัมน์แรก
        all_values = worksheet.get_all_values()
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        df = df.iloc[:, 0:5] # บังคับเอาแค่คอลัมน์ A ถึง E
        
        st.dataframe(df, use_container_width=True)

    elif page == "📦 สต็อกสินค้าคงเหลือ":
        st.title("📦 ระบบตรวจสอบสต็อกสินค้าคงเหลือ")
        sh = gc.open("สต็อกสินค้า")
        worksheet = sh.get_worksheet(0)
        
        all_values = worksheet.get_all_values()
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        df = df.iloc[:, 0:5] # บังคับเอาแค่ 5 คอลัมน์แรกเหมือนกัน
        
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาด: {e}")


