# 📘 Air Quality Dashboard — Streamlit App

Dashboard ini dibangun menggunakan **Streamlit** untuk menampilkan visualisasi kualitas udara. Aplikasi dapat dijalankan secara lokal maupun diakses melalui **Streamlit Cloud**.

---

## ✨ Setup Environment — Anaconda

1. Buat environment baru:

```bash
conda create --name air-dashboard python=3.9
```

2. Aktifkan environment:

```bash
conda activate air-dashboard
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ✨ Setup Environment — Shell / Terminal

1. Buat folder proyek:

```bash
mkdir air_dashboard
cd air_dashboard
```

2. Inisialisasi environment dengan pipenv:

```bash
pipenv install
pipenv shell
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🚀 Cara Menjalankan Streamlit Secara Lokal

Pastikan file `Air.py` berada pada direktori yang sama dengan `requirements.txt`. Jalankan perintah berikut:

```bash
streamlit run Air.py
```

Aplikasi akan terbuka secara otomatis di browser pada URL:

```
http://localhost:8501
```

---

## 🌐 Streamlit Cloud (Deploy)

Aplikasi ini juga tersedia online dan dapat diakses melalui:

👉 [https://airindex.streamlit.app/](https://airindex.streamlit.app/)

---

## 📌 Catatan

* Pastikan semua library yang tercantum di `requirements.txt` telah terinstall.
* Gunakan Python 3.9 untuk kompatibilitas maksimal dengan proyek ini.
