import streamlit as st

def show_page(db, user_profile):
    st.header(f"Dashboard Coach: {user_profile.get('displayName', '')}")
    st.info("Halaman ini sedang dalam tahap pengembangan.")
