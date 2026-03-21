import streamlit as st
import json

# ==========================================
# 1. THE GATEKEEPER
# ==========================================
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔒 Secure environment. Please log in to access The Lab.")
    st.stop()

if "supabase" not in st.session_state:
    from app import init_connection
    supabase = init_connection()
else:
    supabase = st.session_state.supabase

user_id = st.session_state.user.id

# ==========================================
# 2. HELPER FUNCTIONS (CRUD Operations)
# ==========================================
def fetch_my_recipes():
    """Reads all recipes for the current user."""
    res = supabase.table("recipes").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return res.data if res.data else []

def delete_recipe(recipe_id):
    """Deletes a recipe and its associated daily plans to prevent orphaned data."""
    # First, delete from the junction table (daily_plans)
    supabase.table("daily_plans").delete().eq("recipe_id", recipe_id).execute()
    # Then, delete the actual recipe
    supabase.table("recipes").delete().eq("id", recipe_id).execute()
    st.toast("Recipe deleted successfully.", icon="🗑️")

# ==========================================
# 3. UI RENDER & TABS
# ==========================================
st.title("The Lab 🧪")
st.markdown("Manage your personal recipe database and input custom meals.")

tab_library, tab_create = st.tabs(["📚 Recipe Library", "✍️ Add Custom Recipe"])

# ------------------------------------------
# TAB 1: THE LIBRARY (Read & Delete)
# ------------------------------------------
with tab_library:
    st.subheader("Your Encrypted Database")
    
    recipes = fetch_my_recipes()
    
    if not recipes:
        st.info("Your lab is empty. Go to the Discovery engine to generate AI meals, or add one manually.")
    
    for recipe in recipes:
        # Use an expander to keep the UI clean and scannable
        with st.expander(f"🍽️ {recipe['title']} ({recipe['prep_time_mins']} mins)"):
            st.write(f"*{recipe.get('description', 'No description provided.')}*")
            
            # Display Macros in a clean grid
            macros = recipe.get("macros", {})
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Calories", f"{macros.get('calories', 0)}")
            m_col2.metric("Protein", f"{macros.get('protein', 0)}g")
            m_col3.metric("Carbs", f"{macros.get('carbs', 0)}g")
            m_col4.metric("Fat", f"{macros.get('fat', 0)}g")
            
            st.write("---")
            st.markdown("**Ingredients:**")
            ingredients = recipe.get("ingredients", [])
            for item in ingredients:
                amount = item.get("amount", "")
                unit = item.get("unit", "")
                name = item.get("item", "")
                st.markdown(f"- {amount} {unit} **{name}**")
            
            st.write("---")
            # Delete Action with a unique key per recipe to prevent Streamlit button collisions
            if st.button("Delete Recipe", key=f"del_{recipe['id']}", type="secondary"):
                delete_recipe(recipe['id'])
                st.rerun() # Instantly refresh the page to show the updated database

# ------------------------------------------
# TAB 2: MANUAL CREATION (Create)
# ------------------------------------------
with tab_create:
    st.subheader("Manual Recipe Entry")
    
    with st.form("create_recipe_form", clear_on_submit=True):
        title = st.text_input("Recipe Title*")
        description = st.text_input("Short Description")
        prep_time = st.number_input("Prep Time (minutes)", min_value=1, max_value=300, value=15)
        
        st.markdown("---")
        st.markdown("**Macros per Serving**")
        mac_col1, mac_col2, mac_col3, mac_col4 = st.columns(4)
        cal = mac_col1.number_input("Calories", min_value=0, value=0)
        pro = mac_col2.number_input("Protein (g)", min_value=0, value=0)
        carb = mac_col3.number_input("Carbs (g)", min_value=0, value=0)
        fat = mac_col4.number_input("Fat (g)", min_value=0, value=0)
        
        st.markdown("---")
        st.markdown("**Ingredients**")
        raw_ingredients = st.text_area(
            "List ingredients (one per line)", 
            placeholder="2 cups Spinach\n1 lb Chicken Breast\n1 tbsp Olive Oil"
        )
        
        submit_custom = st.form_submit_button("Save to Library", type="primary")
        
        if submit_custom and title:
            # 1. Parse the manual text area into our strict JSON format
            ingredient_list = []
            if raw_ingredients:
                lines = raw_ingredients.strip().split('\n')
                for line in lines:
                    if line.strip():
                        # Simple parsing for manual entry: storing the whole line as the 'item'
                        ingredient_list.append({"amount": "", "unit": "", "item": line.strip()})
            
            # 2. Construct the Payload
            new_recipe = {
                "user_id": user_id,
                "title": title,
                "description": description,
                "prep_time_mins": prep_time,
                "is_custom": True,
                "macros": {"calories": cal, "protein": pro, "carbs": carb, "fat": fat},
                "ingredients": ingredient_list
            }
            
            # 3. Inject to Database
            supabase.table("recipes").insert(new_recipe).execute()
            st.success("Recipe added to your library!")
            st.rerun() # Refresh to show in Tab 1
