import streamlit as st
from supabase import Client
import uuid

# Ensure Supabase client is available
if "supabase" not in st.session_state:
    try:
        from app import init_connection
        supabase: Client = init_connection()
    except Exception:
        st.error("Database connection lost. Please refresh.")
        st.stop()
else:
    supabase = st.session_state.supabase

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

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # ------------------------------------------
    # THE DEVELOPER BYPASS (GUEST MODE)
    # ------------------------------------------
    if st.button("🚀 Test Drive (Guest Mode)", type="primary", use_container_width=True):
        # Create a mock user object with a valid UUID format
        class MockUser:
            id = "11111111-1111-1111-1111-111111111111"
        
        st.session_state.user = MockUser()
        st.session_state.is_premium = True # Give the guest premium access
        
        # Trigger a full app rerun so the Router in app.py unlocks the pages
        st.rerun()
        
    st.markdown("<hr style='margin: 10px 0; opacity: 0.3'>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Log In", "Sign Up"])

    # ------------------------------------------
    # TAB 1: LOGIN
    # ------------------------------------------
    with tab1:
        with st.form("secure_user_login_v2"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Access Dashboard", use_container_width=True):
                try:
                    response = db.auth.sign_in_with_password({"email": email, "password": password})
                    if response.user:
                        st.session_state.user = response.user
                        
                        # Check premium status securely
                        profile_res = db.table("profiles").select("is_premium").eq("id", response.user.id).execute()
                        if profile_res.data:
                            st.session_state.is_premium = profile_res.data[0].get("is_premium", False)
                        else:
                            st.session_state.is_premium = False
                            
                        st.rerun() # Replaced switch_page with rerun
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")

    # ------------------------------------------
    # TAB 2: ONBOARDING
    # ------------------------------------------
    with tab2:
        with st.form("secure_user_signup_v2"):
            new_email = st.text_input("Email Address*")
            new_password = st.text_input("Password*", type="password")
            persona = st.selectbox("Primary Cooking Style", ["Locavore / Seasonal", "Biohacker / Macro-Focused"])
            weight = st.number_input("Current Weight (kg)", value=70)
            goal = st.selectbox("Primary Goal", ["Maintain Health", "Lose Weight"])
            
            if st.form_submit_button("Create Account", use_container_width=True):
                try:
                    auth_response = db.auth.sign_up({"email": new_email, "password": new_password})
                    if auth_response.user:
                        user_id = auth_response.user.id
                        db.table("profiles").upsert({
                            "id": user_id,
                            "is_premium": False,
                            "preferences": {"persona": persona, "weight_kg": weight, "goal": goal}
                        }).execute()
                        st.session_state.user = auth_response.user
                        st.session_state.is_premium = False
                        st.rerun() # Replaced switch_page with rerun
                except Exception as e:
                    st.error(f"Signup failed: {str(e)}")
