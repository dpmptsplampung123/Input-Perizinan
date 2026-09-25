import streamlit as st
from database import init_database

# Konfigurasi page global
st.set_page_config(
    page_title="Sistem Perizinan DPMPTSP",
    page_icon="🏛️",
    layout="wide"
)

# Inisialisasi database
try:
    init_database()
except Exception as e:
    st.error(f"Gagal menghubungkan ke database Supabase: {str(e)}")
    st.info("Pastikan konfigurasi di .streamlit/secrets.toml sudah benar.")
    st.stop()

# Cek status login pengguna
current_user = st.session_state.get("user")

if not current_user:
    # Jika belum login, hanya arahkan ke halaman login
    pg = st.navigation([st.Page("pages/Login.py", title="Masuk ke Sistem", icon="🔐")])
else:
    # Tampilkan informasi user dan tombol logout di sidebar
    st.sidebar.markdown(f"### 👤 {current_user['nama_lengkap']}")
    role_badge = "🛡️ Administrator" if current_user.get("role") == "admin" else "📋 Petugas"
    st.sidebar.caption(f"Akses: **{role_badge}** (@{current_user['username']})")
    
    if st.sidebar.button("🚪 Keluar / Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("---")

    # Daftar halaman utama yang diakses petugas/admin
    pages = [
        st.Page("pages/Home.py", title="Beranda", icon="🏠"),
        st.Page("pages/1_Input_Data_Perizinan.py", title="Input Pendaftaran", icon="📝"),
        st.Page("pages/2_Data_Perizinan.py", title="Masa Berlaku", icon="⏳"),
        st.Page("pages/6_SLA_Monitoring.py", title="SLA Monitoring", icon="⏱️"),
        st.Page("pages/4_Tabel_Data.py", title="Tabel Data", icon="📋"),
        st.Page("pages/5_Import_Data.py", title="Import Data", icon="📥"),
        st.Page("pages/3_Analytics.py", title="Dashboard", icon="📊"),
    ]

    # Halaman manajemen pengguna khusus Administrator
    if current_user.get("role") == "admin":
        pages.append(st.Page("pages/7_Manajemen_Pengguna.py", title="Manajemen Pengguna", icon="⚙️"))

    pg = st.navigation(pages)

# Jalankan Halaman
pg.run()
