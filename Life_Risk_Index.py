# Life_Risk_Index.py
import streamlit as st
import hashlib
import sqlite3
import os
import numpy as np

# -------------------------
# Config: database path
# -------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# -------------------------
# Database helpers
# -------------------------
def get_db_connection():
    # allow usage across Streamlit threads
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
        """
    )
    conn.commit()
    # Insert demo admin account if not exists
    cur.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", hash_password("admin123")),
        )
        conn.commit()
    return conn, cur

def hash_password(password: str) -> str:
    """Return SHA-256 hex digest of password (demo purposes)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def add_user(username: str, password: str, cur, conn) -> bool:
    """Return True if user added, False if already exists or error."""
    try:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hash_password(password)),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username: str, password: str, cur) -> bool:
    """Return True if username/password matches DB."""
    cur.execute(
        "SELECT password FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    if not row:
        return False
    stored_hash = row[0]
    return stored_hash == hash_password(password)

# -------------------------
# Initialize DB & cursor
# -------------------------
conn, cur = init_db()

# -------------------------
# Streamlit page config & CSS
# -------------------------
st.set_page_config(page_title="Life Risk Index", page_icon="📊", layout="wide")

st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 20% 20%, #1a2a3a, #0f2027 60%);
}
.main-title {
    font-size: 56px; font-weight: 900;
    background: linear-gradient(90deg,#00F5A0,#00D9F5,#8E2DE2);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    text-align:center;
}
.glass-card {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(25px);
    padding: 35px;
    border-radius: 28px;
}
.metric-card {
    padding: 55px; border-radius: 30px; text-align: center;
    font-size: 48px; font-weight: 800; color: white;
    background: linear-gradient(135deg,#00F5A0,#00D9F5,#8E2DE2);
}
.break-card {
    background: rgba(255,255,255,0.07);
    padding: 20px;
    border-radius: 18px;
    text-align: center;
    color: white;
}
.break-title { font-size: 16px; opacity: 0.8; }
.break-score { font-size: 28px; font-weight: 700; }
.recommend-card {
    background: rgba(255,255,255,0.1);
    padding: 14px 18px;
    border-radius: 14px;
    margin-bottom: 12px;
    color: #e6edf5;
    border-left: 4px solid #00F5A0;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">Life Risk Index Dashboard</div>', unsafe_allow_html=True)

# -------------------------
# Session state for auth
# -------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# -------------------------
# Sidebar: Authentication
# -------------------------
with st.sidebar.expander("🔐 Account"):
    if st.session_state["authenticated"]:
        st.write(f"Signed in as **{st.session_state['username']}**")
        if st.button("🔓 Logout"):
            st.session_state["authenticated"] = False
            st.session_state["username"] = ""
            st.rerun()
    else:
        st.write("Sign in to access the dashboard")
        username_input = st.text_input("Username", key="login_user")
        password_input = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Sign in"):
            if verify_user(username_input.strip(), password_input, cur):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username_input.strip()
                st.success(f"Welcome, {st.session_state['username']}!")
                st.rerun()
            else:
                st.error("Incorrect username or password")

        st.markdown("---")
        st.write("New user? Create an account (will persist across sessions)")
        new_user = st.text_input("New username", key="reg_user")
        new_pass = st.text_input("New password", type="password", key="reg_pwd")
        if st.button("Create account"):
            nu = new_user.strip()
            if not nu or not new_pass:
                st.error("Provide both username and password")
            else:
                ok = add_user(nu, new_pass, cur, conn)
                if ok:
                    st.success("Account created. You can now sign in.")
                else:
                    st.warning("Username already exists — pick another")

# If not authenticated — show a friendly locked screen and stop here
if not st.session_state["authenticated"]:
    st.markdown(
        """
        <div style="margin-top:40px; padding:24px; border-radius:12px; background: rgba(255,255,255,0.03); color:#e6edf5;">
        <h3>Dashboard locked</h3>
        <p>Please sign in from the sidebar to view and calculate your Life Risk Index.</p>
        <p><small>Demo account: <b>admin</b> / <b>admin123</b></small></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# -------------------------
# SIDEBAR: Inputs (visible only after login)
# -------------------------
st.sidebar.header("📥 Enter Your Information")

monthly_income = st.sidebar.number_input("Monthly Income (₹)", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
monthly_expense = st.sidebar.number_input("Monthly Expenses (₹)", min_value=0.0, value=0.0, step=500.0, format="%.2f")
total_savings = st.sidebar.number_input("Total Savings (₹)", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
total_debt = st.sidebar.number_input("Total Debt (₹)", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
monthly_emi = st.sidebar.number_input("Monthly EMI (₹)", min_value=0.0, value=0.0, step=500.0, format="%.2f")

education_level = st.sidebar.selectbox("Education Level", ["High School", "Graduate", "Post Graduate", "Professional"])
industry_demand = st.sidebar.selectbox("Industry Demand", ["Low", "Medium", "High"])
upskilling_frequency = st.sidebar.slider("Upskilling per year", 0, 6, 1)
years_since_cert = st.sidebar.slider("Years since certification", 0, 10, 1)

weight = st.sidebar.number_input("Weight (kg)", min_value=0.0, value=0.0, step=0.5, format="%.1f")
height_cm = st.sidebar.number_input("Height (cm)", min_value=0.0, value=0.0, step=1.0, format="%.1f")
chronic_disease = st.sidebar.checkbox("Chronic Disease")
smoking = st.sidebar.checkbox("Smoker")
insurance = st.sidebar.checkbox("Health Insurance")
age = st.sidebar.slider("Age", 18, 70, 25)

dependents = st.sidebar.slider("Dependents", 0, 6, 0)
single_income = st.sidebar.checkbox("Single Income Household")

calculate = st.sidebar.button("🚀 Calculate Life Risk Index")

# -------------------------
# CALCULATION & OUTPUT
# -------------------------
if calculate:
    # defensive defaults
    monthly_income = monthly_income or 0.0
    monthly_expense = monthly_expense or 0.0
    total_savings = total_savings or 0.0
    total_debt = total_debt or 0.0
    monthly_emi = monthly_emi or 0.0
    weight = weight or 0.0
    height_cm = height_cm or 0.0

    # Financial F
    savings_ratio = total_savings / (monthly_expense * 6) if monthly_expense > 0 else 0
    debt_income_ratio = total_debt / (monthly_income * 12) if monthly_income > 0 else 0
    emi_ratio = monthly_emi / monthly_income if monthly_income > 0 else 0
    F = 0.5 * min(savings_ratio, 1) + 0.3 * (1 - min(debt_income_ratio, 1)) + 0.2 * (1 - min(emi_ratio, 1))

    # Career S
    edu_map = {"High School": 1, "Graduate": 2, "Post Graduate": 3, "Professional": 4}
    ind_map = {"Low": 1, "Medium": 2, "High": 3}
    S = 0.25 * (edu_map[education_level] / 4) + 0.30 * (ind_map[industry_demand] / 3) + 0.25 * min(upskilling_frequency / 4, 1) + 0.20 * (1 - min(years_since_cert / 5, 1))

    # Health H
    height_m = height_cm / 100 if height_cm > 0 else 1
    bmi = weight / (height_m ** 2) if height_cm > 0 and weight > 0 else 0
    bmi_score = 1 if 18.5 <= bmi <= 24.9 else 0.6
    H = (bmi_score + (1 - int(chronic_disease)) + (1 - int(smoking)) + int(insurance)) / 4

    # Dependency D
    dependency_factor = min(dependents / 4, 1)
    D = 0.7 * (1 - dependency_factor) + 0.3 * (1 - int(single_income))

    # Life Risk Index
    LRI = 0.40 * F + 0.25 * S + 0.20 * H + 0.15 * D

    # ---------- OUTPUT ----------
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📊 Life Risk Score")
    st.markdown(f'<div class="metric-card">{round(LRI * 100, 2)}</div>', unsafe_allow_html=True)

    # Breakdown
    st.markdown("### 🔎 Score Breakdown")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        f'<div class="break-card"><div class="break-title">💰 Financial</div><div class="break-score">{round(F * 100, 1)}</div></div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        f'<div class="break-card"><div class="break-title">📈 Career</div><div class="break-score">{round(S * 100, 1)}</div></div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div class="break-card"><div class="break-title">🏥 Health</div><div class="break-score">{round(H * 100, 1)}</div></div>',
        unsafe_allow_html=True,
    )
    c4.markdown(
        f'<div class="break-card"><div class="break-title">👨‍👩‍👧 Dependency</div><div class="break-score">{round(D * 100, 1)}</div></div>',
        unsafe_allow_html=True,
    )

    # Recommendations
    st.markdown("### 📌 Evidence-Based Recommendations")
    if monthly_income < monthly_expense:
        st.markdown(
            '<div class="recommend-card">⚠️ Expenses exceed income. <a href="https://www.rbi.org.in/FinancialEducation/content/I%20Can%20Do_RBI.pdf" target="_blank">RBI Guide</a></div>',
            unsafe_allow_html=True,
        )
    if debt_income_ratio > 0.5:
        st.markdown(
            '<div class="recommend-card">⚠️ High Debt Ratio. <a href="https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf" target="_blank">SEBI Guide</a></div>',
            unsafe_allow_html=True,
        )
    if savings_ratio < 1:
        st.markdown(
            '<div class="recommend-card">⚠️ Build emergency fund. <a href="https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf" target="_blank">SEBI Guide</a></div>',
            unsafe_allow_html=True,
        )
    if upskilling_frequency < 2:
        st.markdown(
            '<div class="recommend-card">⚠️ Increase upskilling. <a href="https://www3.weforum.org/docs/WEF_Future_of_Jobs_2023.pdf" target="_blank">WEF Report</a></div>',
            unsafe_allow_html=True,
        )
    if bmi > 25:
        st.markdown(
            '<div class="recommend-card">⚠️ Maintain healthy BMI. <a href="https://www.who.int/health-topics/obesity" target="_blank">WHO Guide</a></div>',
            unsafe_allow_html=True,
        )
    if not insurance:
        st.markdown(
            '<div class="recommend-card">⚠️ Obtain health insurance. <a href="https://www.insuranceinstituteofindia.com/documents/6454111/5517dc58-2716-4b6d-afed-ab1fc703a79d" target="_blank">Insurance Guide</a></div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# Clean up: close DB connection when script finishes (optional)
# -------------------------
# Note: Streamlit may keep the process alive; explicit close is fine.
# conn.close()










