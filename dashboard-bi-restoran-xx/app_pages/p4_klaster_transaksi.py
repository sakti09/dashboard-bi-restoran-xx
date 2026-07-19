"""Halaman 4 — Klaster Transaksi (pemilik). Menampilkan HASIL klaster (data), bukan
metrik teknis. Skema rekomendasi penelitian VERSI ROMBAK (3 fitur: X1 frek_makanan,
X2 frek_minuman, X3 total_net; winsorize p99; K-Means++ K=2) berprofil & berlabel
segmen + rekomendasi bisnis. Pengguna dapat memilih kombinasi fitur lain (boleh lebih
dari 2 fitur) — hasilnya bernomor klaster tanpa pelabelan segmen. Custom amount
dipertahankan pada tingkat transaksi sehingga nilai nota utuh; rincian item tiap nota
(termasuk custom amount) ditampilkan pada tabel hasil. Tidak ada aspek jam/alkohol.
Hasil tampil setelah menekan 'Run model'."""
import json as _json
import streamlit as st
from core.ui import page_header, _md
from core.data import download_button
from core.session import ensure_data_loaded
from core import cluster, charts
from core import transaksi as trx


def num(x):
    return f"{x:,.0f}".replace(",", ".")


def rp(x):
    return "Rp " + num(x)


def _clicked_cluster(state, cl_order, label_to_cluster):
    """Tafsirkan pilihan klik pada grafik batang/lingkaran menjadi id klaster.
    Mengutamakan label teks (selaras nama segmen/Klaster), lalu indeks titik."""
    if not state:
        return None
    pts = (state.get("selection", {}) or {}).get("points", []) if isinstance(state, dict) else []
    if not pts:
        return None
    p = pts[0]
    for key in ("label", "x"):
        v = p.get(key)
        if v in label_to_cluster:
            return label_to_cluster[v]
    idx = p.get("point_index")
    if idx is None:
        idx = p.get("point_number")
    if idx is not None and 0 <= idx < len(cl_order):
        return int(cl_order[idx])
    return None


page_header(
    "Klaster Transaksi",
    "Segmentasi nota/transaksi dengan K-Means++ untuk strategi promosi. Pilih fitur "
    "(boleh lebih dari 2), jalankan model, telusuri profil tiap segmen beserta "
    "rekomendasinya, dan unduh hasilnya.")

df = ensure_data_loaded("Modul Klaster Transaksi")

# ---- prasyarat: butuh nomor nota untuk agregasi per transaksi ----
if "receipt_number" not in df.columns:
    st.warning("Dataset belum memiliki kolom **receipt_number**, sehingga agregasi "
               "per nota tidak dapat dilakukan. Unggah ekspor POS yang menyertakan "
               "nomor nota agar modul tingkat transaksi dapat dijalankan.")
    st.stop()

nota_base = trx.build_transaksi_features(df)
if len(nota_base) < trx.TRX_K + 1:
    st.warning("Jumlah nota tidak cukup untuk membentuk klaster pada dataset ini.")
    st.stop()

# ---- pemilihan fitur + tombol run ----
st.markdown('<div class="panel-title">Konfigurasi Klaster</div>', unsafe_allow_html=True)
with st.container(border=True):
    feats = st.multiselect(
        "Fitur klaster (bawaan = rekomendasi penelitian; boleh pilih lebih dari 2 fitur)",
        trx.CANDIDATE_FEATURES, default=list(trx.TRX_FEATURES),
        format_func=lambda f: trx.FEATURE_LABEL.get(f, f))
    st.caption("Rekomendasi fitur penelitian (hasil uji VIF — seluruhnya di bawah ambang 10): "
               "Frekuensi makanan + Frekuensi minuman + Nilai belanja (net). Bila Anda memilih "
               "kombinasi lain, klaster tetap terbentuk namun hanya ditampilkan sebagai nomor "
               "(tanpa pelabelan segmen), karena bukan konfigurasi terbaik hasil penelitian.")
    run = st.button("Run model", type="primary")

