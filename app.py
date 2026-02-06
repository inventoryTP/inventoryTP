import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json

# --- 1. ฟังก์ชันดึงข้อมูล ---
def get_data(spreadsheet_name, sheet_name):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        info = json.loads(st.secrets["gcp_service_account"]["json_data"])
        creds = Credentials.from_service_account_info(info, scopes=scope)
        gc = gspread.authorize(creds)
        sh = gc.open(spreadsheet_name)
        worksheet = sh.worksheet(sheet_name)
        return pd.DataFrame(worksheet.get_all_records())
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

# --- 2. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="TP2025 Dashboard", layout="wide")
st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

if page == "📊 วิเคราะห์ยอดขาย":
    st.title("📊 ระบบวิเคราะห์ยอดขาย ทีพี2025")
    df = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")

    if not df.empty:
        # ล้างชื่อคอลัมน์ให้ไม่มีช่องว่าง (ป้องกัน Error)
        df.columns = [str(c).strip() for c in df.columns]

        # สรุปภาพรวมด้านบน
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 จำนวนรายการทั้งหมด", f"{len(df):,} รายการ")
        with col2:
            if "รวมเงิน" in df.columns:
                total_sales = pd.to_numeric(df["รวมเงิน"], errors='coerce').sum()
                st.metric("💰 ยอดขายรวมทั้งหมด", f"{total_sales:,.2f} บาท")

        # กราฟ (อ้างอิงจากรายได้สูงสุด)
        if "รหัสสินค้า" in df.columns and "รวมเงิน" in df.columns:
            st.subheader("🏆 10 อันดับรหัสสินค้าที่ทำรายได้สูงสุด")
            df["รวมเงิน"] = pd.to_numeric(df["รวมเงิน"], errors='coerce').fillna(0)
            chart_data = df.groupby("รหัสสินค้า")["รวมเงิน"].sum().sort_values(ascending=False).head(10)
            st.bar_chart(chart_data)

        st.divider()

        # --- ตารางที่ 1: รวมรหัสสินค้าเดียวกัน ---
        st.subheader("📝 ตารางสรุปสินค้า (รวมตามรหัสสินค้า)")
        # ใช้ชื่อคอลัมน์ตามรูปของคุณ: "รหัสสินค้า", "ชื่อสินค้า", "จำนวนที่สั่งซื้อ", "รวมเงิน"
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df.columns else df.columns[3]
        m_col = "รวมเงิน" if "รวมเงิน" in df.columns else df.columns[4]
        
        df[q_col] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        df[m_col] = pd.to_numeric(df[m_col], errors='coerce').fillna(0)

        summary_product = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"]).agg({
            q_col: "sum",
            m_col: "sum"
        }).reset_index().sort_values(by=q_col, ascending=False)
        
        st.dataframe(summary_product, use_container_width=True)

        # --- ตารางที่ 2: สรุปวันที่สั่งซื้อ ---
        st.subheader("📅 ตารางสรุปยอดการสั่งซื้อตามวันที่")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df.columns else df.columns[0]
        
        summary_date = df.groupby(date_col).size().reset_index(name="จำนวนรายการที่สั่งซื้อ")
        summary_date = summary_date.sort_values(by="จำนวนรายการที่สั่งซื้อ", ascending=False)
        
        st.dataframe(summary_date, use_container_width=True)

elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้า")
    df_stock = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")
    if not df_stock.empty:
        # แสดงตารางเหลือน้อยกว่า 2
        st.subheader("⚠️ สินค้าที่ต้องเติมด่วน (เหลือน้อยกว่า 2)")
        last_col = df_stock.columns[-1] # สมมติช่องสุดท้ายคือจำนวนคงเหลือ
        df_stock[last_col] = pd.to_numeric(df_stock[last_col], errors='coerce').fillna(0)
        low_stock = df_stock[df_stock[last_col] < 2]
        st.dataframe(low_stock, use_container_width=True)
        
        st.divider()
        st.subheader("📋 รายการสต็อกทั้งหมด")
        st.dataframe(df_stock, use_container_width=True)
