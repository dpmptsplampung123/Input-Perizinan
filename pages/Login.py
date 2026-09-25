import streamlit as st
from database import verify_user

# Desain tampilan halaman Login
st.markdown("""
<style>
    .login-container {
        max-width: 450px;
        margin: auto;
        padding: 2rem;
        background-color: #ffffff;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1f4788;
        margin-bottom: 0.3rem;
    }
    .login-subtitle {
        font-size: 0.95rem;
        color: #666666;
    }
</style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("""
    <div class="login-header">
        <div class="login-title">Sistem Perizinan DPMPTSP</div>
        <div class="login-subtitle">Provinsi Lampung &bull; Portal Petugas & Admin</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=False):
        st.subheader("Silakan Masuk")
        username = st.text_input("Nama Pengguna (Username)", placeholder="Contoh: admin").strip()
        password = st.text_input("Kata Sandi (Password)", type="password", placeholder="••••••••")
        
        submitted = st.form_submit_button("Masuk", type="primary", use_container_width=True)
        
        if submitted:
            if not username or not password:
                st.error("Username dan password wajib diisi.")
            else:
                user = verify_user(username, password)
                if user:
                    st.session_state["user"] = user
                    st.success(f"Selamat datang, {user['nama_lengkap']}!")
                    st.rerun()
                else:
                    st.error("Username atau password salah. Silakan coba lagi.")

    st.markdown("---")
    st.caption("Akses terbatas khusus pegawai dan petugas DPMPTSP Provinsi Lampung.")
