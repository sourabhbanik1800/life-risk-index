# Life_Risk_Index_improved_ui.py
import streamlit as st
import hashlib
import sqlite3
import os
from datetime import datetime
import json
from io import BytesIO

# optional: PDF generation
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except Exception:
    FPDF_AVAILABLE = False

# plotting
import plotly.graph_objects as go

# -------------------------
# Config & DB path
# -------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# -------------------------
# Helpers: DB + auth + reports
# -------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # users
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
        """
    )
    # scores: note inputs_json intentionally omitted from INSERT later (not stored)
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
            report_text TEXT,
            created_at TEXT,
            FOREIGN KEY(username) REFERENCES users(username)
        )
        """
    )
    conn.commit()
    # demo admin
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

def add_score(username: str, lri: float, F: float, S: float, H: float, D: float, report_text: str, cur, conn):
    created_at = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT INTO scores (username, lri, F, S, H, D, report_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (username, float(lri), float(F), float(S), float(H), float(D), report_text, created_at),
    )
    conn.commit()

def get_user_scores(username: str, cur):
    cur.execute(
        "SELECT id, lri, F, S, H, D, report_text, created_at FROM scores WHERE username = ? ORDER BY created_at DESC",
        (username,),
    )
    return cur.fetchall()

def get_score_by_id(score_id: int, cur):
    cur.execute("SELECT * FROM scores WHERE id = ?", (score_id,))
    return cur.fetchone()

def build_text_report(username: str, lri: float, F: float, S: float, H: float, D: float, created_at: str) -> str:
    lines = []
    lines.append("Life Risk Index Report")
    lines.append(f"User: {username}")
    lines.append(f"Generated at (UTC): {created_at}")
    lines.append("")
    lines.append(f"Overall LRI: {round(lri * 100, 2)}%")
    lines.append("")
    lines.append("Component scores (0-100):")
    lines.append(f"  Financial (F): {round(F * 100, 2)}%")
    lines.append(f"  Career (S): {round(S * 100, 2)}%")
    lines.append(f"  Health (H): {round(H * 100, 2)}%")
    lines.append(f"  Dependency (D): {round(D * 100, 2)}%")
    lines.append("")
    lines.append("Recommendations (short):")
    # simple rules
    if F < 0.4:
        lines.append(" - Improve financial resilience: build emergency savings and manage debt.")
    if S < 0.5:
        lines.append(" - Invest in skills and career development.")
    if H < 0.6:
        lines.append(" - Check health habits; consult healthcare resources.")
    if D < 0.5:
        lines.append(" - Reduce dependency risk: plan long-term financial cover.")
    if F >= 0.7 and S >= 0.6 and H >= 0.7:
        lines.append(" - Great overall profile — maintain momentum!")
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
    for line in report_text.split("\n"):
        pdf.multi_cell(0, 8, line)
    return pdf.output(dest="S").encode("latin-1")

# -------------------------
# Init DB
# -------------------------
conn, cur = init_db()

