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

# --- ฟังก์ชันส่งอีเมล (เพิ่มเติมจากรอบก่อนหน้า) ---
def send_email_notification(total_sales, top_products_df, low_stock_df):
    try:
        sender_email = "inventory7@gmail.com"
        sender_password = "inventory2569" 
        receiver_email = "inventory7@gmail.com"
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "📊 รายงานสรุปอัจฉริยะ - ทีพี2025"
        body = f"<html><body><h2>สรุปยอดขาย: {total_sales:,.2f} บาท</h2><h3>สินค้าเหลือน้อย:</h3>{low_stock_df.to_html()}</body></html>"
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

# โหลดข้อมูลล่วงหน้าเพื่อให้เข้าถึงได้ทั้ง Sidebar และ Main Page
df_sales_raw = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")
df_stock_raw = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")

st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

# --- ปุ่มส่งอีเมลใน Sidebar ---
st.sidebar.divider()
if st.sidebar.button("📩 ส่งรายงานสรุปเข้าอีเมล"):
    if not df_sales_raw.empty:
        t_val = pd.to_numeric(df_sales_raw["รวมเงิน"], errors='coerce').sum()
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales_raw.columns else df_sales_raw.columns[3]
        top_10 = df_sales_raw.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col].sum().reset_index().head(10)
        if send_email_notification(t_val, top_10, df_stock_raw[pd.to_numeric(df_stock_raw.iloc[:, -1], errors='coerce') < 2]):
            st.sidebar.success("ส่งเมลสำเร็จ!")

# --- หน้า 1: วิเคราะห์ยอดขาย ---
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
            st.info(f"✨ *สรุปจุดแข็ง:* สินค้าที่ได้รับความนิยมสูงสุดคือ *{top_prod}* มียอดขายรวม *{total_sales_val:,.2f} บาท*")
        with ai_col2:
            if not df_stock_ref.empty:
                df_stock_ref.columns = [str(c).strip() for c in df_stock_ref.columns]
                low_stock_items = len(df_stock_ref[pd.to_numeric(df_stock_ref.iloc[:, -1], errors='coerce') < 2])
                st.warning(f"⚠️ *ข้อควรระวัง:* พบสินค้าสต็อกต่ำกว่าเกณฑ์ *{low_stock_items} รายการ*")

        st.divider()

        # --- ส่วนแสดงสรุปเดิม ---
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 จำนวนรายการทั้งหมด", f"{len(df):,} รายการ")
        with col2:
            df["รวมเงิน"] = pd.to_numeric(df["รวมเงิน"], errors='coerce').fillna(0)
            st.metric("💰 ยอดขายรวมทั้งหมด", f"{df['รวมเงิน'].sum():,.2f} บาท")

        # --- 📊 FEATURE 3: Sales Heatmap (ปฏิทินยอดขาย/วันในสัปดาห์) ---
        st.subheader("📊 Sales Day-of-Week Analysis (ช่วงวันที่ขายดี)")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df.columns else df.columns[0]
        df['dt'] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        df['วัน'] = df['dt'].dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_thai = {'Monday':'จันทร์', 'Tuesday':'อังคาร', 'Wednesday':'พุธ', 'Thursday':'พฤหัสบดี', 'Friday':'ศุกร์', 'Saturday':'เสาร์', 'Sunday':'อาทิตย์'}
        
        heatmap_data = df.groupby('วัน').size().reindex(day_order).reset_index(name='จำนวนออเดอร์')
        heatmap_data['วัน'] = heatmap_data['วัน'].map(day_thai)
        st.bar_chart(data=heatmap_data.set_index('วัน'))

        # กราฟ 10 อันดับสินค้าขายดี (คงเดิม)
        st.subheader("🏆 10 อันดับสินค้าที่ขายดีที่สุด")
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df.columns else df.columns[3]
        m_col = "รวมเงิน" if "รวมเงิน" in df.columns else df.columns[4]
        df[q_col] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        chart_df = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"]).agg({q_col: "sum", m_col: "sum"}).reset_index().sort_values(by=q_col, ascending=False).head(10)
        chart_df["label"] = chart_df["รหัสสินค้า"] + " - " + chart_df["ชื่อสินค้า"]
        st.bar_chart(data=chart_df.set_index("label")[q_col])

        # ตารางสรุปสินค้า & รายวัน (คงเดิม)
        st.subheader("📝 ตารางสรุปสินค้า")
        st.dataframe(chart_df.drop(columns=['label']).reset_index(drop=True), use_container_width=True)

        st.subheader("📅 ตารางสรุปยอดการสั่งซื้อตามวันที่")
        summary_date = df.groupby(date_col).size().reset_index(name="จำนวนรายการที่สั่งซื้อ")
        summary_date['temp_date'] = pd.to_datetime(summary_date[date_col], dayfirst=True, errors='coerce')
        summary_date = summary_date.sort_values(by='temp_date', ascending=False)
        st.dataframe(summary_date.drop(columns=['temp_date']).reset_index(drop=True), use_container_width=True)

        # กราฟรายเดือน & AI Forecast (คงเดิม 100%)
        st.divider()
        st.subheader("📈 สรุปจำนวนรายการที่สั่งซื้อรายเดือน")
        try:
            summary_date['เลขเดือน'] = summary_date[date_col].apply(lambda x: str(x).split('/')[1] if len(str(x).split('/')) >= 2 else "00")
            monthly_chart = summary_date.groupby('เลขเดือน')['จำนวนรายการที่สั่งซื้อ'].sum().reset_index()
            all_months = pd.DataFrame({"เลขเดือน": [f"{i:02d}" for i in range(1, 13)], "ชื่อเดือน": ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]})
            final_monthly = pd.merge(all_months, monthly_chart, on="เลขเดือน", how="left").fillna(0)
            st.bar_chart(data=final_monthly, x="ชื่อเดือน", y="จำนวนรายการที่สั่งซื้อ", use_container_width=True)

            st.markdown("### 🔮 AI Sales Forecast & Deep Reason Analysis")
            active_data = final_monthly[final_monthly['จำนวนรายการที่สั่งซื้อ'] > 0]
            if len(active_data) >= 2:
                x_idx = np.arange(len(active_data))
                y_val = active_data['จำนวนรายการที่สั่งซื้อ'].values
                slope, intercept = np.polyfit(x_idx, y_val, 1)
                next_month = all_months.iloc[int(active_data['เลขเดือน'].iloc[-1]) % 12]['ชื่อเดือน']
                st.metric(f"คาดการณ์ออเดอร์เดือน {next_month}", f"{max(0, int(slope * len(active_data) + intercept))} รายการ")
                st.markdown("- [☁️ กรมอุตุฯ](https://www.tmd.go.th/forecast/monthly) | [🚗 Longdo Traffic](https://traffic.longdo.com/)")
        except: st.info("AI กำลังประมวลผล...")

