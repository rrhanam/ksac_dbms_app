import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import get_performance_records, load_athletes

def show_page(db, user_profile):
    """Menampilkan halaman Personal Best untuk Admin/Coach."""
    if user_profile.get('role') not in ['admin', 'coach']:
        st.error("Halaman ini hanya untuk Admin dan Coach.")
        st.stop()
        
    st.header("🏆 Personal Best Atlet")

    athletes = load_athletes(db)
    if not athletes:
        st.warning("Belum ada data atlet di sistem.")
        st.stop()

    athlete_options = {athlete['id']: athlete['name'] for athlete in athletes}
    options_for_selectbox = {"": "Cari & Pilih Atlet...", **athlete_options}
    
    selected_athlete_id = st.selectbox(
        "Pilih Atlet untuk Melihat Personal Best",
        options=list(options_for_selectbox.keys()),
        format_func=lambda x: options_for_selectbox.get(x, "")
    )

    if not selected_athlete_id:
        st.info("Silakan pilih seorang atlet di atas untuk memulai.")
        st.stop()

    all_records = get_performance_records(db, athlete_id=selected_athlete_id)

    if not all_records:
        st.warning(f"**{athlete_options[selected_athlete_id]}** belum memiliki catatan waktu yang tersimpan.")
        st.stop()

    df = pd.DataFrame(all_records)
    df['time_ms'] = pd.to_numeric(df['time_ms'])
    df['event_date'] = pd.to_datetime(df['event_date'])
    
    best_times_df = df.loc[df.groupby(['distance', 'stroke'])['time_ms'].idxmin()]
    
    st.write("") # Spacer
    
    # Filter Gaya
    stroke_options = ["Semua Gaya"] + sorted(best_times_df['stroke'].unique().tolist())
    filter_stroke = st.selectbox("Filter Gaya", stroke_options)

    # Terapkan filter
    if filter_stroke != "Semua Gaya":
        best_times_df = best_times_df[best_times_df['stroke'] == filter_stroke]

    # Tentukan urutan gaya yang diinginkan
    stroke_order = ["Gaya Kupu-kupu", "Gaya Punggung", "Gaya Dada", "Gaya Bebas"]
    # Ubah kolom 'stroke' menjadi tipe kategori dengan urutan kustom
    best_times_df['stroke'] = pd.Categorical(best_times_df['stroke'], categories=stroke_order, ordered=True)
    # Urutkan berdasarkan kategori gaya, lalu berdasarkan jarak
    best_times_df = best_times_df.sort_values(by=['stroke', 'distance'])

    st.subheader(f"Catatan Waktu Terbaik: {athlete_options[selected_athlete_id]}")
    st.divider()

    if best_times_df.empty:
        st.info("Tidak ada data yang cocok dengan filter yang dipilih.")
    else:
        best_times_df = best_times_df.reset_index(drop=True)
        best_times_df.insert(0, 'No.', range(1, len(best_times_df) + 1))

        best_times_df['Nomor Pertandingan'] = best_times_df['distance'].astype(str) + 'm ' + best_times_df['stroke'].astype(str)
        best_times_df['Tanggal'] = best_times_df['event_date'].dt.strftime('%d %B %Y')
        
        df_display = best_times_df.rename(columns={
            'time_formatted': 'Waktu Terbaik',
            'competition_name': 'Nama Event'
        })
        
        display_columns = ['No.', 'Nomor Pertandingan', 'Nama Event', 'Tanggal', 'Waktu Terbaik']
        
        st.dataframe(
            df_display[display_columns],
            use_container_width=True,
            hide_index=True
        )

        st.write("") # Spacer
        csv = df_display[display_columns].to_csv(index=False).encode('utf-8')
        
        athlete_name = athlete_options.get(selected_athlete_id, "atlet").replace(" ", "_")
        
        if filter_stroke != "Semua Gaya":
            filename = f"pb_{athlete_name}_{filter_stroke.replace(' ', '_')}.csv"
        else:
            filename = f"pb_{athlete_name}.csv"

        st.download_button(
            label="📥 Unduh Laporan CSV",
            data=csv,
            file_name=filename,
            mime="text/csv",
            use_container_width=True
        )
