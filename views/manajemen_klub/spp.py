import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import load_athletes, load_spp_for_month, update_spp_payment

# --- Variabel Global ---
MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
DEFAULT_SPP_AMOUNT = 250000

def show_page(db, user_profile):
    if user_profile.get('role') not in ['coach', 'admin']:
        st.error("Anda tidak memiliki izin untuk mengakses halaman ini.")
        st.stop()
        
    st.header("Manajemen SPP")
    
    # --- Memuat Data ---
    athletes = load_athletes(db)
    # --- PERBAIKAN DI SINI: Mengubah pesan jika tidak ada atlet ---
    if not athletes:
        st.warning("Silahkan input data atlet dulu")
        st.stop()
        
    if 'spp_page' not in st.session_state:
        st.session_state.spp_page = 1

    # --- Filter ---
    today = datetime.now()
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("Tahun", range(today.year - 2, today.year + 2), index=2)
    with col2:
        selected_month_name = st.selectbox("Bulan", MONTHS, index=today.month - 1)
        selected_month_num = MONTHS.index(selected_month_name) + 1
    
    spp_records = load_spp_for_month(db, selected_year, selected_month_num)

    spp_data = []
    for athlete in athletes:
        status_info = spp_records.get(athlete['id'], {})
        status = status_info.get('status', 'Belum Lunas')
        amount = status_info.get('amount', 0)
        spp_data.append({
            'id': athlete['id'],
            'name': athlete['name'],
            'level': athlete['level'],
            'status': status,
            'amount': amount,
            'details': status_info
        })

    df_spp = pd.DataFrame(spp_data)

    # --- Dashboard Ringkasan ---
    st.divider()
    st.subheader(f"Ringkasan untuk {selected_month_name} {selected_year}")
    
    total_athletes = len(df_spp)
    total_lunas = len(df_spp[df_spp['status'] == 'Lunas'])
    total_belum_lunas = total_athletes - total_lunas
    total_pemasukan = df_spp['amount'].sum()
    progress = (total_lunas / total_athletes) * 100 if total_athletes > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Total Lunas", f"{total_lunas} Atlet")
    col2.metric("❌ Belum Lunas", f"{total_belum_lunas} Atlet")
    col3.metric("💰 Total Pemasukan", f"Rp {total_pemasukan:,.0f}")
    
    st.progress(progress / 100, text=f"{progress:.1f}% Pembayaran Selesai")

    # --- Tampilan Daftar Interaktif ---
    st.divider()
    st.subheader("Daftar Status Pembayaran")

    # Filter tambahan
    col_search, col_level, col_status = st.columns(3)
    search_query = col_search.text_input("Cari Nama Atlet", placeholder="Ketik nama...")
    
    levels = sorted(list(set([atlet.get('level') for atlet in athletes if atlet.get('level') is not None])))
    level_options = ["Semua Level"] + levels
    level_filter = col_level.selectbox("Filter Level", level_options, key="spp_level_filter")
    
    status_filter = col_status.selectbox("Filter Status", ["Semua", "Lunas", "Belum Lunas"])

    # Terapkan filter pada dataframe
    df_filtered = df_spp.copy()
    if search_query:
        df_filtered = df_filtered[df_filtered['name'].str.contains(search_query, case=False, na=False)]
    if level_filter != "Semua Level":
        df_filtered = df_filtered[df_filtered['level'] == level_filter]
    if status_filter != "Semua":
        df_filtered = df_filtered[df_filtered['status'] == status_filter]

    if df_filtered.empty:
        st.info("Tidak ada data yang cocok dengan filter yang dipilih.")
    else:
        ITEMS_PER_PAGE = 7
        total_items = len(df_filtered)
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total_items > 0 else 1
        
        if st.session_state.spp_page > total_pages:
            st.session_state.spp_page = total_pages

        start_idx = (st.session_state.spp_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        paginated_df = df_filtered.iloc[start_idx:end_idx]

        for index, row in paginated_df.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([3, 2])
                with col1:
                    st.markdown(f"**{row['name']}**")
                    st.caption(f"Level {row['level']}")
                with col2:
                    if row['status'] == 'Lunas':
                        st.success("Lunas")
                    else:
                        st.error("Belum Lunas")
                    
                    button_label = "Lihat/Edit Detail" if row['status'] == 'Lunas' else "Catat Pembayaran"
                    button_type = "secondary" if row['status'] == 'Lunas' else "primary"
                    if st.button(button_label, key=f"spp_action_{row['id']}", use_container_width=True, type=button_type):
                        payment_dialog(db, user_profile, selected_year, selected_month_num, row)
        
        if total_pages > 1:
            st.write("") # Spacer
            _, nav_col, _ = st.columns([3, 2.5, 3])
            with nav_col:
                cols = st.columns([1, 1, 1], gap="small")
                with cols[0]:
                    if st.button("◀", use_container_width=True, disabled=(st.session_state.spp_page <= 1), key="spp_prev_button"):
                        st.session_state.spp_page -= 1
                        st.rerun()
                with cols[1]:
                    st.markdown(f"""<div style="background-color: var(--secondary-background-color); border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.2em; margin: auto;">{st.session_state.spp_page}</div>""", unsafe_allow_html=True)
                with cols[2]:
                    if st.button("▶", use_container_width=True, disabled=(st.session_state.spp_page >= total_pages), key="spp_next_button"):
                        st.session_state.spp_page += 1
                        st.rerun()
            st.markdown(f"<p style='text-align: center; color: #888; font-size: 0.9em; margin-top: 10px;'>Halaman {st.session_state.spp_page} dari {total_pages}</p>", unsafe_allow_html=True)

    # --- Fitur Export CSV dengan filter terpisah ---
    st.divider()
    with st.expander("📄 Export Laporan ke CSV"):
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        export_year = col_exp1.selectbox("Tahun Laporan", range(today.year - 2, today.year + 2), index=2, key="export_year")
        export_month_name = col_exp1.selectbox("Bulan Laporan", MONTHS, index=today.month - 1, key="export_month")
        export_month_num = MONTHS.index(export_month_name) + 1
        
        export_level_filter = col_exp2.selectbox("Filter Level", level_options, key="spp_export_level_filter")
        export_status_filter = col_exp3.selectbox("Filter Status", ["Semua", "Lunas", "Belum Lunas"], key="spp_export_status_filter")

        if st.button("Buat File CSV untuk Diunduh", use_container_width=True, key="export_spp_csv"):
            with st.spinner("Memproses data..."):
                export_records = load_spp_for_month(db, export_year, export_month_num)
                
                export_data = []
                for athlete in athletes:
                    status_info = export_records.get(athlete['id'], {})
                    status = status_info.get('status', 'Belum Lunas')
                    amount = status_info.get('amount', 0)
                    export_data.append({
                        'id': athlete['id'], 'name': athlete['name'], 'level': athlete['level'],
                        'status': status, 'amount': amount
                    })
                
                df_export = pd.DataFrame(export_data)

                if export_level_filter != "Semua Level":
                    df_export = df_export[df_export['level'] == export_level_filter]
                if export_status_filter != "Semua":
                    df_export = df_export[df_export['status'] == export_status_filter]

                if df_export.empty:
                    st.warning("Tidak ada data untuk diekspor sesuai filter yang dipilih.")
                else:
                    df_export.insert(0, 'No.', range(1, len(df_export) + 1))
                    df_export = df_export.rename(columns={'name': 'Nama Atlet', 'level': 'Level', 'status': 'Status', 'amount': 'Nominal'})
                    csv = df_export[['No.', 'Nama Atlet', 'Level', 'Status', 'Nominal']].to_csv(index=False).encode('utf-8')
                    
                    filename_parts = ["laporan_spp", export_month_name, str(export_year)]
                    if export_level_filter != "Semua Level":
                        filename_parts.append(f"level_{export_level_filter}")
                    if export_status_filter != "Semua":
                        filename_parts.append(export_status_filter)
                    
                    filename = "_".join(filename_parts) + ".csv"
                    filename = filename.lower().replace(" ", "_")

                    st.session_state.csv_spp_data = csv
                    st.session_state.csv_spp_filename = filename

        if "csv_spp_data" in st.session_state and st.session_state.get("csv_spp_filename"):
            st.download_button(
                label="📥 Unduh Laporan CSV",
                data=st.session_state.csv_spp_data,
                file_name=st.session_state.csv_spp_filename,
                mime="text/csv",
                use_container_width=True
            )


def payment_dialog(db, user_profile, year, month, athlete_row):
    """Dialog untuk mencatat atau mengedit pembayaran."""
    
    detail = athlete_row['details']
    
    @st.dialog(f"Pembayaran SPP: {athlete_row['name']}")
    def _dialog():
        st.subheader(f"Detail untuk {MONTHS[month-1]} {year}")
        
        default_amount = detail.get('amount', DEFAULT_SPP_AMOUNT)
        
        try:
            default_date = datetime.strptime(detail.get('payment_date'), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            default_date = datetime.now().date()
        
        methods = ["Transfer", "Tunai", "QRIS"]
        default_method_index = methods.index(detail.get('method')) if detail.get('method') in methods else 0
        
        amount = st.number_input("Nominal Pembayaran (Rp)", value=default_amount, step=50000, key="spp_amount")
        payment_date = st.date_input("Tanggal Pembayaran", value=default_date, key="spp_date")
        method = st.selectbox("Metode Pembayaran", methods, index=default_method_index, key="spp_method")
        notes = st.text_area("Catatan (opsional)", value=detail.get('notes', ''), key="spp_notes")
        
        if st.button("Simpan Pembayaran", type="primary", use_container_width=True):
            payment_details = {
                "amount": amount,
                "payment_date": payment_date,
                "method": method,
                "notes": notes
            }
            if update_spp_payment(db, year, month, athlete_row['id'], payment_details, user_profile, athlete_row['name']):
                st.toast("Data pembayaran berhasil disimpan!", icon="✅")
                st.rerun()
            else:
                st.error("Gagal menyimpan data.")
    
    _dialog()
