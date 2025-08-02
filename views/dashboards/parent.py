import streamlit as st
from utils.database import get_athlete_by_id

def show_page(db, user_profile):
    st.header(f"Dashboard Parent: {user_profile.get('displayName', '')}")
    child_id = user_profile.get("child_athlete_id")
    if not child_id:
        st.error("Akun Anda belum terhubung dengan data atlet. Hubungi administrator.")
        st.stop()
    
    child_data = get_athlete_by_id(db, child_id)
    if not child_data:
        st.error("Data atlet anak tidak ditemukan.")
        st.stop()
        
    st.subheader(f"Menampilkan Data untuk: {child_data.get('name')}")
    st.info("Halaman ini sedang dalam tahap pengembangan.")
