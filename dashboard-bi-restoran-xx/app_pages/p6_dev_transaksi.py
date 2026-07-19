"""Halaman 6 — Developer · Transaksi (teknis). Analisis lengkap klaster tingkat
transaksi (per nota): pemilihan fitur (kombinasi fitur dasar & rekayasa, 1..maks),
penentuan K (Elbow/Silhouette/DBI), korelasi fitur, proyeksi PCA 2D/3D, sebaran, dan
komposisi klaster. Model (K-Means++ / K-Means) dipilih langsung; hasil tampil setelah
menekan 'Run model'."""
import streamlit as st
from sklearn.decomposition import PCA
from core.ui import page_header, _md
from core.data import download_button
from core.session import ensure_data_loaded
from core import cluster, charts
from core import transaksi as trx

# fitur dasar untuk heatmap korelasi (memperlihatkan dasar pemilihan subset fitur)
BASE_FEATS = ["frek_makanan", "frek_minuman", "total_qty",
              "n_item_unik", "total_net", "total_gross"]
KMAX = 10  # rentang K sesuai Notebook 04 (k = 2..10)


def num(x):
    return f"{x:,.0f}".replace(",", ".")


page_header(
    "Developer · Transaksi",
    "Eksperimen teknis klaster tingkat transaksi: pilih kombinasi fitur & model, "
    "tentukan K, lihat korelasi fitur, proyeksi PCA 2D/3D, dan komposisi klaster.")

df = ensure_data_loaded("Modul Developer · Transaksi")

if "receipt_number" not in df.columns:
    st.warning("Dataset belum memiliki kolom **receipt_number**, sehingga agregasi per "
               "nota tidak dapat dilakukan. Unggah ekspor POS yang menyertakan nomor nota.")
    st.stop()

nota_base = trx.build_transaksi_features(df)
if len(nota_base) < trx.TRX_K + 1:
    st.warning("Data nota tidak cukup untuk analisis pada dataset ini.")
    st.stop()

# ---- kontrol: model + pemilihan fitur + tombol run ----
c = st.columns([1, 2])
algo_label = c[0].radio("Model", ["K-Means++", "K-Means"])
feats = c[1].multiselect(
    "Fitur klaster (pilih 1..maks; boleh lebih dari 2 fitur)",
    trx.CANDIDATE_FEATURES, default=list(trx.TRX_FEATURES),
    format_func=lambda f: trx.FEATURE_LABEL.get(f, f))
st.caption("Rekomendasi fitur penelitian (hasil uji VIF — seluruhnya di bawah "
           "ambang 10): Frekuensi makanan + Frekuensi minuman + Nilai belanja (net). "
           "Kombinasi lain boleh dieksplorasi untuk kepentingan pengembang; mutu klaster "
           "yang dihasilkan dapat lebih rendah dan tidak diberi pelabelan segmen.")
run = st.button("Run model", type="primary")

current_cfg = (algo_label, tuple(sorted(feats)))
if run:
    st.session_state["dev_cfg_trx"] = current_cfg
cfg = st.session_state.get("dev_cfg_trx")

if cfg is None:
    st.info("Pilih **Model** dan **Fitur klaster** di atas, lalu tekan **Run model** "
            "untuk menjalankan analisis. Hasil tidak ditampilkan sebelum dijalankan.")
    st.stop()
if cfg != current_cfg:
    st.warning("Konfigurasi berubah sejak terakhir dijalankan. Tekan **Run model** "
               "untuk memperbarui hasil di bawah.")

g_algo_label, g_feats = cfg[0], list(cfg[1])
g_algo = "kmeans++" if g_algo_label == "K-Means++" else "kmeans"
if len(g_feats) < 1:
    st.warning("Pilih minimal satu fitur untuk menjalankan klaster.")
    st.stop()
n_feat = len(g_feats)
is_reco = set(g_feats) == set(trx.TRX_FEATURES)