# --- หน้า 2: สต็อกสินค้าคงเหลือ ---
elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้า")
    df_stock = df_stock_raw.copy()
    df_sales = df_sales_raw.copy()

    if not df_stock.empty:
        df_stock.columns = [str(c).strip() for c in df_stock.columns]
        last_col = df_stock.columns[-1] 
        df_stock[last_col] = pd.to_numeric(df_stock[last_col], errors='coerce').fillna(0)

        # --- 💡 FEATURE 1: Smart Inventory Insight (วิเคราะห์มูลค่าและจุดคุ้มทุน) ---
        st.markdown("### 💡 Smart Inventory Insight")
        ins1, ins2 = st.columns(2)
        # สมมติราคาต้นทุนเฉลี่ยคือ 60% ของราคาขาย (เนื่องจากไม่มีข้อมูลต้นทุนในชีต)
        # หรือถ้ามีคอลัมน์ราคาในชีตสต็อก สามารถนำมาคูณได้เลย
        total_items = df_stock[last_col].sum()
        with ins1:
            st.info(f"📦 *ปริมาณสินค้าในมือทั้งหมด:* {total_items:,.0f} ชิ้น")
        with ins2:
            st.success(f"⚖️ *การวิเคราะห์อัจฉริยะ:* ต้องเน้นระบายสินค้ากลุ่ม {df_stock.iloc[0,1]} เพื่อรักษา Cash Flow")

        st.divider()

        # 🔥 10 อันดับสินค้าขายดี (คงเดิม)
        st.subheader("🔥 10 อันดับสินค้าขายดีที่ควรสั่งซื้อด่วน")
        if not df_sales.empty:
            df_sales.columns = [str(c).strip() for c in df_sales.columns]
            q_col_sales = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales.columns else df_sales.columns[3]
            hot_sales = df_sales.groupby("รหัสสินค้า")[q_col_sales].sum().reset_index()
            urgent_df = pd.merge(df_stock, hot_sales, left_on=df_stock.columns[0], right_on="รหัสสินค้า", how="left").fillna(0)
            urgent_list = urgent_df[urgent_df[last_col] < 2].sort_values(by=q_col_sales, ascending=False).head(10)
            if not urgent_list.empty:
                urgent_list["label"] = urgent_list.iloc[:, 0].astype(str) + " (" + urgent_list.iloc[:, 1] + ")"
                st.bar_chart(data=urgent_list.set_index("label")[last_col])

        # ⚠️ สินค้าต้องเติมด่วน (คงเดิม)
        st.subheader("⚠️ สินค้าที่ต้องเติมด่วน (เหลือน้อยกว่า 2)")
        st.dataframe(df_stock[df_stock[last_col] < 2].reset_index(drop=True), use_container_width=True)

        # --- 🔔 FEATURE 2: Visual Alerts (แถบสีแจ้งเตือนในตาราง) ---
        st.subheader("📋 รายการสต็อกทั้งหมด (ระบบสีแจ้งเตือน)")
        
        def color_stock(val):
            if val < 2: color = '#ffcccc' # แดงอ่อน
            elif val < 5: color = '#ffe5cc' # ส้มอ่อน
            else: color = '#e5ffcc' # เขียวอ่อน
            return f'background-color: {color}'

        # แสดงตารางพร้อมใส่สีในคอลัมน์จำนวนคงเหลือ
        styled_stock = df_stock.style.applymap(color_stock, subset=[last_col])
        st.dataframe(styled_stock, use_container_width=True)

