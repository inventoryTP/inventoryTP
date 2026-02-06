import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- 1. ตั้งค่าการเชื่อมต่อ (ไม่แก้แล้ว) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_gspread_client():
    # ดึงข้อมูลจาก Secrets ที่คุณเพิ่งเซฟไป
    info = json.loads(st.secrets["gcp_service_account"]["json_data"])
    creds = Credentials.from_service_account_info(info, scopes=scope)
    return gspread.authorize(creds)

# --- 2. ตั้งค่าหน้าเว็บ (หน้าตาเดิมที่คุณต้องการ) ---
st.set_page_config(page_title="TP2025 Dashboard", layout="wide")

st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

try:
    gc = get_gspread_client()

    if page == "📊 วิเคราะห์ยอดขาย":
        st.title("📊 ระบบวิเคราะห์ยอดขาย ทีพี2025")
        # เปิดไฟล์ชื่อ "ทีพี2025" (ตามรูปที่ 49)
        sh = gc.open("ทีพี2025")
        data = sh.get_worksheet(0).get_all_records()
        st.dataframe(pd.DataFrame(data), use_container_width=True)

    elif page == "📦 สต็อกสินค้าคงเหลือ":
        st.title("📦 ระบบตรวจสอบสต็อกสินค้าคงเหลือ")
        # เปิดไฟล์ชื่อ "สต็อกสินค้า" (ตามรูปที่ 49)
        sh = gc.open("สต็อกสินค้า")
        data = sh.get_worksheet(0).get_all_records()
        st.dataframe(pd.DataFrame(data), use_container_width=True)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
    st.info("ตรวจสอบว่าคุณได้แชร์สิทธิ์ 'Editor' ใน Google Sheets ให้เมล my-sheets-bot... แล้วหรือยัง?")