# -------------------------
# Lovely UI CSS & header (animated gradient)
# -------------------------
st.set_page_config(page_title="Life Risk Index", page_icon="📊", layout="wide")
st.markdown(
    """
<style>
:root{
  --accent1: #00F5A0;
  --accent2: #00D9F5;
  --accent3: #8E2DE2;
}
body { background: linear-gradient(180deg,#051024 0%, #071826 100%); }
.header {
  text-align:center;
  padding:36px 18px;
  margin-bottom:10px;
}
.h1 {
  font-size:52px;
  font-weight:900;
  background: linear-gradient(90deg,var(--accent1),var(--accent2),var(--accent3));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  letter-spacing:1px;
}
.sub {
  color:#bcd9f4; opacity:0.95; margin-top:6px;
  font-size:16px;
}
.card {
  background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));
  padding:18px;
  border-radius:14px;
  box-shadow: 0 6px 30px rgba(0,0,0,0.45);
}
.metric-card:hover { transform: translateY(-6px); transition: all .25s ease; }
.small-muted { color:#9fb7d3; font-size:13px }
.row-gap { gap: 18px; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="header"><div class="h1">✨ Life Risk Index</div><div class="sub">Clear, friendly, and persistent — your personal resilience dashboard</div></div>', unsafe_allow_html=True)

# -------------------------
# Session state for auth
# -------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# -------------------------
# Authentication sidebar
# -------------------------
with st.sidebar.container():
    st.markdown("## 🔐 Account")
    if st.session_state["authenticated"]:
        st.markdown(f"**Signed in as:**  `{st.session_state['username']}`")
        if st.button("🔓 Logout"):
            st.session_state["authenticated"] = False
            st.session_state["username"] = ""
            st.rerun()
    else:
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
        st.markdown("### Create account (persistent)")
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

# lock screen
if not st.session_state["authenticated"]:
    st.markdown(
        """
        <div class="card" style="margin: 24px;">
            <h3 style="margin-bottom:6px">Dashboard locked 🔒</h3>
            <div class="small-muted">Please sign in from the sidebar to view and calculate your Life Risk Index.</div>
            <div style="margin-top:12px" class="small-muted">Demo: <code>admin</code> / <code>admin123</code></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# -------------------------
# Inputs area (left) + Quick tips (right)
# -------------------------
left, right = st.columns([2, 1])
with left:
    st.markdown("### Enter your details")
    monthly_income = st.number_input("Monthly Income (₹)", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
    monthly_expense = st.number_input("Monthly Expenses (₹)", min_value=0.0, value=0.0, step=500.0, format="%.2f")
    total_savings = st.number_input("Total Savings (₹)", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
    total_debt = st.number_input("Total Debt (₹)", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
    monthly_emi = st.number_input("Monthly EMI (₹)", min_value=0.0, value=0.0, step=500.0, format="%.2f")

    education_level = st.selectbox("Education Level", ["High School", "Graduate", "Post Graduate", "Professional"])
    industry_demand = st.selectbox("Industry Demand", ["Low", "Medium", "High"])
    upskilling_frequency = st.slider("Upskilling per year", 0, 6, 1)
    years_since_cert = st.slider("Years since certification", 0, 10, 1)

    weight = st.number_input("Weight (kg)", min_value=0.0, value=0.0, step=0.5, format="%.1f")
    height_cm = st.number_input("Height (cm)", min_value=0.0, value=0.0, step=1.0, format="%.1f")
    chronic_disease = st.checkbox("Chronic Disease")
    smoking = st.checkbox("Smoker")
    insurance = st.checkbox("Health Insurance")
    age = st.slider("Age", 18, 70, 25)

    dependents = st.slider("Dependents", 0, 6, 0)
    single_income = st.checkbox("Single Income Household")

    calculate = st.button("🚀 Calculate Life Risk Index", key="calc_btn")

with right:
    st.markdown("### Quick tips")
    st.markdown("- Keep 3–6 months of expenses as emergency fund.")
    st.markdown("- Upskill periodically to reduce career risk.")
    st.markdown("- Health insurance reduces household vulnerability.")
    st.markdown("---")
    st.markdown("### Your account")
    st.markdown(f"- Username: **{st.session_state['username']}**")

# -------------------------
# Calculation
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

    # build report_text (we do NOT store inputs)
    created_at = datetime.utcnow().isoformat()
    report_text = build_text_report(st.session_state["username"], LRI, F, S, H, D, created_at)

    # save scores (no input snapshot saved)
    add_score(st.session_state["username"], LRI, F, S, H, D, report_text, cur, conn)

    # ---------- Output: big card + gauge + components ----------
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🎯 Result")
    # gauge chart (plotly)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=round(LRI * 100, 2),
        number={'suffix': "%", 'font': {'size': 36}},
        delta={'reference': 50, 'increasing': {'color': "green"}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#00D9F5"},
            'steps': [
                {'range': [0, 40], 'color': "#FF6B6B"},
                {'range': [40, 70], 'color': "#FFD166"},
                {'range': [70, 100], 'color': "#7CFB9B"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': round(LRI * 100, 2)
            }
        },
        title={'text': "Life Risk Index (higher = better)", 'font': {'size': 14}}
    ))
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
    st.plotly_chart(fig, use_container_width=True)

    # components as metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Financial", f"{round(F*100,1)}%")
    c2.metric("📈 Career", f"{round(S*100,1)}%")
    c3.metric("🏥 Health", f"{round(H*100,1)}%")
    c4.metric("👨‍👩‍👧 Dependency", f"{round(D*100,1)}%")

    # recommendations
    st.markdown("### 🔎 Quick Recommendations")
    if monthly_income < monthly_expense:
        st.info("Expenses exceed income — build a budget and cut discretionary spend.")
    if debt_income_ratio > 0.5:
        st.warning("High debt ratio — consider restructuring or advisory.")
    if savings_ratio := (total_savings / (monthly_expense * 6) if monthly_expense > 0 else 0) < 1:
        st.info("Emergency fund shortfall — aim for 3–6 months of expenses.")
    if upskilling_frequency < 2:
        st.info("Upskilling: consider a short course / certification this year.")
    if bmi > 25:
        st.info("Health: small lifestyle changes can improve BMI and resilience.")
    if not insurance:
        st.info("Consider health insurance to reduce catastrophic risk.")

    st.markdown('</div>', unsafe_allow_html=True)

    # celebration for good scores
    if LRI >= 0.75:
        st.balloons()
        st.success("Fantastic! Your LRI is high — keep it up 🎉")
    else:
        st.success("Saved your score. Check your History below to view or download the report.")

# -------------------------
# History & Reports
# -------------------------
st.markdown("---")
st.header("📚 Your History")
rows = get_user_scores(st.session_state["username"], cur)
if not rows:
    st.info("No saved scores yet. Calculate one to see it here.")
else:
    import pandas as pd
    df = pd.DataFrame([{
        "id": r["id"],
        "date_utc": r["created_at"],
        "lri_%": round(r["lri"] * 100, 2),
        "F_%": round(r["F"] * 100, 2) if r["F"] is not None else None,
        "S_%": round(r["S"] * 100, 2) if r["S"] is not None else None,
        "H_%": round(r["H"] * 100, 2) if r["H"] is not None else None,
        "D_%": round(r["D"] * 100, 2) if r["D"] is not None else None,
    } for r in rows])

    st.dataframe(df.rename(columns={
        "date_utc":"Date (UTC)","lri_%":"LRI (%)","F_%":"Financial (%)","S_%":"Career (%)","H_%":"Health (%)","D_%":"Dependency (%)"
    })[["Date (UTC)","LRI (%)","Financial (%)","Career (%)","Health (%)","Dependency (%)"]], height=260)

    st.markdown("#### LRI Trend")
    df_chart = df.sort_values("date_utc")
    st.line_chart(df_chart.set_index("date_utc")["lri_%"])

    st.markdown("#### View / Download a saved report")
    options = {f"{r['created_at']} — {round(r['lri']*100,2)}%": r["id"] for r in rows}
    choice_label = st.selectbox("Choose a record", list(options.keys()))
    chosen_id = options[choice_label]
    chosen_row = get_score_by_id(chosen_id, cur)
    if chosen_row:
        st.subheader("Saved Report")
        st.markdown(f"**Saved on (UTC):** {chosen_row['created_at']}")
        st.markdown(f"**LRI:** {round(chosen_row['lri']*100,2)}%  •  **Financial:** {round(chosen_row['F']*100,2)}%  •  **Career:** {round(chosen_row['S']*100,2)}%")
        st.markdown(f"**Health:** {round(chosen_row['H']*100,2)}%  •  **Dependency:** {round(chosen_row['D']*100,2)}%")

        # show textual report only (no inputs)
        st.markdown("**Full textual report:**")
        st.code(chosen_row["report_text"], language="text")

        # downloads
        if FPDF_AVAILABLE:
            try:
                pdf_bytes = build_pdf_bytes(chosen_row["report_text"])
                st.download_button("📄 Download PDF report", data=pdf_bytes, file_name=f"lri_report_{chosen_row['id']}.pdf", mime="application/pdf")
            except Exception:
                st.download_button("📄 Download TXT report", data=chosen_row["report_text"].encode("utf-8"), file_name=f"lri_report_{chosen_row['id']}.txt", mime="text/plain")
        else:
            st.download_button("📄 Download TXT report", data=chosen_row["report_text"].encode("utf-8"), file_name=f"lri_report_{chosen_row['id']}.txt", mime="text/plain")

# Done









