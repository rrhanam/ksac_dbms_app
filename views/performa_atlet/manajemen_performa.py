import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from utils.database import (
    load_athletes, 
    get_performance_records, 
    update_performance_record, 
    delete_performance_record
)

# --- Konstanta untuk Gaya & Jarak ---
STROKES = ["Semua Gaya", "Gaya Bebas", "Gaya Punggung", "Gaya Dada", "Gaya Kupu-kupu"]
DISTANCES = ["Semua Jarak", 25, 50, 100, 200, 400, 800, 1500]

def show_page(db, user_profile):
    if user_profile.get('role') not in ['coach', 'admin']:
        st.error("Anda tidak memiliki izin untuk mengakses halaman ini.")
        st.stop()
        
    st.header("Manajemen & Analisa Performa")

    athletes = load_athletes(db)
    all_records = get_performance_records(db)
    
    if not athletes:
        st.warning("Data atlet tidak ditemukan.")
        st.stop()
    
    athlete_options = {athlete['id']: athlete['name'] for athlete in athletes}
    
    # --- Filter ---
    st.subheader("🔍 Filter Data")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        options_for_selectbox = {"": "Cari & Pilih Atlet...", **athlete_options}
        selected_athlete_id = st.selectbox(
            "Cari Nama Atlet",
            options=list(options_for_selectbox.keys()),
            format_func=lambda x: options_for_selectbox.get(x, "")
        )

    filter_stroke = col2.selectbox("Pilih Gaya", STROKES)
    filter_distance = col3.selectbox("Pilih Jarak", DISTANCES)
    limit_options = [5, 10, 15, "Semua"]
    filter_limit = col4.selectbox("Data Terakhir", limit_options, index=0)


    # --- Proses Filtering ---
    df = pd.DataFrame()
    if all_records:
        df = pd.DataFrame(all_records).sort_values(by='event_date', ascending=True)
        
        if selected_athlete_id:
            df = df[df['athlete_id'] == selected_athlete_id]

        if filter_stroke != "Semua Gaya":
            df = df[df['stroke'] == filter_stroke]
        if filter_distance != "Semua Jarak":
            df = df[df['distance'] == filter_distance]
        
        if filter_limit != "Semua" and len(df) > filter_limit:
            df = df.tail(filter_limit)


    # --- Tampilan Tabel Data ---
    st.divider()
    st.subheader("📊 Tabel Data Performa")

    if df.empty:
        st.info("Tidak ada data yang cocok dengan filter yang dipilih atau belum ada catatan waktu yang tersimpan.")
    else:
        df_display_sorted = df.sort_values(by='event_date', ascending=False).reset_index(drop=True)
        
        df_formatted = df_display_sorted.copy()
        df_formatted.insert(0, 'No.', range(1, len(df_formatted) + 1))
        df_formatted['event_date'] = pd.to_datetime(df_formatted['event_date']).dt.strftime('%d/%m/%y')
        
        if 'age_at_event' in df_formatted.columns:
            df_formatted['age_at_event'] = df_formatted['age_at_event'].fillna(0).astype(int)

        df_formatted = df_formatted.rename(columns={
            'athlete_name': 'Nama Atlet', 
            'competition_name': 'Nama Event', 
            'event_date': 'Tanggal',
            'age_at_event': 'Usia',
            'ku_at_event': 'KU',
            'stroke': 'Gaya', 
            'distance': 'Jarak (m)', 
            'time_formatted': 'Waktu'
        })
        
        st.dataframe(
            df_formatted[['No.', 'Nama Atlet', 'Nama Event', 'Tanggal', 'Usia', 'KU', 'Gaya', 'Jarak (m)', 'Waktu']], 
            use_container_width=True, 
            hide_index=True, 
            on_select="rerun", 
            selection_mode="single-row", 
            key="perf_selection"
        )

        col_edit, col_delete = st.columns(2)

        selected_indices = st.session_state.perf_selection['selection']['rows']
        selected_record = None
        if selected_indices:
            selected_record = df_display_sorted.iloc[selected_indices[0]].to_dict()

        if col_edit.button("✏️ Edit Pilihan", use_container_width=True):
            if not selected_record:
                st.warning("Pilih satu baris di tabel terlebih dahulu untuk mengedit.")
            else:
                edit_dialog(db, user_profile, selected_record)
        
        if col_delete.button("❌ Hapus Pilihan", use_container_width=True, type="secondary"):
            if not selected_record:
                st.warning("Pilih satu baris di tabel terlebih dahulu untuk menghapus.")
            else:
                st.session_state.deleting_perf_record = selected_record
                st.rerun()

        st.write("") # Spacer
        csv = df_formatted[['No.', 'Nama Atlet', 'Nama Event', 'Tanggal', 'Usia', 'KU', 'Gaya', 'Jarak (m)', 'Waktu']].to_csv(index=False).encode('utf-8')
        
        filename_parts = ["laporan"]
        if selected_athlete_id:
            athlete_name = athlete_options.get(selected_athlete_id, "atlet").split()[0]
            filename_parts.append(athlete_name)
        if filter_distance != "Semua Jarak":
            filename_parts.append(f"{filter_distance}m")
        if filter_stroke != "Semua Gaya":
            filename_parts.append(filter_stroke)
        
        if len(filename_parts) > 1:
            filename = "_".join(filename_parts) + ".csv"
        else:
            filename = "laporan_performa.csv"
        
        filename = filename.replace(" ", "_")

        st.download_button(
            label="📥 Unduh Laporan CSV",
            data=csv,
            file_name=filename,
            mime="text/csv",
            use_container_width=True
        )

    if 'deleting_perf_record' in st.session_state and st.session_state.deleting_perf_record:
        delete_confirmation_dialog(db, user_profile)

    # --- Grafik Progres dengan Altair ---
    st.divider()
    st.subheader("📈 Grafik Progres Atlet")
    
    if selected_athlete_id and filter_stroke != "Semua Gaya" and filter_distance != "Semua Jarak":
        if len(df) > 1:
            chart_df = df.copy().reset_index() 
            chart_df['session_num'] = chart_df.index + 1
            chart_df['time_seconds'] = chart_df['time_ms'] / 1000.0
            chart_df['age_ku_label'] = chart_df['age_at_event'].fillna(0).astype(int).astype(str) + ' / ' + chart_df['ku_at_event'].fillna('')

            min_time = chart_df['time_seconds'].min()
            max_time = chart_df['time_seconds'].max()
            max_session = chart_df['session_num'].max()

            base = alt.Chart(chart_df).encode(
                x=alt.X('session_num:Q', title='Sesi Latihan / Event', 
                        scale=alt.Scale(domain=[0.5, max_session + 0.5], clamp=True),
                        axis=alt.Axis(tickMinStep=1, format='d', labelFontWeight='bold'))
            )

            line = base.mark_line(color='royalblue').encode(
                y=alt.Y('time_seconds:Q', title='Waktu (MM:SS)', 
                        scale=alt.Scale(domain=[min_time - 5, max_time + 5]),
                        axis=alt.Axis(labelExpr="floor(datum.value / 60) + ':' + slice(toString(100 + floor(datum.value % 60)), -2)", labelFontWeight='bold'))
            )

            points = base.mark_point(size=80, filled=True, color='royalblue').encode(y=alt.Y('time_seconds:Q'))
            
            text = base.mark_text(align='center', baseline='bottom', dy=-8, color='white', fontWeight='bold').encode(
                y=alt.Y('time_seconds:Q'), text=alt.Text('time_formatted:N')
            )

            chart = (line + points + text).encode(
                tooltip=[
                    alt.Tooltip('athlete_name', title='Nama Atlet'),
                    alt.Tooltip('event_date:T', title='Tanggal', format='%d %B %Y'),
                    alt.Tooltip('competition_name', title='Nama Event'),
                    alt.Tooltip('age_ku_label', title='Usia / KU'),
                    alt.Tooltip('time_formatted', title='Waktu')
                ]
            ).properties(
                title=f"Grafik Progres {athlete_options[selected_athlete_id]} - {filter_distance}m {filter_stroke}"
            ).interactive()

            st.altair_chart(chart, use_container_width=True)
            st.caption("Arahkan mouse atau tekan titik biru pada grafik untuk melihat detail. Grafik dapat digeser dan di-zoom.")
        else:
            st.info("Data tidak cukup untuk membuat grafik. Dibutuhkan minimal 2 catatan waktu dengan filter yang sama.")
    else:
        st.info("Pilih 1 atlet spesifik, lalu pilih gaya dan jarak untuk melihat grafik progres.")

