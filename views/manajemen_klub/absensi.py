import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.database import load_athletes, save_attendance, load_attendance, load_attendance_range

def show_page(db, user_profile):
    if user_profile.get('role') not in ['coach', 'admin']:
        st.error("Anda tidak memiliki izin untuk mengakses halaman ini.")
        st.stop()
        
    st.header("Absensi Latihan")

    # --- Bagian Absensi Harian ---
    col1, col2 = st.columns(2)
    selected_date = col1.date_input("Pilih Tanggal Latihan", datetime.now())
    
    athletes = load_athletes(db)
    if not athletes:
        st.warning("Belum ada data atlet. Silakan tambahkan di halaman Manajemen Atlet.")
        st.stop()
        
    levels = sorted(list(set([atlet.get('level') for atlet in athletes if atlet.get('level') is not None])))
    level_options = ["Semua Level"] + levels
    selected_level = col2.selectbox("Filter Level/Kelompok", level_options)

    if selected_level != "Semua Level":
        filtered_athletes = [atlet for atlet in athletes if atlet.get('level') == selected_level]
    else:
        filtered_athletes = athletes

    if filtered_athletes:
        existing_attendance = load_attendance(db, selected_date)
        attendance_data = [{'id': a['id'], 'Nama Atlet': a['name'], 'Level': a['level'], 'Status': existing_attendance.get(a['id'], "Hadir")} for a in filtered_athletes]
        df_attendance = pd.DataFrame(attendance_data)

        edited_df = st.data_editor(
            df_attendance,
            column_config={
                "Status": st.column_config.SelectboxColumn("Status Kehadiran", options=["Hadir", "Izin", "Sakit", "Alpa"], required=True),
                "id": None, "Level": st.column_config.NumberColumn("Level", disabled=True), "Nama Atlet": st.column_config.TextColumn("Nama Atlet", disabled=True),
            },
            hide_index=True, use_container_width=True, key=f"attendance_editor_{selected_date}_{selected_level}"
        )

        if st.button("Simpan Absensi", type="primary", use_container_width=True):
            records_to_save = {row['id']: row['Status'] for _, row in edited_df.iterrows()}
            if not records_to_save:
                st.warning("Tidak ada data absensi untuk disimpan.")
            elif save_attendance(db, selected_date, records_to_save, user_profile.get('displayName')):
                st.success(f"Absensi untuk tanggal {selected_date.strftime('%d %B %Y')} berhasil disimpan!")
                st.rerun()
            else:
                st.error("Terjadi kesalahan saat menyimpan absensi.")
    else:
        st.info("Tidak ada atlet di level yang dipilih.")

    # --- Bagian Ekspor Laporan ---
    st.divider()
    with st.expander("📄 Export Laporan Absensi ke CSV"):
        today = datetime.now().date()
        last_month = today - timedelta(days=30)
        
        # --- PERUBAHAN DI SINI: Tata letak filter baru ---
        col1, col2, col3 = st.columns(3)
        export_start_date = col1.date_input("Dari Tanggal", value=last_month, key="export_start")
        export_end_date = col2.date_input("Sampai Tanggal", value=today, key="export_end")
        
        status_options = ["Semua Status", "Hadir", "Izin", "Sakit", "Alpa"]
        export_status = col3.selectbox("Filter Status", status_options, key="export_status_filter")

        export_level = st.selectbox("Filter Level untuk Ekspor", level_options, key="export_level_filter")

        if st.button("Buat File CSV untuk Diunduh", use_container_width=True):
            if export_start_date > export_end_date:
                st.error("Tanggal mulai tidak boleh melebihi tanggal akhir.")
            else:
                with st.spinner("Memproses data..."):
                    all_records = load_attendance_range(db, export_start_date, export_end_date)
                    
                    athlete_map = {a['id']: {'name': a['name'], 'level': a['level']} for a in athletes}
                    
                    flat_data = []
                    for day_record in all_records:
                        for athlete_id, status in day_record.get('records', {}).items():
                            athlete_info = athlete_map.get(athlete_id)
                            if athlete_info:
                                flat_data.append({"Tanggal": day_record['date'], "Nama Atlet": athlete_info['name'], "Level": athlete_info['level'], "Status": status})
                    
                    if not flat_data:
                        st.warning("Tidak ada data absensi ditemukan pada rentang tanggal yang dipilih.")
                    else:
                        df_export = pd.DataFrame(flat_data)
                        
                        # Terapkan filter
                        if export_level != "Semua Level":
                            df_export = df_export[df_export['Level'] == export_level]
                        if export_status != "Semua Status":
                            df_export = df_export[df_export['Status'] == export_status]

                        if df_export.empty:
                            st.warning(f"Tidak ada data yang cocok dengan filter yang dipilih.")
                        else:
                            csv = df_export.to_csv(index=False).encode('utf-8')
                            st.session_state.csv_data = csv
                            st.session_state.csv_filename = f"laporan_absensi_{export_start_date}_sd_{export_end_date}.csv"

        if "csv_data" in st.session_state:
            st.download_button(
                label="📥 Unduh Laporan CSV",
                data=st.session_state.csv_data,
                file_name=st.session_state.csv_filename,
                mime="text/csv",
                use_container_width=True
            )