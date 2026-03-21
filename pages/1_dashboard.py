import streamlit as st
import datetime
import google.generativeai as genai
import json

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

# Initialize AI Client (Model is assigned later with fallback logic)
try:
    genai.configure(api_key=st.secrets["gcp"]["gemini_api_key"])
except Exception:
    st.error("AI Engine offline. Check GCP secrets.")
    st.stop()

# ==========================================
# 2. STATE MANAGEMENT FOR AI
# ==========================================
if "current_recommendations" not in st.session_state:
    st.session_state.current_recommendations = None

def clean_json(raw_text):
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def update_active_date():
    st.session_state.active_date = st.session_state.date_picker

# ==========================================
# 3. EXECUTIVE UI & KPI HEADER
# ==========================================
col_title, col_date = st.columns([3, 1])
with col_title:
    st.title("Command Center")
with col_date:
    st.date_input(
        "Active Date", 
        value=st.session_state.active_date, 
        key="date_picker", 
        on_change=update_active_date
    )

st.write("---")

# ==========================================
# 4. THE AI RECOMMENDATION ENGINE
# ==========================================
st.subheader("🧠 The AI Chef's Table")
st.markdown("Select your clinical, dietary, and cultural preferences.")

# Row 1 of Preferences
row1_c1, row1_c2, row1_c3 = st.columns(3)
with row1_c1:
    health_focus = st.selectbox(
        "Clinical Focus", 
        ["Maintain Health", "Weight Loss (Caloric Deficit)", "Reduce Cholesterol", "Fatty Liver Support", "Blood Sugar Control"]
    )
with row1_c2:
    diet_type = st.selectbox(
        "Dietary Protocol", 
        ["Locavore / Seasonal", "Mediterranean", "Keto / Ultra Low Carb", "Vegan / Plant-Based"]
    )
with row1_c3:
    cuisine = st.selectbox(
        "Cuisine Style", 
        ["Authentic South Indian", "Global / No Preference", "North Indian", "Pan-Asian", "Continental"]
    )

# Row 2 of Preferences
row2_c1, row2_c2, row2_c3 = st.columns(3)
with row2_c1:
    prep_time = st.selectbox(
        "Maximum Prep Time", 
        ["Under 15 mins", "Under 30 mins", "Weekend Project (60m+)"]
    )
with row2_c2:
    language = st.selectbox(
        "Output Language", 
        ["English", "Tamil (தமிழ்)"]
    )
with row2_c3:
    st.write("") # Spacer to align the button
    generate_btn = st.button("Generate Tailored Menu", type="primary", use_container_width=True)

if generate_btn:
    with st.spinner(f"Architecting {cuisine} recipes in {language}..."):
        prompt = f"""
        You are a clinical nutritionist and an executive chef. Generate 2 highly tailored meal recommendations.
        Health Focus: {health_focus}.
        Dietary Protocol: {diet_type}.
        Cuisine Style: {cuisine}.
        Max Prep Time: {prep_time}.
        
        CRITICAL LANGUAGE RULE: You MUST write the ENTIRE response (including the title, description, ingredient items, and instructions) natively in {language}. Do NOT use English if Tamil is selected.
        
        Return ONLY a valid JSON array of objects. No markdown formatting outside the JSON. Structure:
        [
          {{
            "title": "String",
            "description": "Short explanation of health benefits",
            "prep_time_mins": Integer,
            "macros": {{"calories": Integer, "protein": Integer, "carbs": Integer, "fat": Integer}},
            "ingredients": [{{"item": "String", "amount": Number, "unit": "String"}}],
            "instructions": ["Step 1", "Step 2", "Step 3"]
          }}
        ]
        """
        try:
            # Model Fallback Architecture to prevent 404 errors
            try:
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                response = model.generate_content(prompt)
            except Exception:
                model = genai.GenerativeModel('gemini-pro') # Universally accepted fallback
                response = model.generate_content(prompt)
                
            st.session_state.current_recommendations = json.loads(clean_json(response.text))
        except Exception as e:
            st.error(f"AI Generation failed: {str(e)}")

# Display Recommendations if they exist
if st.session_state.current_recommendations:
    st.markdown("### Suggested Meals")
    for idx, rec in enumerate(st.session_state.current_recommendations):
        with st.expander(f"✨ {rec.get('title', 'Recipe')} ({rec.get('prep_time_mins', 0)} mins)"):
            st.markdown(f"*{rec.get('description', '')}*")
            
            # Macros Grid
            mac = rec.get('macros', {})
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Calories", mac.get('calories', 0))
            m2.metric("Protein", f"{mac.get('protein', 0)}g")
            m3.metric("Carbs", f"{mac.get('carbs', 0)}g")
            m4.metric("Fat", f"{mac.get('fat', 0)}g")
            
            # Details Grid
            col_ing, col_inst = st.columns(2)
            with col_ing:
                st.markdown("**Ingredients**")
                for ing in rec.get('ingredients', []):
                    st.write(f"- {ing.get('amount', '')} {ing.get('unit', '')} {ing.get('item', '')}")
            with col_inst:
                st.markdown("**How to Prepare**")
                for step_num, step in enumerate(rec.get('instructions', []), 1):
                    st.write(f"{step_num}. {step}")
            
            st.write("---")
            
            # Save Logic
            slot = st.selectbox("Assign to:", ["Breakfast", "Lunch", "Dinner", "Snack"], key=f"slot_{idx}")
            if st.button("Accept & Add to Today's Plan", key=f"save_{idx}", type="secondary"):
                # 1. Save to Recipes
                recipe_payload = {
                    "user_id": user_id,
                    "title": rec.get("title", "Unknown"),
                    "description": rec.get("description", ""),
                    "prep_time_mins": rec.get("prep_time_mins", 0),
                    "macros": rec.get("macros", {}),
                    "ingredients": rec.get("ingredients", []),
                    "instructions": rec.get("instructions", []),
                    "is_custom": False
                }
                res = supabase.table("recipes").insert(recipe_payload).execute()
                new_recipe_id = res.data[0]["id"]
                
                # 2. Map to Daily Plan
                plan_payload = {
                    "user_id": user_id,
                    "plan_date": str(st.session_state.active_date),
                    "meal_slot": slot,
                    "recipe_id": new_recipe_id
                }
                supabase.table("daily_plans").insert(plan_payload).execute()
                
                st.success("Added to your schedule!")
                st.session_state.current_recommendations = None # Clear after saving
                st.rerun()

st.write("---")

# ==========================================
# 5. TODAY's ITINERARY (Read from Database)
# ==========================================
st.subheader(f"Scheduled for {st.session_state.active_date.strftime('%B %d, %Y')}")

meals_res = supabase.table("daily_plans").select(
    "meal_slot, recipes(title, prep_time_mins)"
).eq("user_id", user_id).eq("plan_date", str(st.session_state.active_date)).execute()

planned_meals = meals_res.data if meals_res.data else []
slots = ["Breakfast", "Lunch", "Dinner", "Snack"]

for slot in slots:
    meal = next((m for m in planned_meals if m["meal_slot"] == slot), None)
    with st.container():
        if meal and meal.get("recipes"):
            recipe = meal["recipes"]
            st.info(f"🍽️ **{slot}**: {recipe['title']} (Prep: {recipe['prep_time_mins']} mins)")
        else:
            st.markdown(f"<p style='color: #bdc3c7;'>{slot}: Open</p>", unsafe_allow_html=True)
