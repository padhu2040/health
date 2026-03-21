import streamlit as st
import google.generativeai as genai
import json
import re

# ==========================================
# 1. THE GATEKEEPER
# ==========================================
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔒 Secure environment. Please log in to access Discovery.")
    st.stop()

if "supabase" not in st.session_state:
    from app import init_connection
    supabase = init_connection()
else:
    supabase = st.session_state.supabase

user_id = st.session_state.user.id

# ==========================================
# 2. AI INITIALIZATION
# ==========================================
try:
    genai.configure(api_key=st.secrets["gcp"]["gemini_api_key"])
    # Using flash for speed, perfectly fine for text generation
    model = genai.GenerativeModel('gemini-1.5-flash') 
except Exception as e:
    st.error("AI Engine initialization failed. Check your GCP secrets.")
    st.stop()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def clean_json_response(raw_text):
    """Strips markdown formatting if the LLM wraps the JSON in backticks."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

# Fetch user persona for context
@st.cache_data(ttl=600)
def get_user_context(uid):
    res = supabase.table("profiles").select("preferences").eq("id", uid).execute()
    if res.data:
        return res.data[0].get("preferences", {})
    return {}

user_prefs = get_user_context(user_id)
persona = user_prefs.get("persona", "Locavore")
goal = user_prefs.get("goal", "Maintain Health")
allergies = user_prefs.get("allergies", [])

# ==========================================
# 4. UI RENDER
# ==========================================
st.title("The Discovery Engine 🧠")
st.markdown("Let the AI Sous-Chef build a meal based on your pantry and profile.")

with st.form("discovery_form"):
    st.subheader("What are we working with?")
    
    ingredients_input = st.text_area(
        "Available Ingredients", 
        placeholder="e.g., 2 chicken breasts, half a bag of spinach, some old carrots, garlic...",
        help="List what you have. We'll prioritize seasonal/local concepts based on your Locavore profile."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        meal_slot = st.selectbox("Assign to Meal", ["Breakfast", "Lunch", "Dinner", "Snack"])
    with col2:
        # Defaults to the active date selected on the Dashboard
        plan_date = st.date_input("Assign to Date", value=st.session_state.active_date)

    submit_button = st.form_submit_button("Generate & Add to Plan", type="primary", use_container_width=True)

# ==========================================
# 5. GENERATION & DATABASE INJECTION LOGIC
# ==========================================
if submit_button and ingredients_input:
    with st.spinner("Analyzing ingredients and calculating macros..."):
        
        # 1. The Strict System Prompt
        allergy_str = f"Must strictly exclude: {', '.join(allergies)}." if allergies else "No known allergies."
        
        prompt = f"""
        You are a Michelin-star chef and nutritionist. Create a recipe using these ingredients: {ingredients_input}.
        The user's persona is: {persona}. Their goal is: {goal}. {allergy_str}
        
        You MUST return ONLY a valid JSON object. Do not include any other text. 
        The JSON must match this exact structure:
        {{
            "title": "String",
            "description": "Short appetizing description",
            "prep_time_mins": Integer,
            "ingredients": [
                {{"item": "String", "amount": Number, "unit": "String"}}
            ],
            "macros": {{
                "calories": Integer,
                "protein": Integer,
                "carbs": Integer,
                "fat": Integer
            }}
        }}
        """
        
        try:
            # 2. Call Gemini
            response = model.generate_content(prompt)
            clean_text = clean_json_response(response.text)
            recipe_data = json.loads(clean_text)
            
            # 3. Inject into `recipes` table
            recipe_insert = {
                "user_id": user_id,
                "title": recipe_data["title"],
                "description": recipe_data["description"],
                "prep_time_mins": recipe_data["prep_time_mins"],
                "ingredients": recipe_data["ingredients"],
                "macros": recipe_data["macros"],
                "is_custom": False # AI generated
            }
            
            recipe_res = supabase.table("recipes").insert(recipe_insert).execute()
            new_recipe_id = recipe_res.data[0]["id"]
            
            # 4. Map to `daily_plans` table
            plan_insert = {
                "user_id": user_id,
                "plan_date": str(plan_date),
                "meal_slot": meal_slot,
                "recipe_id": new_recipe_id
            }
            supabase.table("daily_plans").insert(plan_insert).execute()
            
            # 5. Success & Route
            st.success(f"Successfully generated **{recipe_data['title']}** and added to your planner!")
            st.balloons()
            
            # Programmatically click back to dashboard to see the result
            st.switch_page("pages/1_dashboard.py")
            
        except Exception as e:
            # Handling the 429 Quota Error or JSON Parsing Error
            error_msg = str(e)
            if "429" in error_msg:
                st.error("Free Tier AI Limit Reached. Please try again in a few minutes or enter a recipe manually in The Lab.")
            elif "Expecting value" in error_msg:
                st.error("The AI returned a malformed response. Please try tweaking your ingredients slightly and try again.")
            else:
                st.error(f"System Error: {error_msg}")
