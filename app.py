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
        st.error(f"Error ดึงข้อมูล: {e}")
        return pd.DataFrame()

# --- 2. ฟังก์ชันส่งอีเมล ---
def send_email_report(total_sales, top_10_html, urgent_stock_html, summary_text):
    try:
        sender_email = "inventory7@gmail.com"
        # หากใช้รหัสผ่านปกติไม่ได้ ให้ใช้ App Password 16 หลักแทน
        sender_password = "inventory2569." 
        receiver_email = "inventory7@gmail.com"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "📊 รายงานสรุปยอดขายและสต็อกด่วน - ทีพี2025"

        body = f"""
        <html>
            <body>
                <h2>📊 รายงานสรุปจากระบบ ทีพี2025</h2>
                <p><b>💰 ยอดขายรวมทั้งหมด:</b> {total_sales:,.2f} บาท</p>
                <hr>
                <h3>🏆 10 อันดับสินค้าที่ขายดีที่สุด</h3>
                {top_10_html}
                <hr>
                <h3>⚠️ สินค้าขายดีที่ควรสั่งซื้อด่วน (สต็อกต่ำ)</h3>
                {urgent_stock_html}
                <hr>
                <h3>🤖 บทสรุปจาก AI</h3>
                <p>{summary_text}</p>
                <br>
                <p><i>ส่งโดยระบบอัตโนมัติ TP2025 Dashboard</i></p>
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

# --- 3. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="TP2025 Dashboard", layout="wide")
st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

if page == "📊 วิเคราะห์ยอดขาย":
    st.title("📊 ระบบวิเคราะห์ยอดขาย ทีพี2025")
    df_sales = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")
    df_stock_ref = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")

    if not df_sales.empty:
        df_sales.columns = [str(c).strip() for c in df_sales.columns]
        
        # จัดการข้อมูลตัวเลข
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales.columns else df_sales.columns[3]
        m_col = "รวมเงิน" if "รวมเงิน" in df_sales.columns else df_sales.columns[4]
        df_sales[q_col] = pd.to_numeric(df_sales[q_col], errors='coerce').fillna(0)
        df_sales[m_col] = pd.to_numeric(df_sales[m_col], errors='coerce').fillna(0)
        
        total_sales_val = df_sales[m_col].sum()

        # 10 อันดับสินค้าขายดี
        top_10_df = df_sales.groupby(["รหัสสินค้า", "ชื่อสินค้า"]).agg({q_col: "sum", m_col: "sum"}).reset_index().sort_values(by=q_col, ascending=False).head(10)

        # เตรียมข้อมูลสต็อกต่ำสำหรับปุ่มส่งเมล
        urgent_html = "ไม่มีรายการสต็อกต่ำ"
        if not df_stock_ref.empty:
            df_stock_ref.columns = [str(c).strip() for c in df_stock_ref.columns]
            last_col_ref = df_stock_ref.columns[-1]
            df_stock_ref[last_col_ref] = pd.to_numeric(df_stock_ref[last_col_ref], errors='coerce').fillna(0)
            urgent_ref_list = pd.merge(df_stock_ref, top_10_df, left_on=df_stock_ref.columns[0], right_on="รหัสสินค้า", how="inner")
            urgent_ref_list = urgent_ref_list[urgent_ref_list[last_col_ref] < 2]
            if not urgent_ref_list.empty:
                urgent_html = urgent_ref_list[[urgent_ref_list.columns[0], urgent_ref_list.columns[1], last_col_ref]].to_html(index=False)

        # --- ส่วนปุ่มส่งอีเมล ---
        st.sidebar.divider()
        st.sidebar.subheader("📧 การส่งรายงาน")
        if st.sidebar.button("ส่งรายงานสรุปเข้า Email"):
            with st.spinner('กำลังส่งอีเมล...'):
                top_10_html = top_10_df.to_html(index=False)
                summary_ai = f"สินค้าที่ขายดีที่สุดคือ {top_10_df.iloc[0]['ชื่อสินค้า']} มียอดขายรวมทั้งหมด {total_sales_val:,.2f} บาท"
                if send_email_report(total_sales_val, top_10_html, urgent_html, summary_ai):
                    st.sidebar.success("✅ ส่งรายงานสำเร็จ!")

        # --- 🤖 ส่วนสรุปข้อมูล AI ---
        st.markdown("### 🤖 AI Executive Summary")
        ai_col1, ai_col2 = st.columns(2)
        top_prod_name = df_sales.groupby("ชื่อสินค้า")[q_col].sum().idxmax()
        
        with ai_col1:
            st.info(f"✨ **สรุปจุดแข็ง:** สินค้าที่ได้รับความนิยมสูงสุดคือ **{top_prod_name}**")
        with ai_col2:
            if not df_stock_ref.empty:
                low_stock_count = len(df_stock_ref[df_stock_ref.iloc[:, -1] < 2])
                st.warning(f"⚠️ **ข้อควรระวัง:** พบสินค้าสต็อกต่ำกว่าเกณฑ์ **{low_stock_count} รายการ**")

        st.divider()
        col1, col2 = st.columns(2)
        col1.metric("📦 จำนวนรายการออเดอร์", f"{len(df_sales):,} รายการ")
        col2.metric("💰 ยอดขายรวมทั้งหมด", f"{total_sales_val:,.2f} บาท")

        st.subheader("🏆 10 อันดับสินค้าที่ขายดีที่สุด")
        chart_df = top_10_df.copy()
        chart_df["label"] = chart_df["รหัสสินค้า"] + " - " + chart_df["ชื่อสินค้า"]
        st.bar_chart(data=chart_df.set_index("label")[q_col])
        st.dataframe(top_10_df, use_container_width=True)

        # ส่วนสรุปรายวันและรายเดือน (โค้ดเดิมที่ปรับปรุงความเสถียร)
        st.subheader("📅 สรุปยอดตามวันที่")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df_sales.columns else df_sales.columns[0]
        summary_date = df_sales.groupby(date_col).size().reset_index(name="จำนวนออเดอร์")
        st.dataframe(summary_date, use_container_width=True)

elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้า")
    df_stock = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")
    df_sales_for_stock = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย") # ดึงข้อมูลมาใหม่เพื่อแก้ NameError

    if not df_stock.empty:
        df_stock.columns = [str(c).strip() for c in df_stock.columns]
        last_col = df_stock.columns[-1] 
        df_stock[last_col] = pd.to_numeric(df_stock[last_col], errors='coerce').fillna(0)
        
        st.subheader("🔥 สินค้าขายดีที่ควรเติมสต็อกด่วน")
        if not df_sales_for_stock.empty:
            df_sales_for_stock.columns = [str(c).strip() for c in df_sales_for_stock.columns]
            q_col_s = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales_for_stock.columns else df_sales_for_stock.columns[3]
            hot_sales = df_sales_for_stock.groupby(df_sales_for_stock.columns[1])[q_col_s].sum().reset_index()
            
            urgent_df = pd.merge(df_stock, hot_sales, left_on=df_stock.columns[0], right_on=hot_sales.columns[0], how="left").fillna(0)
            low_stock_urgent = urgent_df[urgent_df[last_col] < 2].sort_values(by=q_col_s, ascending=False).head(10)
            
            if not low_stock_urgent.empty:
                low_stock_urgent["label"] = low_stock_urgent.iloc[:, 0].astype(str) + " (" + low_stock_urgent.iloc[:, 1] + ")"
                st.bar_chart(data=low_stock_urgent.set_index("label")[last_col])
        
        st.subheader("⚠️ รายการสินค้าที่เหลือน้อยกว่า 2")
        st.dataframe(df_stock[df_stock[last_col] < 2], use_container_width=True)
        st.divider()
        st.subheader("📋 สต็อกทั้งหมด")
        st.dataframe(df_stock, use_container_width=True)
