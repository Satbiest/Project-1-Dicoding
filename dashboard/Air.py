import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import zipfile

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Air Quality Dashboard",
    page_icon="🌤️",
    layout="wide"
)

# ==========================================
# 2. FUNGSI LOAD DATA
# ==========================================
@st.cache_data
def load_data():
    zip_path = "final_df.csv.zip"
    csv_filename = "final_df.csv" 

    if not os.path.exists(zip_path):
        # Fallback jika user punya csv langsung tanpa zip
        if os.path.exists(csv_filename):
            df = pd.read_csv(csv_filename)
        else:
            st.error(f"File '{zip_path}' atau '{csv_filename}' tidak ditemukan.")
            return pd.DataFrame()
    else:
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                if csv_filename in z.namelist():
                    with z.open(csv_filename) as f:
                        df = pd.read_csv(f)
                else:
                    csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                    if csv_files:
                        with z.open(csv_files[0]) as f:
                            df = pd.read_csv(f)
                    else:
                        st.error("Tidak ada file CSV di dalam zip.")
                        return pd.DataFrame()
        except Exception as e:
            st.error(f"Error: {e}")
            return pd.DataFrame()

    # Convert to datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    elif {'year', 'month', 'day'}.issubset(df.columns):
        df['date'] = pd.to_datetime(df[['year', 'month', 'day']])
        
    return df

# Load Data Awal
raw_df = load_data()

if raw_df.empty:
    st.stop()

# ==========================================
# 3. SIDEBAR FILTER
# ==========================================
st.sidebar.header("🎛️ Filter Data")

# --- Filter Tanggal ---
min_date = raw_df['date'].min().date()
max_date = raw_df['date'].max().date()

start_date, end_date = st.sidebar.date_input(
    "Rentang Tanggal:",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# --- Filter Stasiun ---
all_stations = sorted(raw_df['station'].unique().tolist())
selected_stations = st.sidebar.multiselect(
    "Pilih Stasiun:",
    all_stations,
    default=all_stations  # Default pilih semua
)

# --- Terapkan Filter ---
# 1. Filter Tanggal
filtered_df = raw_df[
    (raw_df['date'].dt.date >= start_date) & 
    (raw_df['date'].dt.date <= end_date)
]

# 2. Filter Stasiun
if selected_stations:
    filtered_df = filtered_df[filtered_df['station'].isin(selected_stations)]

# Update Main Dataframe yang akan dipakai visualisasi
main_df = filtered_df

# Menu Navigasi
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Pilih Analisis:",
    ["Overview", "Tren PM2.5", "Hubungan Iklim & Polusi", "Analisis RFM (Risiko)", "Perbandingan Stasiun"]
)

st.sidebar.info(f"Data Tersaring: {main_df.shape[0]:,} baris")

# ==========================================
# 4. VISUALISASI UTAMA
# ==========================================

if menu == "Overview":
    st.title("🌤️ Dashboard Kualitas Udara")
    
    # Cek jika data kosong setelah filter
    if main_df.empty:
        st.warning("Tidak ada data untuk rentang tanggal atau stasiun yang dipilih.")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Data", f"{main_df.shape[0]:,}")
    col2.metric("Stasiun Terpilih", len(main_df['station'].unique()))
    col3.metric("Rata-rata PM2.5", f"{main_df['PM2.5'].mean():.2f}")
    col4.metric("Rata-rata PM10", f"{main_df['PM10'].mean():.2f}")

    st.subheader("Peta Korelasi (Berdasarkan Data Terfilter)")
    
    numeric_cols = ['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3', 'TEMP', 'PRES', 'DEWP', 'RAIN', 'WSPM']
    # Hanya gunakan kolom yang ada dan tidak semua NaN
    valid_cols = [c for c in numeric_cols if c in main_df.columns and main_df[c].notna().any()]
    
    if len(valid_cols) > 1:
        corr = main_df[valid_cols].corr()
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
        st.pyplot(fig)
    else:
        st.info("Data tidak cukup untuk membuat korelasi.")

    with st.expander("Lihat Data Terfilter"):
        st.dataframe(main_df.head(100))

