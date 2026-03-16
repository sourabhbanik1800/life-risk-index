# Life_Risk_Index_premium_ui.py
import streamlit as st
import hashlib
import sqlite3
import os
from datetime import datetime
import json

# Optional PDF
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except Exception:
    FPDF_AVAILABLE = False

import plotly.graph_objects as go
import pandas as pd

# ---------- Config ----------
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# ---------- Database helpers ----------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            lri REAL NOT NULL,
            F REAL,
            S REAL,
            H REAL,
            D REAL,
            report_text TEXT,
            created_at TEXT,
            FOREIGN KEY(username) REFERENCES users(username)
        )
    """)
    conn.commit()
    # demo account
    cur.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                    ("admin", hash_password("admin123")))
        conn.commit()
    return conn, cur

def add_user(username: str, password: str, cur, conn) -> bool:
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username: str, password: str, cur) -> bool:
    cur.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    return bool(row and row[0] == hash_password(password))

def add_score(username: str, lri: float, F: float, S: float, H: float, D: float, report_text: str, cur, conn):
    created_at = datetime.utcnow().isoformat()
    cur.execute("""
        INSERT INTO scores (username, lri, F, S, H, D, report_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (username, float(lri), float(F), float(S), float(H), float(D), report_text, created_at))
    conn.commit()

def get_user_scores(username: str, cur):
    cur.execute("SELECT id, lri, F, S, H, D, report_text, created_at FROM scores WHERE username = ? ORDER BY created_at DESC", (username,))
    return cur.fetchall()

def get_score_by_id(score_id: int, cur):
    cur.execute("SELECT * FROM scores WHERE id = ?", (score_id,))
    return cur.fetchone()

# ---------- Reports ----------
def build_text_report(username: str, lri: float, F: float, S: float, H: float, D: float, created_at: str) -> str:
    lines = []
    lines.append("Life Risk Index — Report")
    lines.append(f"User: {username}")
    lines.append(f"Generated at (UTC): {created_at}")
    lines.append("")
    lines.append(f"Overall LRI: {round(lri * 100, 2)}%")
    lines.append("")
    lines.append("Component Scores (0-100):")
    lines.append(f"  Financial (F): {round(F * 100, 2)}%")
    lines.append(f"  Career (S): {round(S * 100, 2)}%")
    lines.append(f"  Health (H): {round(H * 100, 2)}%")
    lines.append(f"  Dependency (D): {round(D * 100, 2)}%")
    lines.append("")
    lines.append("Short Recommendations:")
    if F < 0.45:
        lines.append(" - Strengthen financial resilience: emergency fund and debt management.")
    if S < 0.50:
        lines.append(" - Invest in upskilling and career planning.")
    if H < 0.60:
        lines.append(" - Improve health habits; consult relevant resources.")
    if D < 0.50:
        lines.append(" - Reduce dependency risk by building buffers.")
    if F >= 0.7 and S >= 0.6 and H >= 0.7:
        lines.append(" - Excellent profile — keep maintaining your habits!")
    return "\n".join(lines)

def build_pdf_bytes(report_text: str, title: str = "Life Risk Index Report") -> bytes:
    if not FPDF_AVAILABLE:
        raise RuntimeError("FPDF not available")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", size=11)
    for line in report_text.split("\n"):
        pdf.multi_cell(0, 8, line)
    return pdf.output(dest="S").encode("latin-1")

# ---------- Init ----------
conn, cur = init_db()

