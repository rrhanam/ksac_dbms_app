import streamlit as st
import pandas as pd
from utils.database import get_all_users, create_user_account, update_user_profile, delete_user_account, load_athletes, get_unlinked_athletes
import re

def show_page(db, auth, user_profile):
    if user_profile.get('role') != 'admin':
        st.error("Halaman ini hanya untuk Administrator.")
        st.stop()

    if st.button("◀ Kembali ke Halaman Utama"):
        st.session_state.page_to_show = 'main'
        st.rerun()

    st.header("Manajemen Pengguna Sistem")

    with st.expander("➕ Tambah Pengguna Baru"):
        role = st.selectbox("Peran (Role)", ["coach", "athlete", "parent", "admin"], key="add_user_role")

        with st.form("add_user_form"):
            st.subheader("Detail Akun")
            
            display_name = st.text_input("Nama Lengkap")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            child_athlete_ids = []
            linked_athlete_id = None

            if role == 'parent':
                st.subheader("Hubungkan ke Atlet (Anak)")
                athletes = load_athletes(db)
                if not athletes:
                    st.warning("Tidak ada data atlet untuk dihubungkan.")
                else:
                    athlete_options = {a['id']: a['name'] for a in athletes}
                    child_athlete_ids = st.multiselect(
                        "Pilih Anak (bisa lebih dari satu)",
                        options=list(athlete_options.keys()),
                        format_func=lambda x: athlete_options.get(x, "")
                    )
            
            elif role == 'athlete':
                st.subheader("Hubungkan ke Data Atlet")
                unlinked_athletes = get_unlinked_athletes(db)
                if not unlinked_athletes:
                    st.warning("Semua atlet sudah memiliki akun.")
                else:
                    athlete_options = {"": "Pilih Data Atlet...", **{a['id']: a['name'] for a in unlinked_athletes}}
                    linked_athlete_id = st.selectbox("Pilih Data Atlet", options=list(athlete_options.keys()), format_func=lambda x: athlete_options.get(x, ""))


            submitted = st.form_submit_button("Buat Akun Pengguna", type="primary")
            if submitted:
                is_valid = True
                if not all([display_name, email, password, role]):
                    st.error("Semua kolom harus diisi.")
                    is_valid = False
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    st.error("Format email tidak valid.")
                    is_valid = False
                elif len(password) < 6:
                    st.error("Password harus terdiri dari minimal 6 karakter.")
                    is_valid = False
                elif role == 'parent' and not child_athlete_ids:
                    st.error("Untuk peran Parent, Anda harus memilih minimal satu atlet.")
                    is_valid = False
                elif role == 'athlete' and not linked_athlete_id:
                    st.error("Untuk peran Athlete, Anda harus menghubungkannya ke data atlet.")
                    is_valid = False
                
                if is_valid:
                    success, message = create_user_account(auth, db, email, password, display_name, role, user_profile, child_athlete_ids, linked_athlete_id)
                    if success:
                        st.success(f"Pengguna '{display_name}' berhasil dibuat!")
                        st.session_state.add_user_role = "coach"
                    else:
                        st.error(f"Gagal membuat pengguna: {message}")

    st.divider()
    st.subheader("Daftar Pengguna Terdaftar")
    all_users = get_all_users(db)

    if not all_users:
        st.info("Belum ada pengguna terdaftar.")
    else:
        df_users = pd.DataFrame(all_users)
        df_display = df_users.rename(columns={'displayName': 'Nama', 'email': 'Email', 'role': 'Peran'})
        
        st.dataframe(
            df_display[['Nama', 'Email', 'Peran']],
            use_container_width=True, hide_index=True, on_select="rerun",
            selection_mode="single-row", key="user_selection"
        )

        selected_indices = st.session_state.user_selection['selection']['rows']
        
        col1, col2 = st.columns(2)
        if col1.button("✏️ Edit Data", use_container_width=True):
            if not selected_indices:
                st.warning("Pilih satu baris di tabel terlebih dahulu untuk mengedit.")
            else:
                selected_user_data = df_users.iloc[selected_indices[0]].to_dict()
                edit_dialog(db, selected_user_data, user_profile)

        if col2.button("❌ Hapus Pengguna", use_container_width=True, type="secondary"):
            if not selected_indices:
                st.warning("Pilih satu baris di tabel terlebih dahulu untuk menghapus.")
            else:
                selected_user_data = df_users.iloc[selected_indices[0]].to_dict()
                if selected_user_data['uid'] == user_profile.get('uid'):
                    st.warning("Anda tidak dapat menghapus akun Anda sendiri.")
                else:
                    st.session_state.deleting_user_data = selected_user_data
                    st.rerun()

    if 'deleting_user_data' in st.session_state and st.session_state.deleting_user_data:
        user_to_delete = st.session_state.deleting_user_data
        st.warning(f"Anda yakin ingin menghapus pengguna **{user_to_delete['displayName']}** ({user_to_delete['email']}) secara permanen? Aksi ini tidak dapat dibatalkan.")
        
        col_yes, col_no = st.columns(2)
        if col_yes.button("YA, SAYA YAKIN", type="primary"):
            success, message = delete_user_account(db, user_to_delete['uid'], user_profile)
            if success:
                st.toast(f"Pengguna {user_to_delete['displayName']} berhasil dihapus.", icon="🗑️")
                del st.session_state.deleting_user_data
                st.rerun()
            else:
                st.error(f"Gagal menghapus: {message}")
        
        if col_no.button("Batal"):
            del st.session_state.deleting_user_data
            st.rerun()

