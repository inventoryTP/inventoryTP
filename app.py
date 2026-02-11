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

# --- ฟังก์ชันส่งอีเมล ---
def send_email_notification(total_sales, top_products_df, low_stock_df):
    try:
        sender_email = "inventory7@gmail.com"
        sender_password = "inventory2569" 
        receiver_email = "inventory7@gmail.com"
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "Report Summary - TP2025"
        body = f"<html><body><h2>Total Sales: {total_sales:,.2f} THB</h2><h3>Low Stock Items:</h3>{low_stock_df.to_html()}</body></html>"
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True
    except: return False

# --- 2. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="TP2025 Dashboard PRO", layout="wide")

df_sales_raw = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")
df_stock_raw = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")

st.sidebar.title("Main Menu")
page = st.sidebar.radio("Go to:", ["Sales Analysis", "Inventory Stock"])

# --- ปุ่มส่งอีเมลใน Sidebar ---
st.sidebar.divider()
if st.sidebar.button("Send Email Report"):
    if not df_sales_raw.empty:
        t_val = pd.to_numeric(df_sales_raw["รวมเงิน"], errors='coerce').sum()
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales_raw.columns else df_sales_raw.columns[3]
        top_10 = df_sales_raw.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col].sum().reset_index().head(10)
        if send_email_notification(t_val, top_10, df_stock_raw[pd.to_numeric(df_stock_raw.iloc[:, -1], errors='coerce') < 2]):
            st.sidebar.success("Success!")

# --- หน้า 1: วิเคราะห์ยอดขาย ---
if page == "Sales Analysis":
    st.title("Sales Analysis TP2025")
    df = df_sales_raw.copy()
    df_stock_ref = df_stock_raw.copy()

    if not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        st.markdown("### AI Executive Summary")
        ai_col1, ai_col2 = st.columns(2)
        total_sales_val = pd.to_numeric(df["รวมเงิน"], errors='coerce').sum()
        top_prod = df.groupby("ชื่อสินค้า")["จำนวนที่สั่งซื้อ"].sum().idxmax()
        
        with ai_col1:
            st.info(f"Top Product: {top_prod} | Total Sales: {total_sales_val:,.2f} THB")
        with ai_col2:
            if not df_stock_ref.empty:
                low_stock_count = len(df_stock_ref[pd.to_numeric(df_stock_ref.iloc[:, -1], errors='coerce') < 2])
                st.warning(f"Low Stock Items: {low_stock_count} items")

        st.divider()
        col1, col2 = st.columns(2)
        with col1: st.metric("Total Transactions", f"{len(df):,} items")
        with col2: st.metric("Total Sales Amount", f"{total_sales_val:,.2f} THB")

        # Sales Heatmap
        st.subheader("Sales by Day of Week")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df.columns else df.columns[0]
        df['dt'] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        df['Day'] = df['dt'].dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = df.groupby('Day').size().reindex(day_order).reset_index(name='Orders')
        st.bar_chart(data=heatmap_data.set_index('Day'))

        st.subheader("Top 10 Best Sellers")
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df.columns else df.columns[3]
        df[q_col] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        chart_df = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col].sum().reset_index().sort_values(by=q_col, ascending=False).head(10)
        chart_df["label"] = chart_df["รหัสสินค้า"].astype(str) + " - " + chart_df["ชื่อสินค้า"]
        st.bar_chart(data=chart_df.set_index("label")[q_col])

        st.subheader("Daily Sales Summary")
        summary_date = df.groupby(date_col).size().reset_index(name="Orders")
        st.dataframe(summary_date, use_container_width=True)

        st.divider()
        st.subheader("Monthly Sales & AI Forecast")
        try:
            summary_date['Month'] = summary_date[date_col].apply(lambda x: str(x).split('/')[1] if len(str(x).split('/')) >= 2 else "00")
            monthly = summary_date.groupby('Month')['Orders'].sum().reset_index()
            st.bar_chart(data=monthly, x="Month", y="Orders")
            st.markdown("- [Weather Forecast](https://www.tmd.go.th/forecast/monthly) | [Traffic Status](https://traffic.longdo.com/)")
        except: st.info("Processing AI Data...")

# --- หน้า 2: สต็อกสินค้าคงเหลือ ---
elif page == "Inventory Stock":
    st.title("Inventory Stock System")
    df_stock = df_stock_raw.copy()
    df_sales = df_sales_raw.copy()

    if not df_stock.empty:
        df_stock.columns = [str(c).strip() for c in df_stock.columns]
        last_col = df_stock.columns[-1] 
        
        # --- จุดที่ปรับแก้: แปลงเป็นตัวเลขจำนวนเต็ม (Integer) เพื่อให้ไม่มีทศนิยม ---
        df_stock[last_col] = pd.to_numeric(df_stock[last_col], errors='coerce').fillna(0).astype(int)

        st.markdown("### Smart Inventory Insight")
        st.info(f"Total Stock Volume: {df_stock[last_col].sum():,.0f} units")

        st.divider()
        st.subheader("Urgent Restock (Lower than 2)")
        low_stock_df = df_stock[df_stock[last_col] < 2].reset_index(drop=True)
        st.dataframe(low_items := low_stock_df, use_container_width=True)

        # --- 🔔 ระบบสีแจ้งเตือน + ตัวเลขหลักเดียว ---
        st.subheader("All Stock (Color Coded)")
        def color_stock(val):
            if val < 2: color = '#ffcccc'
            elif val < 5: color = '#ffe5cc'
            else: color = '#e5ffcc'
            return f'background-color: {color}'

        # แสดงผลโดยตัดทศนิยมทิ้งทั้งหมด
        styled_stock = df_stock.style.applymap(color_stock, subset=[last_col])
        st.dataframe(styled_stock, use_container_width=True)
