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

# Initialize AI Client 
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
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "Full Day" # Tracks how to display the save buttons

def clean_json(raw_text):
    text = raw_text.strip()
    # Strip markdown code blocks safely
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
    st.date_input("Active Date", value=st.session_state.active_date, key="date_picker", on_change=update_active_date)

st.write("---")

# ==========================================
# 4. THE AI MEAL PLANNER ENGINE
# ==========================================
st.subheader("🧠 Daily Menu Architect")

# --- THE BRANCHING LOGIC UI ---
planning_mode = st.radio("What are we planning today?", ["Full Day Itinerary", "Specific Meal or Snack"], horizontal=True)

target_meal = None
if planning_mode == "Specific Meal or Snack":
    target_meal = st.selectbox("Select Target Meal", ["Breakfast", "Mid-Morning Snack", "Lunch", "Evening Snack / Soup", "Dinner", "Healthy Salad"])

st.markdown("<br>", unsafe_allow_html=True) # Spacer

# Preferences Rows
row1_c1, row1_c2, row1_c3 = st.columns(3)
with row1_c1:
    health_focus = st.selectbox("Clinical Focus", ["Maintain Health", "Weight Loss (Caloric Deficit)", "Reduce Cholesterol", "Fatty Liver Support", "Blood Sugar Control", "Kids / Teenagers Nutrition"])
with row1_c2:
    diet_type = st.selectbox("Dietary Protocol", ["Locavore / Seasonal", "Mediterranean", "Keto / Ultra Low Carb", "Vegan / Plant-Based"])
with row1_c3:
    cuisine = st.selectbox("Cuisine Style", ["Authentic South Indian", "Global / No Preference", "North Indian", "Pan-Asian", "Continental"])

row2_c1, row2_c2 = st.columns(2)
with row2_c1:
    language = st.selectbox("Output Language", ["English", "Tamil (Conversational Tanglish)"])
with row2_c2:
    st.write("") 
    generate_btn = st.button(f"Generate {planning_mode}", type="primary", use_container_width=True)

# --- THE DYNAMIC PROMPT BUILDER ---
if generate_btn:
    st.session_state.current_mode = planning_mode # Cache the mode for the rendering logic below
    
    # Adjust the core instruction based on the user's selection
    if planning_mode == "Full Day Itinerary":
        task_instruction = "Generate a FULL DAY meal plan overview. Include exactly 5 meals in this logical order: Breakfast, Mid-Morning Snack, Lunch, Evening Snack/Soup, Dinner."
    else:
        task_instruction = f"Do NOT generate a full day plan. I only need options for: {target_meal}. Generate exactly 3 distinct, creative options for this specific meal type so the user can choose their favorite."

    with st.spinner(f"Architecting options in {language}..."):
        prompt = f"""
        You are an executive chef and clinical nutritionist. 
        Health Focus: {health_focus}.
        Dietary Protocol: {diet_type}.
        Cuisine Style: {cuisine}.
        
        {task_instruction}
        
        CRITICAL LANGUAGE & CONTENT RULES: 
        1. If the language is 'Tamil (Conversational Tanglish)', you MUST write exactly how a modern person in Chennai speaks using a literal MIX of Tamil script and English script. Example: "ரொம்ப healthy ஆன High Protein சுண்டல்", "Kids-க்கு புடிச்ச மாதிரி tasty fruit bowl". 
        2. If the language is 'English', use standard English.
        3. INGREDIENT SPECIFICITY: Whenever you recommend a fruit bowl, vegetable salad, or mixed dish, explicitly name the specific fruits and vegetables.
        4. TRADITIONAL INGREDIENTS: Actively include traditional and native vegetables/fruits (e.g., Murungakkai, Vazhaithandu, Avarakkai, Koyyapazham).
        
        Do NOT generate full recipes with cooking instructions. Just provide a conceptual overview.
        
        Return ONLY a valid JSON object matching this exact structure:
        {{
          "daily_plan": [
            {{
              "slot": "String (e.g. Breakfast, Lunch, or the specific target meal)",
              "category": "String (e.g. Traditional Breakfast, Healthy Snack)",
              "title": "String (Name of the dish)",
              "description": "Short explanation of why it fits the health focus, naming the specific traditional fruits/veggies used.",
              "macros": {{"calories": Integer, "protein": Integer, "carbs": Integer, "fat": Integer}}
            }}
          ]
        }}
        """
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if not available_models:
                st.error("Error: No text-generation models found.")
                st.stop()
                
            chosen_model = next((m for m in available_models if 'flash' in m), available_models[0])
            model = genai.GenerativeModel(chosen_model)
            response = model.generate_content(prompt)
            
            st.session_state.current_recommendations = json.loads(clean_json(response.text))
            
        except Exception as e:
            st.error(f"AI Generation failed: {str(e)}")

