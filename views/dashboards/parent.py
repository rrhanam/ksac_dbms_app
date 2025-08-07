import streamlit as st
from utils.database import get_athlete_by_id

def show_page(db, user_profile):
    st.header(f"👋 Selamat Datang, {user_profile.get('displayName', '')}")

    child_ids = user_profile.get("child_athlete_ids", [])
    
    if not child_ids:
        st.error("Akun Anda belum terhubung dengan data atlet. Hubungi administrator.")
        st.stop()
    
    st.info("Anda dapat melihat performa terbaik anak Anda di halaman 'Personal Best'.")

