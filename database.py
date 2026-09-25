import os
import psycopg2
import bcrypt
from datetime import datetime

def get_database_url():
    """Mengambil connection string Supabase dari st.secrets atau environment"""
    url = None
    # 1. Coba dari streamlit secrets jika ada
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "supabase" in st.secrets and "database_url" in st.secrets["supabase"]:
                url = st.secrets["supabase"]["database_url"]
            elif "database_url" in st.secrets:
                url = st.secrets["database_url"]
    except Exception:
        pass

    # 2. Coba dari file .streamlit/secrets.toml secara manual jika belum dapat
    if not url:
        secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
        if os.path.exists(secrets_path):
            try:
                import tomllib
                with open(secrets_path, "rb") as f:
                    data = tomllib.load(f)
                    url = data.get("supabase", {}).get("database_url") or data.get("database_url")
            except Exception:
                pass

    # 3. Coba dari environment variable
    if not url:
        url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

    if not url:
        raise ValueError("Database connection URL tidak ditemukan! Pastikan .streamlit/secrets.toml sudah dikonfigurasi.")

    # Bersihkan query parameter yang tidak didukung psycopg2 (seperti ?pgbouncer=true)
    if "?" in url:
        url = url.split("?")[0]

    return url

def get_connection():
    """Membuka koneksi ke database PostgreSQL Supabase"""
    return psycopg2.connect(get_database_url())

# ==========================================
# AUTH & USER MANAGEMENT FUNCTIONS
# ==========================================

def hash_password(password: str) -> str:
    """Hash password menggunakan bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def check_password(password: str, hashed: str) -> bool:
    """Verifikasi kecocokan password dengan hash bcrypt"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def verify_user(username: str, password: str):
    """
    Verifikasi login user.
    Mengembalikan dict user jika valid, None jika salah.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, password_hash, nama_lengkap, role
        FROM users
        WHERE username = %s
    """, (username.strip().lower(),))
    row = cursor.fetchone()
    conn.close()

    if row:
        user_id, u_name, p_hash, full_name, role = row
        if check_password(password, p_hash):
            return {
                "id": user_id,
                "username": u_name,
                "nama_lengkap": full_name,
                "role": role
            }
    return None

