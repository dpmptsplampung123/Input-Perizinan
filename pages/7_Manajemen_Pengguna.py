import streamlit as st
from database import get_all_users, create_user, delete_user, update_user_password

# Verifikasi hak akses admin
current_user = st.session_state.get("user")
if not current_user or current_user.get("role") != "admin":
    st.error("Akses ditolak. Halaman ini hanya untuk pengguna dengan hak akses Administrator.")
    st.stop()

st.title("Manajemen Pengguna & Hak Akses")
st.markdown("Kelola akun petugas dan administrator yang dapat mengakses Sistem Perizinan DPMPTSP.")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["Daftar Pengguna", "Tambah Pengguna Baru", "Ganti Password Pengguna"])

with tab1:
    st.subheader("Daftar Akun Terdaftar")
    users = get_all_users()
    
    if users:
        for u in users:
            u_id, username, full_name, role, created_at = u
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
                with col1:
                    st.write(f"**@{username}**")
                    badge = "🛡️ Admin" if role == "admin" else "👤 Petugas"
                    st.caption(badge)
                with col2:
                    st.write(full_name)
                    st.caption(f"Dibuat: {created_at.strftime('%d-%m-%Y %H:%M') if created_at else '-'}")
                with col3:
                    st.info(role.upper())
                with col4:
                    # Jangan biarkan admin menghapus dirinya sendiri jika hanya ada 1 admin
                    if u_id == current_user["id"]:
                        st.caption("Akun Anda saat ini")
                    else:
                        if st.button("Hapus", key=f"del_user_{u_id}", type="secondary"):
                            delete_user(u_id)
                            st.success(f"Pengguna @{username} berhasil dihapus.")
                            st.rerun()
                st.markdown("---")
    else:
        st.info("Belum ada data pengguna.")

with tab2:
    st.subheader("Form Tambah Pengguna")
    with st.form("form_add_user"):
        new_username = st.text_input("Username (huruf kecil/angka tanpa spasi)").strip().lower()
        new_fullname = st.text_input("Nama Lengkap Petugas").strip()
        new_password = st.text_input("Password", type="password")
        new_role = st.selectbox("Peran / Hak Akses", options=["petugas", "admin"], format_func=lambda x: "Petugas / Operator" if x == "petugas" else "Administrator")
        
        btn_add = st.form_submit_button("Simpan Pengguna", type="primary")
        if btn_add:
            if not new_username or not new_fullname or not new_password:
                st.error("Semua field wajib diisi.")
            elif len(new_password) < 6:
                st.error("Password minimal terdiri dari 6 karakter.")
            else:
                try:
                    create_user(new_username, new_password, new_fullname, new_role)
                    st.success(f"Pengguna @{new_username} ({new_fullname}) berhasil ditambahkan!")
                    st.rerun()
                except Exception as e:
                    if "unique" in str(e).lower():
                        st.error(f"Username @{new_username} sudah digunakan. Silakan gunakan username lain.")
                    else:
                        st.error(f"Gagal menambahkan pengguna: {str(e)}")

with tab3:
    st.subheader("Ganti Password Pengguna Lain / Diri Sendiri")
    users = get_all_users()
    user_options = {u[0]: f"{u[2]} (@{u[1]})" for u in users}
    
    with st.form("form_change_password"):
        selected_user_id = st.selectbox(
            "Pilih Pengguna",
            options=list(user_options.keys()),
            format_func=lambda x: user_options[x]
        )
        new_pass_input = st.text_input("Password Baru", type="password")
        confirm_pass_input = st.text_input("Konfirmasi Password Baru", type="password")
        
        btn_change = st.form_submit_button("Perbarui Password", type="primary")
        if btn_change:
            if not new_pass_input or not confirm_pass_input:
                st.error("Password baru wajib diisi.")
            elif new_pass_input != confirm_pass_input:
                st.error("Konfirmasi password tidak cocok.")
            elif len(new_pass_input) < 6:
                st.error("Password minimal 6 karakter.")
            else:
                try:
                    update_user_password(selected_user_id, new_pass_input)
                    st.success("Password berhasil diperbarui.")
                except Exception as e:
                    st.error(f"Gagal memperbarui password: {str(e)}")
