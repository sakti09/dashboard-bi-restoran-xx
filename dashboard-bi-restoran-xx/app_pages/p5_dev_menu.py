"""Halaman 5 — Developer · Menu (teknis). Analisis lengkap klaster menu.
Hasil hanya tampil setelah menekan 'Run model'."""
import streamlit as st
from sklearn.decomposition import PCA
from core.ui import page_header, _md
from core.data import download_button
from core.session import ensure_data_loaded
from core import cluster, charts
from core.menu import (build_menu_features, prep_menu_features, FEATURE_SCHEMES,
                       FEATURE_LABEL, THESIS_K)

FULL_FEATS = ["quantity", "frequency", "net_revenue", "avg_price", "units_per_order"]

page_header("Developer · Menu",
            "Eksperimen teknis klaster tingkat menu: penentuan K, perbandingan algoritme, korelasi fitur, proyeksi PCA 2D/3D, dan komposisi klaster.")

df = ensure_data_loaded("Modul Developer · Menu")
menu = build_menu_features(df)

# ---- kontrol + tombol run ----
c = st.columns([1, 1, 2])
grup = c[0].radio("Kelompok", ["makanan", "minuman"], format_func=str.capitalize)
algo_label = c[1].radio("Model", ["K-Means++", "K-Means"])
scheme_name = c[2].selectbox("Skema fitur", list(FEATURE_SCHEMES.keys()))
run = st.button("Run model", type="primary")

current_cfg = (grup, algo_label, scheme_name)
if run:
    st.session_state["dev_cfg"] = current_cfg
cfg = st.session_state.get("dev_cfg")

if cfg is None:
    st.info("Atur **Kelompok**, **Model**, dan **Skema fitur** di atas, lalu tekan "
            "**Run model** untuk menjalankan analisis. Hasil tidak ditampilkan sebelum dijalankan.")
    st.stop()
if cfg != current_cfg:
    st.warning("Konfigurasi berubah sejak terakhir dijalankan. Tekan **Run model** "
               "untuk memperbarui hasil di bawah.")

# ---- pakai konfigurasi saat Run ditekan ----
g_grup, g_algo_label, g_scheme = cfg
g_algo = "kmeans++" if g_algo_label == "K-Means++" else "kmeans"
g_feat, g_is_main = FEATURE_SCHEMES[g_scheme]

sub = menu[menu["grup"] == g_grup].dropna(subset=g_feat).reset_index(drop=True)
if len(sub) < 5:
    st.warning("Data tidak cukup untuk analisis pada kelompok ini.")
    st.stop()

# ---- praproses (identik Notebook 03: winsorize p95 hanya avg_price -> Z-score) ----
Xz, _ = prep_menu_features(sub, g_feat)

# ---- metrik per K ----
KMAX = 8
metrik = cluster.metrics_over_k(Xz, 2, KMAX, algo=g_algo)
k_sil = int(metrik.loc[metrik["silhouette"].idxmax(), "K"])
k_dbi = int(metrik.loc[metrik["dbi"].idxmin(), "K"])
k_pakai = THESIS_K[g_grup] if g_is_main else k_sil

fitur_txt = " + ".join(FEATURE_LABEL.get(x, x) for x in g_feat)
_md(f'<div class="src-pill">Kelompok: <strong>{g_grup.capitalize()}</strong> &middot; '
    f'Model: <strong>{g_algo_label}</strong> &middot; Fitur: <strong>{fitur_txt}</strong> '
    f'&middot; {len(sub)} menu</div>')

st.markdown('<div class="panel-title">Penentuan K — Elbow, Silhouette, DBI</div>',
            unsafe_allow_html=True)
g = st.columns(3)
with g[0]:
    st.plotly_chart(charts.line_metric_over_k(metrik, "SSE_inertia",
                    "Elbow (SSE / Inertia)", "SSE", best_k=k_pakai), use_container_width=True)
with g[1]:
    st.plotly_chart(charts.line_metric_over_k(metrik, "silhouette",
                    "Silhouette (maks lebih baik)", "Silhouette", best_k=k_sil),
                    use_container_width=True)
with g[2]:
    st.plotly_chart(charts.line_metric_over_k(metrik, "dbi",
                    "Davies-Bouldin (min lebih baik)", "DBI", best_k=k_dbi),
                    use_container_width=True)
st.caption(f"Silhouette maksimum pada K={k_sil}; DBI minimum pada K={k_dbi}. "
           f"K yang dipakai: {k_pakai}"
           + (" (mengikuti kesimpulan penelitian)." if g_is_main else " (Silhouette tertinggi)."))