current_cfg = tuple(sorted(feats))
if run:
    st.session_state["trx_cfg"] = current_cfg
cfg = st.session_state.get("trx_cfg")

if cfg is None:
    st.info("Pilih **Fitur klaster** di atas (atau biarkan bawaan), lalu tekan **Run model** "
            "untuk menjalankan segmentasi. Hasil tidak ditampilkan sebelum dijalankan.")
    st.stop()
if cfg != current_cfg:
    st.warning("Konfigurasi fitur berubah sejak terakhir dijalankan. Tekan **Run model** "
               "untuk memperbarui hasil di bawah.")

g_feats = list(cfg)
if len(g_feats) < 1:
    st.warning("Pilih minimal satu fitur untuk menjalankan klaster.")
    st.stop()
is_reco = set(g_feats) == set(trx.TRX_FEATURES)

# ---- pipeline: winsorize p99 -> Z-score -> K-Means++ ----
# K=2 (penelitian) untuk kombinasi rekomendasi; Silhouette terbaik untuk kombinasi lain.
if is_reco:
    nota, res, _Xz, _sc = trx.run_transaksi_clustering(nota_base, k=trx.TRX_K, algo="kmeans++")
    k_used = trx.TRX_K
else:
    Xz, _sc = trx.prep_features(nota_base, g_feats)
    k_used = cluster.best_k_by_silhouette(Xz, 2, 6)
    r = cluster.run_clustering(Xz, k_used, algo="kmeans++")
    nota = nota_base.copy()
    nota["cluster"] = r["labels"]

# ---- profiling hanya untuk kombinasi rekomendasi ----
if is_reco:
    seg_series, seg_map, reko_map = trx.profile_clusters(nota)
    nota["segmen"] = seg_series
    short_map = {c: trx.short_label(n) for c, n in seg_map.items()}
    label_map = short_map
else:
    seg_map, reko_map, short_map = {}, {}, {}
    label_map = None  # tampilkan nomor klaster saja

# ---- info skema ----
fitur_txt = " + ".join(trx.FEATURE_LABEL.get(c, c) for c in g_feats)
_md(f'<div class="src-pill">Fitur: <strong>{fitur_txt}</strong> &middot; '
    f'Praproses: <strong>winsorize p99 + Z-score</strong> &middot; '
    f'Jumlah klaster: <strong>{k_used}</strong> &middot; {num(len(nota))} nota</div>')
if is_reco:
    st.caption("Skema penelitian tingkat transaksi (versi rombak) — fitur sederhana X1 frekuensi "
               "makanan, X2 frekuensi minuman, X3 nilai belanja; lolos uji VIF (seluruhnya di "
               "bawah 10). K=2 ditetapkan dari Silhouette tertinggi 0,5176 (kategori struktur "
               "'baik') yang diselaraskan DBI (kandidat rentang 0,02). Custom amount tetap "
               "dihitung dalam nilai nota; tidak ada fitur jam ataupun penanda alkohol.")
else:
    st.caption("Kombinasi fitur eksplorasi (bukan skema rekomendasi). Jumlah klaster dipilih "
               "otomatis dari Silhouette tertinggi. Hasil ditampilkan sebagai nomor klaster "
               "tanpa pelabelan segmen.")

# ---- panel kontrol tampilan (filter pasca-klaster) ----
st.markdown('<div class="panel-title">Panel Kontrol</div>', unsafe_allow_html=True)
with st.container(border=True):
    clusters_avail = sorted(nota["cluster"].unique().tolist())
    sel_cl = st.multiselect(
        "Tampilkan klaster", clusters_avail, default=clusters_avail,
        format_func=lambda i: (f"Klaster {i} · {short_map.get(i, i)}" if is_reco
                               else f"Klaster {i}"))

