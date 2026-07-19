"""Halaman 3 — Klaster Menu (pemilik). Hasil klaster (data), bukan metrik.
Skema utama (rekomendasi penelitian) berprofil persona + rekomendasi bisnis
sesuai hasil penelitian; skema alternatif (boleh lebih dari 2 fitur) tanpa profil.
Hasil tampil setelah menekan 'Run model'."""
import streamlit as st
from core.ui import page_header, _md
from core.data import download_button
from core.session import ensure_data_loaded
from core import cluster, charts
from core.menu import (build_menu_features, prep_menu_features, FEATURE_SCHEMES,
                       FEATURE_LABEL, THESIS_K, profile_clusters)


def num(x):
    return f"{x:,.0f}".replace(",", ".")


page_header("Klaster Menu",
            "Segmentasi menu makanan & minuman dengan K-Means++. Atur kelompok & skema, "
            "jalankan model, lalu telusuri dan unduh hasilnya.")

df = ensure_data_loaded("Modul Klaster Menu")
menu = build_menu_features(df)

# ---- pilihan kelompok & skema + tombol run ----
st.markdown('<div class="panel-title">Konfigurasi Klaster</div>', unsafe_allow_html=True)
with st.container(border=True):
    top = st.columns([1, 2])
    grup = top[0].radio("Kelompok menu", ["makanan", "minuman"],
                        format_func=str.capitalize, horizontal=True)
    scheme_name = top[1].selectbox("Skema fitur", list(FEATURE_SCHEMES.keys()))
    run = st.button("Run model", type="primary")

current_cfg = (grup, scheme_name)
if run:
    st.session_state["menu_cfg"] = current_cfg
cfg = st.session_state.get("menu_cfg")

if cfg is None:
    st.info("Pilih **Kelompok menu** dan **Skema fitur** di atas, lalu tekan **Run model** "
            "untuk menjalankan segmentasi. Hasil tidak ditampilkan sebelum dijalankan.")
    st.stop()
if cfg != current_cfg:
    st.warning("Konfigurasi berubah sejak terakhir dijalankan. Tekan **Run model** "
               "untuk memperbarui hasil di bawah.")

g_grup, g_scheme = cfg
feat_cols, do_profile = FEATURE_SCHEMES[g_scheme]

sub = menu[menu["grup"] == g_grup].dropna(subset=feat_cols).reset_index(drop=True)
if len(sub) < 3:
    st.warning("Data menu pada kelompok ini tidak cukup untuk diklaster.")
    st.stop()

# ---- pipeline (identik Notebook 03): winsorize p95 HANYA avg_price -> z-score -> K-Means++ ----
Xz, _ = prep_menu_features(sub, feat_cols)
k = THESIS_K[g_grup] if do_profile else cluster.best_k_by_silhouette(Xz, 2, 6)
res = cluster.run_clustering(Xz, k, algo="kmeans++")
sub["cluster"] = res["labels"]
profil_map, reko_map = {}, {}
if do_profile:
    sub["profil"], profil_map, reko_map = profile_clusters(sub)

# ---- info skema ----
fitur_txt = " + ".join(FEATURE_LABEL.get(c, c) for c in feat_cols)
catatan = ("Skema rekomendasi penelitian (fitur X1 Kuantitas & X2 Harga rata-rata; "
           "winsorize p95 pada harga; Z-score; K-Means++), lengkap dengan persona "
           "dan rekomendasi bisnis tiap klaster sesuai hasil penelitian."
           if do_profile else
           "Skema alternatif pilihan pengguna — tanpa profil persona; K dipilih otomatis (Silhouette).")
_md(f'<div class="src-pill">Kelompok: <strong>{g_grup.capitalize()}</strong> &middot; '
    f'Fitur: <strong>{fitur_txt}</strong> &middot; Jumlah klaster: <strong>{k}</strong> &middot; '
    f'{len(sub)} menu</div>')
st.caption(catatan)

# ---- panel kontrol klaster & kategori ----
st.markdown('<div class="panel-title">Panel Kontrol</div>', unsafe_allow_html=True)
with st.container(border=True):
    pc = st.columns([1.4, 1])
    clusters_avail = sorted(sub["cluster"].unique().tolist())
    sel_cl = pc[0].multiselect("Tampilkan klaster", clusters_avail,
                               default=clusters_avail,
                               format_func=lambda i: f"Klaster {i}")
    cats = sorted(sub["category"].dropna().unique().tolist())
    sel_cat = pc[1].multiselect("Filter kategori", cats, default=cats)

view = sub[sub["cluster"].isin(sel_cl) & sub["category"].isin(sel_cat)].copy()
if len(view) == 0:
    st.warning("Tidak ada menu untuk kombinasi klaster/kategori ini.")
    st.stop()

