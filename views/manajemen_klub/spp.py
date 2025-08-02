import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import load_athletes, load_spp_for_month, update_spp_status

def show_page(db, user_profile):
    if user_profile.get('role') not in ['coach', 'admin']:
        st.error("Anda tidak memiliki izin untuk mengakses halaman ini.")
        st.stop()
        
    st.header("Manajemen SPP")

    # --- Filter Periode dan Status ---
    today = datetime.now()
    col1, col2, col3 = st.columns(3)
    
    selected_year = col1.selectbox("Tahun", range(today.year - 2, today.year + 2), index=2)
    
    months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    selected_month_name = col2.selectbox("Bulan", months, index=today.month - 1)
    selected_month_num = months.index(selected_month_name) + 1
    
    status_filter = col3.selectbox("Filter Status", ["Semua", "Lunas", "Belum Lunas"])

    # --- Memuat Data ---
    athletes = load_athletes(db)
    if not athletes:
        st.warning("Belum ada data atlet.")
        st.stop()

    spp_records = load_spp_for_month(db, selected_year, selected_month_num)

    # --- Gabungkan Data Atlet dengan Status SPP ---
    spp_data = []
    for athlete in athletes:
        status_info = spp_records.get(athlete['id'], {})
        status = status_info.get('status', 'Belum Lunas')
        spp_data.append({
            'id': athlete['id'],
            'Nama Atlet': athlete['name'],
            'Level': athlete['level'],
            'Status': status
        })

    df_spp = pd.DataFrame(spp_data)

    # Terapkan filter status
    if status_filter != "Semua":
        df_spp = df_spp[df_spp['Status'] == status_filter]

    # --- Tabel SPP Interaktif ---
    st.subheader(f"Status Pembayaran untuk {selected_month_name} {selected_year}")
    
    # Simpan DataFrame asli untuk perbandingan
    if 'original_df_spp' not in st.session_state:
        st.session_state.original_df_spp = df_spp.copy()
    
    edited_df = st.data_editor(
        df_spp,
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status Pembayaran",
                options=["Lunas", "Belum Lunas"],
                required=True,
            ),
            "id": None,
            "Level": st.column_config.NumberColumn("Level", disabled=True),
            "Nama Atlet": st.column_config.TextColumn("Nama Atlet", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        key=f"spp_editor_{selected_year}_{selected_month_num}"
    )

    # --- Tombol Simpan ---
    if st.button("Simpan Perubahan", type="primary", use_container_width=True):
        changes_made = 0
        with st.spinner("Menyimpan..."):
            for index, row in edited_df.iterrows():
                original_row = st.session_state.original_df_spp.iloc[index]
                if row['Status'] != original_row['Status']:
                    athlete_id = row['id']
                    new_status = row['Status']
                    update_spp_status(db, selected_year, selected_month_num, athlete_id, new_status, user_profile.get('displayName'))
                    changes_made += 1
        
        if changes_made > 0:
            st.success(f"{changes_made} perubahan status SPP berhasil disimpan!")
            st.rerun()
        else:
            st.info("Tidak ada perubahan yang perlu disimpan.")