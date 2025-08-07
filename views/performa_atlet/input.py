import streamlit as st
from datetime import datetime
from utils.database import load_athletes, add_performance_record

# --- Konstanta untuk Gaya & Jarak ---
STROKES = ["Gaya Bebas", "Gaya Punggung", "Gaya Dada", "Gaya Kupu-kupu"]
DISTANCES = [25, 50, 100, 200, 400, 800, 1500]

# --- Fungsi Helper ---
def calculate_age_by_year(dob_str, event_date):
    """Menghitung usia berdasarkan tahun kelahiran pada saat event."""
    try:
        birth_year = datetime.strptime(dob_str, "%Y-%m-%d").year
        event_year = event_date.year
        return event_year - birth_year
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

def show_page(db, user_profile):
    if user_profile.get('role') not in ['coach', 'admin']:
        st.error("Anda tidak memiliki izin untuk mengakses halaman ini.")
        st.stop()
        
    st.header("Input Hasil Event / Latihan")

    athletes = load_athletes(db)
    if not athletes:
        st.warning("Belum ada data atlet. Silakan tambahkan di halaman Manajemen Atlet.")
        st.stop()

    athlete_options = {athlete['id']: athlete['name'] for athlete in athletes}

    # --- FORMULIR INPUT ---
    with st.form("input_performance_form", clear_on_submit=True):
        st.subheader("Detail Event & Atlet")
        
        col1, col2 = st.columns(2)
        
        with col1:
            options_for_selectbox = {"": "Cari & Pilih Atlet...", **athlete_options}
            selected_athlete_id = st.selectbox(
                "Cari Nama Atlet",
                options=list(options_for_selectbox.keys()),
                format_func=lambda x: options_for_selectbox.get(x, "")
            )

        competition_name = col2.text_input("Nama Kompetisi / Event", "Latihan Harian")
        event_date = st.date_input("Tanggal Event", datetime.now())

        st.divider()
        st.subheader("Catatan Waktu")

        col_stroke, col_dist = st.columns(2)
        stroke = col_stroke.selectbox("Gaya Renang", STROKES)
        distance = col_dist.selectbox("Jarak (meter)", DISTANCES)
        
        st.write("Masukkan Waktu (Menit : Detik . Milidetik)")
        col_min, col_sec, col_ms = st.columns(3)
        minutes = col_min.number_input("Menit", min_value=0, max_value=59, step=1, format="%d")
        seconds = col_sec.number_input("Detik", min_value=0, max_value=59, step=1, format="%d")
        milliseconds = col_ms.number_input("Milidetik (2 digit)", min_value=0, max_value=99, step=1, format="%d")

        submitted = st.form_submit_button("Simpan Catatan Waktu", type="primary", use_container_width=True)

        if submitted:
            if not selected_athlete_id:
                st.error("Silakan pilih atlet terlebih dahulu.")
                return

            selected_athlete_data = next((a for a in athletes if a['id'] == selected_athlete_id), None)
            if not selected_athlete_data or 'date_of_birth' not in selected_athlete_data:
                st.error("Data tanggal lahir atlet tidak ditemukan. Update data atlet terlebih dahulu.")
                return
            
            dob_str = selected_athlete_data['date_of_birth']
            age_at_event = calculate_age_by_year(dob_str, event_date)
            ku_at_event = calculate_ku(age_at_event)

            time_in_ms = (minutes * 60 * 1000) + (seconds * 1000) + (milliseconds * 10)
            time_formatted = f"{minutes:02d}:{seconds:02d}.{milliseconds:02d}"

            record_data = {
                "athlete_id": selected_athlete_id,
                "athlete_name": athlete_options.get(selected_athlete_id),
                "competition_name": competition_name,
                "event_date": datetime.combine(event_date, datetime.min.time()),
                "stroke": stroke,
                "distance": distance,
                "time_ms": time_in_ms,
                "time_formatted": time_formatted,
                "recorded_by": user_profile.get('displayName', 'N/A'),
                "age_at_event": age_at_event,
                "ku_at_event": ku_at_event
            }

            if add_performance_record(db, record_data, user_profile):
                st.success(f"Catatan waktu untuk {athlete_options.get(selected_athlete_id)} berhasil disimpan!")
            else:
                st.error("Terjadi kesalahan saat menyimpan data.")