# ---- terapkan filter ----
view = nota[nota["cluster"].isin(sel_cl)].copy()
if len(view) == 0:
    st.warning("Tidak ada nota untuk kombinasi klaster/filter ini.")
    st.stop()

# ---- ringkasan tiap klaster (chips) ----
chips = ""
for c in clusters_avail:
    n = int((nota["cluster"] == c).sum())
    col = charts.cluster_color(c)
    extra = f' &middot; {short_map.get(c)}' if is_reco else ''
    chips += (f'<div class="cl-chip"><span class="cl-dot" style="background:{col}"></span>'
              f'Klaster {c} &middot; {num(n)} nota{extra}</div>')
_md(f'<div class="cl-row">{chips}</div>')

# ---- sebaran hasil klaster ----
# Skema rekomendasi: dua panel ala Notebook 04 (X1 vs X3 dan X2 vs X3).
# Kombinasi lain: sebaran dua fitur pertama yang dipilih.
if is_reco:
    sc_cols = st.columns(2)
    for ax_i, (fx, fy) in enumerate([("frek_makanan", "total_net"),
                                     ("frek_minuman", "total_net")]):
        pdf = view[["nota", "cluster"]].copy()
        pdf[fx] = trx.plot_axis(view[fx], fx).values
        pdf[fy] = trx.plot_axis(view[fy], fy).values
        with sc_cols[ax_i]:
            st.plotly_chart(charts.scatter_clusters(
                pdf, x=fx, y=fy, cluster_col="cluster",
                title=f"Sebaran Nota — {trx.FEATURE_LABEL[fx]} vs {trx.FEATURE_LABEL[fy]}",
                label_map=label_map, text_col="nota",
                xlab=trx.FEATURE_LABEL.get(fx), ylab=trx.FEATURE_LABEL.get(fy)),
                use_container_width=True)
    st.caption("Setiap titik mewakili satu nota; warna menandai klaster. Kedua panel meniru "
               "sebaran pada notebook penelitian: frekuensi makanan/minuman terhadap nilai "
               "belanja. Sumbu dibatasi persentil ke-99 agar pencilan tidak menekan tampilan.")
elif len(g_feats) >= 2:
    fx, fy = g_feats[0], g_feats[1]
    pdf = view[["nota", "cluster"]].copy()
    pdf[fx] = trx.plot_axis(view[fx], fx).values
    pdf[fy] = trx.plot_axis(view[fy], fy).values
    st.plotly_chart(charts.scatter_clusters(
        pdf, x=fx, y=fy, cluster_col="cluster", title="Sebaran Nota per Klaster",
        label_map=label_map, text_col="nota",
        xlab=trx.FEATURE_LABEL.get(fx), ylab=trx.FEATURE_LABEL.get(fy)),
        use_container_width=True)
    if len(g_feats) > 2:
        st.caption(f"Kombinasi ini memakai {len(g_feats)} fitur; sebaran menampilkan dua fitur "
                   "pertama sebagai sumbu, sedangkan klaster dihitung pada seluruh fitur terpilih.")
else:
    st.info("Sebaran ruang fitur memerlukan minimal 2 fitur (sumbu X & Y).")

# ---- komposisi klaster: batang (jumlah) + lingkaran (kontribusi) — DAPAT DIKLIK ----
st.markdown('<div class="panel-title">Komposisi Klaster</div>', unsafe_allow_html=True)
st.caption("Klik salah satu klaster pada diagram batang atau lingkaran untuk menampilkan "
           "rincian kategori menu di dalam klaster tersebut.")
cl_order = sorted(view["cluster"].unique().tolist())
label_to_cluster = {}
for c in cl_order:
    label_to_cluster[(short_map.get(c, f"Klaster {c}") if is_reco else f"Klaster {c}")] = c

