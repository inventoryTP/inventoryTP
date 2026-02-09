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

# --- ฟังก์ชันส่งอีเมล (ปรับปรุงรหัสผ่านแล้ว) ---
def send_email_notification(total_sales, top_products_df, low_stock_df):
    try:
        sender_email = "inventory7@gmail.com"
        sender_password = "inventory2569" # แก้ไขแล้ว: ไม่มีจุดตามที่แจ้งครับ
        receiver_email = "inventory7@gmail.com"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "📊 รายงานสรุปยอดขายและสต็อก - ทีพี2025"

        top_products_html = top_products_df.to_html(index=False)
        low_stock_html = low_stock_df.to_html(index=False) if not low_stock_df.empty else "<p>ไม่มีสินค้าเหลือน้อย</p>"
        
        body = f"""
        <html>
        <body>
            <h2>📊 รายงานสรุปจากระบบ ทีพี2025</h2>
            <p>💰 <b>ยอดขายรวมทั้งหมด:</b> {total_sales:,.2f} บาท</p>
            <hr>
            <h3>🏆 10 อันดับสินค้าขายดี</h3>
            {top_products_html}
            <hr>
            <h3>⚠️ รายการสินค้าที่ต้องเติมด่วน (เหลือน้อยกว่า 2)</h3>
            {low_stock_html}
            <br>
            <p>ส่งโดยระบบอัตโนมัติ TP2025 Dashboard</p>
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
        st.sidebar.error(f"ไม่สามารถส่งเมลได้: {e}")
        return False

# --- 2. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="TP2025 Dashboard", layout="wide")
st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

# ดึงข้อมูลเตรียมไว้สำหรับ Sidebar
df_for_mail = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")
df_stock_for_mail = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")

# --- ปุ่มส่งอีเมลใน Sidebar ---
st.sidebar.divider()
st.sidebar.subheader("📧 รายงานด่วน")
if st.sidebar.button("📲 ส่งรายงานสรุปเข้า Email"):
    if not df_for_mail.empty:
        total_val = pd.to_numeric(df_for_mail["รวมเงิน"], errors='coerce').sum()
        q_col_m = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_for_mail.columns else df_for_mail.columns[3]
        top_10 = df_for_mail.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col_m].sum().reset_index().sort_values(by=q_col_m, ascending=False).head(10)
        
        last_col_m = df_stock_for_mail.columns[-1]
        df_stock_for_mail[last_col_m] = pd.to_numeric(df_stock_for_mail[last_col_m], errors='coerce').fillna(0)
        low_s = df_stock_for_mail[df_stock_for_mail[last_col_m] < 2]

        with st.spinner('กำลังส่งอีเมล...'):
            if send_email_notification(total_val, top_10, low_s):
                st.sidebar.success("✅ ส่งเข้าเมลสำเร็จ!")
    else:
        st.sidebar.warning("ไม่พบข้อมูลสำหรับส่ง")

# --- เนื้อหาหน้าเว็บ (เหมือนเดิมทุกประการ) ---
if page == "📊 วิเคราะห์ยอดขาย":
    st.title("📊 ระบบวิเคราะห์ยอดขาย ทีพี2025")
    df = df_for_mail
    df_stock_ref = df_stock_for_mail
    if not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        st.markdown("### 🤖 AI Executive Summary")
        ai_col1, ai_col2 = st.columns(2)
        total_sales_val = pd.to_numeric(df["รวมเงิน"], errors='coerce').sum()
        top_prod = df.groupby("ชื่อสินค้า")["จำนวนที่สั่งซื้อ"].sum().idxmax()
        with ai_col1:
            st.info(f"✨ **สรุปจุดแข็ง:** สินค้าที่ได้รับความนิยมสูงสุดคือ **{top_prod}** มียอดขายรวม **{total_sales_val:,.2f} บาท**")
        with ai_col2:
            if not df_stock_ref.empty:
                df_stock_ref.columns = [str(c).strip() for c in df_stock_ref.columns]
                low_stock_items = len(df_stock_ref[pd.to_numeric(df_stock_ref.iloc[:, -1], errors='coerce') < 2])
                st.warning(f"⚠️ **ข้อควรระวัง:** พบสินค้าสต็อกต่ำกว่าเกณฑ์ **{low_stock_items} รายการ**")
        st.divider()
        col1, col2 = st.columns(2)
        with col1: st.metric("📦 จำนวนรายการทั้งหมด", f"{len(df):,} รายการ")
        with col2:
            df["รวมเงิน"] = pd.to_numeric(df["รวมเงิน"], errors='coerce').fillna(0)
            st.metric("💰 ยอดขายรวมทั้งหมด", f"{df['รวมเงิน'].sum():,.2f} บาท")
        st.subheader("🏆 10 อันดับสินค้าที่ขายดีที่สุด")
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df.columns else df.columns[3]
        df[q_col] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        chart_df = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col].sum().reset_index().sort_values(by=q_col, ascending=False).head(10)
        chart_df["label"] = chart_df["รหัสสินค้า"] + " - " + chart_df["ชื่อสินค้า"]
        st.bar_chart(data=chart_df.set_index("label")[q_col])
        st.subheader("📝 ตารางสรุปสินค้า")
        st.dataframe(chart_df.drop(columns=['label']), use_container_width=True)
        # ... ส่วนวิเคราะห์วันที่และรายเดือนคงเดิม ...
        st.subheader("📅 ตารางสรุปยอดการสั่งซื้อตามวันที่")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df.columns else df.columns[0]
        summary_date = df.groupby(date_col).size().reset_index(name="จำนวนรายการที่สั่งซื้อ")
        summary_date['temp_date'] = pd.to_datetime(summary_date[date_col], dayfirst=True, errors='coerce')
        summary_date = summary_date.sort_values(by='temp_date', ascending=False)
        st.dataframe(summary_date.drop(columns=['temp_date']).reset_index(drop=True), use_container_width=True)
        # --- กราฟรายเดือนและพยากรณ์ AI (เหมือนเดิม) ---
        try:
            summary_date['เลขเดือน'] = summary_date[date_col].apply(lambda x: str(x).split('/')[1] if len(str(x).split('/')) >= 2 else "00")
            monthly_chart = summary_date.groupby('เลขเดือน')["จำนวนรายการที่สั่งซื้อ"].sum().reset_index()
            all_months = pd.DataFrame({"เลขเดือน": [f"{i:02d}" for i in range(1, 13)], "ชื่อเดือน": ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]})
            final_monthly = pd.merge(all_months, monthly_chart, on="เลขเดือน", how="left").fillna(0)
            st.subheader("📈 สรุปจำนวนรายการที่สั่งซื้อรายเดือน")
            st.bar_chart(data=final_monthly, x="ชื่อเดือน", y="จำนวนรายการที่สั่งซื้อ")
        except: pass

elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้า")
    df_stock = df_stock_for_mail
    df_sales = df_for_mail
    if not df_stock.empty:
        df_stock.columns = [str(c).strip() for c in df_stock.columns]
        last_col = df_stock.columns[-1] 
        df_stock[last_col] = pd.to_numeric(df_stock[last_col], errors='coerce').fillna(0)
        st.subheader("🔥 10 อันดับสินค้าขายดีที่ควรสั่งซื้อด่วน")
        if not df_sales.empty:
            q_col_sales = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales.columns else df_sales.columns[3]
            hot_sales = df_sales.groupby("รหัสสินค้า")[q_col_sales].sum().reset_index()
            urgent_df = pd.merge(df_stock, hot_sales, left_on=df_stock.columns[0], right_on="รหัสสินค้า", how="left").fillna(0)
            urgent_list = urgent_df[urgent_df[last_col] < 2].sort_values(by=q_col_sales, ascending=False).head(10)
            if not urgent_list.empty:
                urgent_list["label"] = urgent_list["รหัสสินค้า"] + " (" + urgent_list.iloc[:, 1] + ")"
                st.bar_chart(data=urgent_list.set_index("label")[last_col])
        st.subheader("⚠️ สินค้าที่ต้องเติมด่วน (เหลือน้อยกว่า 2)")
        st.dataframe(df_stock[df_stock[last_col] < 2].reset_index(drop=True), use_container_width=True)
        st.divider()
        st.subheader("📋 รายการสต็อกทั้งหมด")
        st.dataframe(df_stock, use_container_width=True)