# ---- ringkasan tiap klaster (chips) ----
chips = ""
for c in clusters_avail:
    n = int((sub["cluster"] == c).sum())
    col = charts.cluster_color(c)
    extra = f' &middot; {profil_map.get(c)}' if do_profile else ''
    chips += (f'<div class="cl-chip"><span class="cl-dot" style="background:{col}"></span>'
              f'Klaster {c} &middot; {n} menu{extra}</div>')
_md(f'<div class="cl-row">{chips}</div>')

# ---- sebaran hasil klaster (visual hasil, bukan metrik) ----
label_map = profil_map if do_profile else None
fig = charts.scatter_clusters(
    view, x=feat_cols[0], y=feat_cols[1], cluster_col="cluster",
    title="Sebaran Menu per Klaster", label_map=label_map,
    xlab=FEATURE_LABEL.get(feat_cols[0]), ylab=FEATURE_LABEL.get(feat_cols[1]))
st.plotly_chart(fig, use_container_width=True)
if len(feat_cols) > 2:
    st.caption(f"Skema ini memakai {len(feat_cols)} fitur; sebaran menampilkan dua fitur "
               "pertama sebagai sumbu, sedangkan klaster dihitung pada seluruh fitur terpilih.")

# ---- komposisi klaster: diagram batang + lingkaran ----
gc = st.columns(2)
with gc[0]:
    st.plotly_chart(
        charts.bar_clusters(view, "cluster", "Jumlah Menu per Klaster",
                            agg="count", label_map=label_map),
        use_container_width=True)
with gc[1]:
    st.plotly_chart(
        charts.pie_clusters(view, "cluster", "Kontribusi Pendapatan per Klaster",
                            value="net_revenue", agg="sum", label_map=label_map),
        use_container_width=True)

# ---- profil persona & rekomendasi (skema utama; sesuai hasil penelitian) ----
st.markdown('<div class="panel-title">Profil Persona & Rekomendasi</div>',
            unsafe_allow_html=True)
if do_profile:
    tot_rev = sub["net_revenue"].sum()
    prof = (sub.groupby("cluster")
               .agg(n=("items", "size"), q=("quantity", "mean"),
                    p=("avg_price", "mean"), rev=("net_revenue", "sum"))
               .reset_index())
    prof["share"] = (prof["rev"] / tot_rev * 100).round(1)
    prof = prof.sort_values("share", ascending=False)
    for _, r in prof.iterrows():
        c = int(r["cluster"])
        if c not in sel_cl:
            continue
        col = charts.cluster_color(c)
        contoh = ", ".join(sub[sub["cluster"] == c]
                           .nlargest(3, "net_revenue")["items"].tolist())
        stats = (f'<span>Menu: <strong>{int(r["n"])}</strong></span>'
                 f'<span>Rata kuantitas: <strong>{r["q"]:.1f}</strong></span>'
                 f'<span>Rata harga: <strong>Rp {r["p"]:,.0f}</strong></span>'
                 f'<span>Kontribusi pendapatan: <strong>{r["share"]}%</strong></span>')
        _md(f'<div class="card prof-card" style="border-left:3px solid {col};margin-bottom:12px;">'
            f'<div class="prof-head"><span class="cl-dot" style="background:{col}"></span>'
            f'<strong>Klaster {c} &middot; {profil_map.get(c, "")}</strong></div>'
            f'<div class="prof-stats">{stats}</div>'
            f'<p class="prof-reko">{reko_map.get(c, "")}</p>'
            f'<p class="prof-reko" style="opacity:.8;">Contoh menu terlaris: {contoh}.</p></div>')
    st.caption("Persona & rekomendasi mengikuti hasil penelitian: karakterisasi popularitas × "
               "harga relatif median (ambang 15%) pada klaster K-Means++ dengan K sesuai "
               "kesimpulan penelitian (makanan K=3, minuman K=5).")
else:
    _md('<div class="card card-cream"><h3>Persona tidak tersedia untuk skema alternatif</h3>'
        '<p>Persona & rekomendasi bisnis hanya diberikan pada <strong>skema utama</strong> '
        '(Kuantitas &amp; Harga rata-rata) sesuai kesimpulan penelitian. Kembalikan skema untuk '
        'melihat profil tiap klaster.</p></div>')

# ---- tabel hasil klaster ----
st.markdown('<div class="panel-title">Data Hasil Klaster</div>', unsafe_allow_html=True)
cols_show = ["items", "category", "cluster"]
if do_profile:
    cols_show.append("profil")
cols_show += ["quantity", "frequency", "net_revenue", "avg_price", "units_per_order"]
tbl = view[cols_show].copy()
tbl["avg_price"] = tbl["avg_price"].round(0)
tbl["units_per_order"] = tbl["units_per_order"].round(2)
tbl = tbl.sort_values(["cluster", "quantity"], ascending=[True, False])
st.dataframe(tbl, use_container_width=True, height=420, hide_index=True)

download_button(tbl, "Unduh hasil klaster (CSV)",
                f"klaster_menu_{g_grup}.csv", key="dl_klaster")
