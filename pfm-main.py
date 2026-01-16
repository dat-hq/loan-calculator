import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Cấu hình trang
st.set_page_config(page_title="Hệ Thống Quản Lý Tài Chính & Dư Nợ", layout="wide", page_icon="💸")

# --- KẾT NỐI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HÀM HỖ TRỢ DỮ LIỆU ---
def load_data():
    try:
        # Đọc dữ liệu từ Sheet đầu tiên, ttl=0 để không cache
        df = conn.read(ttl=0)
        # Nếu sheet rỗng hoặc chưa đúng format, trả về list rỗng
        if df.empty or "amount" not in df.columns:
            return []
        # Chuyển đổi NaN thành None hoặc giá trị mặc định để tránh lỗi JSON
        df = df.replace({np.nan: None})
        return df.to_dict('records')
    except Exception as e:
        # st.error(f"Lỗi kết nối Google Sheets: {e}")
        return []

def save_data(data):
    try:
        if not data:
            df = pd.DataFrame(columns=["id", "name", "partner", "type", "amount", "rate", "date", "status"])
        else:
            df = pd.DataFrame(data)
        
        # Ghi đè cập nhật vào Sheet hiện tại
        conn.update(data=df)
        st.toast("Đã lưu dữ liệu lên Google Sheets!", icon="☁️")
    except Exception as e:
        st.error(f"Không thể lưu dữ liệu: {e}")

