"""Rekayasa fitur tingkat transaksi (per nota), praproses, dan profiling segmen.

Modul ini sejajar dengan core.menu, tetapi bekerja pada tingkat nota: master
diagregasi per ``receipt_number`` menjadi satu baris per nota. Seluruh skema
mereproduksi Notebook 04 VERSI ROMBAK (Pemodelan Klaster Transaksi):

* Fitur klaster  : X1 frek_makanan, X2 frek_minuman, X3 total_net
                   (skema sederhana; terverifikasi uji VIF — seluruhnya di bawah 10)
* Penyaringan    : hanya payment; kategori complimentary & refund dibuang;
                   entri 'custom amount' DIPERTAHANKAN agar nilai nota tetap utuh
                   (unit custom amount tidak dihitung ke frekuensi makanan/minuman,
                   tetapi nilai uangnya tetap masuk total_net/total_gross)
* Praproses      : winsorization persentil ke-99 seluruh fitur -> Z-score
* Algoritme      : K-Means++ (n_init=10, random_state=42)
* Jumlah klaster : K = 2 (Silhouette tertinggi 0,5176 — kategori struktur "baik";
                   kandidat rentang 0,02; DBI validator)
* Profiling      : besaran belanja (total_net) & komposisi frekuensi makanan-minuman
                   — tanpa fitur rasio, tanpa penanda alkohol, tanpa aspek jam/waktu
"""
import numpy as np
import pandas as pd

# Kategori minuman — identik dengan Notebook 04 (sejajar core.menu.MINUMAN_CATS).
# Seluruh kategori lain (termasuk uncategorized non-custom) dihitung sebagai makanan.
GRUP_MINUMAN = {"soft drinks", "alkohol", "juice / drinks", "coffee based",
                "cocktail", "mocktail", "non coffee"}

# Fitur final tingkat transaksi (skema rombak): X1, X2, X3.
TRX_FEATURES = ["frek_makanan", "frek_minuman", "total_net"]
# Jumlah klaster sesuai kesimpulan Notebook 04 versi rombak.
TRX_K = 2
# Persentil winsorization (p99 pada seluruh fitur kontinu tingkat transaksi).
CAP_PCT = 0.99
# Seluruh fitur klaster diwinsor p99 (semuanya besaran/cacah berekori kanan).
WINSOR_FEATURES = list(TRX_FEATURES)

# Fitur per nota yang dapat dipilih untuk klaster (boleh lebih dari 2 fitur).
# Tiga fitur rekomendasi penelitian ditempatkan lebih dahulu; tidak ada fitur
# rasio, penanda alkohol, maupun jam pada skema rombak.
CANDIDATE_FEATURES = ["frek_makanan", "frek_minuman", "total_net",
                      "total_qty", "n_item_unik", "total_gross"]
# Seluruh kandidat adalah besaran/cacah -> layak diwinsor p99.
WINSOR_CANDIDATES = set(CANDIDATE_FEATURES)

FEATURE_LABEL = {
    "frek_makanan": "Frekuensi makanan (unit)",
    "frek_minuman": "Frekuensi minuman (unit)",
    "total_net": "Nilai belanja (net)",
    "total_qty": "Total item",
    "n_item_unik": "Ragam jenis item",
    "total_gross": "Penjualan kotor",
}


def filter_valid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Saring baris sah menuju data tingkat transaksi (Notebook 04 versi rombak):
    hanya pembayaran (payment), buang kategori complimentary (gratis Rp0) dan
    kategori refund. Entri 'custom amount' TIDAK dibuang — nominal terbuka kasir
    adalah bagian sah nilai nota sehingga total belanja tetap utuh. Penyaringan
    bersifat defensif: kolom yang tidak tersedia pada unggahan dilewati."""
    d = df.copy()
    if "event_type" in d.columns:
        d = d[d["event_type"] == "payment"]
    if "category" in d.columns:
        d = d[~d["category"].isin(["complimentary", "refund"])]
    return d.copy()


def _is_custom(items: pd.Series) -> pd.Series:
    return items.astype(str).str.lower().str.contains("custom amount", na=False)


def build_transaksi_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agregasi data transaksi-item menjadi fitur per nota (per receipt_number),
    persis Notebook 04 versi rombak. Satu baris per nota dengan fitur:
    frek_makanan, frek_minuman (unit makanan/minuman; custom amount tidak ikut
    dihitung), total_qty, n_item_unik, total_net, total_gross. Tidak ada kolom
    waktu/jam, rasio, maupun penanda alkohol."""
    d = filter_valid_rows(df)
    for c in ("quantity", "net_sales", "gross_sales"):
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    if "gross_sales" not in d.columns:
        d["gross_sales"] = d["net_sales"]
    cat = d["category"] if "category" in d.columns else pd.Series("", index=d.index)
    is_cust = _is_custom(d["items"]) if "items" in d.columns \
        else pd.Series(False, index=d.index)

    d = d.assign(
        q_minuman=np.where(cat.isin(GRUP_MINUMAN) & ~is_cust, d["quantity"], 0),
        q_makanan=np.where(~cat.isin(GRUP_MINUMAN) & ~is_cust, d["quantity"], 0),
    )
    g = d.groupby("receipt_number")
    nota = pd.DataFrame({
        "frek_makanan": g["q_makanan"].sum(),
        "frek_minuman": g["q_minuman"].sum(),
        "total_qty": g["quantity"].sum(),
        "n_item_unik": g["items"].nunique(),
        "total_net": g["net_sales"].sum(),
        "total_gross": g["gross_sales"].sum(),
    }).reset_index().rename(columns={"receipt_number": "nota"})
    nota = nota[nota["total_qty"] > 0].reset_index(drop=True)
    return nota


