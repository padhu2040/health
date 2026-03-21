import streamlit as st
from supabase import create_client, Client
import datetime

# ==========================================
# 1. PAGE CONFIGURATION & EXECUTIVE CSS
# ==========================================
st.set_page_config(page_title="Daily Bread | OS", page_icon="🌾", layout="wide")

# Injecting Executive Minimalist UI Standards
st.markdown("""
    <style>
    /* Clean Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #eaeaea;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    /* Status Colors */
    .status-success { color: #27ae60; font-weight: bold; }
    .status-risk { color: #c0392b; font-weight: bold; }
    /* Hide default header/footer for app-feel */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GLOBAL STATE INITIALIZATION (Crash Prevention)
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False
if "active_date" not in st.session_state:
    st.session_state.active_date = datetime.date.today()
if "total_macros" not in st.session_state:
    st.session_state.total_macros = {"calories": 0, "protein": 0, "carbs": 0}

# ==========================================
# 3. SUPABASE INITIALIZATION
# ==========================================
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("Database connection failed. Please check your secrets.")
    st.stop()

# ==========================================
# 4. ROUTER & NAVIGATION ARCHITECTURE
# ==========================================
# Define the pages
login_page = st.Page("pages/0_login.py", title="Authentication", icon="🔐")
dashboard_page = st.Page("pages/1_dashboard.py", title="Daily Dashboard", icon="📊", default=True)
discovery_page = st.Page("pages/2_discovery.py", title="AI Discovery", icon="🌱")
lab_page = st.Page("pages/3_lab.py", title="The Lab (Recipes)", icon="🧪")

# Routing Logic based on Auth State
if st.session_state.user is None:
    # Unauthenticated users only see the login page
    pg = st.navigation([login_page])
else:
    # Authenticated users get the full SaaS experience
    pg = st.navigation({
        "Planning": [dashboard_page, discovery_page],
        "Management": [lab_page]
    })

# Run the router
pg.run()
