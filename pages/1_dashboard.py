import streamlit as st
import datetime
import google.generativeai as genai
import json
import re

# ==========================================
# 1. THE GATEKEEPER & SETUP
# ==========================================
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔒 Secure environment. Please log in.")
    st.stop()

if "supabase" not in st.session_state:
    try:
        from app import init_connection
        supabase = init_connection()
    except Exception:
        st.error("Database connection lost. Please refresh.")
        st.stop()
else:
    supabase = st.session_state.supabase

user_id = st.session_state.user.id

# Initialize AI
try:
    genai.configure(api_key=st.secrets["gcp"]["gemini_api_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    st.error("AI Engine offline. Check GCP secrets.")
    st.stop()

# ==========================================
# 2. STATE MANAGEMENT FOR AI
# ==========================================
# We must store AI results in session state so they don't vanish when a user interacts with the page
if "current_recommendations" not in st.session_state:
    st.session_state.current_recommendations = None

def clean_json(raw_text):
    text = raw_text.strip()
    if text.startswith("
http://googleusercontent.com/immersive_entry_chip/0
http://googleusercontent.com/immersive_entry_chip/1
http://googleusercontent.com/immersive_entry_chip/2

### Architectural Upgrades Explained:

1. **Clinical Targeting Prompt:** Look at the `prompt` string sent to Gemini. We explicitly instruct the AI to act as a *clinical nutritionist* and justify *why* the recipe fits their specific focus (e.g., explaining why a specific fiber source was chosen for Fatty Liver support).
2. **Session State Retention:** Notice the `st.session_state.current_recommendations` block. In standard Streamlit, clicking the "Assign to" dropdown inside a generated recipe would cause the page to refresh and delete the AI's output instantly. Caching it in the session state anchors the data to the screen until the user explicitly hits "Accept & Add".
3. **The `instructions` Array:** The AI now outputs a clean array of strings for the steps, which we render as an ordered list using `enumerate()` in the UI. 

Run the SQL command, commit this code, and let me know how the menu generation feels.