def run_transaksi_clustering(nota_df: pd.DataFrame, k: int = TRX_K,
                             algo: str = "kmeans++", seed: int = 42):
    """Pipeline lengkap tingkat transaksi (skema rombak): winsorize p99 seluruh
    fitur X1..X3 -> Z-score -> K-Means(++). Label klaster diturunkan dari ruang
    fitur yang telah diwinsor & distandardisasi, lalu ditempelkan pada data ASLI
    (nilai tak diwinsor) agar profil & tabel mencerminkan nilai sebenarnya.

    Mengembalikan (nota_berlabel, hasil_klastering, Xz, scaler)."""
    from core import cluster as cl  # pakai ulang core.cluster

    d = nota_df.copy()
    for c in WINSOR_FEATURES:
        d[c] = cl.winsorize(d[c].astype(float), CAP_PCT)
    Xz, scaler = cl.standardize(d[TRX_FEATURES].astype(float))
    res = cl.run_clustering(Xz, k, algo=algo, seed=seed)

    out = nota_df.copy()
    out["cluster"] = res["labels"]
    return out, res, Xz, scaler


def prep_features(nota_df: pd.DataFrame, features):
    """Praproses ruang fitur sembarang (boleh lebih dari 2 fitur): winsorize p99
    untuk seluruh fitur besaran/cacah, lalu Z-score. Mengembalikan (Xz, scaler)."""
    from core import cluster as cl
    d = nota_df.copy()
    for c in features:
        if c in WINSOR_CANDIDATES:
            d[c] = cl.winsorize(d[c].astype(float), CAP_PCT)
    return cl.standardize(d[list(features)].astype(float))


def run_custom_clustering(nota_df: pd.DataFrame, features, k: int,
                          algo: str = "kmeans++", seed: int = 42):
    """Versi umum run_transaksi_clustering untuk kombinasi fitur sembarang
    (eksplorasi pemilik/pengembang). Mengembalikan (nota_berlabel, hasil, Xz, scaler)."""
    from core import cluster as cl

    Xz, scaler = prep_features(nota_df, features)
    res = cl.run_clustering(Xz, k, algo=algo, seed=seed)
    out = nota_df.copy()
    out["cluster"] = res["labels"]
    return out, res, Xz, scaler


def build_nota_items(df: pd.DataFrame) -> pd.DataFrame:
    """Daftar rincian item per nota untuk ditampilkan/diekspor agar isi tiap nota
    terbaca — TERMASUK entri custom amount (sesuai skema rombak, custom amount
    tidak dibuang pada tingkat transaksi). Mengembalikan DataFrame [nota, items]
    dengan items berupa rangkaian 'qty× nama item' (urut kuantitas menurun)."""
    d = filter_valid_rows(df)
    if "quantity" in d.columns:
        d = d.assign(quantity=pd.to_numeric(d["quantity"], errors="coerce").fillna(0))
    else:
        d = d.assign(quantity=1)
    per = (d.groupby(["receipt_number", "items"], as_index=False)["quantity"].sum())

    def _fmt(g):
        g = g.sort_values("quantity", ascending=False)
        return "; ".join(f"{int(q)}× {it}" for it, q in zip(g["items"], g["quantity"]))

    out = (per.groupby("receipt_number").apply(_fmt, include_groups=False)
              .reset_index(name="items").rename(columns={"receipt_number": "nota"}))
    return out


def plot_axis(series: pd.Series, feat: str) -> pd.Series:
    """Nilai untuk sumbu scatter: fitur dibatasi p99 (selaras ruang fitur model)
    agar pencilan ekstrem tidak menekan tampilan sebaran."""
    from core import cluster as cl
    if feat in WINSOR_CANDIDATES:
        return cl.winsorize(series.astype(float), CAP_PCT)
    return series.astype(float)


# ---------------------------------------------------------------------------
# Profiling segmen — mereproduksi karakterisasi & interpretasi Notebook 04
# versi rombak (relatif median, ambang 15%; tanpa aspek jam/alkohol/rasio).
# ---------------------------------------------------------------------------
def _tingkat(nilai, med, rendah, tinggi, tol=0.15):
    """Karakterisasi relatif median dengan ambang ±15% (identik Notebook 04)."""
    if nilai >= med * (1 + tol):
        return tinggi
    if nilai <= med * (1 - tol):
        return rendah
    return "sedang"


