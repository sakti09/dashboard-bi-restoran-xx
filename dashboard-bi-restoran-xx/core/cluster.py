"""Pemodelan klaster: K-Means / K-Means++, metrik evaluasi, dan filter subset klaster.
Dipakai oleh halaman Klaster Menu (pemilik) dan Developer (teknis)."""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score


def winsorize(s: pd.Series, p: float = 0.95) -> pd.Series:
    """Batasi nilai tertinggi pada persentil p tanpa membuang amatan."""
    cap = s.quantile(p)
    return s.clip(upper=cap)


def standardize(X: pd.DataFrame):
    sc = StandardScaler()
    return sc.fit_transform(X), sc


def run_clustering(X: np.ndarray, k: int, algo: str = "kmeans++", seed: int = 42):
    """Jalankan pengelompokan. algo: 'kmeans++' atau 'kmeans' (acak).
    Kembalikan dict berisi label, model, dan metrik."""
    init = "k-means++" if algo == "kmeans++" else "random"
    model = KMeans(n_clusters=k, init=init, n_init=10, random_state=seed)
    labels = model.fit_predict(X)
    out = {"labels": labels, "model": model, "inertia": float(model.inertia_)}
    if k > 1 and len(np.unique(labels)) > 1:
        out["silhouette"] = float(silhouette_score(X, labels))
        out["dbi"] = float(davies_bouldin_score(X, labels))
    else:
        out["silhouette"] = float("nan")
        out["dbi"] = float("nan")
    return out


def metrics_over_k(X: np.ndarray, k_min: int = 2, k_max: int = 9,
                   algo: str = "kmeans++", seed: int = 42) -> pd.DataFrame:
    """Hitung SSE/inertia, Silhouette, DBI untuk rentang K (Elbow + validasi)."""
    rows = []
    for k in range(k_min, k_max + 1):
        r = run_clustering(X, k, algo=algo, seed=seed)
        rows.append({"K": k, "SSE_inertia": r["inertia"],
                     "silhouette": r["silhouette"], "dbi": r["dbi"]})
    return pd.DataFrame(rows)


def filter_clusters(df: pd.DataFrame, selected, col: str = "cluster") -> pd.DataFrame:
    """Ambil subset baris untuk kombinasi klaster terpilih (mis. [0], [0,1], semua)."""
    if not selected:
        return df
    return df[df[col].isin(selected)].copy()


def best_k_by_silhouette(X, k_min: int = 2, k_max: int = 6,
                         algo: str = "kmeans++", seed: int = 42) -> int:
    """Pilih K dengan Silhouette tertinggi pada rentang [k_min, k_max]."""
    best_k, best_s = k_min, -1.0
    for k in range(k_min, k_max + 1):
        try:
            r = run_clustering(X, k, algo=algo, seed=seed)
            s = r["silhouette"]
            if s == s and s > best_s:  # s==s menyaring NaN
                best_k, best_s = k, s
        except Exception:
            continue
    return best_k
