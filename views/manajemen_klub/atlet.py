import streamlit as st
import pandas as pd
import re
from datetime import datetime
from utils.database import load_athletes, add_athlete, update_athlete, delete_athlete

# --- Helper Functions ---
def calculate_age_by_year(dob_str):
    """Menghitung usia berdasarkan tahun kelahiran secara dinamis."""
    try:
        birth_year = datetime.strptime(dob_str, "%Y-%m-%d").year
        current_year = datetime.now().year
        return current_year - birth_year
    except (ValueError, TypeError):
        return 0

def calculate_ku(age):
    """Menentukan Kelompok Umur (KU) berdasarkan usia."""
    if age >= 19: return "KU Senior"
    elif 16 <= age <= 18: return "KU 1"
    elif 14 <= age <= 15: return "KU 2"
    elif 12 <= age <= 13: return "KU 3"
    elif 10 <= age <= 11: return "KU 4"
    elif 8 <= age <= 9: return "KU 5"
    else: return "Pra KU"

# --- Main Page Function ---
def show_page(db, user_profile):
    if user_profile.get('role') not in ['coach', 'admin']:
        st.error("Anda tidak memiliki izin untuk mengakses halaman ini.")
        st.stop()

    if 'deleting_athlete_id' not in st.session_state: st.session_state.deleting_athlete_id = None
    if 'current_page' not in st.session_state: st.session_state.current_page = 1

    st.header("Manajemen Daftar Atlet")

    with st.expander("➕ Tambah Atlet Baru"):
        with st.form("add_athlete_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            new_name = col1.text_input("Nama Lengkap Atlet")
            new_dob = col2.date_input("Tanggal Lahir", min_value=datetime(1980, 1, 1), max_value=datetime.now())
            
            col3, col4 = st.columns(2)
            new_level = col3.selectbox("Level/Kelompok", [1, 2, 3, 4, 5])
            new_gender = col4.selectbox("Jenis Kelamin", ["Boy", "Girl"])
            
            if st.form_submit_button("Tambah Atlet", type="primary"):
                name_to_validate = new_name.strip()
                is_valid = True

                if not name_to_validate:
                    st.error("Nama atlet tidak boleh kosong.")
                    is_valid = False
                
                elif len(name_to_validate) < 2:
                    st.error("Nama atlet harus terdiri dari minimal 2 karakter.")
                    is_valid = False

                elif not re.match(r"^[a-zA-Z\s]+$", name_to_validate):
                    st.error("Nama atlet hanya boleh mengandung huruf dan spasi.")
                    is_valid = False

                if is_valid:
                    athlete_list = load_athletes(db)
                    existing_names = [a['name'].strip().lower() for a in athlete_list]
                    if name_to_validate.lower() in existing_names:
                        st.error(f"Atlet dengan nama '{name_to_validate}' sudah terdaftar.")
                        is_valid = False

                if is_valid:
                    if add_athlete(db, name_to_validate, new_dob, new_level, new_gender, user_profile):
                        st.success(f"Atlet '{name_to_validate}' berhasil ditambahkan.")
                    else:
                        st.error("Terjadi kesalahan saat menyimpan ke database.")

    st.divider()
    st.subheader("Daftar Atlet Saat Ini")

    athlete_list = load_athletes(db)
    if not athlete_list:
        st.info("Belum ada atlet terdaftar.")
        st.stop()

    for a in athlete_list:
        a['age'] = calculate_age_by_year(a.get('date_of_birth'))
        a['ku'] = calculate_ku(a['age'])

    df_athletes = pd.DataFrame(athlete_list)

    col1, col2, col3 = st.columns(3)
    search_query = col1.text_input("Cari Nama Atlet", placeholder="Ketik nama untuk mencari...", key="atlet_search_query")
    
    level_options = ["Semua Level"] + sorted(list(set([atlet.get('level') for atlet in athlete_list if atlet.get('level') is not None])))
    level_filter = col2.selectbox("Filter Level", level_options)

    ku_options = ["Semua", "KU Senior", "KU 1", "KU 2", "KU 3", "KU 4", "KU 5", "Pra KU"]
    ku_filter = col3.selectbox("Filter Kelompok Umur", ku_options)

    if search_query:
        df_athletes = df_athletes[df_athletes['name'].str.contains(search_query, case=False, na=False)]
    if level_filter != "Semua Level":
        df_athletes = df_athletes[df_athletes['level'].astype(int) == int(level_filter)]
    if ku_filter != "Semua":
        df_athletes = df_athletes[df_athletes['ku'] == ku_filter]

    ITEMS_PER_PAGE = 8
    total_athletes = len(df_athletes)
    total_pages = (total_athletes + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total_athletes > 0 else 1
    
    if st.session_state.current_page > total_pages:
        st.session_state.current_page = total_pages

    start_idx = (st.session_state.current_page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    df_paginated = df_athletes.iloc[start_idx:end_idx]

    st.dataframe(
        df_paginated[['name', 'date_of_birth', 'age', 'ku', 'gender', 'level']].rename(
            columns={'name': 'Nama Atlet', 'date_of_birth': 'Tanggal Lahir', 'age': 'Usia', 'ku': 'Kelompok Umur', 'gender': 'Jenis Kelamin', 'level': 'Level'}
        ),
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key="athlete_selection"
    )
    
    if total_pages > 1:
        st.write("") # Spacer
        _, nav_col, _ = st.columns([3, 2.5, 3])
        with nav_col:
            cols = st.columns([1, 1, 1], gap="small")
            with cols[0]:
                if st.button("◀", use_container_width=True, disabled=(st.session_state.current_page <= 1)):
                    st.session_state.current_page -= 1
                    st.rerun()
            with cols[1]:
                st.markdown(f"""<div style="background-color: var(--secondary-background-color); border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.2em; margin: auto;">{st.session_state.current_page}</div>""", unsafe_allow_html=True)
            with cols[2]:
                if st.button("▶", use_container_width=True, disabled=(st.session_state.current_page >= total_pages)):
                    st.session_state.current_page += 1
                    st.rerun()
        st.markdown(f"<p style='text-align: center; color: #888; font-size: 0.9em; margin-top: 10px;'>Halaman {st.session_state.current_page} dari {total_pages}</p>", unsafe_allow_html=True)

    selected_row_index = None
    if st.session_state.athlete_selection['selection']['rows']:
        relative_index = st.session_state.athlete_selection['selection']['rows'][0]
        selected_row_index = start_idx + relative_index

    st.divider()
    st.subheader("Aksi")
    col1, col2 = st.columns(2)

    if col1.button("✏️ Edit Data", use_container_width=True):
        if selected_row_index is None:
            st.warning("Pilih baris atlet di tabel terlebih dahulu untuk diedit.")
        else:
            athlete_id = df_athletes.iloc[selected_row_index]['id']
            athlete_data = next((a for a in athlete_list if a['id'] == athlete_id), None)
            if athlete_data:
                @st.dialog(f"Edit Data: {athlete_data['name']}")
                def edit_dialog():
                    with st.form("edit_form"):
                        edited_name = st.text_input("Nama Lengkap", value=athlete_data['name'])
                        try: dob_date = datetime.strptime(athlete_data['date_of_birth'], '%Y-%m-%d').date()
                        except (ValueError, TypeError): dob_date = datetime.now().date()
                        edited_dob = st.date_input("Tanggal Lahir", value=dob_date)
                        col1, col2 = st.columns(2)
                        edited_level = col1.selectbox("Level", [1, 2, 3, 4, 5], index=int(athlete_data.get('level', 1))-1)
                        genders = ["Boy", "Girl"]
                        current_gender_index = genders.index(athlete_data['gender']) if athlete_data.get('gender') in genders else 0
                        edited_gender = col2.selectbox("Jenis Kelamin", genders, index=current_gender_index)
                        
                        if st.form_submit_button("Update Data", type="primary"):
                            name_to_validate = edited_name.strip()
                            is_valid = True

                            if not name_to_validate or len(name_to_validate) < 2 or not re.match(r"^[a-zA-Z\s]+$", name_to_validate):
                                st.error("Nama tidak valid (minimal 2 karakter, hanya huruf/spasi).")
                                is_valid = False
                            
                            if is_valid:
                                other_athletes = [a for a in athlete_list if a['id'] != athlete_data['id']]
                                if name_to_validate.lower() in [a['name'].strip().lower() for a in other_athletes]:
                                    st.error(f"Atlet lain dengan nama '{name_to_validate}' sudah terdaftar.")
                                    is_valid = False
                            
                            if is_valid:
                                updated_data = {'name': name_to_validate, 'date_of_birth': edited_dob.strftime('%Y-%m-%d'), 'level': edited_level, 'gender': edited_gender}
                                if update_athlete(db, athlete_data['id'], updated_data, user_profile):
                                    st.toast(f"Data '{name_to_validate}' berhasil diupdate.", icon="✅")
                                    st.rerun()
                                else: 
                                    st.error("Gagal mengupdate data.")
                    
                    if st.button("Batal"):
                        st.rerun()
                edit_dialog()

    if col2.button("❌ Hapus Atlet", type="secondary", use_container_width=True):
        if selected_row_index is None:
            st.warning("Pilih baris atlet di tabel terlebih dahulu untuk dihapus.")
        else:
            athlete_id = df_athletes.iloc[selected_row_index]['id']
            st.session_state.deleting_athlete_id = athlete_id
            st.rerun()

    if st.session_state.deleting_athlete_id:
        athlete_data = next((a for a in athlete_list if a['id'] == st.session_state.deleting_athlete_id), None)
        if athlete_data:
            st.warning(f"Anda yakin ingin menghapus **{athlete_data['name']}** secara permanen?")
            col1, col2 = st.columns(2)
            if col1.button("YA, SAYA YAKIN", type="primary"):
                if delete_athlete(db, athlete_data['id'], user_profile, athlete_data['name']):
                    st.toast(f"Atlet '{athlete_data['name']}' berhasil dihapus.", icon="🗑️")
                    st.session_state.deleting_athlete_id = None
                    st.rerun()
            if col2.button("Batal"):
                st.session_state.deleting_athlete_id = None
                st.rerun()
    
    # --- Bagian Ekspor Laporan ---
    st.divider()
    with st.expander("📄 Export Laporan Atlet ke CSV"):
        
        col1, col2, col3 = st.columns(3)
        export_level = col1.selectbox("Filter Level", level_options, key="export_level")
        export_ku = col2.selectbox("Filter Kelompok Umur", ku_options, key="export_ku")
        export_gender = col3.selectbox("Filter Jenis Kelamin", ["Semua", "Boy", "Girl"], key="export_gender")

        if st.button("Buat File CSV untuk Diunduh", use_container_width=True, key="export_athlete_csv"):
            df_export_raw = df_athletes.copy()
            
            if export_level != "Semua Level":
                df_export_raw = df_export_raw[df_export_raw['level'].astype(int) == int(export_level)]
            if export_ku != "Semua":
                df_export_raw = df_export_raw[df_export_raw['ku'] == export_ku]
            if export_gender != "Semua":
                df_export_raw = df_export_raw[df_export_raw['gender'] == export_gender]

            if df_export_raw.empty:
                st.warning(f"Tidak ada data yang cocok dengan filter yang dipilih.")
            else:
                df_export_final = df_export_raw.copy()
                df_export_final.insert(0, 'No', range(1, 1 + len(df_export_final)))
                
                final_columns_order = ['No', 'name', 'date_of_birth', 'age', 'ku', 'gender', 'level']
                df_export_final = df_export_final[final_columns_order]
                
                df_export_final = df_export_final.rename(columns={
                    'name': 'Nama Atlet',
                    'date_of_birth': 'Tanggal Lahir',
                    'age': 'Usia',
                    'ku': 'KU',
                    'gender': 'Jenis Kelamin',
                    'level': 'Level'
                })
                
                csv = df_export_final.to_csv(index=False).encode('utf-8')
                st.session_state.csv_athlete_data = csv
                st.session_state.csv_athlete_filename = f"laporan_atlet.csv"

        if "csv_athlete_data" in st.session_state:
            st.download_button(
                label="📥 Unduh Laporan Atlet",
                data=st.session_state.csv_athlete_data,
                file_name=st.session_state.csv_athlete_filename,
                mime="text/csv",
                use_container_width=True
            )
