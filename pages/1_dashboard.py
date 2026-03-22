import streamlit as st
import datetime
import google.generativeai as genai
import json
import random

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
    .premium-card {
        background-color: #ffffff;
        border: 1px solid #eaeaea;
        padding: 24px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        margin-bottom: 0px; 
    }
    .premium-tag {
        font-size: 0.75em;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #888;
        margin-bottom: 6px;
        font-weight: 500;
    }
    .premium-title {
        font-size: 1.25em;
        font-weight: 600;
        color: #111;
        margin-top: 0px;
        margin-bottom: 8px;
        line-height: 1.3;
    }
    .premium-desc {
        font-size: 0.95em;
        color: #555;
        margin-bottom: 16px;
        line-height: 1.6;
    }
    .premium-macros {
        font-size: 0.85em;
        color: #777;
        background-color: #fcfcfc;
        padding: 10px 14px;
        border-radius: 4px;
        display: inline-block;
        border: 1px solid #f0f0f0;
    }
    .recipe-section {
        margin-top: 24px;
        padding-top: 24px;
        border-top: 1px solid #eaeaea;
    }
    .recipe-header {
        font-size: 0.9em;
        font-weight: 600;
        color: #111;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 12px;
    }
    .recipe-list {
        font-size: 0.95em;
        color: #444;
        line-height: 1.7;
        margin-bottom: 20px;
        padding-left: 20px;
    }
    .button-row {
        margin-top: 8px;
        margin-bottom: 32px;
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
You MUST write the values for "category", "title", "description", "ingredients", and "instructions" in the requested language.
1. If 'Pure Tamil': Write strictly in formal Tamil script (தமிழ்). NO English words.
2. If 'Tanglish (Tamil + English)': Use a natural, modern conversational mix of proper Tamil script and English words.
3. If 'English': Use standard English.
4. Always explicitly name specific native fruits/vegetables instead of generic terms.
"""

# ==========================================
# 5. CACHE-WITH-FALLBACK ENGINE
# ==========================================
def fetch_vault_options(slot_name, required_count):
    if not supabase: return []
    res = supabase.table("recipe_bank").select("*").eq("health_focus", health_focus).eq("diet_type", diet_type).eq("cuisine", cuisine).eq("language", language).eq("meal_slot", slot_name).limit(20).execute()
    data = res.data if res.data else []
    
    if len(data) >= required_count:
        random.shuffle(data)
        formatted_options = []
        for d in data[:required_count]:
            formatted_options.append({
                "category": "Curated Selection", 
                "title": d.get("title", ""),
                "description": d.get("description", ""),
                "macros": d.get("macros", {}),
                "prep_time_mins": d.get("prep_time_mins", 15),
                "ingredients": d.get("ingredients", []),
                "instructions": d.get("instructions", []),
                "is_expanded": False
            })
        return formatted_options
    return []

if generate_btn:
    st.session_state.current_mode = planning_mode 
    slots_needed = ["Breakfast", "Mid-Morning Snack", "Lunch", "Evening Snack / Soup", "Dinner"] if planning_mode == "Full Day Itinerary" else [target_meal]
    
    options_per_slot = 3 if planning_mode == "Full Day Itinerary" else 5
    
    with st.spinner("Checking Recipe Vault..."):
        daily_plan = []
        cache_miss = False
        
        for slot in slots_needed:
            options = fetch_vault_options(slot, options_per_slot)
            if not options:
                cache_miss = True
                break
            daily_plan.append({"slot": slot, "selected_index": 0, "options": options})

        if cache_miss:
            st.toast("Vault expanding... Drafting live AI recipes!", icon="🧠")
            
            if planning_mode == "Full Day Itinerary":
                task_instruction = "Generate a FULL DAY meal plan with 5 slots: Breakfast, Mid-Morning Snack, Lunch, Evening Snack, Dinner. For EACH slot, generate EXACTLY 1 distinct recipe option."
            else:
                task_instruction = f"Do NOT generate a full day plan. Generate EXACTLY 3 distinct, creative options for ONE specific meal slot: {target_meal}."

            prompt = f"""
            You are a minimalist culinary nutritionist. Focus: {health_focus}. Protocol: {diet_type}. Cuisine: {cuisine}.
            {task_instruction}
            {LANGUAGE_RULES}
            Return ONLY a valid JSON object matching this exact nested structure:
            {{
              "daily_plan": [
                {{
                  "slot": "String (Meal Slot Name)",
                  "options": [
                    {{
                      "category": "String", "title": "String", "description": "String",
                      "macros": {{"calories": Integer, "protein": Integer, "carbs": Integer, "fat": Integer}},
                      "is_expanded": false, "prep_time_mins": 0, "ingredients": [], "instructions": []
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
                
                raw_data = json.loads(clean_json(response.text))
                for slot_data in raw_data.get("daily_plan", []):
                    slot_data["selected_index"] = 0
                st.session_state.current_recommendations = raw_data
            except Exception as e:
                st.error(f"Live generation failed: {str(e)}")
        else:
            st.session_state.current_recommendations = {"daily_plan": daily_plan}

# ==========================================
# 6. RESULTS, CURATION & INLINE ELABORATION
# ==========================================
if st.session_state.current_recommendations:
    plan = st.session_state.current_recommendations.get("daily_plan", [])
    st.write("---")
    st.markdown(f"<h3 style='font-weight: 400;'>Proposed {st.session_state.current_mode}</h3>", unsafe_allow_html=True)
    
    for idx, slot_data in enumerate(plan):
        curr_idx = slot_data.get("selected_index", 0)
        options = slot_data.get("options", [])
        if not options: continue
        item = options[curr_idx]
        
        html_card = f"""
        <div class="premium-card">
            <div class="premium-tag">{slot_data.get('slot', '')} &bull; {item.get('category', '')}</div>
            <h4 class="premium-title">{item.get('title', 'Dish')}</h4>
            <div class="premium-desc">{item.get('description', '')}</div>
            <div class="premium-macros">
                Cals: {item.get('macros', {}).get('calories', 0)} | 
                Pro: {item.get('macros', {}).get('protein', 0)}g | 
                Carb: {item.get('macros', {}).get('carbs', 0)}g | 
                Fat: {item.get('macros', {}).get('fat', 0)}g
            </div>
        """
        
        # DEFENSIVE PROGRAMMING: Safely handle whatever string/dict the AI returns
        if item.get("is_expanded", False):
            ing_html_parts = []
            for ing in item.get('ingredients', []):
                if isinstance(ing, dict):
                    ing_html_parts.append(f"<li>{ing.get('amount','')} {ing.get('unit','')} {ing.get('item','')}</li>")
                else:
                    ing_html_parts.append(f"<li>{ing}</li>")
            ing_html = "".join(ing_html_parts)
            
            inst_html_parts = []
            for step in item.get('instructions', []):
                if isinstance(step, dict):
                    inst_val = step.get("step", step.get("instruction", str(step)))
                    inst_html_parts.append(f"<li>{inst_val}</li>")
                else:
                    inst_html_parts.append(f"<li>{step}</li>")
            inst_html = "".join(inst_html_parts)
            
            html_card += f"""
<div class="recipe-section">
    <div class="recipe-header">Ingredients</div>
    <ul class="recipe-list">{ing_html}</ul>
    <div class="recipe-header">Preparation ({item.get('prep_time_mins', 0)} mins)</div>
    <ol class="recipe-list">{inst_html}</ol>
</div>
"""
            
        html_card += "</div>"
        st.markdown(html_card, unsafe_allow_html=True)
        
        st.markdown('<div class="button-row">', unsafe_allow_html=True)
        
        if st.session_state.current_mode == "Full Day Itinerary":
            c1, c2, c3 = st.columns([1, 1, 2])
            
            if len(options) > 1:
                if c1.button(f"⟳ Swap ({curr_idx + 1}/{len(options)})", key=f"swap_{idx}", use_container_width=True):
                    st.session_state.current_recommendations["daily_plan"][idx]["selected_index"] = (curr_idx + 1) % len(options)
                    st.rerun()
            
            if not item.get("is_expanded", False):
                if c2.button("📄 View Recipe", key=f"view_{idx}", use_container_width=True):
                    if len(item.get("ingredients", [])) > 0:
                        st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["is_expanded"] = True
                        st.rerun()
                    else:
                        with st.spinner("Drafting recipe..."):
                            try:
                                expand_prompt = f"""
                                You are an executive chef. Write a full recipe for this concept.
                                Dish: {item['title']}
                                Description: {item['description']}
                                {LANGUAGE_RULES}
                                Return JSON: {{"prep_time_mins": Integer, "ingredients": [{{"item": "String", "amount": Number, "unit": "String"}}], "instructions": ["Step 1", "Step 2"]}}
                                """
                                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                                m = genai.GenerativeModel(next((m for m in models if 'flash' in m), models[0]))
                                res_json = json.loads(clean_json(m.generate_content(expand_prompt).text))
                                
                                st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["ingredients"] = res_json.get("ingredients", [])
                                st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["instructions"] = res_json.get("instructions", [])
                                st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["prep_time_mins"] = res_json.get("prep_time_mins", 15)
                                st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["is_expanded"] = True
                                st.rerun()
                            except Exception as expand_err:
                                st.error(f"Failed to draft recipe: {str(expand_err)}")
            else:
                c2.button("✓ Recipe Loaded", key=f"loaded_{idx}", disabled=True, use_container_width=True)

        elif st.session_state.current_mode == "Specific Meal":
            c1, c2, c3 = st.columns([1, 1, 2])
            
            if not item.get("is_expanded", False):
                if c1.button("📄 View Recipe", key=f"view_{idx}", use_container_width=True):
                    if len(item.get("ingredients", [])) > 0:
                        st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["is_expanded"] = True
                        st.rerun()
                    else:
                        with st.spinner("Drafting recipe..."):
                            try:
                                expand_prompt = f"""
                                You are an executive chef. Write a full recipe for this concept.
                                Dish: {item['title']}
                                Description: {item['description']}
                                {LANGUAGE_RULES}
                                Return JSON: {{"prep_time_mins": Integer, "ingredients": [{{"item": "String", "amount": Number, "unit": "String"}}], "instructions": ["Step 1", "Step 2"]}}
                                """
                                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                                m = genai.GenerativeModel(next((m for m in models if 'flash' in m), models[0]))
                                res_json = json.loads(clean_json(m.generate_content(expand_prompt).text))
                                
                                st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["ingredients"] = res_json.get("ingredients", [])
                                st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["instructions"] = res_json.get("instructions", [])
                                st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["prep_time_mins"] = res_json.get("prep_time_mins", 15)
                                st.session_state.current_recommendations["daily_plan"][idx]["options"][curr_idx]["is_expanded"] = True
                                st.rerun()
                            except Exception as expand_err:
                                st.error(f"Failed to draft recipe: {str(expand_err)}")
                            
            if c2.button("💾 Save Option", type="primary", key=f"save_opt_{idx}", use_container_width=True):
                if is_guest:
                    st.success("Guest Mode: Option saved locally. Log in to persist.")
                    st.session_state.current_recommendations = None
                elif supabase:
                    with st.spinner("Saving to Lab..."):
                        res = supabase.table("recipes").insert({
                            "user_id": user_id, "title": item.get("title", ""), "description": item.get("description", ""),
                            "prep_time_mins": item.get("prep_time_mins", 0), "macros": item.get("macros", {}), "ingredients": item.get("ingredients", []), "instructions": item.get("instructions", []), "is_custom": False
                        }).execute()
                        supabase.table("daily_plans").insert({
                            "user_id": user_id, "plan_date": str(st.session_state.active_date), "meal_slot": slot_data.get("slot", "Snack"), "recipe_id": res.data[0]["id"]
                        }).execute()
                        st.success("Saved to Lab!")
                        st.session_state.current_recommendations = None
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.current_mode == "Full Day Itinerary":
        st.write("---")
        if st.button("💾 Save Entire Itinerary to Lab", type="primary", use_container_width=True):
            if is_guest:
                st.success("Guest Mode: Itinerary saved locally. Log in to persist.")
                st.session_state.current_recommendations = None
            elif supabase:
                with st.spinner("Locking in your schedule..."):
                    for slot_data in plan:
                        curr_idx = slot_data.get("selected_index", 0)
                        item = slot_data["options"][curr_idx]
                        
                        res = supabase.table("recipes").insert({
                            "user_id": user_id, "title": item.get("title", ""), "description": item.get("description", ""),
                            "prep_time_mins": item.get("prep_time_mins", 0), "macros": item.get("macros", {}), "ingredients": item.get("ingredients", []), "instructions": item.get("instructions", []), "is_custom": False
                        }).execute()
                        supabase.table("daily_plans").insert({
                            "user_id": user_id, "plan_date": str(st.session_state.active_date), "meal_slot": slot_data.get("slot", "Snack"), "recipe_id": res.data[0]["id"]
                        }).execute()
                    st.success("Full Itinerary Saved to The Lab!")
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
