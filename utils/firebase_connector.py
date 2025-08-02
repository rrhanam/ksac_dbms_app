import streamlit as st
import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore

@st.cache_resource
def initialize_firebase():
    """
    Menginisialisasi Pyrebase (untuk auth) dan Firebase Admin (untuk DB).
    Menggunakan st.secrets untuk keamanan dan menambahkan penanganan error.
    """
    try:
        if not firebase_admin._apps:
            # --- FIX STARTS HERE ---
            # Salin data dari st.secrets ke dictionary biasa agar bisa diubah
            creds_dict = dict(st.secrets["firebase_admin_credentials"])

            # Perbaiki format private_key jika perlu (mengganti string '\\n' menjadi newline)
            if 'private_key' in creds_dict and isinstance(creds_dict['private_key'], str):
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            # --- FIX ENDS HERE ---

            admin_creds = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(admin_creds)
        
        db = firestore.client()

    except Exception as e:
        st.error(f"Gagal terhubung ke Firestore (Admin SDK): {e}. Periksa format file .streamlit/secrets.toml Anda.")
        st.stop()

    try:
        firebase_config = st.secrets["firebase_config"]
        firebase_auth = pyrebase.initialize_app(firebase_config)
    except Exception as e:
        st.error(f"Gagal terhubung ke Firebase Auth (Pyrebase): {e}")
        st.stop()

    return db, firebase_auth