def create_user(username: str, password: str, nama_lengkap: str, role: str = "petugas"):
    """Tambah pengguna baru"""
    conn = get_connection()
    cursor = conn.cursor()
    p_hash = hash_password(password)
    try:
        cursor.execute("""
            INSERT INTO users (username, password_hash, nama_lengkap, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (username.strip().lower(), p_hash, nama_lengkap.strip(), role))
        user_id = cursor.fetchone()[0]
        conn.commit()
        return user_id
    finally:
        conn.close()

def get_all_users():
    """Ambil daftar semua pengguna (tanpa hash password)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, nama_lengkap, role, created_at
        FROM users
        ORDER BY role ASC, username ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_user_password(user_id: int, new_password: str):
    """Ganti password pengguna"""
    conn = get_connection()
    cursor = conn.cursor()
    p_hash = hash_password(new_password)
    try:
        cursor.execute("""
            UPDATE users SET password_hash = %s WHERE id = %s
        """, (p_hash, user_id))
        conn.commit()
    finally:
        conn.close()

def delete_user(user_id: int):
    """Hapus pengguna"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()

# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def init_database():
    """Inisialisasi tabel perizinan dan users di Supabase"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Tabel data perizinan
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS perizinan (
        id SERIAL PRIMARY KEY,
        sektor TEXT NOT NULL,
        kategori_perizinan TEXT NOT NULL,
        nama_pengguna_layanan TEXT,
        nib TEXT,
        alamat TEXT,
        pemilik_pengurus TEXT,
        lokasi_usaha TEXT,
        luas_lahan_usaha TEXT,
        kbli TEXT,
        jenis_usaha TEXT,
        resiko TEXT,
        kapasitas TEXT,
        jenis_permohonan TEXT,
        nomor_permohonan TEXT,
        tanggal_permohonan TEXT,
        nomor_tanggal_permohonan_rekomendasi TEXT,
        nomor_tanggal_rekomendasi TEXT,
        nomor_izin TEXT,
        tanggal_izin TEXT,
        masa_berlaku TEXT,
        npwp TEXT,
        telepon TEXT,
        email TEXT,
        keterangan TEXT,
        jenis_dokumen TEXT,
        rencana_investasi TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Migration: pastikan kolom rencana_investasi ada
    try:
        cursor.execute("ALTER TABLE perizinan ADD COLUMN IF NOT EXISTS rencana_investasi TEXT DEFAULT '';")
        conn.commit()
    except Exception:
        conn.rollback()

    # 2. Tabel users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nama_lengkap TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'petugas',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()

    # 3. Seed akun default admin jika tabel users masih kosong
    cursor.execute("SELECT COUNT(*) FROM users;")
    count = cursor.fetchone()[0]
    if count == 0:
        default_admin_hash = hash_password("admin123")
        cursor.execute("""
            INSERT INTO users (username, password_hash, nama_lengkap, role)
            VALUES (%s, %s, %s, %s)
        """, ("admin", default_admin_hash, "Administrator DPMPTSP", "admin"))
        conn.commit()
        print("Default admin user created: username='admin', password='admin123'")

    conn.close()

# ==========================================
# PERIZINAN CRUD FUNCTIONS
# ==========================================

def insert_perizinan(data):
    """Insert data perizinan baru"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO perizinan (
        sektor, kategori_perizinan, nama_pengguna_layanan, nib, alamat, pemilik_pengurus,
        lokasi_usaha, luas_lahan_usaha, kbli, jenis_usaha, resiko,
        kapasitas, jenis_permohonan, nomor_permohonan, tanggal_permohonan,
        nomor_tanggal_permohonan_rekomendasi,
        nomor_tanggal_rekomendasi, nomor_izin, tanggal_izin,
        masa_berlaku, npwp, telepon, email, keterangan, jenis_dokumen, rencana_investasi
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data.get('sektor', ''), data.get('kategori_perizinan', ''), data.get('nama_pengguna_layanan', ''), data.get('nib', ''),
        data.get('alamat', ''), data.get('pemilik_pengurus', ''), data.get('lokasi_usaha', ''),
        data.get('luas_lahan_usaha', ''), data.get('kbli', ''), data.get('jenis_usaha', ''),
        data.get('resiko', ''), data.get('kapasitas', ''), data.get('jenis_permohonan', ''),
        data.get('nomor_permohonan', ''), data.get('tanggal_permohonan', ''),
        data.get('nomor_tanggal_permohonan_rekomendasi', ''),
        data.get('nomor_tanggal_rekomendasi', ''),
        data.get('nomor_izin', ''), data.get('tanggal_izin', ''), data.get('masa_berlaku', ''),
        data.get('npwp', ''), data.get('telepon', ''), data.get('email', ''),
        data.get('keterangan', ''), data.get('jenis_dokumen', ''), data.get('rencana_investasi', '')
    ))
    
    conn.commit()
    conn.close()

SELECT_COLS = """
    id, sektor, kategori_perizinan, nama_pengguna_layanan, nib, alamat,
    pemilik_pengurus, lokasi_usaha, luas_lahan_usaha, kbli, jenis_usaha,
    resiko, kapasitas, rencana_investasi, jenis_permohonan, nomor_permohonan, tanggal_permohonan,
    nomor_tanggal_permohonan_rekomendasi, nomor_tanggal_rekomendasi,
    nomor_izin, tanggal_izin, masa_berlaku, npwp,
    telepon, email, keterangan, jenis_dokumen, created_at, updated_at
"""

def get_all_perizinan(sektor=None):
    """Ambil semua data perizinan, optional filter by sektor"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if sektor and sektor != 'Semua':
        cursor.execute(f"SELECT {SELECT_COLS} FROM perizinan WHERE sektor = %s ORDER BY created_at DESC", (sektor,))
    else:
        cursor.execute(f"SELECT {SELECT_COLS} FROM perizinan ORDER BY created_at DESC")
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows

def get_perizinan_by_id(id):
    """Ambil data perizinan by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT {SELECT_COLS} FROM perizinan WHERE id = %s", (id,))
    row = cursor.fetchone()
    
    conn.close()
    return row

def update_perizinan(id, data):
    """Update data perizinan"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE perizinan SET
        sektor = %s, kategori_perizinan = %s, nama_pengguna_layanan = %s, nib = %s, alamat = %s,
        pemilik_pengurus = %s, lokasi_usaha = %s, luas_lahan_usaha = %s,
        kbli = %s, jenis_usaha = %s, resiko = %s, kapasitas = %s,
        jenis_permohonan = %s, nomor_permohonan = %s, tanggal_permohonan = %s,
        nomor_tanggal_permohonan_rekomendasi = %s,
        nomor_tanggal_rekomendasi = %s, nomor_izin = %s,
        tanggal_izin = %s, masa_berlaku = %s, npwp = %s, telepon = %s, email = %s,
        keterangan = %s, jenis_dokumen = %s, rencana_investasi = %s, updated_at = CURRENT_TIMESTAMP
    WHERE id = %s
    """, (
        data.get('sektor', ''), data.get('kategori_perizinan', ''), data.get('nama_pengguna_layanan', ''), data.get('nib', ''),
        data.get('alamat', ''), data.get('pemilik_pengurus', ''), data.get('lokasi_usaha', ''),
        data.get('luas_lahan_usaha', ''), data.get('kbli', ''), data.get('jenis_usaha', ''),
        data.get('resiko', ''), data.get('kapasitas', ''), data.get('jenis_permohonan', ''),
        data.get('nomor_permohonan', ''), data.get('tanggal_permohonan', ''),
        data.get('nomor_tanggal_permohonan_rekomendasi', ''),
        data.get('nomor_tanggal_rekomendasi', ''),
        data.get('nomor_izin', ''), data.get('tanggal_izin', ''), data.get('masa_berlaku', ''),
        data.get('npwp', ''), data.get('telepon', ''), data.get('email', ''),
        data.get('keterangan', ''), data.get('jenis_dokumen', ''), data.get('rencana_investasi', ''), id
    ))
    
    conn.commit()
    conn.close()

def delete_perizinan(id):
    """Hapus data perizinan"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM perizinan WHERE id = %s", (id,))
    
    conn.commit()
    conn.close()

def search_field_suggestions(field_name, search_term, limit=3):
    """Search suggestions untuk field tertentu (case-insensitive)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    valid_fields = [
        'nama_pengguna_layanan', 'nib', 'alamat', 'pemilik_pengurus',
        'lokasi_usaha', 'luas_lahan_usaha', 'kbli', 'jenis_usaha',
        'kapasitas', 'jenis_permohonan', 'nomor_permohonan',
        'nomor_tanggal_permohonan_rekomendasi', 'nomor_tanggal_rekomendasi',
        'nomor_izin', 'masa_berlaku', 'npwp', 'telepon', 'email', 'keterangan'
    ]
    
    if field_name not in valid_fields:
        conn.close()
        return []
    
    query = f"""
    SELECT DISTINCT {field_name}
    FROM perizinan
    WHERE {field_name} ILIKE %s AND {field_name} IS NOT NULL AND {field_name} != ''
    ORDER BY {field_name}
    LIMIT %s
    """
    
    cursor.execute(query, (f'%{search_term}%', limit))
    results = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return results

def get_available_years():
    """Mengambil daftar tahun unik dari tanggal_permohonan"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT DISTINCT SUBSTRING(tanggal_permohonan, 1, 4) as year 
    FROM perizinan 
    WHERE tanggal_permohonan IS NOT NULL AND tanggal_permohonan != '' AND LENGTH(tanggal_permohonan) >= 4
    ORDER BY year DESC
    """
    
    cursor.execute(query)
    years = [row[0] for row in cursor.fetchall() if row[0] and row[0].isdigit()]
    
    conn.close()
    return years

def get_analytics_metrics(period=None):
    """
    Get analytics metrics based on period filter
    period dict:
    - type: 'yearly', 'quarterly', 'monthly'
    - year: 'YYYY'
    - quarter: 'TW1', 'TW2', 'TW3', 'TW4' (optional)
    - month: 1-12 (optional)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    where_clauses = ["tanggal_permohonan IS NOT NULL", "tanggal_permohonan != ''"]
    params = []
    
    if period:
        if 'year' in period and period['year']:
            where_clauses.append("SUBSTRING(tanggal_permohonan, 1, 4) = %s")
            params.append(str(period['year']))
            
        if period['type'] == 'monthly' and 'month' in period:
            where_clauses.append("CAST(SUBSTRING(tanggal_permohonan, 6, 2) AS INTEGER) = %s")
            params.append(int(period['month']))
            
        elif period['type'] == 'quarterly' and 'quarter' in period:
            q_map = {
                'TW1': ['01', '02', '03'],
                'TW2': ['04', '05', '06'],
                'TW3': ['07', '08', '09'],
                'TW4': ['10', '11', '12']
            }
            months = q_map.get(period['quarter'], [])
            if months:
                placeholders = ','.join(['%s'] * len(months))
                where_clauses.append(f"SUBSTRING(tanggal_permohonan, 6, 2) IN ({placeholders})")
                params.extend(months)
    
    where_sql = " AND ".join(where_clauses)
    
    metrics = {}
    
    # 1. Jumlah Pelaku Usaha
    cursor.execute("SELECT COUNT(DISTINCT nama_pengguna_layanan) FROM perizinan")
    metrics['jumlah_pelaku'] = cursor.fetchone()[0] or 0
    
    # 2. Total NIB
    cursor.execute("SELECT COUNT(DISTINCT nib) FROM perizinan")
    metrics['total_nib'] = cursor.fetchone()[0] or 0
    
    # 3. Average Process Time (SLA)
    # PostgreSQL: validasi string format tanggal YYYY-MM-DD dengan regex
    cursor.execute("""
        SELECT AVG(tanggal_izin::date - tanggal_permohonan::date)
        FROM perizinan 
        WHERE tanggal_izin ~ '^\\d{4}-\\d{2}-\\d{2}$'
        AND tanggal_permohonan ~ '^\\d{4}-\\d{2}-\\d{2}$'
    """)
    avg_sla = cursor.fetchone()[0]
    metrics['avg_sla'] = round(float(avg_sla), 1) if avg_sla is not None else 0.0

    # 4. Risk Distribution
    cursor.execute("""
        SELECT resiko, COUNT(*) 
        FROM perizinan 
        WHERE resiko IS NOT NULL AND resiko != ''
        GROUP BY resiko
        ORDER BY COUNT(*) DESC
    """)
    metrics['risk_distribution'] = cursor.fetchall()
    
    # 5. Kategori Distribution
    cursor.execute("""
        SELECT kategori_perizinan, COUNT(*) 
        FROM perizinan 
        WHERE kategori_perizinan IS NOT NULL AND kategori_perizinan != ''
        GROUP BY kategori_perizinan
        ORDER BY COUNT(*) DESC
    """)
    metrics['kategori_distribution'] = cursor.fetchall()
    
    # 6. Time Trend
    cursor.execute("""
        SELECT SUBSTRING(tanggal_permohonan, 1, 7) as month, COUNT(*) 
        FROM perizinan 
        WHERE tanggal_permohonan IS NOT NULL AND tanggal_permohonan != '' AND LENGTH(tanggal_permohonan) >= 7
        GROUP BY month
        ORDER BY month
    """)
    metrics['time_trend'] = cursor.fetchall()
    
    # 7. Jenis Permohonan Distribution
    cursor.execute("""
        SELECT jenis_permohonan, COUNT(*) 
        FROM perizinan 
        WHERE jenis_permohonan IS NOT NULL AND jenis_permohonan != ''
        GROUP BY jenis_permohonan
        ORDER BY COUNT(*) DESC
    """)
    metrics['jenis_permohonan_dist'] = cursor.fetchall()
    
    # 8. Geo Distribution
    cursor.execute("""
        SELECT lokasi_usaha, COUNT(*) 
        FROM perizinan 
        WHERE lokasi_usaha IS NOT NULL AND lokasi_usaha != ''
        GROUP BY lokasi_usaha
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    metrics['geo_distribution'] = cursor.fetchall()
    
    # 9. Jenis Dokumen Distribution
    cursor.execute("""
        SELECT jenis_dokumen, COUNT(*) 
        FROM perizinan 
        WHERE jenis_dokumen IS NOT NULL AND jenis_dokumen != ''
        GROUP BY jenis_dokumen
        ORDER BY COUNT(*) DESC
    """)
    metrics['jenis_dokumen_dist'] = cursor.fetchall()
    
    conn.close()
    return metrics
