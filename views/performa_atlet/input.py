import streamlit as st

def show_page(db, user_profile):
    if user_profile.get('role') not in ['coach', 'admin']:
        st.error("Anda tidak memiliki izin untuk mengakses halaman ini.")
        st.stop()
    st.header("Input Hasil Event")
    st.info("Halaman ini sedang dalam tahap pengembangan.")
