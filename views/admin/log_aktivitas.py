import streamlit as st
import pandas as pd
from utils.database import get_logs

def show_page(db, user_profile):
    if user_profile.get('role') != 'admin':
        st.error("Halaman ini hanya untuk Administrator.")
        st.stop()

    if st.button("◀ Kembali ke Halaman Utama"):
        st.session_state.page_to_show = 'main'
        st.rerun()

    st.header("📜 Log Aktivitas Pengguna")
    st.caption("Menampilkan 100 aktivitas terbaru di sistem.")

    logs = get_logs(db, limit=100)

    if not logs:
        st.info("Belum ada aktivitas yang tercatat.")
    else:
        df_logs = pd.DataFrame(logs)
        
        # Format kolom untuk tampilan yang lebih baik
        df_logs['Waktu'] = pd.to_datetime(df_logs['timestamp']).dt.strftime('%d %b %Y, %H:%M:%S')
        df_logs = df_logs.rename(columns={
            'user_name': 'Nama Pengguna',
            'user_role': 'Peran',
            'action': 'Aktivitas'
        })

        st.dataframe(
            df_logs[['Waktu', 'Nama Pengguna', 'Peran', 'Aktivitas']],
            use_container_width=True,
            hide_index=True
        )
