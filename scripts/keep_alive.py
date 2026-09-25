import os
import sys
from datetime import datetime

# Pastikan output utf-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def run_keep_alive():
    """Script ping berkala untuk menjaga Supabase Free Tier tetap aktif."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Memulai Supabase Keep-Alive Ping...")

    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

    # Jika dijalankan lokal, coba baca dari secrets.toml jika env kosong
    if not url:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(script_dir)
        secrets_path = os.path.join(root_dir, ".streamlit", "secrets.toml")
        if os.path.exists(secrets_path):
            try:
                import tomllib
                with open(secrets_path, "rb") as f:
                    data = tomllib.load(f)
                    url = data.get("supabase", {}).get("database_url") or data.get("database_url")
            except Exception as e:
                print(f"Gagal membaca secrets.toml lokal: {e}")

    if not url:
        print("[ERROR] Environment variable DATABASE_URL atau SUPABASE_DB_URL tidak ditemukan!")
        sys.exit(1)

    # Bersihkan query parameter pgbouncer jika ada
    if "?" in url:
        url = url.split("?")[0]

    try:
        import psycopg2
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        
        # 1. Kueri ringan ping
        cur.execute("SELECT 1;")
        res1 = cur.fetchone()[0]
        
        # 2. Baca jumlah data perizinan
        cur.execute("SELECT COUNT(*) FROM perizinan;")
        total_data = cur.fetchone()[0]
        
        print(f"[SUCCESS] Supabase Active & Responsive! Ping result: {res1}, Total data perizinan: {total_data}")
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"[FAIL] Gagal terhubung ke Supabase: {type(e).__name__} - {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_keep_alive()
