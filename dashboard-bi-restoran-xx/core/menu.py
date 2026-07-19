"""Rekayasa fitur tingkat menu, pemetaan makanan/minuman, skema fitur, dan profiling.
Mereproduksi Notebook 03 VERSI ROMBAK: penyaringan payment; kategori complimentary
& refund SELALU dibuang; entri 'custom amount' dibuang dari pemodelan menu (batasan
penelitian); avg_price = net_revenue / quantity. Hasil: 176 menu makanan (K=3) dan
148 menu minuman (K=5)."""
import numpy as np
import pandas as pd

# kategori minuman; sisanya (termasuk 'uncategorized' non-custom) dianggap makanan
MINUMAN_CATS = {"alkohol", "cocktail", "juice / drinks", "soft drinks",
                "coffee based", "non coffee", "mocktail"}
EXCLUDE_CATS = {"complimentary", "refund"}

# K sesuai kesimpulan penelitian (skema utama)
THESIS_K = {"makanan": 3, "minuman": 5}

# nama skema -> (daftar fitur, pakai_profiling). Skema alternatif boleh > 2 fitur.
FEATURE_SCHEMES = {
    "Skema utama — Kuantitas & Harga (rekomendasi penelitian)": (["quantity", "avg_price"], True),
    "Alternatif — Volume & Pendapatan": (["quantity", "net_revenue"], False),
    "Alternatif — Popularitas & Frekuensi": (["quantity", "frequency"], False),
    "Alternatif — Harga & Ukuran Pesanan": (["avg_price", "units_per_order"], False),
    "Alternatif — 3 Fitur: Kuantitas + Harga + Frekuensi": (["quantity", "avg_price", "frequency"], False),
    "Alternatif — 4 Fitur: Kuantitas + Harga + Frekuensi + Pendapatan":
        (["quantity", "avg_price", "frequency", "net_revenue"], False),
}

FEATURE_LABEL = {
    "quantity": "Kuantitas", "avg_price": "Harga rata-rata",
    "net_revenue": "Pendapatan bersih", "frequency": "Frekuensi",
    "units_per_order": "Unit per pesanan", "gross_sales": "Penjualan kotor",
}

# Winsorization tingkat menu (identik Notebook 03): HANYA avg_price yang dibatasi
# pada persentil ke-95; quantity dan fitur volume lain TIDAK diwinsor karena nilai
# besarnya adalah sinyal popularitas yang nyata.
WINSOR_MENU = {"avg_price": 0.95}


def prep_menu_features(sub: pd.DataFrame, feat_cols):
    """Praproses ruang fitur menu (identik Notebook 03): winsorize p95 hanya pada
    avg_price (bila termasuk fitur terpilih), lalu standardisasi Z-score.
    Mengembalikan (Xz, scaler)."""
    from core import cluster as cl
    X = sub[list(feat_cols)].astype(float).copy()
    for c in feat_cols:
        if c in WINSOR_MENU:
            X[c] = cl.winsorize(X[c], WINSOR_MENU[c])
    return cl.standardize(X)


def assign_group(cat):
    if cat in EXCLUDE_CATS:
        return None
    if cat in MINUMAN_CATS:
        return "minuman"
    return "makanan"


def filter_valid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Penyaringan baris menuju skema menu-level (Notebook 03 versi rombak):
    hanya payment; kategori complimentary & refund selalu dibuang; entri
    'custom amount' dibuang dari pemodelan menu (nominal terbuka kasir, tidak
    melekat pada menu tertentu — dicatat sebagai batasan penelitian).
    Defensif: kolom yang tidak tersedia pada unggahan dilewati."""
    d = df.copy()
    if "event_type" in d.columns:
        d = d[d["event_type"] == "payment"]
    if "category" in d.columns:
        d = d[~d["category"].isin(EXCLUDE_CATS)]
    if "items" in d.columns:
        custom = d["items"].astype(str).str.lower().str.contains("custom amount", na=False)
        d = d[~custom]
    return d.copy()


def build_menu_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agregasi data transaksi-item menjadi fitur per menu (identik Notebook 03
    versi rombak): quantity, frequency, net_revenue, gross_sales per menu, lalu
    fitur turunan avg_price = net_revenue/quantity dan units_per_order."""
    d = filter_valid_rows(df)
    for c in ("quantity", "net_sales", "gross_sales"):
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    cat = d.groupby("items")["category"].agg(
        lambda s: s.mode().iloc[0] if len(s.mode()) else None)
    g = d.groupby("items")
    out = pd.DataFrame({
        "quantity": g["quantity"].sum(),
        "frequency": g["receipt_number"].nunique() if "receipt_number" in d.columns else g.size(),
        "net_revenue": g["net_sales"].sum(),
        "gross_sales": g["gross_sales"].sum(),
    })
    out = out[out["quantity"] > 0]
    # avg_price mengikuti Notebook 03: pendapatan bersih dibagi unit terjual
    out["avg_price"] = (out["net_revenue"] / out["quantity"]).replace(
        [np.inf, -np.inf], np.nan)
    out["units_per_order"] = (out["quantity"] / out["frequency"]).replace(
        [np.inf, -np.inf], np.nan)
    out["category"] = cat
    out["grup"] = out["category"].map(assign_group)
    return out.reset_index()