def _nama_segmen(besar: str, komposisi: str) -> str:
    nama = {"besar": "Nota Besar", "sedang": "Nota Menengah", "kecil": "Nota Ringan"}[besar]
    nama += {"didominasi makanan": " Fokus Makanan",
             "didominasi minuman": " Fokus Minuman",
             "campuran makanan-minuman": " Campuran"}[komposisi]
    return nama


def _rekomendasi(besar: str, komposisi: str) -> str:
    """Rekomendasi bisnis per segmen — identik aturan Notebook 04 versi rombak
    (berbasis komposisi & nilai belanja; tanpa aspek waktu)."""
    if besar == "besar":
        return ("Pertahankan pengalaman & tawarkan paket bundling bernilai tinggi; "
                "prioritaskan ketersediaan menu andalan.")
    if komposisi == "didominasi minuman":
        return "Dorong attach makanan (paket minuman + camilan) untuk menaikkan nilai nota."
    if komposisi == "didominasi makanan":
        return "Dorong attach minuman (paket makan + minum) untuk menaikkan nilai nota."
    return "Naikkan nilai nota lewat upsell porsi/menu pendamping yang terjangkau."


def profile_clusters(nota_df: pd.DataFrame):
    """Label segmen objektif per klaster (reproduksi Notebook 04 versi rombak):
    nilai belanja dikarakterisasi relatif median total_net (besar/sedang/kecil,
    ambang 15%), komposisi dari perbandingan rata frekuensi makanan vs minuman
    (dominan bila >= 1,5x). Label diturunkan dari KARAKTERISTIK klaster — bukan
    nomor klaster — sehingga tetap sahih bila data yang diunggah berbeda.

    Mengembalikan (Series segmen per baris, dict segmen per klaster,
    dict rekomendasi per klaster)."""
    med_net = nota_df["total_net"].median()
    prof = nota_df.groupby("cluster").agg(
        fm=("frek_makanan", "mean"),
        fn=("frek_minuman", "mean"),
        net=("total_net", "mean")).reset_index()
    lab, reko = {}, {}
    for _, r in prof.iterrows():
        c = int(r["cluster"])
        besar = _tingkat(r["net"], med_net, "kecil", "besar")
        if r["fm"] >= 1.5 * max(r["fn"], 0.3):
            komposisi = "didominasi makanan"
        elif r["fn"] >= 1.5 * max(r["fm"], 0.3):
            komposisi = "didominasi minuman"
        else:
            komposisi = "campuran makanan-minuman"
        lab[c] = _nama_segmen(besar, komposisi)
        reko[c] = _rekomendasi(besar, komposisi)
    # jamin label unik bila dua klaster berkarakter serupa
    seen = {}
    for c in sorted(lab):
        if lab[c] in seen:
            seen[lab[c]] += 1
            lab[c] = f"{lab[c]} {seen[lab[c]]}"
        else:
            seen[lab[c]] = 1
    return nota_df["cluster"].map(lab), lab, reko


def short_label(name: str) -> str:
    """Versi ringkas nama segmen untuk chip/legenda."""
    return name.split(" (")[0].strip()


def cluster_profile_table(nota_df: pd.DataFrame, seg_map: dict,
                          reko_map: dict = None) -> pd.DataFrame:
    """Ringkasan profil per klaster untuk ditampilkan/diekspor: jumlah & persentase
    nota, rata belanja, rata frekuensi makanan & minuman, ragam item, kontribusi
    pendapatan, segmen, dan (opsional) rekomendasi BI. Tanpa aspek jam/alkohol."""
    tot_rev = nota_df["total_net"].sum()
    n_tot = len(nota_df)
    prof = nota_df.groupby("cluster").agg(
        jumlah_nota=("nota", "size"),
        rata_belanja=("total_net", "mean"),
        rata_frek_makanan=("frek_makanan", "mean"),
        rata_frek_minuman=("frek_minuman", "mean"),
        rata_item=("total_qty", "mean"),
        rata_jenis=("n_item_unik", "mean"),
        total_pendapatan=("total_net", "sum")).reset_index()
    prof["pct_nota"] = (prof["jumlah_nota"] / n_tot * 100).round(1)
    prof["pct_pendapatan"] = (prof["total_pendapatan"] / tot_rev * 100).round(1)
    prof["segmen"] = prof["cluster"].map(seg_map)
    if reko_map is not None:
        prof["rekomendasi_BI"] = prof["cluster"].map(reko_map)
    for c in ("rata_belanja", "rata_frek_makanan", "rata_frek_minuman",
              "rata_item", "rata_jenis"):
        prof[c] = prof[c].round(2)
    return prof.sort_values("pct_pendapatan", ascending=False).reset_index(drop=True)
