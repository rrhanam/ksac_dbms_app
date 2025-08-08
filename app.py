import streamlit as st
from streamlit_option_menu import option_menu
from utils.firebase_connector import initialize_firebase
from utils.auth import load_user_profile
# --- PERUBAHAN DI SINI ---
from utils.database import log_activity, check_email_exists
from views.athlete import personal_best
from views.dashboards import coach, athlete, parent, admin
from views.manajemen_klub import atlet, spp
from views.admin import manajemen_user, log_aktivitas
from views.performa_atlet import input, manajemen_performa, personalbest_coach
from views.parent import personal_best as parent_personal_best

# --- Konfigurasi dan Inisialisasi ---
st.set_page_config(page_title="KSAC DBMS", page_icon="🏊‍♂️", layout="wide")
db, auth = initialize_firebase()

# --- CSS Kustom ---
st.markdown("""
<style>
    /* (CSS Anda tetap di sini) */
</style>
""", unsafe_allow_html=True)


# --- Halaman Login ---
def login_page():
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    _, col_centered, _ = st.columns([1, 2, 1])
    with col_centered:
        st.markdown("<h1 style='text-align: center;'>KSAC Database Management System</h1>", unsafe_allow_html=True)
        st.write("") 
        if 'login_view' not in st.session_state: st.session_state.login_view = 'login'
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
                            user_profile = load_user_profile(db, user['localId'])
                            
                            user_profile['uid'] = user['localId']
                            st.session_state['user_profile'] = user_profile
                            
                            if user_profile:
                                log_activity(db, user_profile, "Pengguna login ke sistem.")
                            
                            st.rerun()
                        except Exception: st.error("Login gagal. Periksa kembali email dan password Anda.")
                    else: st.warning("Email dan Password tidak boleh kosong.")
                if col2.button("Lupa Password?", use_container_width=True):
                    st.session_state.login_view = 'reset'
                    st.rerun()
        elif st.session_state.login_view == 'reset':
            with st.container(border=True):
                st.subheader("🔑 Reset Password")
                reset_email = st.text_input("Masukkan email Anda untuk menerima link reset")
                if st.button("Kirim Email Reset", type="primary", use_container_width=True):
                    # --- PERUBAHAN DI SINI: Menambahkan validasi ---
                    if reset_email:
                        if check_email_exists(db, reset_email):
                            auth.auth().send_password_reset_email(reset_email)
                            st.success("Link reset password telah dikirim ke email Anda.")
                        else:
                            st.error("Email anda tidak terdaftar disistem.")
                    else:
                        st.warning("Silakan masukkan alamat email Anda.")
                if st.button("Kembali ke Login"):
                    st.session_state.login_view = 'login'
                    st.rerun()

# --- Halaman Utama Setelah Login ---
def main_page():
    if 'page_to_show' not in st.session_state:
        st.session_state.page_to_show = 'main'

    user_profile = st.session_state.get('user_profile', {})
    role = user_profile.get("role")
    
    with st.sidebar:
        st.title(f"Selamat Datang,")
        st.header(user_profile.get('displayName', 'Pengguna'))
        st.info(f"Role: {role}")
        if st.button("Logout", type="primary"):
            log_activity(db, user_profile, "Pengguna logout dari sistem.")
            st.session_state.clear()
            st.rerun()
        st.divider()
        if role == 'admin':
            st.subheader("Panel Admin")
            if st.button("Manajemen Pengguna", use_container_width=True):
                st.session_state.page_to_show = 'user_management'
                st.rerun()
            if st.button("Log Aktivitas", use_container_width=True):
                st.session_state.page_to_show = 'activity_log'
                st.rerun()
    
    if st.session_state.page_to_show == 'user_management':
        manajemen_user.show_page(db, auth, user_profile)
    elif st.session_state.page_to_show == 'activity_log':
        log_aktivitas.show_page(db, user_profile)
    else:
        st.title("KSAC Database Management System")
        if role in ['coach', 'admin']:
            selected_category = option_menu(
                menu_title=None,
                options=["Dashboard", "Manajemen Klub", "Performa Atlet"],
                icons=['house-door-fill', 'briefcase-fill', 'trophy-fill'],
                orientation="horizontal",
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent"},
                    "icon": {"color": "#DC3545", "font-size": "20px"},
                    "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#444", "border-bottom": "3px solid transparent", "display": "flex", "align-items": "center", "justify-content": "center", "min-height": "70px"},
                    "nav-link-selected": {"background-color": "transparent", "border-bottom": "3px solid #DC3545", "color": "#DC3545"},
                }
            )
            st.divider()
            if selected_category == "Dashboard":
                if role == 'admin': admin.show_page(db, user_profile)
                else: coach.show_page(db, user_profile)
            elif selected_category == "Manajemen Klub":
                tab1, tab2 = st.tabs(["Manajemen Atlet", "Manajemen SPP"])
                with tab1: atlet.show_page(db, user_profile)
                with tab2: spp.show_page(db, user_profile)
            elif selected_category == "Performa Atlet":
                tab1, tab2, tab3 = st.tabs(["Input Hasil Event", "Manajemen & Analisa", "Personal Best"])
                with tab1: input.show_page(db, user_profile)
                with tab2: manajemen_performa.show_page(db, user_profile)
                with tab3: personalbest_coach.show_page(db, user_profile)
        elif role == 'athlete':
            selected_page = option_menu(
                menu_title=None,
                options=["Dashboard", "Personal Best"],
                icons=['house-door-fill', 'award-fill'],
                orientation="horizontal",
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent"},
                    "icon": {"color": "#DC3545", "font-size": "20px"},
                    "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#444", "border-bottom": "3px solid transparent", "display": "flex", "align-items": "center", "justify-content": "center", "min-height": "70px"},
                    "nav-link-selected": {"background-color": "transparent", "border-bottom": "3px solid #DC3545", "color": "#DC3545"},
                }
            )
            st.divider()
            if selected_page == "Dashboard": athlete.show_page(db, user_profile)
            elif selected_page == "Personal Best": personal_best.show_page(db, user_profile)
        elif role == 'parent':
            selected_page = option_menu(
                menu_title=None,
                options=["Dashboard", "Personal Best"],
                icons=['house-door-fill', 'award-fill'],
                orientation="horizontal",
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent"},
                    "icon": {"color": "#DC3545", "font-size": "20px"},
                    "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#444", "border-bottom": "3px solid transparent", "display": "flex", "align-items": "center", "justify-content": "center", "min-height": "70px"},
                    "nav-link-selected": {"background-color": "transparent", "border-bottom": "3px solid #DC3545", "color": "#DC3545"},
                }
            )
            st.divider()
            if selected_page == "Dashboard":
                parent.show_page(db, user_profile)
            elif selected_page == "Personal Best":
                parent_personal_best.show_page(db, user_profile)
        else:
            st.header("Selamat Datang")
            st.info("Peran Anda tidak terdefinisi atau belum diatur. Hubungi administrator.")

if 'user' not in st.session_state: login_page()
else: main_page()
