"""Dashboard BI Restoran X — entry point.
Jalankan dengan:  streamlit run app.py

Navigasi berbasis PERAN (tanpa login). Pengguna memilih peran di Beranda:
  - Pemilik Restoran  -> modul: Lihat Dataset, Klaster Menu, Klaster Transaksi
  - Pengembang        -> modul: Developer Menu, Developer Transaksi
Peran disimpan di st.session_state["role"] dan dapat diganti lewat tombol di sidebar.
"""
import streamlit as st
from core.ui import inject_css, sidebar_brand, sidebar_footer

st.set_page_config(
    page_title="Dashboard BI Restoran X",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ---- definisi halaman ----
beranda = st.Page("app_pages/p1_beranda.py", title="Beranda",
                  icon=":material/home:", url_path="beranda", default=True)
lihat = st.Page("app_pages/p2_lihat_dataset.py", title="Lihat Dataset",
                icon=":material/database:", url_path="lihat-dataset")
kmenu = st.Page("app_pages/p3_klaster_menu.py", title="Klaster Menu",
                icon=":material/pie_chart:", url_path="klaster-menu")
ktrx = st.Page("app_pages/p4_klaster_transaksi.py", title="Klaster Transaksi",
               icon=":material/receipt_long:", url_path="klaster-transaksi")
devm = st.Page("app_pages/p5_dev_menu.py", title="Developer · Menu",
               icon=":material/insights:", url_path="developer-menu")
devt = st.Page("app_pages/p6_dev_transaksi.py", title="Developer · Transaksi",
               icon=":material/monitoring:", url_path="developer-transaksi")

# ---- gerbang peran (tanpa login) ----
role = st.session_state.get("role")  # None | "pemilik" | "developer"
if role == "pemilik":
    allowed = [beranda, lihat, kmenu, ktrx]
elif role == "developer":
    allowed = [beranda, devm, devt]
else:
    allowed = [beranda]

# routing saja; UI nav dirender manual agar brand bisa di atas
nav = st.navigation(allowed, position="hidden")

# ---- sidebar: brand -> nav (sesuai peran) -> ganti peran -> footer ----
sidebar_brand()
with st.sidebar:
    if role == "pemilik":
        st.markdown('<div class="nav-group">Pemilik Restoran</div>', unsafe_allow_html=True)
        st.page_link(beranda)
        st.page_link(lihat)
        st.page_link(kmenu)
        st.page_link(ktrx)
    elif role == "developer":
        st.markdown('<div class="nav-group">Pengembang</div>', unsafe_allow_html=True)
        st.page_link(beranda)
        st.page_link(devm)
        st.page_link(devt)
    else:
        st.markdown('<div class="nav-group">Menu</div>', unsafe_allow_html=True)
        st.page_link(beranda)
        st.caption("Pilih peran di halaman Beranda untuk menampilkan modul.")

    if role is not None:
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        if st.button("↩  Ganti peran", use_container_width=True, key="switch_role"):
            st.session_state["role"] = None
            st.switch_page(beranda)
sidebar_footer()

nav.run()
