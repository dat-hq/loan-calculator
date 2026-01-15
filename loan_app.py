import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Cấu hình trang
st.set_page_config(page_title="Quản Lý Dư Nợ & Khoản Vay", layout="wide")

st.title("💰 Ứng dụng Quản lý Dư nợ & Tính lãi vay")

# --- KHUNG NHẬP LIỆU ---
with st.sidebar:
    st.header("Thông tin khoản vay")
    loan_amount = st.number_input("Số tiền vay (VNĐ)", min_value=0, value=100000000, step=1000000)
    interest_rate = st.number_input("Lãi suất (%/năm)", min_value=0.0, value=12.0, step=0.1)
    loan_term_months = st.number_input("Thời hạn vay (Tháng)", min_value=1, value=12, step=1)
    start_date = st.date_input("Ngày bắt đầu vay")
    
    method = st.radio("Phương thức trả nợ", ["Dư nợ giảm dần", "Dư nợ ban đầu (Lãi phẳng)"])

# --- HÀM TÍNH TOÁN ---
def calculate_reducing_balance(principal, rate_yearly, months):
    rate_monthly = rate_yearly / 100 / 12
    # Công thức PMT: P * r * (1+r)^n / ((1+r)^n - 1)
    monthly_payment = (principal * rate_monthly * (1 + rate_monthly)**months) / ((1 + rate_monthly)**months - 1)
    
    schedule = []
    balance = principal
    
    for i in range(1, months + 1):
        interest = balance * rate_monthly
        principal_payment = monthly_payment - interest
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

# --- XỬ LÝ DỮ LIỆU ---
if method == "Dư nợ giảm dần":
    df = calculate_reducing_balance(loan_amount, interest_rate, loan_term_months)
else:
    df = calculate_flat_rate(loan_amount, interest_rate, loan_term_months)

# Tổng hợp số liệu
total_paid = df["Tổng trả"].sum()
total_interest = df["Trả lãi"].sum()
monthly_avg = df["Tổng trả"].mean()

# --- HIỂN THỊ KẾT QUẢ ---
col1, col2, col3 = st.columns(3)
col1.metric("Tổng gốc + Lãi phải trả", f"{total_paid:,.0f} đ")
col2.metric("Tổng lãi phải chịu", f"{total_interest:,.0f} đ", delta_color="inverse")
col3.metric("Trả trung bình/tháng", f"{monthly_avg:,.0f} đ")

st.divider()

# Biểu đồ
st.subheader("Biểu đồ dòng tiền")
chart_data = df.melt(id_vars=["Tháng"], value_vars=["Trả gốc", "Trả lãi"], var_name="Loại tiền", value_name="Số tiền")
fig = px.bar(chart_data, x="Tháng", y="Số tiền", color="Loại tiền", title="Cơ cấu trả nợ hàng tháng", barmode='stack')
st.plotly_chart(fig, use_container_width=True)

# Bảng chi tiết
st.subheader("Lịch trả nợ chi tiết")
st.dataframe(df, use_container_width=True)

# Nút tải xuống
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    "Tải lịch trả nợ về Excel (CSV)",
    csv,
    "lich_tra_no.csv",
    "text/csv",
    key='download-csv'
)