gc = st.columns(2)
with gc[0]:
    bar_state = st.plotly_chart(
        charts.bar_clusters(view, "cluster", "Jumlah Transaksi per Klaster",
                            agg="count", label_map=label_map),
        use_container_width=True, key="trx_bar", on_select="rerun")
with gc[1]:
    pie_state = st.plotly_chart(
        charts.pie_clusters(view, "cluster", "Kontribusi Pendapatan per Klaster",
                            value="total_net", agg="sum", label_map=label_map),
        use_container_width=True, key="trx_pie", on_select="rerun")

# deteksi grafik mana yang baru saja diklik (signature berubah pada rerun ini)
sig_bar = _json.dumps(bar_state, sort_keys=True, default=str) if bar_state else ""
sig_pie = _json.dumps(pie_state, sort_keys=True, default=str) if pie_state else ""
prev = st.session_state.get("_trx_drill_sig", {"bar": "", "pie": ""})
drill = st.session_state.get("trx_drill")
# Hanya perbarui bila ada klik baru yang benar-benar mengenai sebuah klaster;
# seleksi kosong (mis. render awal/penghapusan seleksi) tidak menghapus drill aktif.
if sig_bar != prev.get("bar", ""):
    hit = _clicked_cluster(bar_state, cl_order, label_to_cluster)
    if hit is not None:
        drill = hit
elif sig_pie != prev.get("pie", ""):
    hit = _clicked_cluster(pie_state, cl_order, label_to_cluster)
    if hit is not None:
        drill = hit
st.session_state["_trx_drill_sig"] = {"bar": sig_bar, "pie": sig_pie}
# klaster terpilih harus masih ada dalam tampilan; jika tidak, kosongkan
if drill is not None and drill not in cl_order:
    drill = None
st.session_state["trx_drill"] = drill

# ---- space drill-down: rincian kategori untuk klaster yang dipencet ----
drill_box = st.container()
with drill_box:
    if drill is None:
        st.markdown(
            '<div class="card" style="border-style:dashed;text-align:center;'
            'color:var(--text-dim);">Pilih sebuah klaster pada grafik di atas untuk '
            'menampilkan rincian kategori di sini.</div>', unsafe_allow_html=True)
    else:
        nm = short_map.get(drill, f"Klaster {drill}") if is_reco else f"Klaster {drill}"
        head_c1, head_c2 = st.columns([4, 1])
        head_c1.markdown(
            f'<div class="prof-head" style="margin-top:6px;">'
            f'<span class="cl-dot" style="background:{charts.cluster_color(drill)}"></span>'
            f'<strong>Rincian kategori — Klaster {drill}'
            f'{" · " + nm if is_reco else ""}</strong></div>', unsafe_allow_html=True)
        if head_c2.button("Tutup rincian", key="trx_drill_close"):
            st.session_state["trx_drill"] = None
            st.session_state["_trx_drill_sig"] = {"bar": "", "pie": ""}
            st.rerun()
        notas_in = set(view.loc[view["cluster"] == drill, "nota"])
        item_rows = trx.filter_valid_rows(df)
        item_rows = item_rows[item_rows["receipt_number"].isin(notas_in)]
        if "category" in item_rows.columns and len(item_rows):
            item_rows = item_rows.assign(category=item_rows["category"].fillna("(tak terkategori)"))
            dc = st.columns(2)
            with dc[0]:
                st.plotly_chart(
                    charts.bar_categories(item_rows, "Kategori per Item Terjual (kuantitas)",
                                          value="quantity", n=20, color_by_cluster=drill),
                    use_container_width=True)
            with dc[1]:
                st.plotly_chart(
                    charts.donut_category(item_rows, value="quantity"),
                    use_container_width=True)
        else:
            st.info("Rincian kategori tidak tersedia untuk klaster ini.")

# ---- profil segmen & rekomendasi (hanya untuk kombinasi rekomendasi) ----
st.markdown('<div class="panel-title">Profil Segmen & Rekomendasi</div>',
            unsafe_allow_html=True)