def edit_dialog(db, user_data, actor_profile):
    @st.dialog(f"Edit Data: {user_data['displayName']}")
    def _dialog():
        edited_name = st.text_input("Nama Lengkap", value=user_data.get('displayName'))
        st.text_input("Email (tidak dapat diubah)", value=user_data.get('email'), disabled=True)

        roles = ["coach", "athlete", "parent", "admin"]
        current_role_index = roles.index(user_data.get('role', 'coach'))
        new_role = st.selectbox("Peran Pengguna", options=roles, index=current_role_index)
        
        new_child_ids = user_data.get('child_athlete_ids', [])
        new_linked_athlete_id = None

        if new_role == 'parent':
            athletes = load_athletes(db)
            athlete_options = {a['id']: a['name'] for a in athletes}
            new_child_ids = st.multiselect("Hubungkan ke Anak (Atlet)", options=list(athlete_options.keys()), default=new_child_ids, format_func=lambda x: athlete_options.get(x, ""))

        elif new_role == 'athlete':
            unlinked_athletes = get_unlinked_athletes(db)
            currently_linked_athlete = next((a for a in load_athletes(db) if a.get('uid') == user_data['uid']), None)
            
            athlete_options_list = unlinked_athletes
            if currently_linked_athlete:
                athlete_options_list.append(currently_linked_athlete)

            athlete_options = {"": "Pilih Data Atlet...", **{a['id']: a['name'] for a in athlete_options_list}}
            current_athlete_index = list(athlete_options.keys()).index(currently_linked_athlete['id']) if currently_linked_athlete else 0
            
            new_linked_athlete_id = st.selectbox("Hubungkan ke Data Atlet", options=list(athlete_options.keys()), format_func=lambda x: athlete_options.get(x, ""), index=current_athlete_index)


        if st.button("Update Data", type="primary"):
            name_to_validate = edited_name.strip()
            is_valid = True
            if not name_to_validate or len(name_to_validate) < 2 or not re.match(r"^[a-zA-Z\s]+$", name_to_validate):
                st.error("Nama tidak valid (minimal 2 karakter, hanya huruf/spasi).")
                is_valid = False
            
            if is_valid:
                updated_data = {'displayName': name_to_validate, 'role': new_role}
                if new_role == 'parent':
                    if not new_child_ids:
                        st.error("Anda harus memilih minimal satu atlet untuk peran Parent.")
                        return
                    updated_data['child_athlete_ids'] = new_child_ids
                else:
                    if 'child_athlete_ids' in user_data:
                        updated_data['child_athlete_ids'] = None

                if new_role == 'athlete':
                    if not new_linked_athlete_id:
                        st.error("Anda harus memilih data atlet untuk peran Athlete.")
                        return
                    updated_data['linked_athlete_id'] = new_linked_athlete_id
                
                if update_user_profile(db, user_data['uid'], updated_data, actor_profile):
                    st.toast("Data pengguna berhasil diupdate.", icon="✅")
                    st.rerun()
                else:
                    st.error("Gagal mengupdate data.")
    _dialog()
