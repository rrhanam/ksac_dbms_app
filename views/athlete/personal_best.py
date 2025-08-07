import streamlit as st
import pandas as pd
from utils.database import get_performance_records, load_athletes

def show_page(db, user_profile):
    """Menampilkan halaman Personal Best untuk atlet yang sedang login."""
    if user_profile.get('role') != 'athlete':
        st.error("Halaman ini hanya untuk atlet.")
        st.stop()
        
    st.header("🏆 Personal Best")

    # Mencari data atlet yang terhubung dengan UID pengguna
    athletes = load_athletes(db)
    linked_athlete_data = next((a for a in athletes if a.get('uid') == user_profile.get('uid')), None)

    if not linked_athlete_data:
        st.error("Akun Anda belum terhubung dengan data atlet. Hubungi administrator.")
        st.stop()

    athlete_id_for_query = linked_athlete_data.get("id")
    if not athlete_id_for_query:
        st.error("Tidak dapat menemukan ID atlet Anda. Hubungi administrator.")
        st.stop()

    # Memuat semua catatan waktu untuk atlet ini
    all_records = get_performance_records(db, athlete_id=athlete_id_for_query)

    if not all_records:
        st.info("Anda belum memiliki catatan waktu yang tersimpan.")
        st.write("Catatan waktu terbaik Anda akan muncul di sini setelah pelatih memasukkan hasil event.")
        st.stop()

    # Mengolah data untuk menemukan waktu terbaik
    df = pd.DataFrame(all_records)
    df['time_ms'] = pd.to_numeric(df['time_ms'])
    df['event_date'] = pd.to_datetime(df['event_date'])
    
    best_times_df = df.loc[df.groupby(['distance', 'stroke'])['time_ms'].idxmin()]
    
    stroke_options = ["Semua Gaya"] + sorted(best_times_df['stroke'].unique().tolist())
    filter_stroke = st.selectbox("Filter Gaya", stroke_options)

    # Terapkan filter
    if filter_stroke != "Semua Gaya":
        best_times_df = best_times_df[best_times_df['stroke'] == filter_stroke]

    stroke_order = ["Gaya Kupu-kupu", "Gaya Punggung", "Gaya Dada", "Gaya Bebas"]
    best_times_df['stroke'] = pd.Categorical(best_times_df['stroke'], categories=stroke_order, ordered=True)
    best_times_df = best_times_df.sort_values(by=['stroke', 'distance'])

    st.divider()

    if best_times_df.empty:
        st.info("Tidak ada data catatan waktu terbaik yang cocok dengan filter.")
    else:
        best_times_df = best_times_df.reset_index(drop=True)
        best_times_df.insert(0, 'No.', range(1, len(best_times_df) + 1))

        best_times_df['Nomor Pertandingan'] = best_times_df['distance'].astype(str) + 'm ' + best_times_df['stroke'].astype(str)
        best_times_df['Tanggal'] = best_times_df['event_date'].dt.strftime('%d %B %Y')
        
        df_display = best_times_df.rename(columns={
            'time_formatted': 'Waktu Terbaik',
            'competition_name': 'Nama Event'
        })
        
        # --- PERUBAHAN DI SINI: Mengubah urutan kolom ---
        st.dataframe(
            df_display[['No.', 'Nomor Pertandingan', 'Nama Event', 'Tanggal', 'Waktu Terbaik']],
            use_container_width=True,
            hide_index=True
        )
