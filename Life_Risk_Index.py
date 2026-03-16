# Life_Risk_Index_with_history.py
import streamlit as st
import hashlib
import sqlite3
import os
import json
from datetime import datetime
import numpy as np
from io import BytesIO

# Try to import fpdf for PDF generation (optional)
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except Exception:
    FPDF_AVAILABLE = False

# -------------------------
# Config: database path
# -------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# -------------------------
# Database helpers
# -------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # return rows as dict-like
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # users table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
        """
    )
    # scores table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            lri REAL NOT NULL,
            F REAL,
            S REAL,
            H REAL,
            D REAL,
            inputs_json TEXT,
            report_text TEXT,
            created_at TEXT,
            FOREIGN KEY(username) REFERENCES users(username)
        )
        """
    )
    conn.commit()

    # create demo admin if not exists
    cur.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", hash_password("admin123")),
        )
        conn.commit()
    return conn, cur

def add_user(username: str, password: str, cur, conn) -> bool:
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
    cur.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        return False
    return row[0] == hash_password(password)

def add_score(username: str, lri: float, F: float, S: float, H: float, D: float, inputs: dict, report_text: str, cur, conn):
    created_at = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO scores (username, lri, F, S, H, D, inputs_json, report_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            float(lri),
            float(F),
            float(S),
            float(H),
            float(D),
            json.dumps(inputs),
            report_text,
            created_at,
        ),
    )
    conn.commit()

def get_user_scores(username: str, cur):
    cur.execute(
        "SELECT id, lri, F, S, H, D, inputs_json, report_text, created_at FROM scores WHERE username = ? ORDER BY created_at DESC",
        (username,),
    )
    rows = cur.fetchall()
    return rows

def get_score_by_id(score_id: int, cur):
    cur.execute("SELECT * FROM scores WHERE id = ?", (score_id,))
    return cur.fetchone()

# -------------------------
# PDF / report generation
# -------------------------
def build_text_report(username: str, lri: float, F: float, S: float, H: float, D: float, inputs: dict, created_at: str) -> str:
    lines = []
    lines.append(f"Life Risk Index Report")
    lines.append(f"User: {username}")
    lines.append(f"Generated at (UTC): {created_at}")
    lines.append("")
    lines.append(f"Overall LRI: {round(lri * 100, 2)}")
    lines.append("")
    lines.append("Component scores (0-100):")
    lines.append(f"  Financial (F): {round(F * 100, 2)}")
    lines.append(f"  Career (S): {round(S * 100, 2)}")
    lines.append(f"  Health (H): {round(H * 100, 2)}")
    lines.append(f"  Dependency (D): {round(D * 100, 2)}")
    lines.append("")
    lines.append("Inputs snapshot:")
    for k, v in inputs.items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    # short recommendations based on simple rules
    lines.append("Recommendations:")
    if inputs.get("monthly_income", 0) < inputs.get("monthly_expense", 0):
        lines.append(" - Expenses exceed income. Review spending and build budget.")
    if inputs.get("debt_income_ratio", 0) > 0.5:
        lines.append(" - High debt ratio. Consider debt consolidation or advisory.")
    if inputs.get("savings_ratio", 0) < 1:
        lines.append(" - Build an emergency fund (3-6 months expenses).")
    if inputs.get("upskilling_frequency", 0) < 2:
        lines.append(" - Increase upskilling frequency.")
    if inputs.get("bmi", 0) > 25:
        lines.append(" - Maintain a healthy BMI; consult health resources.")
    if not inputs.get("insurance", False):
        lines.append(" - Obtain health insurance.")
    return "\n".join(lines)

def build_pdf_bytes(report_text: str, title: str = "Life Risk Index Report") -> bytes:
    if not FPDF_AVAILABLE:
        raise RuntimeError("FPDF not available")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", size=11)
    # add lines, splitting on newline
    for line in report_text.split("\n"):
        # ensure wide lines wrap
        pdf.multi_cell(0, 8, line)
    return pdf.output(dest="S").encode("latin-1")

