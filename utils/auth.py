import streamlit as st

def load_user_profile(_db, uid):
    if not _db or not uid: return {}
    try:
        user_doc = _db.collection('users').document(uid).get()
        return user_doc.to_dict() if user_doc.exists else {}
    except Exception as e:
        st.warning(f"Gagal memuat profil pengguna: {e}")
        return {}