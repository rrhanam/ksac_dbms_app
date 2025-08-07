import streamlit as st
import pandas as pd
from utils.database import get_performance_records, load_athletes, get_athlete_by_id

def show_page(db, user_profile):
    """Menampilkan halaman Personal Best untuk Parent."""
    if user_profile.get('role') != 'parent':
        st.error("Halaman ini hanya untuk Orang Tua.")
        st.stop()
        
    st.header("🏆 Personal Best Anak")

    child_ids = user_profile.get("child_athlete_ids", [])
    if not child_ids:
        st.error("Akun Anda belum terhubung dengan data atlet. Hubungi administrator.")
        st.stop()

    child_options = {child_id: get_athlete_by_id(db, child_id).get('name', 'N/A') for child_id in child_ids}
    
    # Tampilkan dropdown jika ada lebih dari satu anak
    if len(child_ids) > 1:
        selected_child_id = st.selectbox(
            "Pilih Anak untuk Melihat Personal Best",
            options=list(child_options.keys()),
            format_func=lambda x: child_options[x]
        )
    else:
        selected_child_id = child_ids[0]

    if not selected_child_id:
        st.info("Silakan pilih anak untuk melanjutkan.")
        return

    st.subheader(f"Menampilkan Data untuk: {child_options[selected_child_id]}")
    
    all_records = get_performance_records(db, athlete_id=selected_child_id)

    if not all_records:
        st.info(f"**{child_options[selected_child_id]}** belum memiliki catatan waktu yang tersimpan.")
        return

    df = pd.DataFrame(all_records)
    df['time_ms'] = pd.to_numeric(df['time_ms'])
    df['event_date'] = pd.to_datetime(df['event_date'])
    
    best_times_df = df.loc[df.groupby(['distance', 'stroke'])['time_ms'].idxmin()]
    
    # --- PERUBAHAN DI SINI: Menambahkan filter gaya ---
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
        
        st.dataframe(
            df_display[['No.', 'Nomor Pertandingan', 'Nama Event', 'Tanggal', 'Waktu Terbaik']],
            use_container_width=True,
            hide_index=True
        )