# ==========================================
# 5. DISPLAY & DYNAMIC SAVE LOGIC
# ==========================================
if st.session_state.current_recommendations:
    plan = st.session_state.current_recommendations.get("daily_plan", [])
    
    st.markdown(f"### 📅 Proposed {st.session_state.current_mode}")
    
    for idx, item in enumerate(plan):
        with st.container():
            st.markdown(f"""
            <div style="background-color: #ffffff; border-left: 4px solid #27ae60; border: 1px solid #eaeaea; padding: 15px; margin-bottom: 10px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <p style="margin: 0; color: #7f8c8d; font-size: 0.9em; font-weight: bold;">{item.get('slot', 'Meal')} &bull; {item.get('category', 'Food')}</p>
                <h4 style="margin: 5px 0;">✨ {item.get('title', 'Unknown Dish')}</h4>
                <p style="margin: 0; font-style: italic; color: #34495e;">{item.get('description', '')}</p>
                <div style="margin-top: 10px; font-size: 0.85em; color: #7f8c8d;">
                    <b>Cals:</b> {item.get('macros', {}).get('calories', 0)} | 
                    <b>Pro:</b> {item.get('macros', {}).get('protein', 0)}g | 
                    <b>Carbs:</b> {item.get('macros', {}).get('carbs', 0)}g | 
                    <b>Fat:</b> {item.get('macros', {}).get('fat', 0)}g
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # If in "Specific Meal" mode, render a save button for EACH individual option
            if st.session_state.current_mode == "Specific Meal or Snack":
                if st.button(f"📥 Choose Option {idx+1}", key=f"save_single_{idx}"):
                    if user_id == "11111111-1111-1111-1111-111111111111":
                        st.success("🚀 **Guest Mode:** Meal selected! Create an account to permanently save.")
                        st.session_state.current_recommendations = None
                        st.rerun()
                    else:
                        with st.spinner("Saving meal..."):
                            res = supabase.table("recipes").insert({
                                "user_id": user_id, "title": item.get("title", ""), "description": item.get("description", ""),
                                "prep_time_mins": 0, "macros": item.get("macros", {}), "ingredients": [], "instructions": [], "is_custom": False
                            }).execute()
                            supabase.table("daily_plans").insert({
                                "user_id": user_id, "plan_date": str(st.session_state.active_date), "meal_slot": item.get("slot", "Snack"), "recipe_id": res.data[0]["id"]
                            }).execute()
                        st.success("Meal added to today's plan!")
                        st.session_state.current_recommendations = None
                        st.rerun()

    # If in "Full Day" mode, render the single bulk save button at the bottom
    if st.session_state.current_mode == "Full Day Itinerary":
        st.write("")
        if st.button("💾 Accept & Save Full Itinerary", type="primary", use_container_width=True):
            if user_id == "11111111-1111-1111-1111-111111111111":
                st.success("🚀 **Guest Mode:** Itinerary saved locally for testing! Create a free account to persist.")
                st.session_state.current_recommendations = None
            else:
                with st.spinner("Locking in your schedule..."):
                    for item in plan:
                        res = supabase.table("recipes").insert({
                            "user_id": user_id, "title": item.get("title", ""), "description": item.get("description", ""),
                            "prep_time_mins": 0, "macros": item.get("macros", {}), "ingredients": [], "instructions": [], "is_custom": False
                        }).execute()
                        supabase.table("daily_plans").insert({
                            "user_id": user_id, "plan_date": str(st.session_state.active_date), "meal_slot": item.get("slot", "Snack"), "recipe_id": res.data[0]["id"]
                        }).execute()
                    st.success("Day planner updated successfully!")
                    st.session_state.current_recommendations = None
                    st.rerun()

st.write("---")

# ==========================================
# 6. TODAY's SAVED SCHEDULE (Read from DB)
# ==========================================
st.subheader(f"Locked Schedule for {st.session_state.active_date.strftime('%B %d, %Y')}")

meals_res = supabase.table("daily_plans").select(
    "meal_slot, recipes(title, description)"
).eq("user_id", user_id).eq("plan_date", str(st.session_state.active_date)).execute()

planned_meals = meals_res.data if meals_res.data else []

if not planned_meals:
    st.info("Your calendar is open for this date.")
else:
    for meal in planned_meals:
        with st.container():
            if meal and meal.get("recipes"):
                recipe = meal["recipes"]
                st.markdown(f"**{meal.get('meal_slot')}**")
                st.markdown(f"🍽️ **{recipe['title']}**")
                st.markdown(f"<span style='color: gray; font-size: 0.9em;'>{recipe.get('description', '')}</span>", unsafe_allow_html=True)
                st.write("---")