# -------------------------
# Initialize DB
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

    # build inputs snapshot for storage & report
    inputs_snapshot = {
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "total_savings": total_savings,
        "total_debt": total_debt,
        "monthly_emi": monthly_emi,
        "education_level": education_level,
        "industry_demand": industry_demand,
        "upskilling_frequency": upskilling_frequency,
        "years_since_cert": years_since_cert,
        "weight": weight,
        "height_cm": height_cm,
        "bmi": round(bmi, 2),
        "chronic_disease": bool(chronic_disease),
        "smoking": bool(smoking),
        "insurance": bool(insurance),
        "age": age,
        "dependents": dependents,
        "single_income": bool(single_income),
        "savings_ratio": savings_ratio,
        "debt_income_ratio": debt_income_ratio,
    }

    created_at = datetime.utcnow().isoformat()
    report_text = build_text_report(st.session_state["username"], LRI, F, S, H, D, inputs_snapshot, created_at)

    # store result in DB
    add_score(st.session_state["username"], LRI, F, S, H, D, inputs_snapshot, report_text, cur, conn)

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

    st.markdown("### 📌 Recommendations (quick)")
    if monthly_income < monthly_expense:
        st.markdown('<div class="recommend-card">⚠️ Expenses exceed income. Review your budget.</div>', unsafe_allow_html=True)
    if debt_income_ratio > 0.5:
        st.markdown('<div class="recommend-card">⚠️ High debt ratio. Consider debt advice.</div>', unsafe_allow_html=True)
    if inputs_snapshot["savings_ratio"] < 1:
        st.markdown('<div class="recommend-card">⚠️ Build emergency fund (3–6 months expenses).</div>', unsafe_allow_html=True)
    if upskilling_frequency < 2:
        st.markdown('<div class="recommend-card">⚠️ Increase upskilling frequency.</div>', unsafe_allow_html=True)
    if bmi > 25:
        st.markdown('<div class="recommend-card">⚠️ Maintain healthy BMI.\n</div>', unsafe_allow_html=True)
    if not insurance:
        st.markdown('<div class="recommend-card">⚠️ Obtain health insurance.</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    st.success("Saved your score to your account. You can view it in your History section below.")

# -------------------------
# History & Reports (always visible after login)
# -------------------------
st.markdown("---")
st.header("📚 Your History & Reports")

rows = get_user_scores(st.session_state["username"], cur)
if not rows:
    st.info("No past scores yet. Calculate a score to save it to your account.")
else:
    # show a simple table
    data_for_df = [
        {
            "id": r["id"],
            "date_utc": r["created_at"],
            "lri_%": round(r["lri"] * 100, 2),
            "F_%": round(r["F"] * 100, 2) if r["F"] is not None else None,
            "S_%": round(r["S"] * 100, 2) if r["S"] is not None else None,
            "H_%": round(r["H"] * 100, 2) if r["H"] is not None else None,
            "D_%": round(r["D"] * 100, 2) if r["D"] is not None else None,
        }
        for r in rows
    ]
    import pandas as pd
    df = pd.DataFrame(data_for_df)
    # show recent table
    st.dataframe(df[["date_utc", "lri_%", "F_%", "S_%", "H_%", "D_%"]].rename(
        columns={"date_utc":"Date (UTC)", "lri_%":"LRI (%)", "F_%":"Financial (%)", "S_%":"Career (%)", "H_%":"Health (%)", "D_%":"Dependency (%)"}
    ), height=240)

    # line chart for trend
    st.markdown("#### LRI Trend")
    # use the dataframe sorted ascending by date for chart
    df_chart = df.sort_values("date_utc")
    st.line_chart(df_chart.set_index("date_utc")["lri_%"])

    # select a saved record to inspect / download
    st.markdown("#### View / Download a saved report")
    options = {f"{r['created_at']} — {round(r['lri']*100,2)}%": r["id"] for r in rows}
    choice_label = st.selectbox("Choose a record", options=list(options.keys()))
    chosen_id = options[choice_label]
    chosen_row = get_score_by_id(chosen_id, cur)
    if chosen_row:
        st.subheader("Saved Report")
        st.text(f"Saved on (UTC): {chosen_row['created_at']}")
        st.markdown(f"**LRI:** {round(chosen_row['lri']*100,2)}%  \n**Financial:** {round(chosen_row['F']*100,2)}%  \n**Career:** {round(chosen_row['S']*100,2)}%  \n**Health:** {round(chosen_row['H']*100,2)}%  \n**Dependency:** {round(chosen_row['D']*100,2)}")
        st.markdown("**Inputs snapshot:**")
        try:
            inputs_obj = json.loads(chosen_row["inputs_json"])
            st.json(inputs_obj)
        except Exception:
            st.text("Could not parse inputs snapshot.")

        st.markdown("**Full textual report:**")
        st.code(chosen_row["report_text"], language="text")

        # prepare download: PDF if available else TXT
        if FPDF_AVAILABLE:
            try:
                pdf_bytes = build_pdf_bytes(chosen_row["report_text"])
                st.download_button(
                    label="📄 Download PDF report",
                    data=pdf_bytes,
                    file_name=f"lri_report_{chosen_row['id']}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error("PDF generation error — offering TXT instead.")
                st.download_button(
                    label="📄 Download TXT report",
                    data=chosen_row["report_text"].encode("utf-8"),
                    file_name=f"lri_report_{chosen_row['id']}.txt",
                    mime="text/plain",
                )
        else:
            st.download_button(
                label="📄 Download TXT report",
                data=chosen_row["report_text"].encode("utf-8"),
                file_name=f"lri_report_{chosen_row['id']}.txt",
                mime="text/plain",
            )

# -------------------------
# (Optional) Close DB on exit - not mandatory as Streamlit keeps process alive
# -------------------------
# conn.close()










