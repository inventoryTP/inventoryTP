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
def send_email_report(total_sales, top_10_html, urgent_stock_html, summary_text):
    try:
        sender_email = "inventory7@gmail.com"
        sender_password = "inventory2569."  # แนะนำให้ใช้ App Password หากติด Error
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
    df = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")
    df_stock_ref = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")

    if not df.empty:
        df.columns = [str(c).strip() for c in df.columns]

        # เตรียมข้อมูลสำหรับอีเมล
        total_sales_val = pd.to_numeric(df["รวมเงิน"], errors='coerce').sum()
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df.columns else df.columns[3]
        m_col = "รวมเงิน" if "รวมเงิน" in df.columns else df.columns[4]
        df[q_col] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        df[m_col] = pd.to_numeric(df[m_col], errors='coerce').fillna(0)
        
        # 10 อันดับสินค้าขายดี
        top_10_df = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"]).agg({q_col: "sum", m_col: "sum"}).reset_index().sort_values(by=q_col, ascending=False).head(10)
        
        # สินค้าขายดีที่ควรซื้อด่วน
        urgent_stock_html = "ไม่มีรายการด่วน"
        if not df_stock_ref.empty:
            df_stock_ref.columns = [str(c).strip() for c in df_stock_ref.columns]
            last_col_ref = df_stock_ref.columns[-1]
            df_stock_ref[last_col_ref] = pd.to_numeric(df_stock_ref[last_col_ref], errors='coerce').fillna(0)
            hot_sales_ref = df.groupby("รหัสสินค้า")[q_col].sum().reset_index()
            urgent_ref_df = pd.merge(df_stock_ref, hot_sales_ref, left_on=df_stock_ref.columns[0], right_on="รหัสสินค้า", how="left").fillna(0)
            urgent_list_ref = urgent_ref_df[urgent_ref_df[last_col_ref] < 2].sort_values(by=q_col, ascending=False).head(10)
            if not urgent_list_ref.empty:
                urgent_stock_html = urgent_list_ref[[urgent_list_ref.columns[0], urgent_list_ref.columns[1], last_col_ref]].to_html(index=False)

        # --- ส่วนปุ่มส่งอีเมล (เพิ่มใหม่) ---
        st.sidebar.divider()
        st.sidebar.subheader("📧 การส่งรายงาน")
        if st.sidebar.button("ส่งรายงานสรุปเข้า Email"):
            with st.spinner('กำลังส่งอีเมล...'):
                top_10_html = top_10_df.to_html(index=False)
                summary_ai = f"สินค้าที่ขายดีที่สุดคือ {top_10_df.iloc[0]['ชื่อสินค้า']} และมียอดขายรวมทั้งหมด {total_sales_val:,.2f} บาท"
                if send_email_report(total_sales_val, top_10_html, urgent_stock_html, summary_ai):
                    st.sidebar.success("✅ ส่งรายงานสำเร็จ!")

        # --- 🤖 ส่วนสรุปข้อมูลเดิมด้วย AI ---
        st.markdown("### 🤖 AI Executive Summary")
        ai_col1, ai_col2 = st.columns(2)
        top_prod = df.groupby("ชื่อสินค้า")["จำนวนที่สั่งซื้อ"].sum().idxmax()
        
        with ai_col1:
            st.info(f"✨ **สรุปจุดแข็ง:** สินค้าที่ได้รับความนิยมสูงสุดคือ **{top_prod}** มียอดขายรวม **{total_sales_val:,.2f} บาท**")
        with ai_col2:
            if not df_stock_ref.empty:
                low_stock_items = len(df_stock_ref[pd.to_numeric(df_stock_ref.iloc[:, -1], errors='coerce') < 2])
                st.warning(f"⚠️ **ข้อควรระวัง:** พบสินค้าสต็อกต่ำกว่าเกณฑ์ **{low_stock_items} รายการ**")

        st.divider()

        # ส่วนแสดงผลเดิม
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 จำนวนรายการทั้งหมด", f"{len(df):,} รายการ")
        with col2:
            st.metric("💰 ยอดขายรวมทั้งหมด", f"{total_sales_val:,.2f} บาท")

        st.subheader("🏆 10 อันดับสินค้าที่ขายดีที่สุด")
        chart_df = top_10_df.copy()
        chart_df["label"] = chart_df["รหัสสินค้า"] + " - " + chart_df["ชื่อสินค้า"]
        st.bar_chart(data=chart_df.set_index("label")[q_col])

        st.subheader("📝 ตารางสรุปสินค้า")
        st.dataframe(top_10_df, use_container_width=True)

        st.subheader("📅 ตารางสรุปยอดการสั่งซื้อตามวันที่")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df.columns else df.columns[0]
        summary_date = df.groupby(date_col).size().reset_index(name="จำนวนรายการที่สั่งซื้อ")
        summary_date['temp_date'] = pd.to_datetime(summary_date[date_col], dayfirst=True, errors='coerce')
        summary_date = summary_date.sort_values(by='temp_date', ascending=False)
        graph_monthly_data = summary_date.copy()
        st.dataframe(summary_date.drop(columns=['temp_date']).reset_index(drop=True), use_container_width=True)

        st.divider()
        st.subheader("📈 สรุปจำนวนรายการที่สั่งซื้อรายเดือน")
        try:
            def extract_month(date_str):
                parts = str(date_str).split('/')
                return parts[1] if len(parts) >= 2 else "00"

            graph_monthly_data['เลขเดือน'] = graph_monthly_data[date_col].apply(extract_month)
            monthly_chart = graph_monthly_data.groupby('เลขเดือน')['จำนวนรายการที่สั่งซื้อ'].sum().reset_index()
            all_months = pd.DataFrame({
                "เลขเดือน": [f"{i:02d}" for i in range(1, 13)],
                "ชื่อเดือน": ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
            })
            final_monthly = pd.merge(all_months, monthly_chart, on="เลขเดือน", how="left").fillna(0)
            st.bar_chart(data=final_monthly, x="ชื่อเดือน", y="จำนวนรายการที่สั่งซื้อ", use_container_width=True)

            st.markdown("### 🔮 AI Sales Forecast & Deep Reason Analysis")
            active_data = final_monthly[final_monthly['จำนวนรายการที่สั่งซื้อ'] > 0]
            
            if len(active_data) >= 2:
                x_vals = np.arange(len(active_data))
                y_vals = active_data['จำนวนรายการที่สั่งซื้อ'].values
                slope, intercept = np.polyfit(x_vals, y_vals, 1)
                prediction = max(0, int(slope * len(active_data) + intercept))
                
                current_month_idx = int(active_data['เลขเดือน'].iloc[-1])
                next_month_name = all_months.iloc[current_month_idx % 12]['ชื่อเดือน']

                season_deep_analysis = {
                    4: "🚙 **วิเคราะห์อะไหล่:** เมษายนรถวิ่งระยะไกลสูง ระบบระบายความร้อนควรสำรองอะไหล่",
                    5: "🌧️ **วิเคราะห์อะไหล่:** เริ่มเข้าฤดูฝน ใบปัดน้ำฝนและระบบเบรกจะมีแรงซื้อสูง",
                    12: "🚩 **วิเคราะห์อะไหล่:** ช่วงปีใหม่ ระบบไฟส่องสว่างและแบตเตอรี่ต้องพร้อมใช้งาน",
                    1: "🔧 **วิเคราะห์อะไหล่:** หลังเดินทางไกล อะไหล่กลุ่มไส้กรองจะมียอดสั่งสูง"
                }
                
                specific_reason = season_deep_analysis.get((current_month_idx % 12) + 1, f"⚙️ **วิเคราะห์อะไหล่:** เดือน{next_month_name} เน้นเช็คระยะปกติ")
                
                p_col1, p_col2 = st.columns(2)
                p_col1.metric(f"คาดการณ์ออเดอร์ในเดือน {next_month_name}", f"{prediction} รายการ")
                
                with p_col2:
                    st.info(f"💡 **บทวิเคราะห์แนวโน้ม:** {'📈 เพิ่มขึ้น' if slope > 0 else '📉 ชะลอตัว'}")
                    st.write(f"{specific_reason}")
                    st.markdown("---")
                    st.markdown("**🔗 ตรวจสอบปัจจัยสัญจรและอากาศ:**")
                    st.markdown("- [☁️ กรมอุตุฯ](https://www.tmd.go.th/forecast/monthly) | [🚗 Longdo Traffic](https://traffic.longdo.com/)")
            else:
                st.info("💡 AI กำลังวิเคราะห์ข้อมูล...")
        except:
            st.info("AI กำลังรอข้อมูลเพื่อประมวลผล...")

elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้า")
    df_stock = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")
    df
