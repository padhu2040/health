import streamlit as st
from supabase import Client
import json

# Ensure Supabase client is available from the master router
if "supabase" not in st.session_state:
    try:
        from app import init_connection
        supabase: Client = init_connection()
    except Exception:
        st.error("Database connection lost. Please refresh the app.")
        st.stop()
else:
    supabase = st.session_state.supabase # Assuming you stash it in session_state, or just re-import

# Re-initialize for safety if running directly
@st.cache_resource
def get_db():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    from supabase import create_client
    return create_client(url, key)

db = get_db()

# ==========================================
# UI: EXECUTIVE MINIMALIST LOGIN
# ==========================================
st.markdown("<h1 style='text-align: center;'>Welcome to Daily Bread</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7f8c8d;'>Your personal culinary operating system.</p>", unsafe_allow_html=True)

# Create centered columns for a clean form layout
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    tab1, tab2 = st.tabs(["Log In", "Sign Up & Onboard"])

    # ------------------------------------------
    # TAB 1: EXISTING USER LOGIN
    # ------------------------------------------
    with tab1:
        with st.form("secure_user_login_v1"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Access Dashboard", use_container_width=True)

            if submitted:
                try:
                    # Authenticate with Supabase
                    response = db.auth.sign_in_with_password({"email": email, "password": password})
                    if response.user:
                        st.session_state.user = response.user
                        
                        # Fetch premium status from profiles
                        profile_res = db.table("profiles").select("is_premium").eq("id", response.user.id).execute()
                        if profile_res.data:
                            st.session_state.is_premium = profile_res.data[0].get("is_premium", False)
                        
                        st.success("Authentication successful. Routing...")
                        st.switch_page("pages/1_dashboard.py")
                except Exception as e:
                    st.error(f"Login failed: Invalid credentials or network error.")

    # ------------------------------------------
    # TAB 2: NEW USER ONBOARDING (Progressive Profiling)
    # ------------------------------------------
    with tab2:
        with st.form("secure_user_signup_v1"):
            st.subheader("1. Account Details")
            new_email = st.text_input("Email Address*")
            new_password = st.text_input("Password*", type="password", help="Minimum 6 characters")
            
            st.markdown("---")
            st.subheader("2. Your Dietary Profile")
            
            # The Locavore persona is default, but we offer choices
            persona = st.selectbox("Primary Cooking Style", 
                                   ["Locavore / Seasonal", "Biohacker / Macro-Focused", "Time-Starved Executive", "Budget Maximizer"])
            
            col_a, col_b = st.columns(2)
            with col_a:
                weight = st.number_input("Current Weight (kg)", min_value=30, max_value=300, value=70)
            with col_b:
                goal = st.selectbox("Primary Goal", ["Maintain Health", "Lose Weight", "Build Muscle"])

            allergies = st.multiselect("Any strict dietary exclusions?", ["Gluten", "Dairy", "Nuts", "Shellfish", "Soy"])

            signup_submitted = st.form_submit_button("Create Account & Setup Profile", use_container_width=True)

            if signup_submitted:
                try:
                    # 1. Create the Auth User
                    auth_response = db.auth.sign_up({"email": new_email, "password": new_password})
                    
                    if auth_response.user:
                        user_id = auth_response.user.id
                        
                        # 2. Construct the JSONB preferences payload
                        preferences_payload = {
                            "persona": persona,
                            "weight_kg": weight,
                            "goal": goal,
                            "allergies": allergies
                        }

                        # 3. Create the Public Profile record securely linking to the Auth ID
                        db.table("profiles").upsert({
                            "id": user_id,
                            "is_premium": False,
                            "preferences": preferences_payload
                        }).execute()

                        # 4. Update Session State and Route
                        st.session_state.user = auth_response.user
                        st.session_state.is_premium = False
                        
                        st.success("Profile created! Routing to your new dashboard...")
                        st.switch_page("pages/1_dashboard.py")
                        
                except Exception as e:
                    # Catch the Supabase 400 error (e.g., user already exists)
                    if "User already registered" in str(e):
                         st.error("An account with this email already exists. Please log in.")
                    else:
                         st.error(f"Signup failed. Please try again.")

# Google/Apple OAuth Placeholder 
st.markdown("<br><p style='text-align: center; font-size: 0.8em; color: #bdc3c7;'>OAuth integrations (Google/Apple) will be active in production.</p>", unsafe_allow_html=True)