# ---- praproses + klaster final (winsorize p99 -> Z-score -> K-Means(++)) ----
# K=5 bila kombinasi fitur = rekomendasi penelitian; selain itu K dipilih dari Silhouette.
Xz, _scaler = trx.prep_features(nota_base, g_feats)
metrik = cluster.metrics_over_k(Xz, 2, KMAX, algo=g_algo)
k_sil = int(metrik.loc[metrik["silhouette"].idxmax(), "K"])
k_dbi = int(metrik.loc[metrik["dbi"].idxmin(), "K"])
k_pakai = trx.TRX_K if is_reco else k_sil

res = cluster.run_clustering(Xz, k_pakai, algo=g_algo)
nota = nota_base.copy()
nota["cluster"] = res["labels"]

fitur_txt = " + ".join(trx.FEATURE_LABEL.get(x, x) for x in g_feats)
reko_tag = " (rekomendasi penelitian)" if is_reco else " (kombinasi eksplorasi)"
_md(f'<div class="src-pill">Model: <strong>{g_algo_label}</strong> &middot; '
    f'Fitur: <strong>{fitur_txt}</strong>{reko_tag} &middot; '
    f'Praproses: <strong>winsorize p99 + Z-score</strong> &middot; {num(len(nota))} nota</div>')

st.markdown('<div class="panel-title">Penentuan K — Elbow, Silhouette, DBI</div>',
            unsafe_allow_html=True)
g = st.columns(3)
with g[0]:
    st.plotly_chart(charts.line_metric_over_k(metrik, "SSE_inertia",
                    "Elbow (SSE / Inertia)", "SSE", best_k=k_pakai),
                    use_container_width=True)
with g[1]:
    st.plotly_chart(charts.line_metric_over_k(metrik, "silhouette",
                    "Silhouette (maks lebih baik)", "Silhouette", best_k=k_sil),
                    use_container_width=True)
with g[2]:
    st.plotly_chart(charts.line_metric_over_k(metrik, "dbi",
                    "Davies-Bouldin (min lebih baik)", "DBI", best_k=k_dbi),
                    use_container_width=True)
if is_reco:
    st.caption(f"Silhouette maksimum pada K={k_sil}; DBI minimum pada K={k_dbi}. "
               f"K yang dipakai: {k_pakai} (mengikuti kesimpulan penelitian versi  — "
               f"Silhouette tertinggi 0,5176 berkategori struktur 'baik', diselaraskan DBI, "
               f"kandidat dalam rentang ±0,02).")
else:
    st.caption(f"Silhouette maksimum pada K={k_sil}; DBI minimum pada K={k_dbi}. "
               f"K yang dipakai: {k_pakai} (Silhouette tertinggi untuk kombinasi fitur ini).")
show = metrik.copy()
show["SSE_inertia"] = show["SSE_inertia"].round(3)
show["silhouette"] = show["silhouette"].round(4)
show["dbi"] = show["dbi"].round(4)
st.dataframe(show, use_container_width=True, hide_index=True)
download_button(show, "Unduh metrik per K (CSV)", "metrik_K_transaksi.csv",
                key="dl_metrik_trx")

# ---- heatmap korelasi fitur dasar ----
st.markdown('<div class="panel-title">Korelasi Antar-Fitur Dasar</div>',
            unsafe_allow_html=True)
hcols = [x for x in BASE_FEATS if x in nota.columns]
st.plotly_chart(charts.heatmap_corr(nota.fillna(nota[hcols].median()), hcols,
                "Heatmap Korelasi Fitur Dasar Transaksi"), use_container_width=True)
st.caption("Fitur besaran (total_qty, n_item_unik, total_gross) berkorelasi sangat tinggi "
           "dengan total_net — semuanya mengukur dimensi besaran nota yang sama sehingga "
           "cukup diwakili X3 Nilai belanja. Fitur terpilih penelitian: X1 frek_makanan, "
           "X2 frek_minuman, X3 total_net; ketiganya memiliki VIF di bawah ambang 10 "
           "sehingga multikolinearitas dapat diterima dan PCA tidak diperlukan.")

# ---- proyeksi PCA 2D & 3D (ruang fitur final) ----
st.markdown('<div class="panel-title">Proyeksi PCA 2 Komponen (2D)</div>',
            unsafe_allow_html=True)
