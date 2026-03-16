# Life_Risk_Index_improved_ui.py
import streamlit as st
import hashlib
import sqlite3
import os
from datetime import datetime
import json
from io import BytesIO

# --- Add near top of file with other imports ---
import urllib.parse

# --- Add this RESOURCE_MAP near your helper functions (e.g., after build_pdf_bytes) ---
RESOURCE_MAP = {
    "financial_emergency": [
        {
            "title": "SEBI — Financial Education Booklet (personal finance primer, emergency fund advice)",
            "url": "https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf",
            "source": "SEBI"
        },
        {
            "title": "RBI — I Can Do (Financial Planning booklet)",
            "url": "https://www.rbi.org.in/FinancialEducation/content/I%20Can%20Do_RBI.pdf",
            "source": "Reserve Bank of India"
        }
    ],
    "debt_management": [
        {
            "title": "SEBI — Financial Education Booklet (debt, budgeting sections)",
            "url": "https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf",
            "source": "SEBI"
        }
    ],
    "upskilling": [
        {
            "title": "NSDC — Free Learning Resources (training curricula & short courses)",
            "url": "https://nsdcindia.org/free-learning-resources",
            "source": "NSDC"
        },
        {
            "title": "Skill India Digital Hub — Free upskilling courses",
            "url": "https://skillindiadigital.gov.in/",
            "source": "Skill India"
        }
    ],
    "health_bmi": [
        {
            "title": "WHO — Body Mass Index (BMI) guidance & classification",
            "url": "https://www.who.int/data/gho/data/themes/topics/topic-details/GHO/body-mass-index",
            "source": "World Health Organization"
        },
        {
            "title": "National Institute of Nutrition — Dietary Guidelines for Indians (2024)",
            "url": "https://www.nin.res.in/dietaryguidelines/pdfjs/locale/DGI07052024P.pdf",
            "source": "National Institute of Nutrition"
        }
    ],
    "health_insurance": [
        {
            "title": "IRDAI — Consumer Brochure / Insurance Consumer Education",
            "url": "https://irdai.gov.in/documents/38105/49819/IRDA%2BBrochure.pdf/e76c551c-9036-44de-6933-bb5aed15004d?download=true",
            "source": "IRDAI"
        },
        {
            "title": "IRDAI — policyholder portal & consumer education",
            "url": "https://irdai.gov.in/",
            "source": "IRDAI"
        }
    ],
    "smoking_cessation": [
        {
            "title": "WHO — Tobacco: Health effects & quitting resources",
            "url": "https://www.who.int/health-topics/tobacco",
            "source": "World Health Organization"
        },
    ]
}

def render_resources_for(key):
    """
    Render a compact list of reputable resources (links) for the given key.
    """
    resources = RESOURCE_MAP.get(key, [])
    if not resources:
        return
    st.markdown("**Authoritative resources you can download / read:**")
    for r in resources:
        safe_url = r["url"]
        st.markdown(f"- [{r['title']}]({safe_url}) — _{r['source']}_")
    st.markdown("---")

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
    """
    More informative textual report showing component values and short rationale.
    """
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
    lines.append("Short rationale & recommendations:")
    # Financial rationale
    if F < 0.45:
        lines.append(" - Financial: Low resilience. Priority: build emergency fund, reduce high-cost debt, and improve savings rate.")
    elif F < 0.70:
        lines.append(" - Financial: Moderate. Keep building liquidity and reduce EMI burden where possible.")
    else:
        lines.append(" - Financial: Strong. Maintain savings discipline and avoid over-leveraging.")

    # Career rationale
    if S < 0.5:
        lines.append(" - Career: Upskilling and certification recency are low relative to your role/industry — consider targeted courses.")
    elif S < 0.75:
        lines.append(" - Career: Good. Keep updating skills and monitor industry demand.")
    else:
        lines.append(" - Career: Strong. Continue to sustain market relevance via occasional upskilling.")

    # Health rationale
    if H < 0.6:
        lines.append(" - Health: Health indicators suggest elevated risk (BMI, chronic conditions, or smoking). Consult healthcare and consider insurance.")
    else:
        lines.append(" - Health: Good. Keep healthy habits and regular checkups.")

    # Dependency rationale
    if D < 0.5:
        lines.append(" - Dependency: Household is relatively vulnerable (multiple dependents, single income, or age-related risk). Plan life cover & contingencies.")
    else:
        lines.append(" - Dependency: Dependency risk is manageable. Maintain contingency planning for dependents.")

    lines.append("")
    lines.append("Actionable next steps (prioritized):")
    lines.append("  1) Build 3–6 months emergency fund.")
    lines.append("  2) Reduce high-interest debt / negotiate EMIs.")
    lines.append("  3) Enrol in 1 short certification this year.")
    lines.append("  4) If uninsured, consider basic health & life cover.")
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

    # NEW inputs
    monthly_investment = st.number_input("Monthly Investment (₹) — SIP / mutual funds / recurring", min_value=0.0, value=0.0, step=500.0, format="%.2f")
    job_stability = st.selectbox("Job Stability", ["Low", "Medium", "High"])
    number_of_earners = st.slider("Number of Earners in Household", 1, 4, 1)

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
    # defensive defaults & casts
    monthly_income = float(monthly_income or 0.0)
    monthly_expense = float(monthly_expense or 0.0)
    total_savings = float(total_savings or 0.0)
    total_debt = float(total_debt or 0.0)
    monthly_emi = float(monthly_emi or 0.0)
    monthly_investment = float(monthly_investment or 0.0)
    weight = float(weight or 0.0)
    height_cm = float(height_cm or 0.0)
    number_of_earners = int(number_of_earners or 1)

    # ----- Financial (F) - integrated model with monthly_investment -----
   # ----- Financial Stability Score (Enhanced Logic) -----

