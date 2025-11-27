import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

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
    # Cek apakah file ada
    file_path = 'final_df.csv.zip'
    
    if not os.path.exists(file_path):
        st.error(f"File '{file_path}' tidak ditemukan di folder ini. Mohon upload atau pindahkan file ke folder yang sama dengan script ini.")
        return pd.DataFrame()

    # Baca data
    df = pd.read_csv(file_path)

    # Pastikan kolom tanggal dalam format datetime
    # Jika di CSV sudah ada kolom 'date'
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    # Jika belum ada, buat dari kolom year, month, day
    elif {'year', 'month', 'day'}.issubset(df.columns):
        df['date'] = pd.to_datetime(df[['year', 'month', 'day']])
        
    return df

# Memuat data
main_df = load_data()

# Hentikan aplikasi jika data gagal dimuat
if main_df.empty:
    st.stop()

# ==========================================
# 3. SIDEBAR & FILTER
# ==========================================
st.sidebar.header("Filter & Navigasi")

# Menu Navigasi
menu = st.sidebar.radio(
    "Pilih Analisis:",
    ["Overview", "Tren PM2.5 (6 Bulan Terakhir)", "Hubungan Iklim & Polusi", "Analisis RFM (Risiko)", "Perbandingan Stasiun"]
)

# Informasi Dataset
st.sidebar.markdown("---")
st.sidebar.info(f"Dataset: `final_df.csv`\n\nJumlah Baris: {main_df.shape[0]:,}")

# ==========================================
# 4. VISUALISASI UTAMA
# ==========================================

if menu == "Overview":
    st.title("🌤️ Dashboard Kualitas Udara")
    st.markdown("Analisis menyeluruh terhadap data kualitas udara dari file `final_df.csv`.")

    # Metric Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Data", f"{main_df.shape[0]:,}")
    col2.metric("Jumlah Stasiun", len(main_df['station'].unique()))
    col3.metric("Rata-rata PM2.5", f"{main_df['PM2.5'].mean():.2f}")
    col4.metric("Rentang Waktu", f"{main_df['date'].dt.year.min()} - {main_df['date'].dt.year.max()}")

    # Heatmap Korelasi
    st.subheader("Peta Korelasi (Cuaca vs Polutan)")
    
    # Mengambil hanya kolom numerik yang relevan
    numeric_cols = ['PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3', 'TEMP', 'PRES', 'DEWP', 'RAIN', 'WSPM']
    # Pastikan kolom tersebut ada di dataframe
    available_cols = [col for col in numeric_cols if col in main_df.columns]
    
    if available_cols:
        corr = main_df[available_cols].corr()
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
        st.pyplot(fig)
    else:
        st.warning("Kolom numerik untuk korelasi tidak lengkap.")

    # Data Sample
    with st.expander("Lihat Sampel Data"):
        st.dataframe(main_df.head(100))

elif menu == "Tren PM2.5 (6 Bulan Terakhir)":
    st.title("📈 Tren PM2.5: 6 Bulan Terakhir")
    
    # Filter data 6 bulan terakhir
    max_date = main_df['date'].max()
    start_date = max_date - pd.DateOffset(months=6)
    
    df_last_6_months = main_df[main_df['date'] >= start_date].copy()
    
    # Agregasi harian
    daily_avg = df_last_6_months.groupby(['date', 'station'])['PM2.5'].mean().reset_index()
    
    # Identifikasi Top 5 Stasiun dengan rata-rata tertinggi
    top_stations = daily_avg.groupby('station')['PM2.5'].mean().nlargest(5).index.tolist()
    df_top5 = daily_avg[daily_avg['station'].isin(top_stations)]
    
    st.info(f"Periode Analisis: **{start_date.date()}** s/d **{max_date.date()}**")

    # Visualisasi Line Chart
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.lineplot(data=df_top5, x='date', y='PM2.5', hue='station', marker='o', ax=ax)
    plt.title('Tren Harian PM2.5 (5 Stasiun Tertinggi)')
    plt.xlabel('Tanggal')
    plt.ylabel('Konsentrasi PM2.5')
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # Kesimpulan otomatis
    st.markdown(f"""
    **Insight:**
    Grafik di atas menampilkan 5 stasiun dengan rata-rata polusi tertinggi dalam 6 bulan terakhir.
    Stasiun yang termasuk adalah: **{', '.join(top_stations)}**.
    """)