if is_reco:
    prof = trx.cluster_profile_table(nota, seg_map, reko_map)
    prof = prof[prof["cluster"].isin(sel_cl)]
    for _, r in prof.iterrows():
        c = int(r["cluster"])
        col = charts.cluster_color(c)
        stats = (f'<span>Nota: <strong>{num(r["jumlah_nota"])}</strong> ({r["pct_nota"]}%)</span>'
                 f'<span>Rata belanja: <strong>{rp(r["rata_belanja"])}</strong></span>'
                 f'<span>Frek. makanan: <strong>{r["rata_frek_makanan"]:.1f}</strong></span>'
                 f'<span>Frek. minuman: <strong>{r["rata_frek_minuman"]:.1f}</strong></span>'
                 f'<span>Ragam item: <strong>{r["rata_jenis"]:.1f}</strong></span>'
                 f'<span>Kontribusi: <strong>{r["pct_pendapatan"]}%</strong></span>')
        _md(f'<div class="card prof-card" style="border-left:3px solid {col};margin-bottom:12px;">'
            f'<div class="prof-head"><span class="cl-dot" style="background:{col}"></span>'
            f'<strong>Klaster {c} &middot; {r["segmen"]}</strong></div>'
            f'<div class="prof-stats">{stats}</div>'
            f'<p class="prof-reko">{r["rekomendasi_BI"]}</p></div>')
    st.caption("Segmen & rekomendasi mengikuti hasil penelitian (versi rombak): karakterisasi "
               "nilai belanja relatif median (ambang 15%) dan komposisi frekuensi "
               "makanan–minuman. Pada dataset penelitian terbentuk dua segmen: Nota Besar "
               "Campuran (21,1% nota; 46,5% pendapatan) dan Nota Menengah Campuran "
               "(78,9% nota; 53,5% pendapatan).")
else:
    _md('<div class="card card-cream"><h3>Pelabelan segmen tidak tersedia</h3>'
        '<p>Kombinasi fitur yang dipilih <strong>bukan</strong> konfigurasi klaster terbaik '
        'hasil penelitian, sehingga hasil hanya ditampilkan sebagai nomor klaster tanpa '
        'profil segmen maupun rekomendasi bisnis. Untuk memperoleh pelabelan segmen, '
        'kembalikan pilihan fitur ke rekomendasi penelitian (Frekuensi makanan + Frekuensi '
        'minuman + Nilai belanja), lalu tekan Run model.</p></div>')

# ---- tabel hasil klaster (sertakan rincian item tiap nota, termasuk custom amount) ----
st.markdown('<div class="panel-title">Data Hasil Klaster</div>', unsafe_allow_html=True)
items_map = trx.build_nota_items(df)
base_cols = ["nota", "cluster"]
if is_reco:
    base_cols.append("segmen")
base_cols += ["frek_makanan", "frek_minuman", "total_net",
              "total_qty", "n_item_unik", "total_gross"]
tbl = view[base_cols].copy()
tbl = tbl.merge(items_map, on="nota", how="left")
tbl["items"] = tbl["items"].fillna("")
tbl = tbl.sort_values(["cluster", "total_net"], ascending=[True, False])
# kolom 'items' (daftar isi nota, termasuk custom amount) tepat setelah nota
order = ["nota", "items"] + [c for c in base_cols if c != "nota"]
tbl = tbl[order]
st.dataframe(tbl, use_container_width=True, height=420, hide_index=True,
             column_config={"items": st.column_config.TextColumn("items", width="large")})
st.caption("Kolom items memuat seluruh isi nota — termasuk entri custom amount — sesuai "
           "skema penelitian tingkat transaksi yang mempertahankan nilai nota utuh.")

download_button(tbl, "Unduh hasil klaster (CSV)", "klaster_transaksi.csv",
                key="dl_klaster_trx")
