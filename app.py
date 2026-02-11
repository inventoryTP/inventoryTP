import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# --- 2. ฟังก์ชันส่งอีเมล (ปรับปรุงให้ส่งไปที่ inventorytp7@gmail.com) ---
def send_email_notification(total_sales, top_products_df, low_stock_df):
    try:
        sender_email = "inventory7@gmail.com"
        sender_password = "inventory2569" 
        receiver_email = "inventorytp7@gmail.com" # อีเมลเป้าหมาย

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "📊 รายงานสรุปยอดขายและสต็อก - ทีพี2025"

        # สร้างตาราง HTML สำหรับส่งในเมล
        body = f"""
        <html>
        <body>
            <h2 style="color: #2E86C1;">📊 สรุปรายงานระบบ ทีพี2025</h2>
            <p style="font-size: 16px;">💰 <b>ยอดขายรวมทั้งหมด:</b> {total_sales:,.2f} บาท</p>
            <hr>
            <h3>🏆 10 อันดับสินค้าขายดี</h3>
            {top_products_df.to_html(index=False)}
            <hr>
            <h3 style="color: #CB4335;">⚠️ สินค้าที่ต้องเติมด่วน (เหลือน้อยกว่า 2)</h3>
            {low_stock_df.to_html(index=False) if not low_stock_df.empty else "<p>ไม่มีสินค้าเหลือน้อย</p>"}
            <br>
            <p style="color: grey;">ส่งโดยระบบอัตโนมัติ TP2025 Dashboard</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        return False

# --- 3. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="TP2025 Dashboard PRO", layout="wide")

# โหลดข้อมูลล่วงหน้า (เพื่อให้ปุ่มส่งเมลและหน้าเว็บใช้ข้อมูลชุดเดียวกัน)
df_sales_raw = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")
df_stock_raw = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")

st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

# --- ปุ่มส่งอีเมลใน Sidebar (เพิ่มการทำงาน) ---
st.sidebar.divider()
if st.sidebar.button("📩 ส่งรายงานสรุปเข้าอีเมล"):
    if not df_sales_raw.empty:
        # ดึงข้อมูลสรุปยอดขาย
        t_val = pd.to_numeric(df_sales_raw["รวมเงิน"], errors='coerce').sum()
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales_raw.columns else df_sales_raw.columns[3]
        top_10 = df_sales_raw.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col].sum().reset_index().sort_values(by=q_col, ascending=False).head(10)
        
        # ดึงข้อมูลสต็อกต่ำ
        last_col = df_stock_raw.columns[-1]
        low_stock_data = df_stock_raw[pd.to_numeric(df_stock_raw[last_col], errors='coerce') < 2].copy()
        
        with st.spinner('กำลังส่งรายงาน...'):
            if send_email_notification(t_val, top_10, low_stock_data):
                st.sidebar.success(f"ส่งรายงานสำเร็จ! ไปยัง { 'inventorytp7@gmail.com' }")
    else:
        st.sidebar.warning("ไม่พบข้อมูลสำหรับส่ง")

# --- ส่วนแสดงผลหน้าเว็บ (เหมือนเดิม 100%) ---

if page == "📊 วิเคราะห์ยอดขาย":
    st.title("📊 ระบบวิเคราะห์ยอดขาย ทีพี2025")
    df = df_sales_raw.copy()
    df_stock_ref = df_stock_raw.copy()

    if not df.empty:
        df.columns = [str(c).strip() for c in df.columns]

        # --- 🤖 ส่วนสรุปข้อมูลเดิมด้วย AI ---
        st.markdown("### 🤖 AI Executive Summary")
        ai_col1, ai_col2 = st.columns(2)
        total_sales_val = pd.to_numeric(df["รวมเงิน"], errors='coerce').sum()
        top_prod = df.groupby("ชื่อสินค้า")["จำนวนที่สั่งซื้อ"].sum().idxmax()
        
        with ai_col1:
            st.info(f"✨ *สรุปจุดแข็ง:* สินค้าที่ได้รับความนิยมสูงสุดคือ {top_prod} มียอดขายรวม {total_sales_val:,.2f} บาท")
        with ai_col2:
            if not df_stock_ref.empty:
                df_stock_ref.columns = [str(c).strip() for c in df_stock_ref.columns]
                low_stock_items = len(df_stock_ref[pd.to_numeric(df_stock_ref.iloc[:, -1], errors='coerce') < 2])
                st.warning(f"⚠️ *ข้อควรระวัง:* พบสินค้าสต็อกต่ำกว่าเกณฑ์ {low_stock_items} รายการ")

        st.divider()

        # ส่วน Metric
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 จำนวนรายการทั้งหมด", f"{len(df):,} รายการ")
        with col2:
            df["รวมเงิน"] = pd.to_numeric(df["รวมเงิน"], errors='coerce').fillna(0)
            st.metric("💰 ยอดขายรวมทั้งหมด", f"{df['รวมเงิน'].sum():,.2f} บาท")

        # กราฟเดิมและตารางเดิมทั้งหมด... (ใส่โค้ดส่วนแสดงผลเดิมของคุณต่อที่นี่ได้เลย)
        st.subheader("🏆 10 อันดับสินค้าที่ขายดีที่สุด")
        # ... (โค้ดกราฟและตารางเดิมของคุณ)

elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้า")
    # ... (โค้ดหน้าสต็อกเดิมของคุณ 100%)
