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
    is_guest = (user_id == "11111111-1111-1111-1111-111111111111")

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
        margin-bottom: 8px;
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
    .action-container {
        margin-bottom: 24px;
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
        language = st.selectbox("Language", ["English", "Pure Tamil", "Tanglish (Tamil + English)"])

generate_btn = st.button("Generate Plan", type="primary", use_container_width=True)

LANGUAGE_RULES = f"""
CRITICAL INSTRUCTIONS FOR LANGUAGE: {language}
You MUST write the values for "category", "title", and "description" in the requested language.
1. If 'Pure Tamil': You MUST write strictly in formal Tamil script (தமிழ்) for all text fields. Absolutely NO English words.
2. If 'Tanglish (Tamil + English)': Use a natural, modern conversational mix of proper Tamil script and English words.
3. If 'English': Use standard English.
4. Always explicitly name specific native fruits/vegetables instead of generic terms.
"""

# ==========================================
# 5. AI ENGINE (PRE-FETCHING ARCHITECTURE)
# ==========================================
if generate_btn:
    st.session_state.current_mode = planning_mode 
    
    if planning_mode == "Full Day Itinerary":
        task_instruction = "Generate a FULL DAY meal plan with 5 slots: Breakfast, Mid-Morning Snack, Lunch, Evening Snack, Dinner. For EACH slot, generate exactly 3 distinct recipe options."
    else:
        task_instruction = f"Do NOT generate a full day plan. Generate exactly 5 distinct, creative options for ONE specific meal slot: {target_meal}."

    with st.spinner("Compiling Options Matrix..."):
        prompt = f"""
        You are a minimalist culinary nutritionist.
        Focus: {health_focus}. Protocol: {diet_type}. Cuisine: {cuisine}.
        
        {task_instruction}
        
        {LANGUAGE_RULES}
        
        Return ONLY a valid JSON object matching this exact nested structure:
        {{
          "daily_plan": [
            {{
              "slot": "String (Meal Slot Name)",
              "options": [
                {{
                  "category": "String",
                  "title": "String",
                  "description": "String",
                  "macros": {{"calories": Integer, "protein": Integer, "carbs": Integer, "fat": Integer}}
                }}
              ]
            }}
          ]
        }}
        """
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            chosen_model = next((m for m in available_models if 'flash' in m), available_models[0])
            model = genai.GenerativeModel(chosen_model)
            response = model.generate_content(prompt)
            
            # Parse and initialize the UI state index for each slot
            raw_data = json.loads(clean_json(response.text))
            for slot_data in raw_data.get("daily_plan", []):
                slot_data["selected_index"] = 0
                
            st.session_state.current_recommendations = raw_data
        except Exception as e:
            st.error("Generation failed. Please try again.")

# ==========================================
# 6. RESULTS & ZERO-LATENCY CURATION
# ==========================================
if st.session_state.current_recommendations:
    plan = st.session_state.current_recommendations.get("daily_plan", [])
    st.write("---")
    st.markdown(f"<h3 style='font-weight: 400;'>Proposed {st.session_state.current_mode}</h3>", unsafe_allow_html=True)
    
    # -----------------------------------------------------
    # MODE A: FULL DAY ITINERARY (With Local Swapping)
    # -----------------------------------------------------
    if st.session_state.current_mode == "Full Day Itinerary":
        for idx, slot_data in enumerate(plan):
            curr_idx = slot_data.get("selected_index", 0)
            options = slot_data.get("options", [])
            
            # Failsafe if AI returned an empty options array
            if not options: continue
            
            item = options[curr_idx]
            
            st.markdown(f"""
            <div class="flat-card">
                <div class="flat-tag">{slot_data.get('slot', '')} &bull; {item.get('category', '')}</div>
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
            
            st.markdown('<div class="action-container">', unsafe_allow_html=True)
            col_swap, col_space = st.columns([2, 4])
            with col_swap:
                # INSTANT SWAP BUTTON
                if len(options) > 1:
                    if st.button(f"🔄 Swap (Option {curr_idx + 1}/{len(options)})", key=f"swap_{idx}", use_container_width=True):
                        st.session_state.current_recommendations["daily_plan"][idx]["selected_index"] = (curr_idx + 1) % len(options)
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Bulk Save
        st.write("---")
        if st.button("💾 Create Full Itinerary", type="primary", use_container_width=True):
            if is_guest:
                st.success("Guest Mode: Itinerary created! Log in to permanently save to your Lab.")
                st.session_state.current_recommendations = None
            elif supabase:
                with st.spinner("Saving to your Lab..."):
                    for slot_data in plan:
                        curr_idx = slot_data.get("selected_index", 0)
                        item = slot_data["options"][curr_idx]
                        
                        res = supabase.table("recipes").insert({
                            "user_id": user_id, "title": item.get("title", ""), "description": item.get("description", ""),
                            "prep_time_mins": 0, "macros": item.get("macros", {}), "ingredients": [], "instructions": [], "is_custom": False
                        }).execute()
                        supabase.table("daily_plans").insert({
                            "user_id": user_id, "plan_date": str(st.session_state.active_date), "meal_slot": slot_data.get("slot", "Snack"), "recipe_id": res.data[0]["id"]
                        }).execute()
                    st.success("✨ Itinerary Created! Head over to The Lab.")
                    st.session_state.current_recommendations = None
                    st.rerun()

    # -----------------------------------------------------
    # MODE B: SPECIFIC MEAL (Pick 1 from 5 options)
    # -----------------------------------------------------
    elif st.session_state.current_mode == "Specific Meal" and len(plan) > 0:
        slot_data = plan[0] # Specific meal only has 1 slot array
        options = slot_data.get("options", [])
        
        for opt_idx, item in enumerate(options):
            st.markdown(f"""
            <div class="flat-card">
                <div class="flat-tag">{slot_data.get('slot', '')} Option {opt_idx + 1} &bull; {item.get('category', '')}</div>
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
            
            st.markdown('<div class="action-container">', unsafe_allow_html=True)
            if st.button(f"🍳 Create Recipe {opt_idx+1}", key=f"save_specific_{opt_idx}"):
                if is_guest:
                    st.success("Guest Mode: Recipe chosen! Log in to permanently save.")
                    st.session_state.current_recommendations = None
                    st.rerun()
                elif supabase:
                    with st.spinner("Adding to your Lab..."):
                        res = supabase.table("recipes").insert({
                            "user_id": user_id, "title": item.get("title", ""), "description": item.get("description", ""),
                            "prep_time_mins": 0, "macros": item.get("macros", {}), "ingredients": [], "instructions": [], "is_custom": False
                        }).execute()
                        supabase.table("daily_plans").insert({
                            "user_id": user_id, "plan_date": str(st.session_state.active_date), "meal_slot": slot_data.get("slot", "Snack"), "recipe_id": res.data[0]["id"]
                        }).execute()
                        st.success("✨ Recipe Created! Head over to The Lab.")
                        st.session_state.current_recommendations = None
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

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
