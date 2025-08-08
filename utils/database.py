import streamlit as st
from datetime import datetime, time
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import DELETE_FIELD
from firebase_admin import auth as admin_auth

# --- FUNGSI BARU ---
def check_email_exists(_db, email):
    """Mengecek apakah email sudah terdaftar di koleksi users."""
    try:
        # Mencari dokumen di koleksi 'users' yang field 'email'-nya cocok
        users_ref = _db.collection('users').where(filter=FieldFilter('email', '==', email)).limit(1).stream()
        # Jika ada dokumen yang ditemukan, return True
        return len(list(users_ref)) > 0
    except Exception as e:
        st.error(f"Terjadi kesalahan saat validasi email: {e}")
        return False

# --- FUNGSI LOG AKTIVITAS ---
def log_activity(_db, user_profile, action):
    try:
        log_entry = {
            "timestamp": datetime.now(),
            "user_id": user_profile.get('uid', 'N/A'),
            "user_name": user_profile.get('displayName', 'N/A'),
            "user_role": user_profile.get('role', 'N/A'),
            "action": action
        }
        _db.collection('activity_logs').add(log_entry)
    except Exception as e:
        print(f"Error logging activity: {e}")

def get_logs(_db, limit=100):
    try:
        logs_ref = _db.collection('activity_logs').order_by("timestamp", direction="DESCENDING").limit(limit).stream()
        return [doc.to_dict() for doc in logs_ref]
    except Exception as e:
        st.error(f"Gagal memuat log aktivitas: {e}")
        return []

# --- FUNGSI PENGGUNA (USERS) ---
def get_all_users(_db):
    try:
        users_ref = _db.collection('users').stream()
        return [{'uid': doc.id, **doc.to_dict()} for doc in users_ref]
    except Exception as e:
        st.error(f"Gagal memuat data pengguna: {e}")
        return []

def create_user_account(pyrebase_auth, _db, email, password, display_name, role, actor_profile, child_athlete_ids=None, linked_athlete_id=None):
    try:
        user = pyrebase_auth.auth().create_user_with_email_and_password(email, password)
        uid = user['localId']
        
        user_profile = {
            "displayName": display_name, "email": email, "role": role,
            "created_at": datetime.now()
        }
        
        if role == 'parent' and child_athlete_ids:
            user_profile['child_athlete_ids'] = child_athlete_ids
        
        _db.collection('users').document(uid).set(user_profile)
        admin_auth.set_custom_user_claims(uid, {'role': role})
        
        if role == 'athlete' and linked_athlete_id:
            _db.collection('athletes').document(linked_athlete_id).update({'uid': uid})
        
        log_activity(_db, actor_profile, f"Membuat pengguna baru: {display_name} ({role})")
        return True, "Sukses"
    except Exception as e:
        error_message = str(e)
        if "EMAIL_EXISTS" in error_message: return False, "Email ini sudah terdaftar."
        if "WEAK_PASSWORD" in error_message: return False, "Password terlalu lemah."
        return False, error_message

def update_user_profile(_db, uid, new_data, actor_profile):
    try:
        user_doc = _db.collection('users').document(uid).get()
        original_role = user_doc.to_dict().get('role') if user_doc.exists else None
        
        new_role = new_data.get('role')
        new_linked_athlete_id = new_data.pop('linked_athlete_id', None)

        if original_role == 'athlete' and new_role != 'athlete':
            old_link_query = _db.collection('athletes').where(filter=FieldFilter('uid', '==', uid)).limit(1).stream()
            for doc in old_link_query:
                doc.reference.update({'uid': DELETE_FIELD})

        if new_role == 'athlete' and new_linked_athlete_id:
            old_link_query = _db.collection('athletes').where(filter=FieldFilter('uid', '==', uid)).limit(1).stream()
            for doc in old_link_query:
                if doc.id != new_linked_athlete_id:
                    doc.reference.update({'uid': DELETE_FIELD})
            _db.collection('athletes').document(new_linked_athlete_id).update({'uid': uid})

        if new_data.get('child_athlete_ids') is None:
            new_data['child_athlete_ids'] = DELETE_FIELD

        _db.collection('users').document(uid).update(new_data)
        if 'role' in new_data:
            admin_auth.set_custom_user_claims(uid, {'role': new_data['role']})
        
        log_activity(_db, actor_profile, f"Mengupdate data pengguna (UID: {uid})")
        return True
    except Exception as e:
        st.error(f"Gagal mengupdate profil: {e}")
        return False