elif menu == "Hubungan Iklim & Polusi":
    st.title("💧 Analisis Korelasi: Kelembaban & PM10")
    
    # Filter Tahun 2016 (Sesuai analisis notebook Anda)
    df_2016 = main_df[main_df['date'].dt.year == 2016]
    
    if not df_2016.empty:
        correlation = df_2016['DEWP'].corr(df_2016['PM10'])
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.metric("Korelasi (DEWP vs PM10)", f"{correlation:.4f}")
            st.caption("Tahun: 2016")
            
        with col2:
            st.write("**Interpretasi:**")
            if abs(correlation) < 0.3:
                st.info("Korelasi sangat lemah. Kelembaban (Dew Point) tidak secara langsung mempengaruhi tingkat PM10 secara signifikan pada tahun ini.")
            else:
                st.info("Terdapat korelasi yang cukup terlihat antara kelembaban dan PM10.")
                
        # Scatter Plot
        st.subheader("Scatter Plot")
        # Sampling agar ringan
        sample_size = min(5000, len(df_2016))
        df_sample = df_2016.sample(n=sample_size, random_state=42)
        
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.regplot(data=df_sample, x='DEWP', y='PM10', 
                    scatter_kws={'alpha':0.3, 's':10}, line_kws={'color':'red'}, ax=ax)
        plt.title('Hubungan DEWP vs PM10 (Sampel Data)')
        st.pyplot(fig)
    else:
        st.warning("Data untuk tahun 2016 tidak ditemukan.")

elif menu == "Analisis RFM (Risiko)":
    st.title("🚨 Analisis RFM (Recency, Frequency, Magnitude)")
    st.write("Mengidentifikasi karakteristik kejadian polusi tinggi (**PM2.5 > 100**).")

    # Logika RFM
    main_df['high_pollution'] = main_df['PM2.5'] > 100
    max_date_global = main_df['date'].max()
    
    # Filter kejadian tinggi
    high_poll_df = main_df[main_df['high_pollution'] == True]
    
    if not high_poll_df.empty:
        # 1. Recency
        recency_df = high_poll_df.groupby('station')['date'].max().reset_index()
        recency_df['Recency'] = (max_date_global - recency_df['date']).dt.days
        
        # 2. Frequency
        freq_df = high_poll_df.groupby('station').size().reset_index(name='Frequency')
        
        # 3. Magnitude
        mag_df = high_poll_df.groupby('station')['PM2.5'].mean().reset_index(name='Magnitude')
        
        # Merge
        rfm = recency_df[['station', 'Recency']].merge(freq_df, on='station').merge(mag_df, on='station')
        rfm = rfm.sort_values(by='Frequency', ascending=False)
        
        # Tampilkan Tabel
        st.dataframe(rfm.style.background_gradient(cmap="OrRd", subset=['Frequency', 'Magnitude']))
        
        # Visualisasi
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Frekuensi Kejadian Tinggi")
            fig, ax = plt.subplots()
            sns.barplot(data=rfm, x='Frequency', y='station', palette="magma", ax=ax)
            st.pyplot(fig)
            
        with col2:
            st.subheader("Magnitude (Rata-rata Saat Tinggi)")
            fig, ax = plt.subplots()
            sns.barplot(data=rfm, x='Magnitude', y='station', palette="Reds", ax=ax)
            st.pyplot(fig)
    else:
        st.success("Tidak ada kejadian polusi tinggi (PM2.5 > 100) dalam dataset ini.")

elif menu == "Perbandingan Stasiun":
    st.title("🌍 Perbandingan Antar Stasiun")
    
    # Hitung rata-rata
    avg_df = main_df.groupby('station')[['PM2.5', 'PM10']].mean().reset_index()
    
    # Transformasi data untuk plotting (melt)
    avg_melted = avg_df.melt(id_vars='station', var_name='Polutan', value_name='Konsentrasi')
    
    st.subheader("Rata-rata PM2.5 dan PM10")
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=avg_melted, x='station', y='Konsentrasi', hue='Polutan', palette='viridis', ax=ax)
    plt.xticks(rotation=45)
    st.pyplot(fig)

    # Pola Jam
    st.subheader("⏰ Pola Polusi Berdasarkan Jam (Rata-rata Global)")
    hourly = main_df.groupby('hour')[['PM2.5', 'PM10']].mean().reset_index()
    
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    sns.lineplot(data=hourly, x='hour', y='PM2.5', label='PM2.5', marker='o', ax=ax2)
    sns.lineplot(data=hourly, x='hour', y='PM10', label='PM10', marker='o', ax=ax2)
    plt.xlabel("Jam (0-23)")
    plt.ylabel("Konsentrasi")
    plt.grid(True, linestyle='--', alpha=0.5)
    st.pyplot(fig2)
