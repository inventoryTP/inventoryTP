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

# --- 2. ฟังก์ชันส่งอีเมล ---
def send_email_notification(total_sales, top_products_df, low_stock_df):
    try:
        sender_email = "inventory7@gmail.com"
        sender_password = "inventory2569" 
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

# --- 3. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="TP2025 Dashboard", layout="wide")

# โหลดข้อมูลหลัก (ดึงครั้งเดียวใช้ได้ทั้งแอป)
df_sales_raw = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")
df_stock_raw = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")

st.sidebar.title("🚀 เมนูหลัก")
page = st.sidebar.radio("เลือกหน้าที่จะดู:", ["📊 วิเคราะห์ยอดขาย", "📦 สต็อกสินค้าคงเหลือ"])

# --- ปุ่มส่งอีเมลใน Sidebar ---
st.sidebar.divider()
st.sidebar.subheader("📧 รายงานด่วน")
if st.sidebar.button("📲 ส่งรายงานสรุปเข้า Email"):
    if not df_sales_raw.empty:
        total_val_mail = pd.to_numeric(df_sales_raw["รวมเงิน"], errors='coerce').sum()
        q_col_mail = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales_raw.columns else df_sales_raw.columns[3]
        top_10_mail = df_sales_raw.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col_mail].sum().reset_index().sort_values(by=q_col_mail, ascending=False).head(10)
        
        low_stock_mail = pd.DataFrame()
        if not df_stock_raw.empty:
            last_col_idx = df_stock_raw.columns[-1]
            temp_stock = df_stock_raw.copy()
            temp_stock[last_col_idx] = pd.to_numeric(temp_stock[last_col_idx], errors='coerce').fillna(0)
            low_stock_mail = temp_stock[temp_stock[last_col_idx] < 2]

        with st.spinner('กำลังส่งอีเมล...'):
            if send_email_notification(total_val_mail, top_10_mail, low_stock_mail):
                st.sidebar.success("✅ ส่งเข้าเมลสำเร็จ!")
    else:
        st.sidebar.warning("ไม่พบข้อมูลสำหรับส่ง")

