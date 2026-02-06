import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- 1. เชื่อมต่อระบบ (ใช้กุญแจจาก Secrets) ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_data(sheet_name):
    try:
        info = json.loads(st.secrets["gcp_service_account"]["json_data"])
        creds = Credentials.from_service_account_info(info, scopes=scope)
        gc = gspread.authorize(creds)
        sh = gc.open(sheet_name)
        worksheet = sh.get_worksheet(0)
        
        # ดึงข้อมูลและจัดการปัญหาช่องว่าง/คอลัมน์ซ้ำ
        data = worksheet.get_all_values()
        if not data:
            return pd.DataFrame()
        
        # สร้าง DataFrame และเลือกเฉพาะคอลัมน์ที่มีข้อมูลจริง (A-E)
        df = pd.DataFrame(data[1:], columns=data[0])
        df = df.iloc[:, 0:5] 
        return df
    except Exception as e:
        st.error(f"เชื่อมต่อไฟล์ {sheet_name} ไม่สำเร็จ: {e}")
        return pd.DataFrame()

# --- 2. หน้าตาเว็บ (แบบเดิมที่คุณชอบ) ---
st.set_page_config(page_title="TP2025 Dashboard", layout="wide")

# เมนูข้างๆ
st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

if page == "📊 วิเคราะห์ยอดขาย":
    st.title("📊 ระบบวิเคราะห์ยอดขาย ทีพี2025")
    df_sales = get_data("ทีพี2025")
    if not df_sales.empty:
        st.write("### ข้อมูลยอดขายล่าสุด")
        st.dataframe(df_sales, use_container_width=True)
        # เพิ่มกราฟเล็กๆ ให้ดูสวยงามเหมือนเดิม
        if "รวมเงิน" in df_sales.columns:
            st.bar_chart(df_sales.set_index(df_sales.columns[2])["รวมเงิน"])

elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้าคงเหลือ")
    df_stock = get_data("สต็อกสินค้า")
    if not df_stock.empty:
        st.write("### รายการสินค้าในสต็อก")
        st.dataframe(df_stock, use_container_width=True)



