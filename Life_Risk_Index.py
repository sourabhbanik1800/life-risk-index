import streamlit as st
import numpy as np

    # Your existing dashboard code starts here

st.set_page_config(page_title="Life Risk Index", page_icon="📊", layout="wide")

# ---------------------------------------------------
# UI
# ---------------------------------------------------
st.markdown("""
<style>

/* Main App Background */
[data-testid="stAppViewContainer"]{
background: linear-gradient(135deg,#F8FBFF,#EEF3F9);
font-family: 'Inter', sans-serif;
}

/* Remove default padding to use full screen */
.block-container{
padding-top:2rem;
padding-left:3rem;
padding-right:3rem;
padding-bottom:2rem;
max-width:1400px;
}

/* Dashboard Title */
.main-title{
font-size:54px;
font-weight:800;
text-align:center;
color:#0A2540;
margin-bottom:10px;
}

.subtitle{
text-align:center;
color:#6B7280;
font-size:18px;
margin-bottom:40px;
}

/* Section Container */
.section-card{
background:white;
padding:30px;
border-radius:20px;
box-shadow:0px 10px 30px rgba(0,0,0,0.06);
margin-bottom:30px;
}

/* Main Score Card */
.metric-card{
background:linear-gradient(135deg,#3B82F6,#06B6D4);
color:white;
font-size:65px;
font-weight:900;
text-align:center;
padding:60px;
border-radius:25px;
box-shadow:0px 15px 40px rgba(0,0,0,0.15);
}

/* Breakdown Cards */
.break-card{
background:white;
padding:25px;
border-radius:18px;
text-align:center;
box-shadow:0px 6px 20px rgba(0,0,0,0.06);
transition:0.3s;
}

.break-card:hover{
transform:translateY(-5px);
box-shadow:0px 12px 30px rgba(0,0,0,0.12);
}

.break-title{
font-size:14px;
color:#6B7280;
margin-bottom:6px;
}

.break-score{
font-size:32px;
font-weight:800;
color:#0A2540;
}

/* Recommendation Cards */
.recommend-card{
background:#F8FAFC;
padding:18px;
border-radius:14px;
margin-bottom:12px;
border-left:6px solid #3B82F6;
font-size:15px;
color:#1E293B;
}

/* Sidebar */
[data-testid="stSidebar"]{
background:white;
border-right:1px solid #E5E7EB;
}

/* Buttons */
.stButton>button{
background:linear-gradient(135deg,#3B82F6,#06B6D4);
color:white;
border:none;
padding:10px 20px;
border-radius:10px;
font-weight:600;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 class='main-title'>Life Risk Index Dashboard</h1>
<p class='subtitle'>Analyze your financial, career, health, and dependency risk in one intelligent score</p>
""", unsafe_allow_html=True)


# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------
st.sidebar.header("📥 Enter Your Information")

monthly_income = st.sidebar.number_input("Monthly Income (₹)", value=None)
monthly_expense = st.sidebar.number_input("Monthly Expenses (₹)", value=None)
total_savings = st.sidebar.number_input("Total Savings (₹)", value=None)
total_debt = st.sidebar.number_input("Total Debt (₹)", value=None)
monthly_emi = st.sidebar.number_input("Monthly EMI (₹)", value=None)

education_level = st.sidebar.selectbox("Education Level", ["High School","Graduate","Post Graduate","Professional"])
industry_demand = st.sidebar.selectbox("Industry Demand", ["Low","Medium","High"])
upskilling_frequency = st.sidebar.slider("Upskilling per year", 0, 6, 1)
years_since_cert = st.sidebar.slider("Years since certification", 0, 10, 1)

weight = st.sidebar.number_input("Weight (kg)", value=None)
height_cm = st.sidebar.number_input("Height (cm)", value=None)
chronic_disease = st.sidebar.checkbox("Chronic Disease")
smoking = st.sidebar.checkbox("Smoker")
insurance = st.sidebar.checkbox("Health Insurance")
age = st.sidebar.slider("Age", 18, 70, 25)

dependents = st.sidebar.slider("Dependents", 0, 6, 0)
single_income = st.sidebar.checkbox("Single Income Household")

calculate = st.sidebar.button("🚀 Calculate Life Risk Index")