# ---------- Page config & Premium CSS ----------
st.set_page_config(page_title="Life Risk Index", page_icon="✨", layout="wide")
st.markdown(
    """
    <style>
    /* Page background and base */
    :root{
      --bg: #fbfcfe;
      --card: #ffffff;
      --muted: #5b6b76;
      --accent1: #00bfa6; /* teal */
      --accent2: #2563eb; /* blue */
      --soft-shadow: 0 8px 30px rgba(16,24,40,0.08);
      --glass: rgba(255,255,255,0.7);
    }
    html, body, #root, .stApp {
      background: linear-gradient(180deg, #f6f9fb 0%, #ffffff 100%);
      color: #0b1220;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }
    .premium-header {
      text-align: center;
      padding: 40px 18px 10px 18px;
    }
    .brand {
      font-weight: 800;
      font-size: 44px;
      background: linear-gradient(90deg, var(--accent1), var(--accent2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: 0.4px;
    }
    .tagline { color: var(--muted); margin-top:6px; font-size:15px; }

    /* Sidebar styling */
    .css-1d391kg { background: linear-gradient(180deg, #ffffff, #fbfdff) !important; }
    .sidebar .stButton>button { border-radius:10px; box-shadow: var(--soft-shadow); }
    .sidebar .stTextInput>div>div>input, .sidebar .stTextInput>div>div>textarea {
      border-radius:10px; padding:12px; border:1px solid rgba(16,24,40,0.06); background:#fcfdff;
    }

    /* Card */
    .card {
      background: var(--card);
      border-radius: 14px;
      padding: 20px;
      box-shadow: var(--soft-shadow);
      border: 1px solid rgba(16,24,40,0.03);
    }
    .metric-card {
      border-radius:12px; padding:18px; background:linear-gradient(90deg, rgba(2,132,199,0.06), rgba(0,191,166,0.03));
      box-shadow: 0 6px 18px rgba(16,24,40,0.04);
    }
    .metric-title { color:#334155; font-weight:700; margin-bottom:6px; }
    .metric-value { font-size:22px; font-weight:800; color: #0b1220; }

    /* hover lift */
    .metric-card:hover { transform: translateY(-6px); transition: all .18s ease; }

    /* small text */
    .muted { color: var(--muted); font-size:13px; }

    /* bright badge */
    .badge {
      display:inline-block; padding:6px 10px; border-radius:999px; background: linear-gradient(90deg, var(--accent1), var(--accent2));
      color:white; font-weight:700; font-size:13px;
    }

    /* Download button style (Streamlit renders its own, but this helps) */
    .stDownloadButton>button { border-radius:10px; }

    </style>
    """, unsafe_allow_html=True)

# ---------- Header ----------
st.markdown('<div class="premium-header"><div class="brand">✨ Life Risk Index</div><div class="tagline">Premium, bright, and clear — your personal resilience dashboard</div></div>', unsafe_allow_html=True)
st.write("")  # spacing

# ---------- Session state ----------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ---------- Sidebar: account (left) ----------
with st.sidebar:
    st.markdown("<div class='card'><h3 style='margin:0 0 8px 0'>🔒 Account</h3>", unsafe_allow_html=True)
    if st.session_state["authenticated"]:
        st.markdown(f"<div class='muted'>Signed in as <strong>{st.session_state['username']}</strong></div>", unsafe_allow_html=True)
        if st.button("Sign out"):
            st.session_state["authenticated"] = False
            st.session_state["username"] = ""
            st.rerun()
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown("<div class='muted'>Quick Actions</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:8px'><button style='padding:8px 12px;border-radius:8px; background:linear-gradient(90deg,#00bfa6,#2563eb); color:white; border:none; font-weight:600'>New Calculation</button></div>", unsafe_allow_html=True)
    else:
        username_input = st.text_input("Username", key="login_user")
        password_input = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Sign in"):
            if verify_user(username_input.strip(), password_input, cur):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username_input.strip()
                st.success(f"Welcome back, {st.session_state['username']}!")
                st.rerun()
            else:
                st.error("Incorrect username or password")
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin:0 0 8px 0'>Create account</h4>", unsafe_allow_html=True)
        new_user = st.text_input("New username", key="reg_user")
        new_pass = st.text_input("New password", type="password", key="reg_pwd")
        if st.button("Create account"):
            nu = new_user.strip()
            if not nu or not new_pass:
                st.error("Please provide both username and password")
            else:
                ok = add_user(nu, new_pass, cur, conn)
                if ok:
                    st.success("Account created — you can sign in now.")
                else:
                    st.warning("Username already exists — choose another")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Lock screen ----------