# ---------------------------------------------------------------------------
# Profiling — mereproduksi karakterisasi & persona Notebook 03 versi rombak:
# popularitas (quantity) x harga (avg_price) relatif median, ambang +-15%.
# ---------------------------------------------------------------------------
PERSONA_MENU = {
    ("tinggi", "murah"): "Volume Andalan Harga Terjangkau",
    ("tinggi", "sedang"): "Bintang Penjualan",
    ("tinggi", "mahal"): "Unggulan Premium",
    ("sedang", "murah"): "Pengisi Menu Ekonomis",
    ("sedang", "sedang"): "Menu Tengah Stabil",
    ("sedang", "mahal"): "Premium Selektif",
    ("rendah", "murah"): "Kurang Bergerak Murah",
    ("rendah", "sedang"): "Kurang Bergerak",
    ("rendah", "mahal"): "Premium Jarang Terjual",
}

REKO_MENU = {
    "Volume Andalan Harga Terjangkau":
        "Penarik trafik utama — pertahankan harga & ketersediaan; jadikan pintu masuk upsell.",
    "Bintang Penjualan":
        "Volume terbesar — jaga stok & konsistensi; kandidat utama paket bundling.",
    "Unggulan Premium":
        "Motor pendapatan — jaga kualitas & ketersediaan; tonjolkan sebagai menu andalan.",
    "Pengisi Menu Ekonomis":
        "Pelengkap volume — dorong lewat paket hemat/combo agar berkontribusi lebih besar.",
    "Menu Tengah Stabil":
        "Stabil — pantau berkala; uji promosi ringan untuk menaikkan volume.",
    "Premium Selektif":
        "Margin baik dengan permintaan cukup — promosi tertarget (pairing/rekomendasi pelayan).",
    "Kurang Bergerak Murah":
        "Kaji ulang — promosi khusus, perbaikan resep/penyajian, atau rotasi keluar menu.",
    "Kurang Bergerak":
        "Kaji ulang — promosi khusus, perbaikan resep/penyajian, atau rotasi keluar menu.",
    "Premium Jarang Terjual":
        "Evaluasi — bundling/promo khusus untuk mengangkat penjualan, atau pertimbangkan rotasi menu.",
}


def _tingkat(nilai, med, rendah, tinggi, tol=0.15):
    """Karakterisasi relatif median dengan ambang +-15% (identik Notebook 03)."""
    if nilai >= med * (1 + tol):
        return tinggi
    if nilai <= med * (1 - tol):
        return rendah
    return "sedang"


def profile_clusters(menu_df: pd.DataFrame):
    """Label persona per klaster (reproduksi Notebook 03 versi rombak):
    popularitas dari rata quantity dan tingkat harga dari rata avg_price,
    keduanya relatif median seluruh menu pada kelompok tsb (ambang 15%).
    Label diturunkan dari karakteristik klaster — bukan nomor — sehingga tetap
    sahih untuk data unggahan berbeda.

    Mengembalikan (Series persona per baris, dict persona per klaster,
    dict rekomendasi per klaster)."""
    d = menu_df
    med_q = d["quantity"].median()
    med_p = d["avg_price"].median()
    means = d.groupby("cluster").agg(q=("quantity", "mean"), p=("avg_price", "mean"))
    lab, reko = {}, {}
    for c, r in means.iterrows():
        pop = _tingkat(r["q"], med_q, "rendah", "tinggi")
        hrg = _tingkat(r["p"], med_p, "murah", "mahal")
        lab[int(c)] = PERSONA_MENU[(pop, hrg)]
        reko[int(c)] = REKO_MENU[PERSONA_MENU[(pop, hrg)]]
    # jamin label unik bila dua klaster berkarakter serupa
    seen = {}
    for c in sorted(lab):
        if lab[c] in seen:
            seen[lab[c]] += 1
            lab[c] = f"{lab[c]} {seen[lab[c]]}"
        else:
            seen[lab[c]] = 1
    return d["cluster"].map(lab), lab, reko
