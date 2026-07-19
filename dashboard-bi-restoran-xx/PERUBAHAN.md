# Catatan Perubahan — Dashboard Versi Rombak (2026-07-19)

Penyesuaian dashboard terhadap Notebook 03 & 04 versi rombak. **Halaman 2 (Lihat
Dataset / KPI insight) tidak diubah isinya** — hanya ditambah kontrol opsional
"POV Jam Transaksi" (nonaktif secara bawaan; tampilan lama tetap identik).

## Berkas yang berubah

| Berkas | Perubahan |
|---|---|
| `core/transaksi.py` | DITULIS ULANG — skema fitur baru: X1 `frek_makanan`, X2 `frek_minuman`, X3 `total_net`; K=2; custom amount DIPERTAHANKAN; fitur `rasio_minuman`, `ada_alkohol`, dan `jam` DIHAPUS; profiling segmen + rekomendasi mengikuti karakterisasi Notebook 04 (median ±15%, dominasi 1,5×). |
| `core/menu.py` | Penyaringan identik Notebook 03 (payment; buang complimentary + refund + custom amount); `avg_price = net_revenue/quantity`; winsorize p95 HANYA `avg_price` (`prep_menu_features`); persona 9 kombinasi popularitas×harga + rekomendasi; 2 skema alternatif baru (3 & 4 fitur). |
| `core/charts.py` | + `bar_by_hour()` untuk POV jam opsional di halaman 2. |
| `app_pages/p3_klaster_menu.py` | Pipeline pakai `prep_menu_features`; bagian baru "Profil Persona & Rekomendasi" (skema utama); dukungan skema >2 fitur. |
| `app_pages/p4_klaster_transaksi.py` | DITULIS ULANG — fitur baru (boleh pilih >2 dari 6 kandidat), K=2, dua panel sebaran ala notebook (X1 vs X3, X2 vs X3), profil segmen + rekomendasi sesuai laporan, filter alkohol DIHAPUS, kolom jam/rasio DIHAPUS, tabel hasil memuat daftar item per nota termasuk custom amount. Drill-down rincian kategori tetap ada. |
| `app_pages/p5_dev_menu.py` | Praproses pakai `prep_menu_features`; caption sebaran >2 fitur. |
| `app_pages/p6_dev_transaksi.py` | Fitur dasar korelasi baru; caption VIF/K baru; tabel hasil tanpa jam/rasio/alkohol; items termasuk custom amount. |
| `app_pages/p2_lihat_dataset.py` | TAMBAHAN OPSIONAL SAJA: expander "POV Jam Transaksi" (checkbox + slider jam + grafik pola per jam). Bawaan nonaktif — insight lama tak berubah. |
| `app_pages/p1_beranda.py` | PERBAIKAN BUG: tombol "Buka modul" semula tautan `<a href>` mentah — klik memicu muat-ulang penuh sehingga sesi (peran) hilang dan halaman tujuan tak terdaftar di navigasi → error "Page not found". Kini memakai `st.button` + `st.switch_page` (navigasi internal, sesi tetap). Tampilan kartu tidak berubah. |
| `README.md` | + ringkasan skema pemodelan versi rombak. |

## Verifikasi (dataset penelitian)

- Klaster Menu skema utama mereproduksi Notebook 03 persis: makanan K=3
  (silhouette 0,4705; C0 Unggulan Premium 90 menu 40,3%; C1 Pengisi Menu Ekonomis
  68 menu 13,1%; C2 Bintang Penjualan 18 menu 46,6%); minuman K=5 (silhouette
  0,6359; 85/15/2/38/8).
- Klaster Transaksi mereproduksi Notebook 04 persis: 5.075 nota; K=2 (silhouette
  0,5176; DBI 0,9100); C0 Nota Besar Campuran (1.071 nota; 21,1%; 46,5%
  pendapatan); C1 Nota Menengah Campuran (4.004 nota; 78,9%; 53,5%).
- 10 uji asap AppTest (semua halaman & beberapa kombinasi fitur): LULUS tanpa error.
- Uji tombol beranda (5 tombol "Buka modul" kedua peran + pemilihan peran) melalui
  aplikasi penuh (`app.py` + `st.navigation`): LULUS — berpindah halaman tanpa error
  dan sesi peran tetap tersimpan.
