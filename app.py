import streamlit as st
from streamlit_option_menu import option_menu
from utils.firebase_connector import initialize_firebase
from utils.auth import load_user_profile
from views import personal_best
# Impor dari sub-folder baru
from views.dashboards import coach, athlete, parent, admin
from views.manajemen_klub import atlet, absensi, spp
from views.performa_atlet import input, analisa

# --- Konfigurasi dan Inisialisasi ---
st.set_page_config(page_title="KSAC DBMS", page_icon="🏊‍♂️", layout="wide")
db, auth = initialize_firebase()

# --- Halaman Login ---
def login_page():
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    
    _, col_centered, _ = st.columns([1, 2, 1])

    with col_centered:
        st.markdown("<h1 style='text-align: center;'>KSAC Database Management System</h1>", unsafe_allow_html=True)
        st.write("") 

        if 'login_view' not in st.session_state:
            st.session_state.login_view = 'login'

        if st.session_state.login_view == 'login':
            with st.container(border=True):
                st.subheader("👋 Selamat Datang")
                st.write("Silakan login untuk mengakses sistem.")
                
                email = st.text_input("Email", placeholder="email@anda.com", key="login_email")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
                st.write("")

                col1, col2 = st.columns(2)
                
                if col1.button("Login", type="primary", use_container_width=True):
                    if email and password:
                        try:
                            user = auth.auth().sign_in_with_email_and_password(email, password)
                            st.session_state['user'] = user
                            st.session_state['user_profile'] = load_user_profile(db, user['localId'])
                            st.rerun()
                        except Exception:
                            st.error("Login gagal. Periksa kembali email dan password Anda.")
                    else:
                        st.warning("Email dan Password tidak boleh kosong.")

                if col2.button("Lupa Password?", use_container_width=True):
                    st.session_state.login_view = 'reset'
                    st.rerun()

        elif st.session_state.login_view == 'reset':
            with st.container(border=True):
                st.subheader("🔑 Reset Password")
                reset_email = st.text_input("Masukkan email Anda untuk menerima link reset")
                
                if st.button("Kirim Email Reset", type="primary", use_container_width=True):
                    auth.auth().send_password_reset_email(reset_email)
                    st.success("Link reset password telah dikirim ke email Anda.")
                
                if st.button("Kembali ke Login"):
                    st.session_state.login_view = 'login'
                    st.rerun()

# --- Halaman Utama Setelah Login ---
def main_page():
    user_profile = st.session_state.get('user_profile', {})
    role = user_profile.get("role")
    
    with st.sidebar:
        st.title(f"Selamat Datang,")
        st.header(user_profile.get('displayName', 'Pengguna'))
        st.info(f"Role: {role}")
        if st.button("Logout", type="primary"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        
    st.title("KSAC Database Management System")

    # --- Navigasi Berbasis Peran ---
    if role in ['coach', 'admin']:
        # Navigasi Atas (Kategori Utama)
        selected_category = option_menu(
            menu_title=None,
            options=["Dashboard", "Manajemen Klub", "Performa Atlet"],
            icons=['house-door-fill', 'briefcase-fill', 'trophy-fill'],
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#FFC107", "font-size": "20px"},
                "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#444", "border-bottom": "3px solid transparent", "display": "flex", "align-items": "center", "justify-content": "center", "min-height": "70px"},
                "nav-link-selected": {"background-color": "transparent", "border-bottom": "3px solid #FFC107", "color": "#FFC107"},
            }
        )
        st.divider()

        # --- Routing menggunakan Tabs ---
        if selected_category == "Dashboard":
            if role == 'admin':
                admin.show_page(db, user_profile)
            else: # role == 'coach'
                coach.show_page(db, user_profile)
        
        elif selected_category == "Manajemen Klub":
            tab1, tab2, tab3 = st.tabs(["Manajemen Atlet", "Absensi Latihan", "Manajemen SPP"])
            with tab1:
                atlet.show_page(db, user_profile)
            with tab2:
                absensi.show_page(db, user_profile)
            with tab3:
                spp.show_page(db, user_profile)

        elif selected_category == "Performa Atlet":
            tab1, tab2 = st.tabs(["Input Hasil Event", "Analisa Latihan"])
            with tab1:
                input.show_page(db, user_profile)
            with tab2:
                analisa.show_page(db, user_profile)

    elif role == 'athlete':
        # Navigasi khusus untuk Atlet
        selected_page = option_menu(menu_title=None, options=["Dashboard", "Personal Best"], icons=['house-door-fill', 'award-fill'], orientation="horizontal", styles={"container": {"padding": "0!important", "background-color": "transparent"}, "icon": {"color": "#FFC107", "font-size": "20px"}, "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#444", "border-bottom": "3px solid transparent", "display": "flex", "align-items": "center", "justify-content": "center", "min-height": "70px"}, "nav-link-selected": {"background-color": "transparent", "border-bottom": "3px solid #FFC107", "color": "#FFC107"}})
        st.divider()
        if selected_page == "Dashboard": 
            athlete.show_page(db, user_profile)
        elif selected_page == "Personal Best": 
            personal_best.show_page(db, user_profile)
            
    elif role == 'parent':
        # Navigasi khusus untuk Parent (hanya dashboard)
        parent.show_page(db, user_profile)
        
    else:
        st.header("Selamat Datang")
        st.info("Peran Anda tidak terdefinisi atau belum diatur. Hubungi administrator.")

# --- Alur Utama Aplikasi ---
if 'user' not in st.session_state:
    login_page()
else:
    main_page()