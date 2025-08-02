import streamlit as st

def show_page(db, user_profile):
    """Menampilkan halaman placeholder untuk Personal Best Atlet."""
    if user_profile.get('role') != 'athlete':
        st.error("Halaman ini hanya untuk atlet.")
        st.stop()
        
    st.header("🏆 Personal Best")
    st.info("Halaman ini akan menampilkan catatan waktu terbaik Anda di setiap nomor pertandingan.")
    st.info("Fitur ini sedang dalam tahap pengembangan.")

