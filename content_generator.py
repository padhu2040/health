import os
import json
import random
from supabase import create_client, Client
import google.generativeai as genai

# --- 1. SETUP CREDENTIALS (Pulled from secure environment variables later) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") # Use your SERVICE ROLE key here if RLS is on
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY]):
    print("Missing environment variables. Exiting.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

def clean_json(raw_text):
    text = str(raw_text).strip()
    text = text.replace("```json", "").replace("```", "")
    return text.strip()

# --- 2. THE COMBINATION MATRIX ---
# The script will randomly pick one trait from each list every time it runs
HEALTH_FOCUSES = ["Maintain Health", "Weight Loss", "Reduce Cholesterol", "Fatty Liver Support", "Blood Sugar Control", "Kids Nutrition"]
DIETS = ["Seasonal / Local", "Mediterranean", "Keto / Low Carb", "Plant-Based"]
CUISINES = ["South Indian", "Global", "North Indian", "Pan-Asian", "Continental"]
LANGUAGES = ["English", "Pure Tamil", "Tanglish (Tamil + English)"]
SLOTS = ["Breakfast", "Mid-Morning Snack", "Lunch", "Evening Snack / Soup", "Dinner", "Healthy Salad"]

def generate_and_store_recipe():
    """Generates a single full recipe and pushes it to Supabase."""
    
    # Pick random traits
    focus = random.choice(HEALTH_FOCUSES)
    diet = random.choice(DIETS)
    cuisine = random.choice(CUISINES)
    lang = random.choice(LANGUAGES)
    slot = random.choice(SLOTS)
    
    print(f"Drafting: {focus} | {diet} | {cuisine} | {lang} | {slot}")

    prompt = f"""
    You are an executive culinary nutritionist.
    Target: {focus}, {diet}, {cuisine} cuisine, for {slot}.
    
    CRITICAL LANGUAGE RULES: {lang}
    1. If 'Pure Tamil': Write ALL text strictly in formal Tamil script (தமிழ்). NO English words.
    2. If 'Tanglish (Tamil + English)': Use a natural, modern conversational mix of proper Tamil script and English words.
    3. If 'English': Use standard English.
    4. Explicitly name specific native fruits/vegetables (e.g., Murungakkai, Vazhaithandu) instead of generic terms.

    Return ONLY a valid JSON object matching this exact structure:
    {{
      "title": "String",
      "description": "String",
      "prep_time_mins": Integer,
      "macros": {{"calories": Integer, "protein": Integer, "carbs": Integer, "fat": Integer}},
      "ingredients": [
        {{"item": "String", "amount": Number, "unit": "String"}}
      ],
      "instructions": [
        "String (Step 1)",
        "String (Step 2)"
      ]
    }}
    """
    
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        m = genai.GenerativeModel(next((m for m in models if 'flash' in m), models[0]))
        response = m.generate_content(prompt)
        
        recipe_data = json.loads(clean_json(response.text))
        
        # Insert into the Super Database
        payload = {
            "health_focus": focus,
            "diet_type": diet,
            "cuisine": cuisine,
            "language": lang,
            "meal_slot": slot,
            "title": recipe_data.get("title", "Unknown"),
            "description": recipe_data.get("description", ""),
            "prep_time_mins": recipe_data.get("prep_time_mins", 15),
            "macros": recipe_data.get("macros", {}),
            "ingredients": recipe_data.get("ingredients", []),
            "instructions": recipe_data.get("instructions", [])
        }
        
        supabase.table("recipe_bank").insert(payload).execute()
        print(f"✅ Successfully saved: {recipe_data.get('title')}")
        
    except Exception as e:
        print(f"❌ Failed to generate or save: {str(e)}")

# --- 3. EXECUTION ---
# Let's generate a batch of 5 recipes every time this script runs
if __name__ == "__main__":
    print("Initiating Content Engine Batch Run...")
    for _ in range(5):
        generate_and_store_recipe()
    print("Batch complete.")
