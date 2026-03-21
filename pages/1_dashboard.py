import streamlit as st

# 1. THE GATEKEEPER (Must be the first logic executed)
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("🔒 Secure environment. Please log in to access your dashboard.")
    st.stop()

# 2. PAGE CONTENT
st.title(f"Dashboard: {st.session_state.active_date.strftime('%A, %b %d')}")

st.markdown('<p class="status-success">System Sync: Active</p>', unsafe_allow_html=True)

# 3. EXECUTIVE KPI CARDS (Placeholder for Macro Totals)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Calories Target", "2,100 kcal", delta="-150 kcal")
with col2:
    st.metric("Protein", "160g", delta="On Track")
with col3:
    st.metric("Carbs", "180g", delta="Under")

st.write("---")
st.subheader("Today's Locavore Meal Plan")
st.info("The database query connecting to Supabase will go here, using `.eq('user_id', st.session_state.user.id)` to ensure strict data isolation.")
