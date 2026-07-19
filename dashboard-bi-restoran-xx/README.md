# Dashboard BI Restoran X

Business Intelligence Dashboard untuk segmentasi penjualan menggunakan **K-Means++**.


- **Klaster Menu** — penyaringan: hanya `payment`; kategori `complimentary` & `refund`
  selalu dibuang; `custom amount` dibuang dari pemodelan menu (batasan penelitian).
  Fitur utama X1 `quantity` + X2 `avg_price` (= net_revenue/quantity); winsorize p95
  hanya pada `avg_price`; Z-score; K-Means++ (makanan **K=3**, minuman **K=5**).
  Persona & rekomendasi per klaster mengikuti karakterisasi popularitas × harga.
- **Klaster Transaksi** — `custom amount` DIPERTAHANKAN (nilai nota utuh; ikut pada
  daftar item per nota). Fitur utama X1 `frek_makanan` + X2 `frek_minuman` +
  X3 `total_net` (VIF < 10); winsorize p99; Z-score; K-Means++ **K=2**
  (Silhouette 0,5176 — struktur "baik"). Tanpa fitur rasio, tanpa penanda alkohol,
  tanpa aspek jam pada pemodelan/profil. Pengguna dapat memilih kombinasi fitur lain
  (boleh lebih dari 2 fitur) sebagai eksplorasi tanpa pelabelan segmen.
- **POV Jam** hanya tersedia sebagai kontrol opsional pada halaman Lihat Dataset
  (KPI insight) — bukan bagian pemodelan.

## Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

Dashboard terbuka di `http://localhost:8501`.

## Struktur Proyek

```
dashboard-bi-restoran-x/
├── Home.py                  # entry point + navigasi (st.navigation)
├── app_pages/               # isi tiap halaman
│   ├── p1_beranda.py        # 1. Beranda
│   ├── p2_lihat_dataset.py  # 2. Lihat Dataset (pemilik)
│   ├── p3_klaster_menu.py   # 3. Klaster Menu (pemilik)
│   ├── p4_klaster_transaksi.py  # 4. Klaster Transaksi (lanjutan)
│   ├── p5_dev_menu.py       # 5. Developer · Menu (teknis)
│   └── p6_dev_transaksi.py  # 6. Developer · Transaksi (lanjutan)
├── core/                    # logika bersama
│   ├── ui.py                # injeksi CSS, brand, komponen UI
│   ├── data.py              # baca CSV/XLSX, validasi, unduh
│   └── cluster.py           # K-Means / K-Means++, metrik, filter klaster
├── assets/
│   ├── style.css            # design token (warna, tipografi, komponen)
│   └── streamlit.css        # override chrome Streamlit
├── data/
│   └── data_master_2023_2024_final.csv   # dataset master bawaan
└── .streamlit/config.toml   # tema dark + olive
```



## Format Data Masukan

Dataset yang diunggah harus mengikuti struktur **hasil ekspor langsung POS**
(master final), berformat `.csv` atau `.xlsx`. Kolom inti yang wajib ada:
`items, quantity, net_sales, gross_sales, category`.


