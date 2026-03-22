# Save the Entire Day Button
    st.write("")
    if st.button("💾 Accept & Save Full Itinerary", type="primary", use_container_width=True):
        
        # --- THE GUEST MODE INTERCEPTOR ---
        if user_id == "11111111-1111-1111-1111-111111111111":
            st.success("🚀 **Guest Mode:** Itinerary 'saved' locally for testing! To persist this to your calendar and unlock The Lab, please log out and create a free account.")
            st.session_state.current_recommendations = None
            # We don't rerun immediately so they can read the message
            
        else:
            # --- THE REAL DATABASE SAVE ---
            with st.spinner("Locking in your schedule..."):
                try:
                    for item in plan:
                        # 1. Save title to recipes 
                        recipe_payload = {
                            "user_id": user_id,
                            "title": item.get("title", "Unknown"),
                            "description": item.get("description", ""),
                            "prep_time_mins": 0, 
                            "macros": item.get("macros", {}),
                            "ingredients": [], 
                            "instructions": [], 
                            "is_custom": False
                        }
                        res = supabase.table("recipes").insert(recipe_payload).execute()
                        new_recipe_id = res.data[0]["id"]
                        
                        # 2. Map to Daily Plan
                        plan_payload = {
                            "user_id": user_id,
                            "plan_date": str(st.session_state.active_date),
                            "meal_slot": item.get("slot", "Snack"),
                            "recipe_id": new_recipe_id
                        }
                        supabase.table("daily_plans").insert(plan_payload).execute()
                        
                    st.success("Day planner updated successfully! Head to 'The Lab' later to expand these into full recipes.")
                    st.session_state.current_recommendations = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Database Error: {str(e)}")