def edit_dialog(db, user_profile, record):
    @st.dialog("Edit Catatan Waktu")
    def _dialog():
        with st.form("edit_perf_form"):
            st.subheader(f"Mengedit untuk: {record.get('athlete_name')}")
            
            edited_competition = st.text_input("Nama Event", value=record.get('competition_name'))
            
            try: current_date = pd.to_datetime(record.get('event_date')).date()
            except: current_date = datetime.now().date()
            
            edited_date = st.date_input("Tanggal Event", value=current_date)

            stroke_options = [s for s in STROKES if s != "Semua Gaya"]
            distance_options = [d for d in DISTANCES if d != "Semua Jarak"]
            
            current_stroke_index = stroke_options.index(record.get('stroke')) if record.get('stroke') in stroke_options else 0
            current_dist_index = distance_options.index(record.get('distance')) if record.get('distance') in distance_options else 0

            col_style, col_dist = st.columns(2)
            edited_stroke = col_style.selectbox("Gaya", stroke_options, index=current_stroke_index)
            edited_distance = col_dist.selectbox("Jarak (m)", distance_options, index=current_dist_index)
            
            st.divider()

            try:
                time_parts = record.get('time_formatted', '0:0.0').replace('.', ':').split(':')
                current_min, current_sec, current_ms = map(int, time_parts)
            except (IndexError, ValueError): current_min, current_sec, current_ms = 0, 0, 0

            st.write("Waktu (Menit : Detik . Milidetik)")
            col_min, col_sec, col_ms = st.columns(3)
            minutes = col_min.number_input("Menit", min_value=0, max_value=59, value=current_min, format="%d")
            seconds = col_sec.number_input("Detik", min_value=0, max_value=59, value=current_sec, format="%d")
            milliseconds = col_ms.number_input("Milidetik", min_value=0, max_value=99, value=current_ms, format="%d")

            col_submit, col_cancel = st.columns(2)
            submitted = col_submit.form_submit_button("Update Catatan", type="primary", use_container_width=True)
            cancelled = col_cancel.form_submit_button("Batal", use_container_width=True)

            if submitted:
                time_in_ms = (minutes * 60 * 1000) + (seconds * 1000) + (milliseconds * 10)
                time_formatted = f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}"
                
                updated_data = {
                    "competition_name": edited_competition,
                    "event_date": datetime.combine(edited_date, datetime.min.time()),
                    "stroke": edited_stroke,
                    "distance": edited_distance,
                    "time_ms": time_in_ms,
                    "time_formatted": time_formatted
                }
                if update_performance_record(db, record['id'], updated_data, user_profile, record.get('athlete_name')):
                    st.toast("Catatan berhasil diupdate!", icon="✅")
                    st.rerun()
                else:
                    st.error("Gagal menyimpan data.")
            
            if cancelled:
                st.rerun()
    _dialog()

def delete_confirmation_dialog(db, user_profile):
    record = st.session_state.deleting_perf_record
    
    st.error(f"Anda yakin ingin menghapus catatan waktu **{record.get('time_formatted')}** untuk **{record.get('athlete_name')}** secara permanen?")
    
    col1, col2 = st.columns(2)
    if col1.button("YA, HAPUS SEKARANG", type="primary", use_container_width=True):
        if delete_performance_record(db, record['id'], user_profile, record.get('athlete_name'), record.get('time_formatted')):
            st.toast("Catatan berhasil dihapus.", icon="🗑️")
            del st.session_state.deleting_perf_record
            st.rerun()
    if col2.button("Batal", use_container_width=True):
        del st.session_state.deleting_perf_record
        st.rerun()
