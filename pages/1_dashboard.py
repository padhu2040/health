import streamlit as st
import datetime

# ==========================================
# 1. THE GATEKEEPER
# ==========================================
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔒 Secure environment. Please log in to access your dashboard.")
    st.stop()

# Ensure Supabase client is available
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

# ==========================================
# 2. DATA FETCHING & DYNAMIC ENGINE
# ==========================================
@st.cache_data(ttl=600) # Cache for 10 minutes to reduce database load
def fetch_user_profile(uid):
    res = supabase.table("profiles").select("preferences, is_premium").eq("id", uid).execute()
    if res.data:
        return res.data[0]
    return {"preferences": {}, "is_premium": False}

profile_data = fetch_user_profile(user_id)
prefs = profile_data.get("preferences", {})
persona = prefs.get("persona", "Locavore")
weight = prefs.get("weight_kg", 70)
goal = prefs.get("goal", "Maintain Health")

# --- Macro Math Engine ---
# A basic TDEE (Total Daily Energy Expenditure) calculation 
base_calories = weight * 24 * 1.2 # BMR * sedentary multiplier
if goal == "Lose Weight":
    target_calories = base_calories - 300
elif goal == "Build Muscle":
    target_calories = base_calories + 300
else:
    target_calories = base_calories

# Protein standard: ~1.8g per kg for active/building, 1.2g for maintenance
target_protein = weight * 1.8 if goal == "Build Muscle" else weight * 1.2
target_carbs = (target_calories * 0.45) / 4 # 45% of diet from carbs

# ==========================================
# 3. GLOBAL STATE SYNCHRONIZATION
# ==========================================
def update_date():
    st.session_state.active_date = st.session_state.date_picker

# ==========================================
# 4. EXECUTIVE UI RENDER
# ==========================================
col_title, col_date = st.columns([3, 1])
with col_title:
    st.title("Command Center")
    st.markdown(f"<p style='color: #7f8c8d;'>Operating Mode: <b>{persona}</b> | Target: <b>{goal}</b></p>", unsafe_allow_html=True)

with col_date:
    st.date_input(
        "Active Date", 
        value=st.session_state.active_date, 
        key="date_picker", 
        on_change=update_date
    )

st.write("---")

# --- KPI CARDS ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Daily Energy Target", f"{int(target_calories)} kcal")
with col2:
    st.metric("Protein Goal", f"{int(target_protein)}g")
with col3:
    st.metric("Carb Allowance", f"{int(target_carbs)}g")

st.write("---")

# ==========================================
# 5. MEAL SLOTS & DATABASE QUERY
# ==========================================
st.subheader(f"Meal Plan for {st.session_state.active_date.strftime('%B %d, %Y')}")

# Fetch today's meals using strict Multi-Tenancy guardrails
meals_res = supabase.table("daily_plans").select(
    "meal_slot, recipes(title, prep_time_mins)"
).eq("user_id", user_id).eq("plan_date", str(st.session_state.active_date)).execute()

planned_meals = meals_res.data if meals_res.data else []

# Render the meal slots (Empty State vs Filled State)
slots = ["Breakfast", "Lunch", "Dinner", "Snack"]

for slot in slots:
    # Find if a meal is booked for this slot
    meal = next((m for m in planned_meals if m["meal_slot"] == slot), None)
    
    with st.container():
        st.markdown(f"**{slot}**")
        if meal and meal.get("recipes"):
            recipe = meal["recipes"]
            st.info(f"🍽️ **{recipe['title']}** (Prep: {recipe['prep_time_mins']} mins)")
        else:
            # Empty state UI
            st.markdown("<p style='color: #bdc3c7; font-style: italic;'>No meal planned.</p>", unsafe_allow_html=True)
            if st.button(f"+ Add {slot}", key=f"add_{slot}"):
                st.switch_page("pages/2_discovery.py")
        st.write("") # Spacing

st.write("---")

# ==========================================
# 6. PRODUCT-LED GROWTH (The Paywall)
# ==========================================
st.subheader("Fulfillment")

if st.button("🛒 Generate Instacart Grocery List", use_container_width=True):
    if st.session_state.is_premium:
        st.success("Compiling your list... (Integration logic goes here)")
    else:
        st.warning("🌟 **Premium Feature!** Upgrade your account to automatically send your weekly meal plan ingredients directly to Instacart or output a sorted PDF.")
        st.button("Upgrade Now for $4.99/mo (Razorpay)", type="primary")
