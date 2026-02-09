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

        # กราฟ 10 อันดับสินค้าขายดี (คงเดิม)
        st.subheader("🏆 10 อันดับสินค้าที่ขายดีที่สุด (เรียงจากจำนวนสั่งซื้อ)")
        q_col = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df.columns else df.columns[3]
        m_col = "รวมเงิน" if "รวมเงิน" in df.columns else df.columns[4]
        df[q_col] = pd.to_numeric(df[q_col], errors='coerce').fillna(0)
        df[m_col] = pd.to_numeric(df[m_col], errors='coerce').fillna(0)

        chart_df = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"]).agg({
            q_col: "sum",
            m_col: "sum"
        }).reset_index().sort_values(by=q_col, ascending=False).head(10)

        chart_df["label"] = chart_df["รหัสสินค้า"] + " - " + chart_df["ชื่อสินค้า"] + " (" + chart_df[m_col].map('{:,.0f}'.format) + " บาท)"
        st.bar_chart(data=chart_df.set_index("label")[q_col])

        # ตารางสรุปสินค้า (คงเดิม)
        st.subheader("📝 ตารางสรุปสินค้า (รวมตามรหัสสินค้า)")
        summary_product = df.groupby(["รหัสสินค้า", "ชื่อสินค้า"]).agg({
            q_col: "sum",
            m_col: "sum"
        }).reset_index().sort_values(by=q_col, ascending=False)
        summary_product = summary_product.reset_index(drop=True)
        summary_product.index = summary_product.index + 1
        st.dataframe(summary_product, use_container_width=True)

        # ตารางสรุปรายวัน (คงเดิม)
        st.subheader("📅 ตารางสรุปยอดการสั่งซื้อตามวันที่")
        date_col = "วันที่สั่งซื้อ" if "วันที่สั่งซื้อ" in df.columns else df.columns[0]
        summary_date = df.groupby(date_col).size().reset_index(name="จำนวนรายการที่สั่งซื้อ")
        summary_date['temp_date'] = pd.to_datetime(summary_date[date_col], dayfirst=True, errors='coerce')
        summary_date = summary_date.sort_values(by='temp_date', ascending=False)
        graph_monthly_data = summary_date.copy()
        display_date_table = summary_date.drop(columns=['temp_date']).reset_index(drop=True)
        display_date_table.index = display_date_table.index + 1
        st.dataframe(display_date_table, use_container_width=True)

        # --- ปรับปรุงจุดที่ต้องการ: กราฟรายเดือน เรียงจากซ้ายไปขวา (ม.ค. - ธ.ค.) ---
        st.divider()
        st.subheader("📈 สรุปจำนวนรายการที่สั่งซื้อรายเดือน (มกราคม - ธันวาคม)")
        
        try:
            def extract_month(date_str):
                parts = str(date_str).split('/')
                if len(parts) >= 2:
                    return parts[1] 
                return "00"

            graph_monthly_data['เลขเดือน'] = graph_monthly_data[date_col].apply(extract_month)
            monthly_chart = graph_monthly_data.groupby('เลขเดือน')['จำนวนรายการที่สั่งซื้อ'].sum().reset_index()
            
            # บังคับโครงสร้างเดือน 01-12
            all_months = pd.DataFrame({
                "เลขเดือน": [f"{i:02d}" for i in range(1, 13)],
                "ชื่อเดือน": ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", 
                             "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
            })
            
            # รวมข้อมูลและเรียงตามเลขเดือนเพื่อล็อกลำดับ ซ้าย -> ขวา
            final_monthly = pd.merge(all_months, monthly_chart, on="เลขเดือน", how="left").fillna(0)
            final_monthly = final_monthly.sort_values('เลขเดือน')

            # แสดงกราฟแบบระบุแกนเพื่อป้องกัน Streamlit สลับตำแหน่งเอง
            st.bar_chart(data=final_monthly, x="ชื่อเดือน", y="จำนวนรายการที่สั่งซื้อ", use_container_width=True)
            
        except Exception as e:
            st.info("ไม่สามารถแสดงกราฟรายเดือนได้")

elif page == "📦 สต็อกสินค้าคงเหลือ":
    st.title("📦 ระบบตรวจสอบสต็อกสินค้า")
    df_stock = get_data("สต็อกสินค้า", "สินค้าคงเหลือ")
    df_sales = get_data("ทีพี2025", "แปลงข้อมูลยอดขาย")

    if not df_stock.empty:
        df_stock.columns = [str(c).strip() for c in df_stock.columns]
        last_col = df_stock.columns[-1] 
        df_stock[last_col] = pd.to_numeric(df_stock[last_col], errors='coerce').fillna(0)

        st.subheader("🔥 10 อันดับสินค้าขายดีที่ควรสั่งซื้อด่วน (โชว์จำนวนคงเหลือจริงในกราฟ)")
        if not df_sales.empty:
            df_sales.columns = [str(c).strip() for c in df_sales.columns]
            q_col_sales = "จำนวนที่สั่งซื้อ" if "จำนวนที่สั่งซื้อ" in df_sales.columns else df_sales.columns[3]
            hot_sales = df_sales.groupby("รหัสสินค้า")[q_col_sales].sum().reset_index()
            urgent_df = pd.merge(df_stock, hot_sales, left_on=df_stock.columns[0], right_on="รหัสสินค้า", how="left")
            urgent_df[q_col_sales] = urgent_df[q_col_sales].fillna(0)
            urgent_list = urgent_df[urgent_df[last_col] < 2].sort_values(by=q_col_sales, ascending=False).head(10)
            
            if not urgent_list.empty:
                urgent_list["label"] = urgent_list["รหัสสินค้า"] + " (" + urgent_list.iloc[:, 1] + ")"
                st.bar_chart(data=urgent_list.set_index("label")[last_col])
            else:
                st.success("🎉 ยังไม่มีสินค้าขายดีที่สต็อกต่ำกว่า 2")

        st.subheader("⚠️ สินค้าที่ต้องเติมด่วน (เหลือน้อยกว่า 2)")
        low_stock = df_stock[df_stock[last_col] < 2].reset_index(drop=True)
        low_stock.index = low_stock.index + 1
        st.dataframe(low_stock, use_container_width=True)
        
        st.divider()
        st.subheader("📋 รายการสต็อกทั้งหมด")
        all_stock = df_stock.reset_index(drop=True)
        all_stock.index = all_stock.index + 1
        st.dataframe(all_stock, use_container_width=True)
