"""Halaman 1 — Beranda. Gerbang pemilihan PERAN (tanpa login) + syarat data.
Belum memilih peran  -> tampil dua pilihan: Pemilik Restoran / Pengembang.
Sudah memilih peran  -> tampil kartu modul sesuai peran + opsi ganti peran.
Pilihan peran disimpan di st.session_state["role"] dan dipakai app.py untuk
menyaring menu navigasi di sidebar."""
import streamlit as st
from core.ui import page_header, _md
from core.data import REQUIRED_CORE, POS_EXPECTED

role = st.session_state.get("role")  # None | "pemilik" | "developer"

IC = {
    "data": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/></svg>',
    "pie": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 11h.01"/><path d="M11 15h.01"/><path d="M16 16h.01"/><path d="m2 16 20 6-6-20A20 20 0 0 0 2 16"/><path d="M5.71 17.11a17.04 17.04 0 0 1 11.4-11.4"/></svg>',
    "receipt": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 17.5v-11"/></svg>',
    "chart": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 12v5h12V8l-5 5-4-4Z"/></svg>',
    "chart2": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>',
    "owner": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 7l1-4h18l1 4"/><path d="M2 7a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/><path d="M4 7v12a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V7"/><path d="M9 21v-6h6v6"/></svg>',
    "dev": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/><line x1="12" y1="4" x2="11" y2="20"/></svg>',
}


def module_card(icon, title, desc, href):
    inner = (f'<div class="menu-card-icon">{icon}</div>'
             f'<h3>{title}</h3><p>{desc}</p>'
             f'<span class="btn btn-primary btn-block">Buka modul</span>')
    return f'<a class="menu-card" href="{href}" target="_self">{inner}</a>'


def role_panel(icon, title, desc):
    """Kartu deskriptif peran (non-tautan); aksi pilih lewat tombol di bawahnya."""
    return (f'<div class="menu-card" style="cursor:default;">'
            f'<div class="menu-card-icon">{icon}</div>'
            f'<h3>{title}</h3><p>{desc}</p></div>')


# ====================== BELUM MEMILIH PERAN: pemilih ======================
if role is None:
    page_header(
        "Selamat datang di Dashboard BI Restoran X",
        "Pilih peran Anda untuk menampilkan modul yang sesuai. Tanpa login — "
        "peran dapat diganti kapan saja melalui sidebar.")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        _md(role_panel(
            IC["owner"], "Pemilik Restoran",
            "Sisi bisnis: telusuri data penjualan, segmentasi menu, dan segmentasi "
            "transaksi/nota beserta profil tiap segmen dan rekomendasi strategi promosi."))
        if st.button("Masuk sebagai Pemilik Restoran", key="pick_owner",
                     type="primary", use_container_width=True):
            st.session_state["role"] = "pemilik"
            st.rerun()
    with c2:
        _md(role_panel(
            IC["dev"], "Pengembang / Developer",
            "Sisi teknis: metrik evaluasi (Elbow, Silhouette, Davies-Bouldin), reduksi "
            "PCA, korelasi antar fitur, serta pemilihan kombinasi fitur dan jumlah klaster."))
        if st.button("Masuk sebagai Developer", key="pick_dev",
                     use_container_width=True):
            st.session_state["role"] = "developer"
            st.rerun()

# ====================== SUDAH MEMILIH PERAN: kartu modul ======================
else:
    if role == "pemilik":
        nama_peran = "Pemilik Restoran"
        ajakan = "Pilih salah satu modul bisnis di bawah untuk memulai."
        cards = [
            module_card(IC["data"], "Lihat Dataset",
                        "Unggah data POS (CSV/XLSX), jelajahi insight lewat panel kontrol, "
                        "lalu unduh hasil sesuai filter.", "lihat-dataset"),
            module_card(IC["pie"], "Klaster Menu",
                        "Segmentasi menu makanan &amp; minuman dengan K-Means++. Kontrol "
                        "klaster, lihat &amp; unduh hasilnya.", "klaster-menu"),
            module_card(IC["receipt"], "Klaster Transaksi",
                        "Segmentasi nota/transaksi dengan K-Means++. Telusuri profil segmen, "
                        "rincian kategori, lalu unduh.", "klaster-transaksi"),
        ]
    else:  # developer
        nama_peran = "Pengembang / Developer"
        ajakan = "Pilih salah satu modul teknis di bawah untuk memulai."
        cards = [
            module_card(IC["chart"], "Developer &middot; Menu",
                        "Eksperimen teknis lengkap: metrik Elbow/Silhouette/DBI, PCA, "
                        "heatmap korelasi, dan pemilihan kombinasi fitur.", "developer-menu"),
            module_card(IC["chart2"], "Developer &middot; Transaksi",
                        "Eksperimen teknis klaster transaksi: Elbow/Silhouette/DBI, PCA "
                        "2D/3D, korelasi, dan pemilihan kombinasi fitur.", "developer-transaksi"),
        ]

    page_header(
        "Selamat datang di Dashboard BI Restoran X",
        f"Peran aktif: <strong>{nama_peran}</strong>. {ajakan}")

    _md(f'<div class="src-pill">Peran aktif: <strong>{nama_peran}</strong> &middot; '
        'gunakan tombol <strong>Ganti peran</strong> di sidebar untuk berpindah.</div>')
    _md(f'<div class="menu-grid" style="margin-top:14px;">{"".join(cards)}</div>')

# ---- kartu format/syarat data (umum untuk kedua peran) ----
_chips = "".join(
    f'<span class="col-chip{" req" if c in REQUIRED_CORE else ""}">{c}</span>'
    for c in POS_EXPECTED)
_md('<div class="card card-cream" style="margin-top:24px;">'
    '<h3>Syarat &amp; Format Data</h3>'
    '<p>Dashboard ini bekerja setelah Anda <strong>memuat dataset</strong> pada tiap modul '
    '(belum ada hasil yang ditampilkan sebelum dijalankan). Berkas dapat berupa '
    '<strong>.csv</strong> maupun <strong>.xlsx</strong>, dan harus merupakan '
    '<strong>hasil ekspor langsung dari sistem POS</strong> (bukan data olahan bagian keuangan). '
    'Struktur kolom yang diharapkan:</p>'
    f'<div class="col-chips">{_chips}</div>'
    '<p style="font-size:11.8px;color:var(--text-dim);margin:8px 0 0;">'
    'Kolom bertanda hijau wajib ada. Kolom <strong>bulan</strong> tidak perlu disertakan — '
    'sistem otomatis menurunkannya dari kolom <strong>datetime</strong> untuk visual bulanan.</p></div>')
