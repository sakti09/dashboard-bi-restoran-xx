"""Pemuatan & validasi data. Mendukung CSV dan XLSX di semua halaman.
Kolom 'bulan' TIDAK ada pada ekspor POS asli; di-derive dari 'datetime'."""
from pathlib import Path
import io
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_MASTER = DATA_DIR / "data_master_2023_2024_final.csv"

# Kolom yang diharapkan dari ekspor langsung POS (tanpa 'bulan'/'tahun').
POS_EXPECTED = ["receipt_number", "items", "quantity", "item_price", "gross_sales",
                "discounts", "refunds", "net_sales", "payment_method", "event_type",
                "datetime", "variant", "category"]
NUMERIC_COLUMNS = ["quantity", "item_price", "gross_sales", "discounts",
                   "refunds", "net_sales"]
# Kolom inti yang wajib ada agar dataset dapat diproses.
REQUIRED_CORE = ["items", "quantity", "net_sales", "gross_sales", "category"]


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df


def _read_csv_bytes(raw) -> pd.DataFrame:
    text = raw.decode("utf-8-sig", errors="replace") if isinstance(raw, (bytes, bytearray)) else raw
    for sep in (",", ";", "\t"):
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep)
            if df.shape[1] > 1:
                return df
        except Exception:
            continue
    return pd.read_csv(io.StringIO(text))


def _read_any(file) -> pd.DataFrame:
    name = getattr(file, "name", str(file)).lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file, engine="openpyxl")
    if hasattr(file, "read"):
        return _read_csv_bytes(file.read())
    with open(file, "rb") as fh:
        return _read_csv_bytes(fh.read())


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for c in NUMERIC_COLUMNS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def ensure_month(df: pd.DataFrame) -> pd.DataFrame:
    """Pastikan kolom 'bulan' (YYYY-MM) tersedia. Bila tak ada, derive dari 'datetime'.
    Ini menjaga visual bulanan tetap tampil meski POS tidak mengekspor kolom 'bulan'."""
    if "bulan" not in df.columns and "datetime" in df.columns:
        dt = pd.to_datetime(df["datetime"], errors="coerce")
        df["bulan"] = dt.dt.strftime("%Y-%m")
    return df


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    return ensure_month(coerce_numeric(_normalize_cols(df)))


def validate_master(df: pd.DataFrame):
    missing_core = [c for c in REQUIRED_CORE if c not in df.columns]
    if missing_core:
        return False, "Kolom inti tidak lengkap.", missing_core
    return True, "Struktur sesuai.", []


@st.cache_data(show_spinner=False)
def load_default_master() -> pd.DataFrame:
    df = pd.read_csv(DEFAULT_MASTER, encoding="utf-8-sig")
    return _prepare(df)


def load_uploaded(file) -> pd.DataFrame:
    return _prepare(_read_any(file))


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def download_button(df: pd.DataFrame, label: str, filename: str, key: str = None):
    st.download_button(label=label, data=to_csv_bytes(df),
                       file_name=filename, mime="text/csv", key=key)