# ---------------------------------------------------
# CALCULATION
# ---------------------------------------------------
if calculate:

    monthly_income = monthly_income or 0
    monthly_expense = monthly_expense or 0
    total_savings = total_savings or 0
    total_debt = total_debt or 0
    monthly_emi = monthly_emi or 0
    weight = weight or 0
    height_cm = height_cm or 0

    savings_ratio = total_savings/(monthly_expense*6) if monthly_expense>0 else 0
    debt_income_ratio = total_debt/(monthly_income*12) if monthly_income>0 else 0
    emi_ratio = monthly_emi/monthly_income if monthly_income>0 else 0

    F = 0.5*min(savings_ratio,1)+0.3*(1-min(debt_income_ratio,1))+0.2*(1-min(emi_ratio,1))

    edu_map={"High School":1,"Graduate":2,"Post Graduate":3,"Professional":4}
    ind_map={"Low":1,"Medium":2,"High":3}
    S=0.25*(edu_map[education_level]/4)+0.30*(ind_map[industry_demand]/3)+0.25*min(upskilling_frequency/4,1)+0.20*(1-min(years_since_cert/5,1))

    height_m=height_cm/100 if height_cm>0 else 1
    bmi=weight/(height_m**2) if height_cm>0 else 0
    bmi_score=1 if 18.5<=bmi<=24.9 else 0.6
    H=(bmi_score+(1-int(chronic_disease))+(1-int(smoking))+int(insurance))/4

    dependency_factor=min(dependents/4,1)
    D=0.7*(1-dependency_factor)+0.3*(1-int(single_income))

    LRI=0.40*F+0.25*S+0.20*H+0.15*D

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📊 Life Risk Score")
    st.markdown(f'<div class="metric-card">{round(LRI*100,2)}</div>', unsafe_allow_html=True)

    # -----------------------------
    # BREAKDOWN BACK AGAIN
    # -----------------------------
    st.markdown("### 🔎 Score Breakdown")
    c1,c2,c3,c4=st.columns(4)
    c1.markdown(f'<div class="break-card"><div class="break-title">💰 Financial</div><div class="break-score">{round(F*100,1)}</div></div>',unsafe_allow_html=True)
    c2.markdown(f'<div class="break-card"><div class="break-title">📈 Career</div><div class="break-score">{round(S*100,1)}</div></div>',unsafe_allow_html=True)
    c3.markdown(f'<div class="break-card"><div class="break-title">🏥 Health</div><div class="break-score">{round(H*100,1)}</div></div>',unsafe_allow_html=True)
    c4.markdown(f'<div class="break-card"><div class="break-title">👨‍👩‍👧 Dependency</div><div class="break-score">{round(D*100,1)}</div></div>',unsafe_allow_html=True)

    # -----------------------------
    # RECOMMENDATIONS WITH LINKS
    # -----------------------------
    st.markdown("### 📌 Evidence-Based Recommendations")

    if monthly_income < monthly_expense:
        st.markdown('<div class="recommend-card">⚠️ Expenses exceed income. <a href="https://www.rbi.org.in/FinancialEducation/content/I%20Can%20Do_RBI.pdf" target="_blank">RBI Guide</a></div>', unsafe_allow_html=True)

    if debt_income_ratio > 0.5:
        st.markdown('<div class="recommend-card">⚠️ High Debt Ratio. <a href="https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf" target="_blank">SEBI Guide</a></div>', unsafe_allow_html=True)

    if savings_ratio < 1:
        st.markdown('<div class="recommend-card">⚠️ Build emergency fund. <a href="https://investor.sebi.gov.in/pdf/downloadable-documents/Financial%20Education%20Booklet%20-%20English.pdf" target="_blank">SEBI Guide</a></div>', unsafe_allow_html=True)

    if upskilling_frequency < 2:
        st.markdown('<div class="recommend-card">⚠️ Increase upskilling. <a href="https://www3.weforum.org/docs/WEF_Future_of_Jobs_2023.pdf" target="_blank">WEF Report</a></div>', unsafe_allow_html=True)

    if bmi > 25:
        st.markdown('<div class="recommend-card">⚠️ Maintain healthy BMI. <a href="https://www.who.int/health-topics/obesity" target="_blank">WHO Guide</a></div>', unsafe_allow_html=True)

    if not insurance:
        st.markdown('<div class="recommend-card">⚠️ Obtain health insurance. <a href="https://www.insuranceinstituteofindia.com/documents/6454111/5517dc58-2716-4b6d-afed-ab1fc703a79d" target="_blank">Insurance Guide</a></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)