# Step 1 — Total expenses include EMI and SIP
total_expense = monthly_expense + monthly_emi + monthly_investment

# Step 2 — Cashflow ratio
expense_ratio = total_expense / monthly_income if monthly_income > 0 else 1

# Ideal financial planning guideline
# Expenses should not exceed ~70% of income

cashflow_score = 1 - min(expense_ratio, 1)

# Step 3 — EMI burden (debt stress)
emi_ratio = monthly_emi / monthly_income if monthly_income > 0 else 1

# Ideal EMI limit ~30% income
emi_health = 1 - min(emi_ratio / 0.30, 1)

# Step 4 — Investment discipline (SIP reward)
sip_ratio = monthly_investment / monthly_income if monthly_income > 0 else 0

# Ideal SIP = 20–30% income
sip_score = min(sip_ratio / 0.25, 1)

# Step 5 — Emergency fund calculation
emergency_months = total_savings / monthly_expense if monthly_expense > 0 else 0
emergency_score = min(emergency_months / 6, 1)

# Step 6 — Debt burden
annual_income = monthly_income * 12 if monthly_income > 0 else 0
debt_ratio = total_debt / annual_income if annual_income > 0 else 1
debt_score = 1 - min(debt_ratio, 1)

# Step 7 — Job stability multiplier
js_map = {"Low":0.9,"Medium":1,"High":1.05}
job_factor = js_map[job_stability]

# Step 8 — Final Financial Score
F = (
      0.30 * emergency_score
    + 0.20 * debt_score
    + 0.20 * emi_health
    + 0.15 * cashflow_score
    + 0.15 * sip_score
)

