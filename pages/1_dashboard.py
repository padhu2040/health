import streamlit as st
import datetime
import google.generativeai as genai
import json

# ==========================================
# 1. SETUP & SILENT AUTHENTICATION
# ==========================================
if "user" not in st.session_state or st.session_state.user is None:
    user_id = "11111111-1111-1111-1111-111111111111"
    is_guest = True
else:
    user_id = st.session_state.user.id
    is_guest = False

if "supabase" not in st.session_state:
    try:
        from app import init_connection
        supabase = init_connection()
    except Exception:
        supabase = None
else:
    supabase = st.session_state.supabase

try:
    genai.configure(api_key=st.secrets["gcp"]["gemini_api_key"])
except Exception:
    st.error("Engine offline. Check configuration.")
    st.stop()

# ==========================================
# 2. STATE MANAGEMENT & CSS
# ==========================================
if "current_recommendations" not in st.session_state:
    st.session_state.current_recommendations = None
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "Full Day" 
if "active_date" not in st.session_state:
    st.session_state.active_date = datetime.date.today()

def clean_json(raw_text):
    text = str(raw_text).strip()
    text = text.replace("```json", "")
    text = text.replace("```", "")
    return text.strip()

def update_active_date():
    st.session_state.active_date = st.session_state.date_picker

