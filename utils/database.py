import streamlit as st
from datetime import datetime

# --- FUNGSI ATLET ---
@st.cache_data(ttl=30)
def load_athletes(_db):
    if not _db: return []
    try:
        athletes_ref = _db.collection('athletes').order_by("name").stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in athletes_ref]
    except Exception as e:
        st.error(f"Gagal memuat data atlet: {e}")
        return []
def get_athlete_by_id(_db, athlete_id):
    if not _db or not athlete_id: return None
    try:
        doc_ref = _db.collection('athletes').document(athlete_id)
        doc = doc_ref.get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None
    except Exception as e:
        st.error(f"Gagal mengambil data atlet: {e}")
        return None
def add_athlete(_db, name, dob, level, gender):
    if not all([_db, name, dob, level, gender]): return False
    try:
        _db.collection('athletes').add({'name': name, 'date_of_birth': dob.strftime('%Y-%m-%d'), 'level': level, 'gender': gender, 'created_at': datetime.now()})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Gagal menambahkan atlet: {e}")
        return False
def update_athlete(_db, athlete_id, new_data):
    if not all([_db, athlete_id, new_data]): return False
    try:
        _db.collection('athletes').document(athlete_id).update(new_data)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Gagal mengupdate atlet: {e}")
        return False
def delete_athlete(_db, athlete_id):
    if not all([_db, athlete_id]): return False
    try:
        _db.collection('athletes').document(athlete_id).delete()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Gagal menghapus atlet: {e}")
        return False

# --- FUNGSI ABSENSI ---
def save_attendance(_db, date, records, recorded_by):
    if not all([_db, date, records]): return False
    try:
        date_str = date.strftime('%Y-%m-%d')
        doc_ref = _db.collection('attendance_records').document(date_str)
        doc_ref.set({'date': date_str, 'records': records, 'recorded_by': recorded_by}, merge=True)
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan absensi: {e}")
        return False
def load_attendance(_db, date):
    if not _db or not date: return {}
    try:
        date_str = date.strftime('%Y-%m-%d')
        doc_ref = _db.collection('attendance_records').document(date_str)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get('records', {})
        return {}
    except Exception as e:
        st.error(f"Gagal memuat absensi: {e}")
        return {}
@st.cache_data(ttl=60)
def load_attendance_range(_db, start_date, end_date):
    if not all([_db, start_date, end_date]): return []
    try:
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        docs = _db.collection('attendance_records').where('date', '>=', start_str).where('date', '<=', end_str).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Gagal memuat laporan absensi: {e}")
        return []

# --- FUNGSI SPP (BARU) ---
def load_spp_for_month(_db, year, month):
    """Memuat data pembayaran SPP untuk bulan dan tahun tertentu."""
    if not all([_db, year, month]): return {}
    try:
        doc_id = f"{year}-{month:02d}"
        doc_ref = _db.collection('spp_payments').document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get('payments', {})
        return {}
    except Exception as e:
        st.error(f"Gagal memuat data SPP: {e}")
        return {}

def update_spp_status(_db, year, month, athlete_id, status, updated_by):
    """Memperbarui status pembayaran SPP seorang atlet."""
    if not all([_db, year, month, athlete_id, status]): return False
    try:
        doc_id = f"{year}-{month:02d}"
        doc_ref = _db.collection('spp_payments').document(doc_id)
        # Menggunakan dot notation untuk update field di dalam map
        doc_ref.set({
            'month_year': f"{month:02d}-{year}",
            'payments': {
                athlete_id: {
                    'status': status,
                    'updated_by': updated_by,
                    'updated_at': datetime.now()
                }
            }
        }, merge=True)
        return True
    except Exception as e:
        st.error(f"Gagal memperbarui status SPP: {e}")
        return False