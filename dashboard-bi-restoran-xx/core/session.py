"""State bersama antar-halaman: dataset master disimpan di session_state sehingga
satu kali diunggah dapat dipakai semua halaman (sinkron lintas halaman)."""
import streamlit as st

_KEY = "master_df"
_SRC = "master_source"


def has_master() -> bool:
    return st.session_state.get(_KEY) is not None


def get_master():
    return st.session_state.get(_KEY)


def set_master(df, source: str):
    st.session_state[_KEY] = df
    st.session_state[_SRC] = source


def master_source() -> str:
    return st.session_state.get(_SRC, "")


def clear_master():
    st.session_state.pop(_KEY, None)
    st.session_state.pop(_SRC, None)


def ensure_data_loaded(context: str = "Modul ini"):
    """Gerbang data: jika belum ada master, tampilkan prompt muat/unggah lalu hentikan.
    Mengembalikan DataFrame master bila sudah tersedia (dipakai lintas halaman)."""
    if has_master():
        return get_master()

    from core.ui import _md
    from core.data import load_default_master, load_uploaded, validate_master

    _md('<div class="card card-cream"><h3>Belum ada dataset dimuat</h3>'
        f'<p>{context} memerlukan dataset terlebih dahulu. Muat dataset penelitian sebagai '
        'contoh, atau unggah berkas POS Anda (CSV/XLSX). Dataset yang dimuat otomatis '
        'dipakai pada seluruh halaman.</p></div>')
    c1, c2 = st.columns([1, 1.5])
    with c1:
        if st.button("Muat dataset penelitian (contoh)", type="primary"):
            set_master(load_default_master(), "Dataset penelitian — master 2023–2024")
            st.rerun()
    with c2:
        up = st.file_uploader("atau unggah CSV/XLSX", type=["csv", "xlsx", "xls"])
        if up is not None:
            try:
                d = load_uploaded(up)
                ok, msg, miss = validate_master(d)
                if ok:
                    set_master(d, f"Unggahan — {up.name}")
                    st.rerun()
                else:
                    st.error("Kolom inti belum ada: " + ", ".join(miss))
            except Exception as e:
                st.error(f"Gagal membaca berkas: {e}")
    st.stop()