st.markdown("""
<style>
    .flat-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 20px;
        margin-bottom: 12px;
        border-radius: 2px;
    }
    .flat-tag {
        font-size: 0.75em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #777;
        margin-bottom: 4px;
    }
    .flat-title {
        font-size: 1.1em;
        font-weight: 600;
        color: #111;
        margin-bottom: 6px;
        margin-top: 0px;
    }
    .flat-desc {
        font-size: 0.9em;
        color: #444;
        margin-bottom: 16px;
        line-height: 1.5;
    }
    .flat-macros {
        font-size: 0.8em;
        color: #888;
        border-top: 1px solid #eee;
        padding-top: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. MINIMALIST UI HEADER
# ==========================================
st.markdown("<h2 style='font-weight: 400; color: #111; margin-bottom: 0px;'>Menu Architect</h2>", unsafe_allow_html=True)
if is_guest:
    st.markdown("<p style='color: #888; font-size: 0.9em;'>Operating in Guest Mode. <a href='/login' target='_self'>Log in</a> to save plans.</p>", unsafe_allow_html=True)
else:
    st.markdown("<p style='color: #888; font-size: 0.9em;'>Design your nutritional itinerary.</p>", unsafe_allow_html=True)

# ==========================================
# 4. CONFIGURATION COMPONENT
# ==========================================
planning_mode = st.radio("Mode", ["Full Day Itinerary", "Specific Meal"], horizontal=True, label_visibility="collapsed")

target_meal = None
if planning_mode == "Specific Meal":
    target_meal = st.selectbox("Select Meal", ["Breakfast", "Mid-Morning Snack", "Lunch", "Evening Snack / Soup", "Dinner", "Healthy Salad"], label_visibility="collapsed")

with st.expander("Filter Preferences", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        health_focus = st.selectbox("Focus", ["Maintain Health", "Weight Loss", "Reduce Cholesterol", "Fatty Liver Support", "Blood Sugar Control", "Kids Nutrition"])
        diet_type = st.selectbox("Protocol", ["Seasonal / Local", "Mediterranean", "Keto / Low Carb", "Plant-Based"])
    with col2:
        cuisine = st.selectbox("Cuisine", ["South Indian", "Global", "North Indian", "Pan-Asian", "Continental"])
        language = st.selectbox("Language", ["English", "Tanglish (Tamil + English)", "Pure Tamil"])

generate_btn = st.button("Generate Plan", type="primary", use_container_width=True)

# ==========================================
# 5. AI ENGINE
# ==========================================
if generate_btn:
    st.session_state.current_mode = planning_mode 
    
    if planning_mode == "Full Day Itinerary":
        task_instruction = "Generate a FULL DAY meal plan overview. Include exactly 5 meals: Breakfast, Mid-Morning Snack, Lunch, Evening Snack, Dinner."
    else:
        task_instruction = f"Do NOT generate a full day plan. I only need options for: {target_meal}. Generate exactly 5 distinct, creative options for this specific meal type so the user can choose their favorite."

    with st.spinner("Compiling..."):
        prompt = f"""
        You are a minimalist, high-end culinary nutritionist.
        Focus: {health_focus}. Protocol: {diet_type}. Cuisine: {cuisine}.
        
        {task_instruction}
        
        CRITICAL LANGUAGE RULES: 
        1. If language is 'Tanglish (Tamil + English)': Use a natural, modern mix of proper Tamil script and English words. 
        2. If language is 'Pure Tamil': Write strictly in formal Tamil script.
        3. If language is 'English': Use standard English.
        4. Always explicitly name specific native fruits/vegetables instead of generic terms.
        
        Return ONLY a valid JSON object matching this exact structure:
        {{
          "daily_plan": [
            {{
              "slot": "String (e.g. Breakfast or Target Meal)",
              "category": "String (e.g. Traditional, Quick Prep)",
              "title": "String",
              "description": "String (Short nutritional rationale)",
              "macros": {{"calories": Integer, "protein": Integer, "carbs": Integer, "fat": Integer}}
            }}
          ]
        }}
        """
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            chosen_model = next((m for m in available_models if 'flash' in m), available_models[0])
            model = genai.GenerativeModel(chosen_model)
            response = model.generate_content(prompt)
            st.session_state.current_recommendations = json.loads(clean_json(response.text))
        except Exception as e:
            st.error("Generation failed. Please try again.")

# ==========================================
# 6. RESULTS & PERSISTENCE
# ==========================================
if st.session_state.current_recommendations:
    plan = st.session_state.current_recommendations.get("daily_plan", [])
    st.write("---")
    st.markdown(f"<h3 style='font-weight: 400;'>Proposed {st.session_state.current_mode}</h3>", unsafe_allow_html=True)
    
    for idx, item in enumerate(plan):
        st.markdown(f"""
        <div class="flat-card">
            <div class="flat-tag">{item.get('slot', '')} &bull; {item.get('category', '')}</div>
            <h4 class="flat-title">{item.get('title', 'Dish')}</h4>
            <div class="flat-desc">{item.get('description', '')}</div>
            <div class="flat-macros">
                Cals: {item.get('macros', {}).get('calories', 0)} &bull; 
                Pro: {item.get('macros', {}).get('protein', 0)}g &bull; 
                Carb: {item.get('macros', {}).get('carbs', 0)}g &bull; 
                Fat: {item.get('macros', {}).get('fat', 0)}g
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.current_mode == "Specific Meal":
            if st.button(f"Select Option {idx+1}", key=f"save_{idx}", use_container_width=True):
                if is_guest:
                    st.toast("Saved to local session. Log in to persist data.")
                    st.session_state.current_recommendations = None
                    st.rerun()
                elif supabase:
                    res = supabase.table("recipes").insert({
                        "user_id": user_id, "title": item.get("title", ""), "description": item.get("description", ""),
                        "prep_time_mins": 0, "macros": item.get("macros", {}), "ingredients": [], "instructions": [], "is_custom": False
                    }).execute()
                    supabase.table("daily_plans").insert({
                        "user_id": user_id, "plan_date": str(st.session_state.active_date), "meal_slot": item.get("slot", "Snack"), "recipe_id": res.data[0]["id"]
                    }).execute()
                    st.toast("Saved to database.")
                    st.session_state.current_recommendations = None
                    st.rerun()

    if st.session_state.current_mode == "Full Day Itinerary":
        st.write("")
        if st.button("Save Full Itinerary", type="primary", use_container_width=True):
            if is_guest:
                st.toast("Itinerary saved to local session. Log in to persist.")
                st.session_state.current_recommendations = None
                st.rerun()
            elif supabase:
                for item in plan:
                    res = supabase.table("recipes").insert({
                        "user_id": user_id, "title": item.get("title", ""), "description": item.get("description", ""),
                        "prep_time_mins": 0, "macros": item.get("macros", {}), "ingredients": [], "instructions": [], "is_custom": False
                    }).execute()
                    supabase.table("daily_plans").insert({
                        "user_id": user_id, "plan_date": str(st.session_state.active_date), "meal_slot": item.get("slot", "Snack"), "recipe_id": res.data[0]["id"]
                    }).execute()
                st.toast("Itinerary saved.")
                st.session_state.current_recommendations = None
                st.rerun()

# ==========================================
# 7. AGENDA VIEWER
# ==========================================
if not is_guest and supabase:
    st.write("---")
    col_a, col_b = st.columns([2,1])
    with col_a:
        st.markdown(f"<h3 style='font-weight: 400; font-size: 1.1em;'>Agenda for {st.session_state.active_date.strftime('%b %d, %Y')}</h3>", unsafe_allow_html=True)
    with col_b:
        st.date_input("Change Date", value=st.session_state.active_date, key="date_picker", on_change=update_active_date, label_visibility="collapsed")

    meals_res = supabase.table("daily_plans").select("meal_slot, recipes(title)").eq("user_id", user_id).eq("plan_date", str(st.session_state.active_date)).execute()
    planned_meals = meals_res.data if meals_res.data else []

    if not planned_meals:
        st.markdown("<p style='color: #888; font-size: 0.9em;'>No meals scheduled.</p>", unsafe_allow_html=True)
    else:
        for meal in planned_meals:
            if meal and meal.get("recipes"):
                st.markdown(f"<div style='border-bottom: 1px solid #eee; padding: 8px 0;'><span style='color: #888; font-size: 0.8em; text-transform: uppercase;'>{meal.get('meal_slot')}</span><br><span style='font-weight: 500; color: #111;'>{meal['recipes']['title']}</span></div>", unsafe_allow_html=True)