F = F * job_factor
F = max(0, min(F,1))

    # ----- Career (S) with job_stability included -----
    edu_map = {"High School": 1, "Graduate": 2, "Post Graduate": 3, "Professional": 4}
    ind_map = {"Low": 1, "Medium": 2, "High": 3}
    edu_score = edu_map[education_level] / 4.0
    ind_score = ind_map[industry_demand] / 3.0
    upskill_score = min(upskilling_frequency / 4.0, 1.0)
    cert_recency = max(0.0, 1.0 - (years_since_cert / 5.0))

    # age/experience adjustment
    if 25 <= age <= 45:
        age_boost = 1.0
    elif 46 <= age <= 55:
        age_boost = 0.95
    else:
        age_boost = 0.9

    S_raw = 0.30 * edu_score + 0.30 * ind_score + 0.25 * upskill_score + 0.15 * cert_recency
    # incorporate job stability as multiplier (stable job increases career resilience slightly)
    S = S_raw * age_boost * js_factor
    S = max(0.0, min(S, 1.0))

    # if financial situation is poor, slightly reduce career resilience (less ability to invest in learning)
    if F < 0.35:
        S = S * 0.96

    # ----- Health (H) -----
    height_m = (height_cm / 100.0) if height_cm > 0 else None
    if height_m and weight > 0:
        bmi = weight / (height_m ** 2)
    else:
        bmi = 0.0

    if 18.5 <= bmi <= 24.9:
        bmi_score = 1.0
    elif 25.0 <= bmi <= 29.9:
        bmi_score = 0.75
    elif bmi >= 30.0:
        bmi_score = 0.45
    elif 16.0 <= bmi < 18.5:
        bmi_score = 0.7
    else:
        bmi_score = 0.6 if bmi > 0 else 0.7

    smoking_penalty = 0.15 if smoking else 0.0
    chronic_penalty = 0.25 if chronic_disease else 0.0
    insurance_bonus = 0.08 if insurance else 0.0

    if age >= 60:
        age_factor = 0.75
    elif age >= 45:
        age_factor = 0.85
    elif age >= 30:
        age_factor = 0.95
    else:
        age_factor = 1.0

    H_raw = (0.50 * bmi_score + 0.20 * (1 - chronic_penalty) + 0.20 * (1 - smoking_penalty) + 0.10 * (1 + insurance_bonus))
    H = H_raw * age_factor
    H = max(0.0, min(H, 1.0))

    # ----- Dependency (D) with number_of_earners -----
    dep_count = dependents
    dep_base_risk = min(dep_count * 0.18, 0.9)

    single_income_risk = 0.22 if single_income else 0.0

    # age-based dependency risk
    if age >= 60:
        age_dep_risk = 0.25
    elif age >= 50:
        age_dep_risk = 0.18
    elif age >= 40:
        age_dep_risk = 0.12
    elif age >= 30:
        age_dep_risk = 0.08
    else:
        age_dep_risk = 0.05

    # reduce dependency risk by number of earners (more earners -> less household vulnerability)
    # each additional earner reduces dependency risk by ~12% multiplicatively but keep a floor
    earner_factor = 1.0 - 0.12 * (number_of_earners - 1)
    earner_factor = max(0.6, earner_factor)  # do not drop below 0.6 to avoid unrealistic elimination
    dep_base_risk = dep_base_risk * earner_factor

    total_dep_risk = dep_base_risk + single_income_risk + age_dep_risk
    total_dep_risk = min(total_dep_risk, 0.95)
    D = 1.0 - total_dep_risk
    D = max(0.0, min(D, 1.0))

    # ----- Life Risk Index (LRI) -----
    LRI = 0.40 * F + 0.25 * S + 0.20 * H + 0.15 * D
    LRI = max(0.0, min(LRI, 1.0))

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

    # ------------------------------------
    # Score Explanation Panel (contribution breakdown)
    # ------------------------------------
    st.markdown("### 🔍 Score Breakdown (how sub-factors contributed)")

    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Financial",
        "📈 Career",
        "🏥 Health",
        "👨‍👩‍👧 Dependency"
    ])

    # ---------- Financial ----------
    with tab1:
        emergency_contribution = 0.40 * emergency_coverage
        debt_contribution = 0.25 * debt_health
        emi_contribution = 0.20 * emi_health
        savings_contribution = 0.15 * savings_rate_clamped

        st.markdown("**Financial resilience factors**")
        st.write(f"Emergency Fund Coverage contribution: **{round(emergency_contribution*100,2)}%**")
        st.progress(emergency_coverage)

        st.write(f"Debt-to-Income health contribution: **{round(debt_contribution*100,2)}%**")
        st.progress(debt_health)

        st.write(f"EMI burden contribution: **{round(emi_contribution*100,2)}%**")
        st.progress(emi_health)

        st.write(f"Savings / Investment rate contribution: **{round(savings_contribution*100,2)}%**")
        st.progress(savings_rate_clamped)

        # show small computed numbers
        st.markdown(f"- Emergency months covered (incl. partial investments): **{round(emergency_months,2)} months**")
        st.markdown(f"- Debt-to-income ratio (annual): **{round(debt_to_income,2)}**")
        st.markdown(f"- EMI burden (monthly_emi / income): **{round(emi_burden,2)}**")
        st.markdown(f"- Monthly investment treated as partially liquid: **₹{round(effective_liquid_from_investment,2)}** per month equivalent")
        st.info(f"Final Financial Score = {round(F*100,2)}%")

    # ---------- Career ----------
    with tab2:
        edu_contribution = 0.30 * edu_score
        industry_contribution = 0.30 * ind_score
        upskill_contribution = 0.25 * upskill_score
        cert_contribution = 0.15 * cert_recency

        st.markdown("**Career stability factors**")
        st.write(f"Education contribution: **{round(edu_contribution*100,2)}%**")
        st.progress(edu_score)

        st.write(f"Industry demand contribution: **{round(industry_contribution*100,2)}%**")
        st.progress(ind_score)

        st.write(f"Upskilling contribution: **{round(upskill_contribution*100,2)}%**")
        st.progress(upskill_score)

        st.write(f"Certification recency contribution: **{round(cert_contribution*100,2)}%**")
        st.progress(cert_recency)

        st.markdown(f"- Age/experience multiplier applied: **{round(age_boost,2)}x**")
        st.markdown(f"- Job stability multiplier applied: **{round(js_factor,2)}x**")
        st.info(f"Final Career Score = {round(S*100,2)}%")

    # ---------- Health ----------
    with tab3:
        bmi_contribution = 0.50 * bmi_score
        chronic_contribution = 0.20 * (1 - chronic_penalty)
        smoking_contribution = 0.20 * (1 - smoking_penalty)
        insurance_contribution = 0.10 * (1 if insurance else 0.0)

        st.markdown("**Health resilience factors**")
        st.write(f"BMI contribution: **{round(bmi_contribution*100,2)}%**")
        st.progress(bmi_score)

        st.write(f"Chronic condition contribution: **{round(chronic_contribution*100,2)}%**")
        st.progress(1 - chronic_penalty)

        st.write(f"Smoking contribution: **{round(smoking_contribution*100,2)}%**")
        st.progress(1 - smoking_penalty)

        st.write(f"Health insurance protection (binary): **{round(insurance_contribution*100,2)}%**")
        st.progress(1.0 if insurance else 0.0)

        st.markdown(f"- Age health factor applied: **{round(age_factor,2)}x**")
        st.info(f"Final Health Score = {round(H*100,2)}%")

    # ---------- Dependency ----------
    with tab4:
        dependent_risk = dep_base_risk
        dependent_progress = 1.0 - dependent_risk
        single_income_progress = 1.0 - single_income_risk
        age_dep_progress = 1.0 - age_dep_risk
        earner_protection = 1.0 - earner_factor

        st.markdown("**Household dependency risk factors**")
        st.write(f"Dependents risk (contribution to risk): **{round(dependent_risk*100,2)}%**")
        st.progress(dependent_progress)

        st.write(f"Single income risk (contribution to risk): **{round(single_income_risk*100,2)}%**")
        st.progress(single_income_progress)

        st.write(f"Age dependency risk (contribution to risk): **{round(age_dep_risk*100,2)}%**")
        st.progress(age_dep_progress)

        st.write(f"Multiple earners protection: **{round(earner_protection*100,2)}%**")
        st.progress(earner_protection)

        st.markdown(f"- Number of earners used: **{number_of_earners}**")
        st.info(f"Final Dependency Score = {round(D*100,2)}%")

    # -------------------------
    # Enhanced recommendations with official docs
    # -------------------------
    st.markdown("### 🔎 Quick Recommendations (official guidance links included)")

    # Financial / budgeting
    if monthly_income < monthly_expense + monthly_investment + monthly_emi:
        st.info("Expenses + investments + EMIs exceed income — re-evaluate cashflow (reduce discretionary spend or investment commitments temporarily).")
        render_resources_for("financial_emergency")

    # Debt
    if debt_to_income > 0.5 or (monthly_emi / monthly_income if monthly_income>0 else 1.0) > 0.4:
        st.warning("High debt burden — consider restructuring, EMI negotiation or advisory.")
        render_resources_for("debt_management")

    # Emergency fund check
    savings_months_display = (total_savings + effective_liquid_from_investment * 6.0) / monthly_expense if monthly_expense > 0 else 0
    if savings_months_display < 3:
        st.info("Emergency fund shortfall — aim for at least 3 months (ideally 6) of expenses.")
        render_resources_for("financial_emergency")

    # Career / upskilling
    if upskilling_frequency < 2 or cert_recency < 0.5:
        st.info("Career: Consider enrolling in a short course or certification this year.")
        render_resources_for("upskilling")

    # BMI / Health
    if bmi > 25:
        st.info("Health: Small lifestyle changes can improve BMI and resilience; consider dietary guidance.")
        render_resources_for("health_bmi")
    if chronic_disease:
        st.info("Health: Manage chronic conditions proactively with your healthcare provider.")
        render_resources_for("health_bmi")

    # Insurance
    if not insurance:
        st.info("Consider health insurance to reduce catastrophic risk.")
        render_resources_for("health_insurance")

    # Smoking
    if smoking:
        st.info("Smoking increases health risk — seek cessation resources.")
        render_resources_for("smoking_cessation")

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
