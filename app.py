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
        df.columns = [str(c).strip() for c in df.columns]

        # ส่วนแสดงสรุปด้านบน
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 จำนวนรายการทั้งหมด", f"{len(df):,} รายการ")
        with col2:
            if "รวมเงิน" in df.columns:
                df["รวมเงิน"] = pd.to_numeric(df["รวมเงิน"], errors='coerce').fillna(0)
                st.metric("💰 ยอดขายรวมทั้งหมด", f"{df['รวมเงิน'].sum():,.2f} บาท")

        # --- ตารางที่ 1: รวมรหัสสินค้าเดียวกัน ---
        st.subheader("📝 ตารางสรุปสินค้า (รวมตามรหัสสินค้า)")
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df.columns else df.columns[3]
        m_col = "รวมเงิน" if "รวมเงิน" in df.columns else df.columns[4]
        
        df[q_col] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)

        # รวมกลุ่มข้อมูล
        summary_product = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"]).agg({
            q_col: "sum",
            m_col: "sum"
        }).reset_index().sort_values(by=q_col, ascending=False)
        
        # --- แก้ไขจุดนี้: รีเซ็ตลำดับให้เริ่มจาก 1 ---
        summary_product = summary_product.reset_index(drop=True)
        summary_product.index = summary_product.index + 1
        
        st.dataframe(summary_product, use_container_width=True)

        # --- ตารางที่ 2: สรุปวันที่สั่งซื้อ ---
        st.subheader("📅 ตารางสรุปยอดการสั่งซื้อตามวันที่")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df.columns else df.columns[0]
        
        summary_date = df.groupby(date_col).size().reset_index(name="จำนวนรายการที่สั่งซื้อ")
        summary_date = summary_date.sort_values(by="จำนวนรายการที่สั่งซื้อ", ascending=False)
        
        # รีเซ็ตลำดับให้เริ่มจาก 1 เช่นกัน
        summary_date = summary_date.reset_index(drop=True)
        summary_date.index = summary_date.index + 1
        
        st.dataframe(summary_date, use_container_width=True)

elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้า")
    df_stock = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")
    if not df_stock.empty:
        # แสดงตารางเหลือน้อยกว่า 2
        st.subheader("⚠️ สินค้าที่ต้องเติมด่วน (เหลือน้อยกว่า 2)")
        df_stock.columns = [str(c).strip() for c in df_stock.columns]
        # ค้นหาคอลัมน์คงเหลือ (มักเป็นคอลัมน์สุดท้าย)
        last_col = df_stock.columns[-1] 
        df_stock[last_col] = pd.to_numeric(df_stock[last_col], errors='coerce').fillna(0)
        low_stock = df_stock[df_stock[last_col] < 2].reset_index(drop=True)
        low_stock.index = low_stock.index + 1
        st.dataframe(low_stock, use_container_width=True)
        
        st.divider()
        st.subheader("📋 รายการสต็อกทั้งหมด")
        all_stock = df_stock.reset_index(drop=True)
        all_stock.index = all_stock.index + 1
        st.dataframe(all_stock, use_container_width=True)
