"""UI helpers: injeksi CSS terpusat, brand sidebar, dan komponen visual berulang."""
from pathlib import Path
import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def _md(html_str: str):
    """Render HTML mentah dengan aman: rata-kirikan tiap baris agar Markdown
    tidak menganggap indentasi >=4 spasi sebagai blok kode."""
    cleaned = "\n".join(line.strip() for line in html_str.splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


def inject_css():
    """Suntik style.css (design token) + streamlit.css (override chrome) per rerun."""
    css = ""
    for name in ("style.css", "streamlit.css"):
        fp = ASSETS / name
        if fp.exists():
            css += fp.read_text(encoding="utf-8") + "\n"
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def sidebar_brand():
    with st.sidebar:
        _md('<div class="sb-brand"><h1>BI&nbsp;DASHBOARD</h1>'
            '<p>Restoran X &middot; Ubud, Bali</p></div>')


def sidebar_footer():
    with st.sidebar:
        _md('<div class="sb-foot">Skripsi <strong>Desak 2208561143</strong><br>'
            'Informatika &middot; Universitas Udayana &middot; 2026</div>')


def page_header(title: str, subtitle: str = ""):
    sub = f'<p>{subtitle}</p>' if subtitle else ''
    _md(f'<div class="page-header"><h1>{title}</h1>{sub}</div><div class="divider"></div>')


def under_construction(title: str, msg: str):
    icon = ('<svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" '
            'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>')
    _md(f'<div class="uc-wrap"><div class="uc-ic">{icon}</div>'
        f'<h3>{title}</h3><p>{msg}</p></div>')