def delete_user_account(_db, uid, actor_profile):
    try:
        admin_auth.delete_user(uid)
        _db.collection('users').document(uid).delete()
        log_activity(_db, actor_profile, f"Menghapus pengguna (UID: {uid})")
        return True, "Sukses"
    except Exception as e:
        return False, str(e)


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

def get_unlinked_athletes(_db):
    """Mengambil daftar atlet yang belum memiliki akun pengguna (uid)."""
    all_athletes = load_athletes(_db)
    return [athlete for athlete in all_athletes if 'uid' not in athlete]

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

def add_athlete(_db, name, dob, level, gender, actor_profile):
    try:
        _db.collection('athletes').add({'name': name, 'date_of_birth': dob.strftime('%Y-%m-%d'), 'level': level, 'gender': gender, 'created_at': datetime.now()})
        st.cache_data.clear()
        log_activity(_db, actor_profile, f"Menambahkan atlet baru: {name}")
        return True
    except Exception as e:
        st.error(f"Gagal menambahkan atlet: {e}")
        return False

def update_athlete(_db, athlete_id, new_data, actor_profile):
    try:
        _db.collection('athletes').document(athlete_id).update(new_data)
        st.cache_data.clear()
        log_activity(_db, actor_profile, f"Mengupdate data atlet: {new_data.get('name')}")
        return True
    except Exception as e:
        st.error(f"Gagal mengupdate atlet: {e}")
        return False

def delete_athlete(_db, athlete_id, actor_profile, athlete_name):
    try:
        _db.collection('athletes').document(athlete_id).delete()
        st.cache_data.clear()
        log_activity(_db, actor_profile, f"Menghapus atlet: {athlete_name}")
        return True
    except Exception as e:
        st.error(f"Gagal menghapus atlet: {e}")
        return False

# --- FUNGSI SPP ---
def load_spp_for_month(_db, year, month):
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

def update_spp_payment(_db, year, month, athlete_id, payment_details, actor_profile, athlete_name):
    try:
        doc_id = f"{year}-{month:02d}"
        doc_ref = _db.collection('spp_payments').document(doc_id)
        update_data = {'status': 'Lunas', 'amount': payment_details['amount'], 'payment_date': payment_details['payment_date'].strftime('%Y-%m-%d'), 'method': payment_details['method'], 'notes': payment_details['notes'], 'updated_by': actor_profile['displayName'], 'updated_at': datetime.now()}
        doc_ref.set({'month_year': f"{month:02d}-{year}", 'payments': { athlete_id: update_data }}, merge=True)
        st.cache_data.clear()
        log_activity(_db, actor_profile, f"Mencatat pembayaran SPP untuk {athlete_name} (Bulan: {month}-{year})")
        return True
    except Exception as e:
        st.error(f"Gagal memperbarui status SPP: {e}")
        return False

# --- FUNGSI PERFORMA ATLET ---
def add_performance_record(db, record_data, actor_profile):
    try:
        record_data['created_at'] = datetime.now()
        db.collection('performance_records').add(record_data)
        log_activity(_db, actor_profile, f"Menambahkan catatan waktu untuk {record_data['athlete_name']}")
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan catatan waktu: {e}")
        return False

def get_performance_records(db, athlete_id=None):
    if not db:
        return []
    try:
        query = db.collection('performance_records')
        if athlete_id:
            query = query.where(filter=FieldFilter('athlete_id', '==', athlete_id))
        
        docs = query.stream()
        records = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        
        sorted_records = sorted(records, key=lambda x: x.get('event_date', datetime.min), reverse=True)
        
        return sorted_records
    except Exception as e:
        st.error(f"Gagal memuat catatan waktu: {e}")
        return []

def update_performance_record(db, record_id, new_data, actor_profile, athlete_name):
    try:
        new_data['updated_at'] = datetime.now()
        db.collection('performance_records').document(record_id).update(new_data)
        log_activity(_db, actor_profile, f"Mengupdate catatan waktu untuk {athlete_name}")
        return True
    except Exception as e:
        st.error(f"Gagal memperbarui catatan waktu: {e}")
        return False

def delete_performance_record(db, record_id, actor_profile, athlete_name, time_formatted):
    try:
        db.collection('performance_records').document(record_id).delete()
        log_activity(_db, actor_profile, f"Menghapus catatan waktu {time_formatted} untuk {athlete_name}")
        return True
    except Exception as e:
        st.error(f"Gagal menghapus catatan waktu: {e}")
        return False