if n_feat >= 2:
    pca2 = PCA(n_components=2, random_state=42).fit(Xz)
    co2 = pca2.transform(Xz)
    v1, v2 = pca2.explained_variance_ratio_[:2] * 100
    st.plotly_chart(charts.scatter_pca(co2, nota["cluster"].values,
                    "Proyeksi PCA 2D Hasil Klaster", v1, v2), use_container_width=True)
else:
    st.info("Proyeksi PCA 2D memerlukan minimal 2 fitur. Tambahkan fitur untuk menampilkan proyeksi ini.")

st.markdown('<div class="panel-title">Proyeksi PCA 3 Komponen (3D)</div>',
            unsafe_allow_html=True)
if n_feat >= 3:
    pca3 = PCA(n_components=3, random_state=42).fit(Xz)
    co3 = pca3.transform(Xz)
    w1, w2, w3 = pca3.explained_variance_ratio_[:3] * 100
    st.plotly_chart(charts.scatter_pca_3d(co3, nota["cluster"].values,
                    "Proyeksi PCA 3D Hasil Klaster", w1, w2, w3), use_container_width=True)
    st.caption(f"Klik & seret untuk memutar grafik 3D. Total varians 3 komponen: {w1+w2+w3:.1f}%.")
else:
    st.info("Proyeksi PCA 3D memerlukan minimal 3 fitur. Tambahkan fitur untuk menampilkan proyeksi ini.")

# ---- komposisi klaster (bar + pie) ----
st.markdown('<div class="panel-title">Komposisi Klaster</div>', unsafe_allow_html=True)
gc = st.columns(2)
with gc[0]:
    st.plotly_chart(charts.bar_clusters(nota, "cluster", "Jumlah Transaksi per Klaster",
                    agg="count"), use_container_width=True)
with gc[1]:
    st.plotly_chart(charts.pie_clusters(nota, "cluster", "Kontribusi Pendapatan per Klaster",
                    value="total_net", agg="sum"), use_container_width=True)

# ---- sebaran ruang fitur ----
st.markdown('<div class="panel-title">Sebaran Klaster pada Ruang Fitur</div>',
            unsafe_allow_html=True)
if n_feat >= 2:
    fx, fy = g_feats[0], g_feats[1]
    pdf = nota[["nota", "cluster"]].copy()
    pdf[fx] = trx.plot_axis(nota[fx], fx).values
    pdf[fy] = trx.plot_axis(nota[fy], fy).values
    st.plotly_chart(charts.scatter_clusters(
        pdf, fx, fy, "cluster", "Sebaran Nota per Klaster",
        text_col="nota", xlab=trx.FEATURE_LABEL.get(fx, fx),
        ylab=trx.FEATURE_LABEL.get(fy, fy)), use_container_width=True)
else:
    st.info("Sebaran ruang fitur memerlukan minimal 2 fitur (sumbu X & Y).")

# ---- tabel hasil (sertakan rincian item tiap nota, termasuk custom amount) ----
st.markdown('<div class="panel-title">Data Hasil Klaster</div>', unsafe_allow_html=True)
items_map = trx.build_nota_items(df)
out = nota[["nota", "cluster", "frek_makanan", "frek_minuman", "total_net",
            "total_qty", "n_item_unik", "total_gross"]].copy()
out = out.merge(items_map, on="nota", how="left")
out["items"] = out["items"].fillna("")
out = out.sort_values(["cluster", "total_net"], ascending=[True, False])
# kolom 'items' diletakkan tepat setelah identitas nota agar isi nota mudah terbaca
cols_order = ["nota", "items", "cluster", "frek_makanan", "frek_minuman", "total_net",
              "total_qty", "n_item_unik", "total_gross"]
out = out[cols_order]
st.dataframe(out, use_container_width=True, height=380, hide_index=True,
             column_config={"items": st.column_config.TextColumn("items", width="large")})
st.caption("Kolom items memuat seluruh isi nota — termasuk entri custom amount — sesuai "
           "skema penelitian tingkat transaksi yang mempertahankan nilai nota utuh.")
download_button(out, "Unduh hasil klaster (CSV)", "dev_klaster_transaksi.csv",
                key="dl_dev_trx")