# --- CSS TÙY CHỈNH (AESTHETICS) ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff10; /* Semi-transparent for dark mode compatibility */
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background-color: #4CAF50; 
        color: white;
        border: none;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    </style>
    """, unsafe_allow_html=True)

# --- NAVIGATION ---
st.sidebar.title("📌 Menu")
page = st.sidebar.radio("Chọn chức năng", ["Công cụ tính lãi", "Quản lý sổ nợ"])

st.sidebar.divider()
st.sidebar.info("Ứng dụng hỗ trợ tính toán và quản lý các khoản vay cá nhân/doanh nghiệp hiệu quả.")

# --- HÀM TÍNH TOÁN (GIỮ NGUYÊN TỪ PHIÊN BẢN CŨ) ---
def calculate_reducing_balance(principal, rate_yearly, months):
    rate_monthly = rate_yearly / 100 / 12
    # Công thức PMT: P * r * (1+r)^n / ((1+r)^n - 1)
    if rate_yearly == 0:
        monthly_payment = principal / months
    else:
        monthly_payment = (principal * rate_monthly * (1 + rate_monthly)**months) / ((1 + rate_monthly)**months - 1)
    
    schedule = []
    balance = principal
    
    for i in range(1, months + 1):
        interest = balance * rate_monthly
        principal_payment = monthly_payment - interest
        if i == months: # Xử lý làm tròn tháng cuối
            principal_payment = balance
            monthly_payment = principal_payment + interest
        
        balance -= principal_payment
        if balance < 0: balance = 0
        
        schedule.append({
            "Tháng": i,
            "Trả gốc": round(principal_payment),
            "Trả lãi": round(interest),
            "Tổng trả": round(monthly_payment),
            "Dư nợ còn lại": round(balance)
        })
    return pd.DataFrame(schedule)

def calculate_flat_rate(principal, rate_yearly, months):
    principal_per_month = principal / months
    interest_per_month = principal * (rate_yearly / 100 / 12)
    monthly_payment = principal_per_month + interest_per_month
    
    schedule = []
    balance = principal
    
    for i in range(1, months + 1):
        balance -= principal_per_month
        if balance < 0: balance = 0
        
        schedule.append({
            "Tháng": i,
            "Trả gốc": round(principal_per_month),
            "Trả lãi": round(interest_per_month),
            "Tổng trả": round(monthly_payment),
            "Dư nợ còn lại": round(balance)
        })
    return pd.DataFrame(schedule)

# --- HÀM HỖ TRỢ FORMAT TIỀN ---
def format_currency_cb(key):
    try:
        raw = st.session_state[key]
        # Giữ lại số
        clean = raw.replace(',', '').replace('.', '').strip()
        if clean:
            val = int(clean)
            # Cập nhật lại state với định dạng có dấu phẩy
            st.session_state[key] = f"{val:,.0f}" 
    except:
        pass

def parse_currency(value_str):
    try:
        if not value_str: return 0.0
        return float(value_str.replace(',', '').replace('.', '').strip())
    except:
        return 0.0

# --- TRANG CÔNG CỤ TÍNH LÃI ---
if page == "Công cụ tính lãi":
    st.title("💰 Ứng dụng Tính Lãi Vay (Calculator)")
    
    col_input, col_result = st.columns([1, 2], gap="large")
    
    with col_input:
        st.subheader("Thông tin khoản vay")
        with st.container(border=True):
            # Input tiền vay dạng text để auto-format
            if 'loan_amount_input' not in st.session_state:
                st.session_state.loan_amount_input = "100,000,000"
            
            st.text_input("Số tiền vay (VNĐ)", key="loan_amount_input", on_change=format_currency_cb, args=("loan_amount_input",))
            loan_amount = parse_currency(st.session_state.loan_amount_input)
            
            interest_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, value=12.0, step=0.1)
            loan_term_months = st.number_input("Thời hạn vay (Tháng)", min_value=1, value=12, step=1)
            start_date = st.date_input("Ngày bắt đầu vay")
            method = st.radio("Phương thức trả nợ", ["Dư nợ giảm dần", "Dư nợ ban đầu (Lãi phẳng)"])

    # Xử lý tính toán
    if method == "Dư nợ giảm dần":
        df = calculate_reducing_balance(loan_amount, interest_rate, loan_term_months)
    else:
        df = calculate_flat_rate(loan_amount, interest_rate, loan_term_months)

    total_paid = df["Tổng trả"].sum()
    total_interest = df["Trả lãi"].sum()
    monthly_avg = df["Tổng trả"].mean()

    with col_result:
        st.subheader("Kết quả dự tính")
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng gốc + Lãi", f"{total_paid:,.0f} đ", delta="Tổng chi")
        m2.metric("Tổng lãi phải chịu", f"{total_interest:,.0f} đ", delta_color="inverse")
        m3.metric("Trả trung bình/tháng", f"{monthly_avg:,.0f} đ")
        
        st.divider()
        
        tab1, tab2 = st.tabs(["Biểu đồ dòng tiền", "Lịch trả nợ chi tiết"])
        with tab1:
            chart_data = df.melt(id_vars=["Tháng"], value_vars=["Trả gốc", "Trả lãi"], var_name="Loại tiền", value_name="Số tiền")
            fig = px.bar(chart_data, x="Tháng", y="Số tiền", color="Loại tiền", title="Cơ cấu trả nợ hàng tháng", barmode='stack',
                         color_discrete_map={"Trả gốc": "#4CAF50", "Trả lãi": "#FF5722"})
            st.plotly_chart(fig, use_container_width=True)
            
        with tab2:
            st.dataframe(df, use_container_width=True, height=400)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Tải bảng tính về (CSV)",
                csv,
                "lich_tra_no.csv",
                "text/csv",
                key='download-csv',
                use_container_width=True
            )

# --- TRANG QUẢN LÝ SỔ NỢ ---
elif page == "Quản lý sổ nợ":
    st.title("🗂️ Quản Lý Sổ Nợ")
    
    # Initialize session state for debts if not exists
    if 'debts' not in st.session_state:
        st.session_state.debts = load_data()

    # --- METRICS OVERVIEW ---
    total_borrow = sum(d['amount'] for d in st.session_state.debts if d['type'] == 'Đi vay')
    total_lend = sum(d['amount'] for d in st.session_state.debts if d['type'] == 'Cho vay')
    count_active = len(st.session_state.debts)

    col1, col2, col3 = st.columns(3)
    col1.metric("Tổng Đi Vay", f"{total_borrow:,.0f} đ", delta="Nợ phải trả", delta_color="inverse")
    col2.metric("Tổng Cho Vay", f"{total_lend:,.0f} đ", delta="Tài sản")
    col3.metric("Số Khoản Vay Đang QL", f"{count_active} khoản")

    st.divider()

    # --- ADD NEW DEBT FORM (CUSTOM LAYOUT) ---
    with st.expander("➕ Thêm khoản vay mới", expanded=True):
        st.caption("Điền thông tin và nhấn Lưu để thêm vào sổ theo dõi")
        
        # Grid Layout 3-3 to align rows
        c1, c2 = st.columns(2, gap="medium")
        
        with c1:
            new_name = st.text_input("Tên khoản vay / Mục đích", placeholder="Vd: Vay mua nhà")
            new_partner = st.text_input("Đối tác (Người vay/Cho vay)", placeholder="Vd: Ngân hàng A")
            new_type = st.selectbox("Loại hình", ["Đi vay", "Cho vay"])
        
        with c2:
            # Check initialization
            if 'new_amount_input' not in st.session_state:
                st.session_state.new_amount_input = "10,000,000"
                
            st.text_input("Số tiền (VNĐ)", key="new_amount_input", on_change=format_currency_cb, args=("new_amount_input",))
            new_amount = parse_currency(st.session_state.new_amount_input)
            
            new_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, step=0.1, value=10.0)
            new_date = st.date_input("Ngày giải ngân", datetime.now())
        
        st.write("") # Spacer
        # Nút lưu full width
        if st.button("💾 LƯU KHOẢN VAY", type="primary", use_container_width=True):
            if new_name and new_amount > 0:
                new_id = datetime.now().strftime('%Y%m%d%H%M%S')
                new_debt = {
                    "id": new_id,
                    "name": new_name,
                    "partner": new_partner,
                    "type": new_type,
                    "amount": new_amount,
                    "rate": new_rate,
                    "date": new_date.strftime("%Y-%m-%d"),
                    "status": "Đang hoạt động"
                }
                st.session_state.debts.append(new_debt)
                save_data(st.session_state.debts)
                st.success(f"Đã thêm khoản '{new_name}' thành công!")
                # Optional: Clear inputs by resetting session state keys if needed
            else:
                st.warning("⚠️ Vui lòng nhập Tên khoản vay và Số tiền lớn hơn 0")

    # --- DISPLAY DEBTS ---
    st.subheader("📋 Danh sách các khoản vay")
    
    if st.session_state.debts:
        # Prepare Dataframe
        df_debts = pd.DataFrame(st.session_state.debts)
        
        # Display nicely
        display_df = df_debts[["id", "type", "name", "partner", "amount", "rate", "date", "status"]].copy()
        
        # Use Data Editor for potentially editable views in future, currently just display
        st.dataframe(
            display_df,
            column_config={
                "id": st.column_config.TextColumn("ID", width="small", disabled=True),
                "type": st.column_config.TextColumn("Loại", width="small"),
                "name": st.column_config.TextColumn("Mục đích", width="medium"),
                "partner": st.column_config.TextColumn("Đối tác", width="medium"),
                "amount": st.column_config.NumberColumn("Số tiền", format="%d đ"),
                "rate": st.column_config.NumberColumn("Lãi suất (%)", format="%.1f%%"),
                "date": st.column_config.DateColumn("Ngày", format="DD/MM/YYYY"),
                "status": st.column_config.TextColumn("Trạng thái", width="small")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # --- DELETE FUNCTION ---
        with st.container(border=True):
            st.write("🗑️ **Khu vực quản lý (Xóa)**")
            col_del_1, col_del_2 = st.columns([3, 1])
            with col_del_1:
                delete_id = st.selectbox("Chọn khoản vay để xóa (theo ID - Mục đích)", 
                                        options=[d['id'] for d in st.session_state.debts],
                                        format_func=lambda x: next((f"{d['id']} - {d['name']} ({d['amount']:,}đ)" for d in st.session_state.debts if d['id'] == x), x),
                                        key="delete_select",
                                        index=None,
                                        placeholder="Chọn ID muốn xóa..."
                )
            with col_del_2:
                if st.button("Xóa vĩnh viễn", type="primary"):
                    if delete_id:
                        st.session_state.debts = [d for d in st.session_state.debts if d['id'] != delete_id]
                        save_data(st.session_state.debts)
                        st.success("Đã xóa dữ liệu!")
                        st.rerun()
                    else:
                        st.warning("Hãy chọn khoản vay để xóa.")
    else:
        st.info("Hiện chưa có dữ liệu sổ nợ. Hãy thêm khoản vay đầu tiên ở trên! 👆")