elif menu == "Tren PM2.5":
    st.title("📈 Tren PM2.5")
    
    if main_df.empty:
        st.warning("Data kosong. Silakan sesuaikan filter.")
        st.stop()

    # Agregasi Harian agar grafik tidak terlalu berat jika rentang tanggal panjang
    daily_avg = main_df.groupby(['date', 'station'])['PM2.5'].mean().reset_index()
    
    # Identifikasi Top 5 Stasiun dari data yang TERFILTER
    top_stations = daily_avg.groupby('station')['PM2.5'].mean().nlargest(5).index.tolist()
    df_plot = daily_avg[daily_avg['station'].isin(top_stations)]
    
    st.markdown(f"Menampilkan tren untuk stasiun terpilih dalam rentang: **{start_date}** s/d **{end_date}**")

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.lineplot(data=df_plot, x='date', y='PM2.5', hue='station', marker='o', ax=ax)
    plt.title('Tren Harian PM2.5')
    plt.xlabel('Tanggal')
    plt.xticks(rotation=45)
    st.pyplot(fig)

elif menu == "Hubungan Iklim & Polusi":
    st.title("💧 Hubungan Iklim & Polusi")
    
    if main_df.empty:
        st.warning("Data kosong.")
        st.stop()

    st.markdown("Scatter plot di bawah ini menggunakan data yang sudah difilter tanggal dan stasiunnya.")

    correlation = main_df['DEWP'].corr(main_df['PM10'])
    st.metric("Korelasi (DEWP vs PM10)", f"{correlation:.4f}")

    # Sampling untuk scatter plot agar ringan
    sample_size = min(2000, len(main_df))
    df_sample = main_df.sample(n=sample_size, random_state=42)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.regplot(data=df_sample, x='DEWP', y='PM10', 
                scatter_kws={'alpha':0.4, 's':15}, line_kws={'color':'red'}, ax=ax)
    plt.title(f'Scatter Plot DEWP vs PM10 (Sampel {sample_size} Data)')
    st.pyplot(fig)

elif menu == "Analisis RFM (Risiko)":
    st.title("🚨 Analisis Risiko Polusi (RFM)")
    
    if main_df.empty:
        st.warning("Data kosong.")
        st.stop()

    # Logika RFM
    # Kita hitung berdasarkan data terfilter
    main_df['high_pollution'] = main_df['PM2.5'] > 100
    
    # Reference date untuk Recency adalah tanggal MAX dari data terfilter
    current_analysis_date = main_df['date'].max()
    
    high_poll_df = main_df[main_df['high_pollution'] == True]
    
    if not high_poll_df.empty:
        recency = high_poll_df.groupby('station')['date'].max().reset_index()
        recency['Recency'] = (current_analysis_date - recency['date']).dt.days
        
        freq = high_poll_df.groupby('station').size().reset_index(name='Frequency')
        mag = high_poll_df.groupby('station')['PM2.5'].mean().reset_index(name='Magnitude')
        
        rfm = recency[['station', 'Recency']].merge(freq, on='station').merge(mag, on='station')
        rfm = rfm.sort_values(by='Frequency', ascending=False)
        
        st.write(f"Analisis RFM berdasarkan data terpilih (Max Date: {current_analysis_date.date()})")
        st.dataframe(rfm.style.background_gradient(cmap="OrRd", subset=['Frequency', 'Magnitude']))
        
        col1, col2 = st.columns(2)
        with col1:
            fig, ax = plt.subplots()
            sns.barplot(data=rfm, x='Frequency', y='station', palette="magma", ax=ax)
            ax.set_title("Frekuensi Kejadian Tinggi")
            st.pyplot(fig)
        with col2:
            fig, ax = plt.subplots()
            sns.barplot(data=rfm, x='Magnitude', y='station', palette="Reds", ax=ax)
            ax.set_title("Rata-rata PM2.5 saat Tinggi")
            st.pyplot(fig)
    else:
        st.success("Tidak ada kejadian polusi tinggi (PM2.5 > 100) pada data yang difilter.")

elif menu == "Perbandingan Stasiun":
    st.title("🌍 Perbandingan Antar Stasiun")
    
    if main_df.empty:
        st.warning("Data kosong.")
        st.stop()

    avg_df = main_df.groupby('station')[['PM2.5', 'PM10']].mean().reset_index()
    avg_melted = avg_df.melt(id_vars='station', var_name='Polutan', value_name='Konsentrasi')
    
    st.subheader("Rata-rata Polutan (Data Terfilter)")
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=avg_melted, x='station', y='Konsentrasi', hue='Polutan', palette='viridis', ax=ax)
    plt.xticks(rotation=45)
    st.pyplot(fig)
    
    st.subheader("Pola Jam (Hourly)")
    hourly = main_df.groupby('hour')[['PM2.5', 'PM10']].mean().reset_index()
    
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    sns.lineplot(data=hourly, x='hour', y='PM2.5', label='PM2.5', marker='o', ax=ax2)
    sns.lineplot(data=hourly, x='hour', y='PM10', label='PM10', marker='o', ax=ax2)
    plt.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig2)