if not st.session_state["authenticated"]:
    st.markdown("""
        <div class="card" style="margin:22px 0;">
            <h2 style="margin:0 0 8px 0">Dashboard locked</h2>
            <div class="muted">Sign in from the left to view and calculate your Life Risk Index.</div>
            <div style="margin-top:10px" class="muted">Demo account: <span class='badge'>admin</span> &nbsp; <span style='font-weight:600;color:#0b1220'>admin123</span></div>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# ---------- Main layout (after login) ----------
# two columns: left inputs & right summary/history
col_inputs, col_summary = st.columns([2, 1], gap="large")

with col_inputs:
    st.markdown('<div class="card"><h3 style="margin-top:0">Enter your details</h3>', unsafe_allow_html=True)
    monthly_income = st.number_input("Monthly Income (₹)", min_value=0.0, value=65000.0, step=1000.0, format="%.2f")
    monthly_expense = st.number_input("Monthly Expenses (₹)", min_value=0.0, value=25000.0, step=500.0, format="%.2f")
    total_savings = st.number_input("Total Savings (₹)", min_value=0.0, value=50000.0, step=1000.0, format="%.2f")
    total_debt = st.number_input("Total Debt (₹)", min_value=0.0, value=650000.0, step=1000.0, format="%.2f")
    monthly_emi = st.number_input("Monthly EMI (₹)", min_value=0.0, value=12000.0, step=500.0, format="%.2f")

    st.markdown("---")
    education_level = st.selectbox("Education Level", ["High School", "Graduate", "Post Graduate", "Professional"])
    industry_demand = st.selectbox("Industry Demand", ["Low", "Medium", "High"])
    upskilling_frequency = st.slider("Upskilling per year", 0, 6, 1)
    years_since_cert = st.slider("Years since certification", 0, 10, 1)

    st.markdown("---")
    weight = st.number_input("Weight (kg)", min_value=0.0, value=70.0, step=0.5, format="%.1f")
    height_cm = st.number_input("Height (cm)", min_value=0.0, value=172.0, step=1.0, format="%.1f")
    chronic_disease = st.checkbox("Chronic Disease")
    smoking = st.checkbox("Smoker")
    insurance = st.checkbox("Health Insurance", value=True)
    age = st.slider("Age", 18, 70, 28)

    dependents = st.slider("Dependents", 0, 6, 0)
    single_income = st.checkbox("Single Income Household")

    calculate = st.button("Calculate Life Risk Index", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_summary:
    st.markdown('<div class="card"><h4 style="margin:0 0 8px 0">Hello, <strong>{}</strong></h4>'.format(st.session_state["username"]), unsafe_allow_html=True)
    st.markdown("<div class='muted'>Quick summary & history</div>", unsafe_allow_html=True)
    # show last saved score if exists
    rows = get_user_scores(st.session_state["username"], cur)
    if rows:
        last = rows[0]
        st.markdown(f"<div style='margin-top:12px' class='metric-card'><div class='metric-title'>Latest LRI</div><div class='metric-value'>{round(last['lri']*100,2)}%</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top:10px' class='muted'>Saved on (UTC): {last['created_at']}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='margin-top:12px' class='metric-card'><div class='metric-title'>No scores yet</div><div class='metric-value'>Calculate to save your first LRI</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Calculation logic ----------
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

    # LRI
    LRI = 0.40 * F + 0.25 * S + 0.20 * H + 0.15 * D

    # build and save report (we do NOT store inputs)
    created_at = datetime.utcnow().isoformat()
    report_text = build_text_report(st.session_state["username"], LRI, F, S, H, D, created_at)
    add_score(st.session_state["username"], LRI, F, S, H, D, report_text, cur, conn)

    # ---------- Output result (large card) ----------
    st.markdown("<div class='card' style='margin-top:18px'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin:0 0 8px 0'>Your Life Risk Index</h3>", unsafe_allow_html=True)

    # Plotly gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(LRI * 100, 2),
        number={'suffix': "%", 'font': {'size': 36}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#00bfa6"},
            'steps': [
                {'range': [0, 40], 'color': "#ffccd5"},
                {'range': [40, 70], 'color': "#ffe9c6"},
                {'range': [70, 100], 'color': "#d4ffe9"}
            ],
            'threshold': {'line': {'color': "#0b1220", 'width': 4}, 'thickness': 0.75, 'value': round(LRI * 100, 2)}
        },
        title={'text': "Higher = Better", 'font': {'size': 13}}
    ))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-title'>💰 Financial</div><div class='metric-value'>{round(F*100,1)}%</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-title'>📈 Career</div><div class='metric-value'>{round(S*100,1)}%</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-title'>🏥 Health</div><div class='metric-value'>{round(H*100,1)}%</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-title'>👨‍👩‍👧 Dependency</div><div class='metric-value'>{round(D*100,1)}%</div></div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)
    # recommendations
    if monthly_income < monthly_expense:
        st.info("Expenses exceed income — create a budget and reduce discretionary spending.")
    if debt_income_ratio > 0.5:
        st.warning("High debt ratio — consider repayment restructuring or professional advice.")
    if total_savings / (monthly_expense*6) if monthly_expense>0 else 0 < 1:
        st.info("Emergency fund goal: target 3–6 months of expenses.")
    if upskilling_frequency < 2:
        st.info("Upskilling suggestion: complete at least 1 short course this year.")
    if bmi > 25:
        st.info("Health tip: small lifestyle changes can improve long-term resilience.")
    if not insurance:
        st.info("Consider a health insurance plan to reduce catastrophic risk.")

    st.markdown("</div>", unsafe_allow_html=True)

    # celebration & CTA
    if LRI >= 0.75:
        st.success("Great work — your LRI is strong! 🎉")
        st.balloons()
    else:
        st.success("Saved your score. View your History below to download the report.")

# ---------- History section ----------
st.markdown("<div style='margin-top:20px' class='card'><h3 style='margin:0 0 8px 0'>History & Reports</h3>", unsafe_allow_html=True)
rows = get_user_scores(st.session_state["username"], cur)
if not rows:
    st.info("No saved scores yet — calculate one above to save it to your account.")
else:
    df = pd.DataFrame([{
        "id": r["id"],
        "date_utc": r["created_at"],
        "lri_%": round(r["lri"]*100,2),
        "F_%": round(r["F"]*100,2) if r["F"] is not None else None,
        "S_%": round(r["S"]*100,2) if r["S"] is not None else None,
        "H_%": round(r["H"]*100,2) if r["H"] is not None else None,
        "D_%": round(r["D"]*100,2) if r["D"] is not None else None,
    } for r in rows])
    st.dataframe(df.rename(columns={"date_utc":"Date (UTC)","lri_%":"LRI (%)","F_%":"Financial (%)","S_%":"Career (%)","H_%":"Health (%)","D_%":"Dependency (%)"})[["Date (UTC)","LRI (%)","Financial (%)","Career (%)","Health (%)","Dependency (%)"]], height=260)
    st.markdown("#### Trend")
    df_chart = df.sort_values("date_utc")
    st.line_chart(df_chart.set_index("date_utc")["lri_%"])
    st.markdown("#### View / Download a saved report")
    options = {f"{r['created_at']} — {round(r['lri']*100,2)}%": r["id"] for r in rows}
    choice_label = st.selectbox("Choose a record", list(options.keys()))
    chosen_id = options[choice_label]
    chosen_row = get_score_by_id(chosen_id, cur)
    if chosen_row:
        st.markdown(f"**Saved on (UTC):** {chosen_row['created_at']}")
        st.markdown(f"**LRI:** {round(chosen_row['lri']*100,2)}%  •  **Financial:** {round(chosen_row['F']*100,2)}%  •  **Career:** {round(chosen_row['S']*100,2)}%")
        st.markdown(f"**Health:** {round(chosen_row['H']*100,2)}%  •  **Dependency:** {round(chosen_row['D']*100,2)}%")
        st.markdown("**Full textual report:**")
        st.code(chosen_row["report_text"], language="text")
        # download
        if FPDF_AVAILABLE:
            try:
                pdf_bytes = build_pdf_bytes(chosen_row["report_text"])
                st.download_button("📄 Download PDF report", data=pdf_bytes, file_name=f"lri_report_{chosen_row['id']}.pdf", mime="application/pdf")
            except Exception:
                st.download_button("📄 Download TXT report", data=chosen_row["report_text"].encode("utf-8"), file_name=f"lri_report_{chosen_row['id']}.txt", mime="text/plain")
        else:
            st.download_button("📄 Download TXT report", data=chosen_row["report_text"].encode("utf-8"), file_name=f"lri_report_{chosen_row['id']}.txt", mime="text/plain")
st.markdown("</div>", unsafe_allow_html=True)