show = metrik.copy()
show["SSE_inertia"] = show["SSE_inertia"].round(3)
show["silhouette"] = show["silhouette"].round(4)
show["dbi"] = show["dbi"].round(4)
st.dataframe(show, use_container_width=True, hide_index=True)
download_button(show, "Unduh metrik per K (CSV)", f"metrik_K_{g_grup}.csv", key="dl_metrik")

# ---- klaster final (model terpilih) ----
res = cluster.run_clustering(Xz, k_pakai, algo=g_algo)
sub["cluster"] = res["labels"]

# ---- heatmap korelasi ----
st.markdown('<div class="panel-title">Korelasi Antar-Fitur</div>', unsafe_allow_html=True)
hcols = [x for x in FULL_FEATS if x in sub.columns]
st.plotly_chart(charts.heatmap_corr(sub.fillna(sub[hcols].median()), hcols,
                "Heatmap Korelasi Fitur Menu"), use_container_width=True)
st.caption("Korelasi tinggi (mendekati 1) menandakan fitur saling tumpang tindih — "
           "dasar pemilihan subset fitur pada skema utama.")

# ---- PCA: hitung sekali untuk 2D & 3D ----
Xfull = sub[hcols].fillna(sub[hcols].median())
Xfull_z, _ = cluster.standardize(Xfull)

st.markdown('<div class="panel-title">Proyeksi PCA 2 Komponen (2D)</div>', unsafe_allow_html=True)
pca2 = PCA(n_components=2).fit(Xfull_z)
co2 = pca2.transform(Xfull_z)
v1, v2 = pca2.explained_variance_ratio_[:2] * 100
st.plotly_chart(charts.scatter_pca(co2, sub["cluster"].values,
                "Proyeksi PCA 2D Hasil Klaster", v1, v2), use_container_width=True)

st.markdown('<div class="panel-title">Proyeksi PCA 3 Komponen (3D)</div>', unsafe_allow_html=True)
pca3 = PCA(n_components=3).fit(Xfull_z)
co3 = pca3.transform(Xfull_z)
w1, w2, w3 = pca3.explained_variance_ratio_[:3] * 100
st.plotly_chart(charts.scatter_pca_3d(co3, sub["cluster"].values,
                "Proyeksi PCA 3D Hasil Klaster", w1, w2, w3), use_container_width=True)
st.caption(f"Klik & seret untuk memutar grafik 3D. Total varians 3 komponen: {w1+w2+w3:.1f}%.")

# ---- komposisi klaster (bar + pie, insight kelompok) ----
st.markdown('<div class="panel-title">Komposisi Klaster</div>', unsafe_allow_html=True)
gc = st.columns(2)
with gc[0]:
    st.plotly_chart(charts.bar_clusters(sub, "cluster", "Jumlah Menu per Klaster",
                    agg="count"), use_container_width=True)
with gc[1]:
    st.plotly_chart(charts.pie_clusters(sub, "cluster", "Kontribusi Pendapatan per Klaster",
                    value="net_revenue", agg="sum"), use_container_width=True)

# ---- sebaran ruang fitur ----
st.markdown('<div class="panel-title">Sebaran Klaster pada Ruang Fitur</div>',
            unsafe_allow_html=True)
st.plotly_chart(charts.scatter_clusters(sub, g_feat[0], g_feat[1], "cluster",
                "Sebaran Menu per Klaster", xlab=FEATURE_LABEL.get(g_feat[0]),
                ylab=FEATURE_LABEL.get(g_feat[1])), use_container_width=True)
if len(g_feat) > 2:
    st.caption(f"Skema ini memakai {len(g_feat)} fitur; sebaran menampilkan dua fitur pertama "
               "sebagai sumbu, sedangkan klaster dihitung pada seluruh fitur terpilih.")

# ---- tabel hasil ----
st.markdown('<div class="panel-title">Data Hasil Klaster</div>', unsafe_allow_html=True)
out = sub[["items", "category", "cluster"] + hcols].copy()
out["avg_price"] = out["avg_price"].round(0)
out["units_per_order"] = out["units_per_order"].round(2)
out = out.sort_values(["cluster", "quantity"], ascending=[True, False])
st.dataframe(out, use_container_width=True, height=380, hide_index=True)
download_button(out, "Unduh hasil klaster (CSV)", f"dev_klaster_menu_{g_grup}.csv", key="dl_dev")