# --- หน้าวิเคราะห์ยอดขาย ---
if page == "📊 วิเคราะห์ยอดขาย":
    st.title("📊 ระบบวิเคราะห์ยอดขาย ทีพี2025")
    df = df_sales_raw.copy()
    df_stock_ref = df_stock_raw.copy()

    if not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        
        # --- 🤖 AI Executive Summary ---
        st.markdown("### 🤖 AI Executive Summary")
        ai_col1, ai_col2 = st.columns(2)
        total_sales_val = pd.to_numeric(df["รวมเงิน"], errors='coerce').sum()
        top_prod_name = df.groupby("ชื่อสินค้า")["จำนวนที่สั่งซื้อ"].sum().idxmax()
        
        with ai_col1:
            st.info(f"✨ **สรุปจุดแข็ง:** สินค้าที่ได้รับความนิยมสูงสุดคือ **{top_prod_name}** มียอดขายรวม **{total_sales_val:,.2f} บาท**")
        with ai_col2:
            if not df_stock_ref.empty:
                df_stock_ref.columns = [str(c).strip() for c in df_stock_ref.columns]
                low_stock_count = len(df_stock_ref[pd.to_numeric(df_stock_ref.iloc[:, -1], errors='coerce') < 2])
                st.warning(f"⚠️ **ข้อควรระวัง:** พบสินค้าสต็อกต่ำกว่าเกณฑ์ **{low_stock_count} รายการ**")

        st.divider()

        # สรุปภาพรวม
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 จำนวนรายการทั้งหมด", f"{len(df):,} รายการ")
        with col2:
            df["รวมเงิน"] = pd.to_numeric(df["รวมเงิน"], errors='coerce').fillna(0)
            st.metric("💰 ยอดขายรวมทั้งหมด", f"{df['รวมเงิน'].sum():,.2f} บาท")

        # กราฟ 10 อันดับสินค้าขายดี
        st.subheader("🏆 10 อันดับสินค้าที่ขายดีที่สุด")
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df.columns else df.columns[3]
        df[q_col] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        top_10_df = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"])[q_col].sum().reset_index().sort_values(by=q_col, ascending=False).head(10)
        top_10_df["label"] = top_10_df["รหัสสินค้า"] + " - " + top_10_df["ชื่อสินค้า"]
        st.bar_chart(data=top_10_df.set_index("label")[q_col])

        # ตารางสรุปสินค้า
        st.subheader("📝 ตารางสรุปสินค้า")
        st.dataframe(top_10_df.drop(columns=['label']).reset_index(drop=True), use_container_width=True)

        # ตารางสรุปรายวัน
        st.subheader("📅 ตารางสรุปยอดการสั่งซื้อตามวันที่")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df.columns else df.columns[0]
        summary_date = df.groupby(date_col).size().reset_index(name="จำนวนรายการที่สั่งซื้อ")
        summary_date['temp_date'] = pd.to_datetime(summary_date[date_col], dayfirst=True, errors='coerce')
        summary_date = summary_date.sort_values(by='temp_date', ascending=False)
        st.dataframe(summary_date.drop(columns=['temp_date']).reset_index(drop=True), use_container_width=True)

        # กราฟรายเดือน
        st.divider()
        st.subheader("📈 สรุปจำนวนรายการที่สั่งซื้อรายเดือน")
        try:
            summary_date['เลขเดือน'] = summary_date[date_col].apply(lambda x: str(x).split('/')[1] if len(str(x).split('/')) >= 2 else "00")
            monthly_chart = summary_date.groupby('เลขเดือน')['จำนวนรายการที่สั่งซื้อ'].sum().reset_index()
            all_months = pd.DataFrame({"เลขเดือน": [f"{i:02d}" for i in range(1, 13)], "ชื่อเดือน": ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]})
            final_monthly = pd.merge(all_months, monthly_chart, on="เลขเดือน", how="left").fillna(0)
            st.bar_chart(data=final_monthly, x="ชื่อเดือน", y="จำนวนรายการที่สั่งซื้อ", use_container_width=True)

            # --- 🔮 AI พยากรณ์ + ลิงก์จราจร/อากาศ (กลับมาแล้วครบๆ) ---
            st.markdown("### 🔮 AI Sales Forecast & Deep Reason Analysis")
            active_data = final_monthly[final_monthly['จำนวนรายการที่สั่งซื้อ'] > 0]
            
            if len(active_data) >= 2:
                x_vals = np.arange(len(active_data))
                y_vals = active_data['จำนวนรายการที่สั่งซื้อ'].values
                slope, intercept = np.polyfit(x_vals, y_vals, 1)
                
                last_month_num = int(active_data['เลขเดือน'].iloc[-1])
                next_month_name = all_months.iloc[last_month_num % 12]['ชื่อเดือน']
                next_month_idx = (last_month_num % 12) + 1

                season_reasons = {
                    4: "🚙 **เมษายน:** รถวิ่งระยะไกลสูง ระบบระบายความร้อนควรสำรองอะไหล่",
                    5: "🌧️ **พฤษภาคม:** เริ่มเข้าฤดูฝน ใบปัดน้ำฝนและระบบเบรกจะขายดี",
                    12: "🚩 **ธันวาคม:** ช่วงปีใหม่ ระบบไฟและแบตเตอรี่ต้องพร้อม",
                    1: "🔧 **มกราคม:** หลังปีใหม่ อะไหล่กลุ่มไส้กรองจะมียอดสั่งสูง"
                }
                reason = season_reasons.get(next_month_idx, f"⚙️ **วิเคราะห์:** เดือน{next_month_name} เน้นเช็คระยะปกติ")

                p_col1, p_col2 = st.columns(2)
                p_col1.metric(f"คาดการณ์ออเดอร์ในเดือน {next_month_name}", f"{max(0, int(slope * len(active_data) + intercept))} รายการ")
                with p_col2:
                    st.info(f"💡 **แนวโน้ม:** {'📈 เพิ่มขึ้น' if slope > 0 else '📉 ชะลอตัว'}")
                    st.write(reason)
                    st.markdown("---")
                    st.markdown("**🔗 ตรวจสอบปัจจัยสัญจรและอากาศ:**")
                    st.markdown("- [☁️ กรมอุตุฯ](https://www.tmd.go.th/forecast/monthly) | [🚗 Longdo Traffic](https://traffic.longdo.com/)")
        except: st.info("AI กำลังประมวลผลข้อมูล...")

# --- หน้าสต็อกสินค้า (เช็คแล้วว่ามาครบ) ---
elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้า")
    df_stock = df_stock_raw.copy()
    df_sales = df_sales_raw.copy()

    if not df_stock.empty:
        df_stock.columns = [str(c).strip() for c in df_stock.columns]
        last_col = df_stock.columns[-1] 
        df_stock[last_col] = pd.to_numeric(df_stock[last_col], errors='coerce').fillna(0)
        
        st.subheader("🔥 10 อันดับสินค้าขายดีที่ควรสั่งซื้อด่วน")
        if not df_sales.empty:
            df_sales.columns = [str(c).strip() for c in df_sales.columns]
            q_col_s = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales.columns else d
