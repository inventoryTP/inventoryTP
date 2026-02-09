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
        st.error(f"Data Error: {e}")
        return pd.DataFrame()

# --- 2. ฟังก์ชันส่งอีเมล (รหัส inventory2569) ---
def send_email_notification(total_sales, top_products_df, low_stock_df):
    try:
        sender_email = "inventory7@gmail.com"
        sender_password = "inventory2569" 
        receiver_email = "inventory7@gmail.com"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "Report Summary - TP2025"

        top_html = top_products_df.to_html(index=False)
        low_html = low_stock_df.to_html(index=False) if not low_stock_df.empty else "<p>No low stock items</p>"
        
        body = f"""
        <html>
        <body>
            <h2>Report Summary - TP2025</h2>
            <p>Total Sales: {total_sales:,.2f} THB</p>
            <hr>
            <h3>Top 10 Best Sellers</h3>
            {top_html}
            <hr>
            <h3>Low Stock Warning (< 2)</h3>
            {low_html}
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
        st.sidebar.error(f"Email Error: {e}")
        return False

# --- 3. ตั้งค่าหน้าเว็บและการโหลดข้อมูล ---
st.set_page_config(page_title="TP2025 Dashboard", layout="wide")

# โหลดข้อมูลเตรียมไว้ (Global)
df_sales_all = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")
df_stock_all = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")

st.sidebar.title("Main Menu")
page = st.sidebar.radio("Go to:", ["Sales Analysis", "Inventory Stock"])

# --- ปุ่มส่งอีเมลใน Sidebar ---
st.sidebar.divider()
if st.sidebar.button("Send Email Report"):
    if not df_sales_all.empty:
        t_val = pd.to_numeric(df_sales_all["รวมเงิน"], errors='coerce').sum()
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales_raw.columns else df_sales_raw.columns[3]
        t_10 = df_sales_all.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col].sum().reset_index().sort_values(by=q_col, ascending=False).head(10)
        
        l_stock = pd.DataFrame()
        if not df_stock_all.empty:
            last_c = df_stock_all.columns[-1]
            tmp = df_stock_all.copy()
            tmp[last_c] = pd.to_numeric(tmp[last_c], errors='coerce').fillna(0)
            l_stock = tmp[tmp[last_c] < 2]

        if send_email_notification(t_val, t_10, l_stock):
            st.sidebar.success("Email Sent!")
    else:
        st.sidebar.warning("No data to send")

# --- หน้าที่ 1: วิเคราะห์ยอดขาย ---
if page == "Sales Analysis":
    st.title("Sales Analysis System TP2025")
    df = df_sales_all.copy()
    
    if not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        
        # AI Summary
        st.markdown("### AI Executive Summary")
        total_sales = pd.to_numeric(df["รวมเงิน"], errors='coerce').sum()
        st.info(f"Total Sales: {total_sales:,.2f} THB")

        st.divider()
        # กราฟ 10 อันดับ
        st.subheader("Top 10 Best Sellers")
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df.columns else df.columns[3]
        df[q_col] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        chart_data = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col].sum().reset_index().sort_values(by=q_col, ascending=False).head(10)
        chart_data["label"] = chart_data["รหัสสินค้า"].astype(str) + " - " + chart_data["ชื่อสินค้า"]
        st.bar_chart(data=chart_data.set_index("label")[q_col])

        # ตารางรายวัน
        st.subheader("Daily Sales Summary")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df.columns else df.columns[0]
        daily = df.groupby(date_col).size().reset_index(name="Orders")
        st.dataframe(daily, use_container_width=True)

        # AI Forecast & Links
        st.divider()
        st.markdown("### AI Sales Forecast & Analysis")
        st.write("Checking external factors...")
        st.markdown("- [Weather Forecast (TMD)](https://www.tmd.go.th/forecast/monthly)")
        st.markdown("- [Traffic Status (Longdo)](https://traffic.longdo.com/)")

# --- หน้าที่ 2: สต็อกสินค้าคงเหลือ ---
elif page == "Inventory Stock":
    st.title("Inventory Management System")
    df_s = df_stock_all.copy()
    df_v = df_sales_all.copy()

    if not df_s.empty:
        df_s.columns = [str(c).strip() for c in df_s.columns]
        last_col = df_s.columns[-1]
        df_s[last_col] = pd.to_numeric(df_s[last_col], errors='coerce').fillna(0)
        
        st.subheader("Items Needing Urgent Restock (< 2)")
        low_items = df_s[df_s[last_col] < 2].reset_index(drop=True)
        st.dataframe(low_items, use_container_width=True)
        
        st.divider()
        st.subheader("All Stock Items")
        st.dataframe(df_s, use_container_width=True)
    else:
        st.warning("No stock data found in Google Sheets")
