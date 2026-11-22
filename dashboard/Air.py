"""AirIndexx — dasbor analitik kualitas udara dalam satu file.

Python 3.10+ | Jalankan: streamlit run app.py
Sumber: unggahan CSV/ZIP, dashboard/final_df.csv.zip, final_df.csv,
atau data demo sintetis yang disertakan di dalam kode.
"""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
import zlib
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Any

import altair as alt
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st


# 1. KONSTANTA DAN IDENTITAS VISUAL
APP_DIR = Path(__file__).resolve().parent
MAX_BYTES = 200 * 1024 * 1024
MENUS = [
    "Overview",
    "Tren PM2.5",
    "Hubungan Iklim & Polusi",
    "Analisis RFM (Risiko)",
    "Perbandingan Stasiun",
    "Pertanyaan Bisnis & Pola Waktu",
]
POLLUTANTS = ["PM2.5", "PM10", "SO2", "NO2", "CO", "O3"]
WEATHER = ["DEWP", "TEMP", "PRES", "RAIN", "WSPM"]
NUMERIC = POLLUTANTS + WEATHER
MONTHS = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
PALETTE = ["#0d9488", "#4667dc", "#ef963f", "#9970cf", "#df627b", "#407d9f"]
CATEGORIES = [
    "Baik", "Sedang", "Tidak sehat bagi kelompok sensitif",
    "Tidak sehat", "Sangat tidak sehat", "Berbahaya",
]
CATEGORY_COLORS = ["#16a078", "#e6b341", "#ed8b3a", "#db5965", "#9a67bc", "#8e3557"]
CATEGORY_LIMITS = [9.0, 35.4, 55.4, 125.4, 225.4]
EPA_SOURCE = (
    "https://www.epa.gov/system/files/documents/2024-02/"
    "pm-naaqs-air-quality-index-fact-sheet.pdf"
)
MODERN_STREAMLIT = tuple(int(x) for x in st.__version__.split(".")[:2]) >= (1, 49)

CSS = """
<style>
  .stApp { background: #f4f7fb; color: #182b46; }
  .stApp p, .stApp label { color: #43566d; }
  .stApp [data-testid="stCaptionContainer"] p { color: #64748b; }
  .stApp [data-testid="stWidgetLabel"] p { color: #334b67; }
  [data-testid="stHeader"] { background: rgba(244,247,251,.96); }
  .block-container { max-width: 1500px; padding-top: 2rem; padding-bottom: 3rem; }
  h1, h2, h3, h4 { color: #182b46; letter-spacing: -.025em; }
  h2 { font-size: 1.55rem !important; }
  h3 { font-size: 1.16rem !important; }
  [data-testid="stSidebar"] { background: #fff; border-right: 1px solid #e1e8f1; }
  [data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
  [data-testid="stSidebar"] [data-baseweb="select"] > div,
  [data-testid="stSidebar"] [data-baseweb="input"],
  [data-testid="stSidebar"] [data-baseweb="base-input"],
  [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background: #f4f7fb; color: #334b67; border-color: #dfe7f0; }
  [data-testid="stSidebar"] input { background: #f4f7fb; color: #334b67; -webkit-text-fill-color: #334b67; }
  [data-testid="stSidebar"] [data-baseweb="select"] svg { color: #64748b; }
  [data-testid="stSidebar"] [data-baseweb="tag"] { background: #dff3ef; color: #126b64; }
  [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
  .stApp [data-testid="stDownloadButton"] button {
    color: #126b64; background: #fff; border: 1px solid #dce7ed; border-radius: 10px; }
  .stApp [data-testid="stAlertContainer"] p { color: #254a69; }
  .stApp [data-testid="stFileUploaderDropzoneInstructions"] small { color: #64748b; }
  .brand { font-size: 1.8rem; font-weight: 850; color: #192f4c; letter-spacing: -.07em; }
  .brand span { color: #0d9488; }
  .brand-sub { color: #64748b; font-size: .88rem; margin: -.2rem 0 1.4rem; }
  .hero { position: relative; overflow: hidden; border-radius: 24px;
    background: linear-gradient(115deg,#132943 0%,#1a4255 65%,#106964 100%);
    color: white; padding: 2.2rem 2.5rem; margin-bottom: 1.25rem;
    box-shadow: 0 10px 30px rgba(19,41,67,.10); }
  .hero:after { content: ''; position: absolute; right: -70px; top: -135px;
    width: 350px; height: 350px; border: 55px solid rgba(124,232,211,.07);
    border-radius: 50%; pointer-events: none; }
  .hero-kicker { color: #8de3d6; font-size: .86rem; font-weight: 650;
    letter-spacing: .12em; text-transform: uppercase; }
  .hero h1 { color: #fff; font-size: clamp(2rem,4vw,3rem); margin: .3rem 0; }
  .hero p { color: #d0e0e9; font-size: 1rem; max-width: 800px; margin: .5rem 0 1rem; }
  .hero-meta { display: flex; gap: .6rem; flex-wrap: wrap; position: relative; z-index: 1; }
  .hero-tag { padding: .35rem .7rem; background: rgba(255,255,255,.10);
    border: 1px solid rgba(255,255,255,.16); border-radius: 50px; font-size: .85rem; }
  [data-testid="stMetric"] { background: #fff; padding: 1.1rem 1.3rem;
    border: 1px solid #e4eaf2; border-radius: 18px;
    box-shadow: 0 4px 18px rgba(34,58,90,.035); min-height: 136px; }
  [data-testid="stMetricLabel"] { color: #64748b; }
  [data-testid="stMetricValue"] { color: #182b46; font-weight: 750; }
  .insight { background: #fff; border: 1px solid #e2eaf1; border-left: 4px solid #0d9488;
    padding: 1.1rem 1.2rem; border-radius: 14px; margin: .4rem 0 1rem; height: 100%; }
  .insight strong { display: block; color: #126b64; font-size: .9rem; margin-bottom: .4rem; }
  .insight p { color: #43566d; font-size: .93rem; line-height: 1.65; margin: 0; }
  .badge { display: inline-block; padding: .35rem .8rem; border-radius: 50px;
    font-size: .88rem; font-weight: 650; margin: .5rem 0; border: 1px solid #dce5ee; }
  .section-note { color: #64748b; font-size: .9rem; margin-bottom: 1rem; }
  [data-testid="stVegaLiteChart"], [data-testid="stImage"] { background: #fff;
    border-radius: 16px; padding: .4rem; border: 1px solid #e6ebf2; }
  [data-testid="stExpander"] { background: #fff; border-radius: 14px; }
  .footer { color: #738297; font-size: .83rem; border-top: 1px solid #dfe7f0;
    margin-top: 2rem; padding-top: 1rem; }
  @media (max-width: 740px) {
    .block-container { padding: 1rem; }
    .hero { padding: 1.6rem; border-radius: 18px; }
    [data-testid="stMetric"] { min-height: 112px; }
  }
</style>
"""


# 2. PEMBACAAN DAN VALIDASI DATA (TANPA MUTASI DATA SUMBER)
class DataValidationError(ValueError):
    """Kesalahan input yang bisa ditindaklanjuti pengguna."""


def canonical_column(name: Any) -> str:
    clean = str(name).strip().lstrip("\ufeff")
    token = clean.lower().replace(" ", "").replace("_", "").replace(".", "")
    aliases = {
        "pm25": "PM2.5", "pm10": "PM10", "so2": "SO2", "no2": "NO2",
        "co": "CO", "o3": "O3", "temp": "TEMP", "pres": "PRES",
        "dewp": "DEWP", "rain": "RAIN", "wspm": "WSPM",
        "date": "date", "datetime": "date", "timestamp": "date", "tanggal": "date",
        "station": "station", "stationname": "station", "stasiun": "station",
        "hour": "hour", "jam": "hour", "year": "year", "month": "month", "day": "day",
    }
    return aliases.get(token, clean)


def normalize_data(raw: pd.DataFrame, dayfirst: bool = False) -> tuple[pd.DataFrame, dict]:
    if raw.empty:
        raise DataValidationError("File tidak berisi baris data.")
    df = raw.copy()
    df.columns = [canonical_column(c) for c in df.columns]
    if df.columns.duplicated().any():
        duplicate = df.columns[df.columns.duplicated()].tolist()
        raise DataValidationError(f"Nama kolom bertabrakan setelah normalisasi: {duplicate}.")
    if "PM2.5" not in df:
        raise DataValidationError("Kolom wajib PM2.5 tidak ditemukan. Alias PM25/pm2_5 juga didukung.")

    notes: list[str] = []
    report: dict[str, Any] = {"input_rows": len(df), "notes": notes}
    if "date" in df:
        text = df["date"].astype("string").str.strip()
        # Pertahankan jam lokal yang tertulis; jangan geser hari menjadi UTC.
        local = text.str.replace(
            r"([T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)(?:Z|[+-]\d{2}:?\d{2})$",
            r"\1", regex=True,
        )
        if text.ne(local).fillna(False).any():
            notes.append("Offset zona waktu dilepas; tanggal dan jam lokal sumber dipertahankan.")
        parsed = pd.to_datetime(local, format="mixed", errors="coerce", dayfirst=dayfirst)
        explicit_time = bool(local.loc[parsed.notna()].str.contains(r"[T ]\d{1,2}:\d{2}", na=False).any())
    elif {"year", "month", "day"}.issubset(df.columns):
        parts = df[["year", "month", "day"]].apply(pd.to_numeric, errors="coerce")
        # pandas dapat melempar ValueError untuk komponen tanggal yang tidak integral.
        parts = parts.where(parts.mod(1).eq(0))
        parsed = pd.to_datetime(parts, errors="coerce")
        explicit_time = False
    else:
        raise DataValidationError("Sediakan date/datetime, atau tiga kolom year, month, dan day.")

    report["invalid_dates"] = int(parsed.isna().sum())
    df["date"] = parsed
    df = df.loc[df["date"].notna()].copy()
    if df.empty:
        raise DataValidationError("Semua tanggal tidak valid. Periksa format tanggal CSV.")
    if report["invalid_dates"]:
        notes.append(f"{report['invalid_dates']:,} baris dengan tanggal tidak valid dikeluarkan.")

    if "station" not in df:
        df["station"] = "Stasiun tunggal"
        notes.append("Kolom station tidak tersedia; seluruh data dianggap berasal dari Stasiun tunggal.")
    df["station"] = df["station"].astype("string").str.strip().replace("", pd.NA)
    unknown = int(df["station"].isna().sum())
    df["station"] = df["station"].fillna("Tidak diketahui")
    if unknown:
        notes.append(f"{unknown:,} nama stasiun kosong diberi label Tidak diketahui.")

    if "hour" in df:
        hour = pd.to_numeric(df["hour"], errors="coerce")
        valid_hour = hour.between(0, 23) & hour.mod(1).eq(0)
        report["invalid_hours"] = int((~valid_hour).sum())
        df["hour"] = hour.where(valid_hour).astype("Int64")
        # Prioritaskan kolom hour; date pada dataset dasar sering hanya berisi hari.
        rebuilt = df["date"].dt.normalize() + pd.to_timedelta(hour.where(valid_hour, 0), unit="h")
        df.loc[valid_hour, "date"] = rebuilt.loc[valid_hour]
        report["hourly_available"] = bool(valid_hour.any())
        if report["invalid_hours"]:
            notes.append(
                f"{report['invalid_hours']:,} nilai hour tidak valid dikecualikan dari analisis jam; "
                "baris tetap digunakan pada analisis lain."
            )
    else:
        df["hour"] = df["date"].dt.hour.astype("Int64")
        report["invalid_hours"] = 0
        report["hourly_available"] = explicit_time
        notes.append("Kolom hour diekstrak otomatis dari date.")
        if not explicit_time:
            notes.append("Sumber hanya memuat tanggal. Analisis jam dinonaktifkan agar tidak memberi puncak 00:00 semu.")

    invalid_numeric: dict[str, int] = {}
    for col in NUMERIC:
        if col not in df:
            continue
        original = df[col]
        numeric = pd.to_numeric(original, errors="coerce").replace([np.inf, -np.inf], np.nan)
        if col in POLLUTANTS + ["RAIN", "WSPM"]:
            numeric = numeric.mask(numeric < 0)
        invalid_numeric[col] = int((original.notna() & numeric.isna()).sum())
        df[col] = numeric
    report["invalid_numeric"] = invalid_numeric
    changed = sum(invalid_numeric.values())
    if changed:
        notes.append(f"{changed:,} sel numerik tidak valid/negatif diubah menjadi nilai kosong, tanpa imputasi.")

    # Hapus duplikat analitik; kolom ID seperti No tidak menentukan keunikan pengukuran.
    analytic_cols = [c for c in ["date", "station", "hour"] + NUMERIC if c in df]
    before = len(df)
    df = df.drop_duplicates(subset=analytic_cols).sort_values(["date", "station"]).reset_index(drop=True)
    report["duplicates"] = before - len(df)
    if report["duplicates"]:
        notes.append(f"{report['duplicates']:,} duplikat pengukuran identik dikeluarkan.")
    report["repeated_timestamps"] = int(df.duplicated(["date", "station"], keep=False).sum())
    if report["repeated_timestamps"]:
        notes.append(
            "Ada pengukuran berbeda pada stasiun dan timestamp yang sama. Semua dipertahankan; "
            "rata-rata serta frekuensi menggunakan bobot per observasi."
        )
    if not df["PM2.5"].notna().any():
        raise DataValidationError("Kolom PM2.5 tidak memiliki nilai numerik nonnegatif yang valid.")
    report["output_rows"] = len(df)
    report["missing_optional"] = [c for c in NUMERIC if c not in df]
    return df, report


@st.cache_data(show_spinner=False, max_entries=4)
def zip_members(payload: bytes) -> list[str]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            return sorted(
                i.filename for i in archive.infolist()
                if not i.is_dir() and i.filename.lower().endswith(".csv")
                and not i.filename.startswith("__MACOSX/")
            )
    except zipfile.BadZipFile as exc:
        raise DataValidationError("Arsip ZIP rusak atau bukan file ZIP yang valid.") from exc


@st.cache_data(show_spinner=False, max_entries=4)
def read_dataset(
    payload: bytes, filename: str, member: str | None = None, dayfirst: bool = False,
) -> tuple[pd.DataFrame, dict]:
    if len(payload) > MAX_BYTES:
        raise DataValidationError("File melebihi batas 200 MB.")
    if filename.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                members = zip_members(payload)
                if not members:
                    raise DataValidationError("Tidak ada CSV di dalam ZIP.")
                preferred = next((x for x in members if Path(x).name.lower() == "final_df.csv"), members[0])
                member = member or preferred
                if member not in members:
                    raise DataValidationError("CSV yang dipilih tidak ada di dalam ZIP.")
                info = archive.getinfo(member)
                if info.file_size > MAX_BYTES:
                    raise DataValidationError("CSV di dalam ZIP melebihi batas 200 MB setelah dekompresi.")
                if info.flag_bits & 1:
                    raise DataValidationError("ZIP berpassword tidak didukung. Unggah CSV tanpa enkripsi.")
                # Baca di memori, tanpa mengekstrak path dari arsip ke filesystem.
                with archive.open(member) as handle:
                    payload = handle.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise DataValidationError("CSV di dalam ZIP terlalu besar.")
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError, zlib.error, EOFError) as exc:
            raise DataValidationError(f"ZIP tidak dapat dibaca: {exc}") from exc
    if not payload:
        raise DataValidationError("File kosong.")
    encoding = "utf-16" if payload.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        text = payload.decode(encoding)
    except UnicodeDecodeError:
        text = payload.decode("cp1252")
    try:
        try:
            separator = csv.Sniffer().sniff(text[:32768], delimiters=",;\t|").delimiter
        except csv.Error:
            separator = ","
        raw = pd.read_csv(
            io.StringIO(text), sep=separator, decimal="," if separator == ";" else ".",
            na_values=["NA", "N/A", "null", "NULL", "None", "-"], low_memory=False,
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DataValidationError(f"CSV tidak dapat dibaca. Periksa delimiter dan susunan kolom. {exc}") from exc
    return normalize_data(raw, dayfirst=dayfirst)


@st.cache_data(show_spinner=False, max_entries=4)
def read_local(path: str, modified_ns: int, file_size: int) -> bytes:
    """mtime dan ukuran menjadi kunci cache agar file yang diganti tidak memakai data lama."""
    if file_size > MAX_BYTES:
        raise DataValidationError("File lokal melebihi batas 200 MB.")
    with Path(path).open("rb") as handle:
        payload = handle.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise DataValidationError("File lokal melebihi batas 200 MB.")
    return payload


def find_local_file() -> Path | None:
    candidates = [
        "dashboard/final_df.csv.zip", "final_df.csv", "dashboard/final_df.csv",
        "final_df.csv.zip", "data/final_df.csv", "data/final_df.csv.zip",
    ]
    for base in dict.fromkeys([APP_DIR, Path.cwd()]):
        for name in candidates:
            if (base / name).is_file():
                return base / name
    return None


@st.cache_data(show_spinner=False)
def demo_data() -> tuple[pd.DataFrame, dict]:
    """Dataset sintetis deterministik; bukan data pengukuran nyata."""
    rng = np.random.default_rng(42)
    timestamps = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h")
    frames = []
    for station, offset in [("Aotizhongxin", 18), ("Changping", 0), ("Dongsi", 12), ("Guanyuan", 6)]:
        n = len(timestamps)
        hour = timestamps.hour.to_numpy()
        season = 25 * np.cos(2 * np.pi * (timestamps.month.to_numpy() - 1) / 12)
        rush = 24 * np.exp(-((hour - 8) / 2.0) ** 2) + 30 * np.exp(-((hour - 20) / 2.5) ** 2)
        weekend = np.where(timestamps.dayofweek >= 5, -9, 0)
        temp = 15 - season * .6 + rng.normal(0, 4, n)
        wind = np.clip(rng.gamma(2, 1, n), .1, 9)
        pm25 = np.clip(45 + offset + season + rush + weekend - 4 * wind + rng.normal(0, 15, n), 1, 350)
        frame = pd.DataFrame({
            "date": timestamps, "station": station, "hour": hour,
            "PM2.5": pm25.round(1), "PM10": (pm25 * 1.35 + rng.gamma(2, 6, n)).round(1),
            "SO2": rng.gamma(2, 5, n).round(1), "NO2": (pm25 * .45 + rng.uniform(2, 15, n)).round(1),
            "CO": rng.uniform(250, 1700, n).round(1), "O3": np.clip(65 + temp * 2 + rng.normal(0, 15, n), 0, None).round(1),
            "TEMP": temp.round(1), "PRES": rng.normal(1012, 8, n).round(1),
            "DEWP": (temp - rng.uniform(3, 14, n)).round(1),
            "RAIN": np.where(rng.random(n) < .06, rng.gamma(1, 2, n), 0).round(1),
            "WSPM": wind.round(1),
        })
        frame.loc[rng.random(n) < .012, "PM2.5"] = np.nan
        frames.append(frame)
    return normalize_data(pd.concat(frames, ignore_index=True))


# 3. FUNGSI ANALISIS MURNI: DAPAT DIUJI TANPA MENJALANKAN UI
def resolve_date_range(value: Any, minimum: date, maximum: date) -> tuple[date, date, str | None]:
    if isinstance(value, (date, datetime, pd.Timestamp)):
        bounds = [pd.Timestamp(value).date()]
    elif value is None:
        bounds = []
    else:
        bounds = [pd.Timestamp(x).date() for x in value if x is not None]
    note = None
    if not bounds:
        return minimum, maximum, "Tanggal belum dipilih; seluruh rentang data digunakan."
    if len(bounds) == 1:
        start = end = bounds[0]
        note = "Satu tanggal dipilih; analisis menggunakan satu hari penuh."
    else:
        start, end = bounds[:2]
        if start > end:
            start, end = end, start
            note = "Urutan tanggal dibalik otomatis menjadi awal hingga akhir."
    start, end = max(minimum, min(start, maximum)), max(minimum, min(end, maximum))
    return start, end, note


def filter_data(df: pd.DataFrame, start: date, end: date, stations: list[str]) -> pd.DataFrame:
    days = df["date"].dt.normalize()
    mask = days.between(pd.Timestamp(start), pd.Timestamp(end)) & df["station"].isin(stations)
    return df.loc[mask].copy()


def category_of(values: pd.Series) -> pd.Series:
    # Pemotongan (bukan pembulatan) satu desimal sesuai interval breakpoint EPA.
    finite = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    truncated = np.floor(finite.where(finite >= 0) * 10 + 1e-9) / 10
    return pd.cut(
        truncated, bins=[-np.inf] + CATEGORY_LIMITS + [np.inf],
        labels=CATEGORIES, right=True, ordered=True,
    )


def hourly_statistics(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.dropna(subset=["PM2.5", "hour"]).groupby("hour", as_index=False)
        .agg(pm25=("PM2.5", "mean"), observations=("PM2.5", "count"))
        .sort_values("hour")
    )


def temporal_statistics(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = df.loc[df["PM2.5"].notna(), ["date", "station", "PM2.5"]].copy()
    work["day_type"] = np.where(work["date"].dt.dayofweek < 5, "Hari Kerja", "Akhir Pekan")
    work["month"] = work["date"].dt.month
    work["day"] = work["date"].dt.normalize()
    daytypes = work.groupby("day_type", as_index=False).agg(
        pm25=("PM2.5", "mean"), observations=("PM2.5", "count"), days=("day", "nunique"),
    )
    monthly = work.groupby("month", as_index=False).agg(
        pm25=("PM2.5", "mean"), observations=("PM2.5", "count"), days=("day", "nunique"),
    )
    monthly["month_name"] = monthly["month"].map(dict(enumerate(MONTHS, 1)))
    return daytypes, monthly


def calculate_rfm(df: pd.DataFrame, threshold: float = 100) -> pd.DataFrame:
    work = df.copy()  # Hindari SettingWithCopyWarning dan perubahan pada main_df.
    work["high_pollution"] = work["PM2.5"].gt(threshold)
    reference = work["date"].max().normalize()
    totals = work.groupby("station")["PM2.5"].count().rename("Observasi valid").to_frame()
    high = work.loc[work["high_pollution"]].copy()
    summary = high.groupby("station").agg(
        Last_high=("date", "max"), Frequency=("PM2.5", "size"), Magnitude=("PM2.5", "mean"),
    )
    rfm = totals.join(summary, how="left")
    rfm["Frequency"] = rfm["Frequency"].fillna(0).astype(int)
    rfm["Recency"] = (reference - rfm["Last_high"].dt.normalize()).dt.days.astype("Int64")
    rfm["Proporsi tinggi (%)"] = 100 * rfm["Frequency"] / rfm["Observasi valid"].replace(0, np.nan)
    rfm["Status"] = np.select(
        [rfm["Observasi valid"].eq(0), rfm["Frequency"].eq(0)],
        ["Data PM2.5 kosong", "Tanpa observasi tinggi"], default="Ada observasi tinggi",
    )
    return (
        rfm.reset_index()[[
            "station", "Recency", "Frequency", "Magnitude", "Observasi valid", "Proporsi tinggi (%)", "Status",
        ]].sort_values(["Frequency", "Proporsi tinggi (%)"], ascending=False, na_position="last")
        .reset_index(drop=True)
    )


def business_insights(df: pd.DataFrame, hourly_available: bool) -> list[tuple[str, str]]:
    items = []
    hourly = hourly_statistics(df) if hourly_available else pd.DataFrame()
    if not hourly.empty:
        highest = hourly["pm25"].max()
        tied = hourly.loc[np.isclose(hourly["pm25"], highest, rtol=0, atol=1e-9), "hour"]
        hours = ", ".join(f"{int(h):02d}:00" for h in tied)
        items.append(("Jam prioritas pemantauan", f"Rata-rata PM2.5 tertinggi pada {hours}: {highest:.1f} µg/m³. Gunakan periode ini untuk memprioritaskan pemantauan operasional."))
    else:
        items.append(("Pola per jam", "Informasi jam yang valid belum tersedia pada data terfilter. Jam puncak belum dapat disimpulkan."))
    daytypes, monthly = temporal_statistics(df)
    means = daytypes.set_index("day_type")["pm25"]
    if {"Hari Kerja", "Akhir Pekan"}.issubset(means.index):
        working, weekend = float(means["Hari Kerja"]), float(means["Akhir Pekan"])
        difference = weekend - working
        if np.isclose(difference, 0, atol=1e-9, rtol=0):
            text = f"Rata-rata hari kerja dan akhir pekan sama, yaitu {working:.1f} µg/m³."
        else:
            direction = "lebih tinggi" if difference > 0 else "lebih rendah"
            relative = f" ({abs(difference) / working * 100:.1f}%)" if working > 0 else ""
            text = f"Akhir pekan {direction} {abs(difference):.1f} µg/m³{relative} dibanding hari kerja. Evaluasi jadwal aktivitas dengan mempertimbangkan cakupan observasi."
        items.append(("Hari kerja vs akhir pekan", text))
    else:
        items.append(("Hari kerja vs akhir pekan", "Perbandingan memerlukan observasi valid pada kedua jenis hari. Perluas rentang tanggal untuk melengkapinya."))
    if not monthly.empty:
        highest = monthly["pm25"].max()
        tied = monthly.loc[np.isclose(monthly["pm25"], highest, rtol=0, atol=1e-9), "month_name"]
        month_names = ", ".join(tied)
        qualification = "Hanya satu bulan tersedia; pola musiman belum dapat dibandingkan." if len(monthly) == 1 else "Siapkan kapasitas pemantauan lebih besar pada periode ini."
        items.append(("Pola bulanan", f"{month_names} memiliki rata-rata tertinggi, {highest:.1f} µg/m³. {qualification}"))
    return items


# 4. KOMPONEN UI DAN GRAFIK
def number(value: Any, digits: int = 1) -> str:
    return "—" if pd.isna(value) else f"{float(value):,.{digits}f}"


def insight(title: str, text: str) -> None:
    st.markdown(
        f'<div class="insight"><strong>{escape(title)}</strong><p>{escape(text)}</p></div>',
        unsafe_allow_html=True,
    )


def display_chart(chart: Any, height: int = 330) -> None:
    chart = (
        chart.properties(height=height)
        .configure(
            background="#ffffff",
            view=alt.ViewConfig(strokeWidth=0),
            axis=alt.AxisConfig(
                labelColor="#63738a", titleColor="#465a73", gridColor="#edf1f6",
                domainColor="#dce5ef", tickColor="#dce5ef", labelFontSize=12, titleFontSize=13,
            ),
            legend=alt.LegendConfig(labelColor="#465a73", titleColor="#465a73", orient="bottom"),
        )
    )
    kwargs = {"width": "stretch"} if MODERN_STREAMLIT else {"use_container_width": True}
    st.altair_chart(chart, theme=None, **kwargs)


def display_table(df: Any, **kwargs: Any) -> None:
    sizing = {"width": "stretch"} if MODERN_STREAMLIT else {"use_container_width": True}
    st.dataframe(df, hide_index=True, **sizing, **kwargs)


def bar_chart(df: pd.DataFrame, x: str, y: str, x_title: str, y_title: str, color: str = PALETTE[0]) -> Any:
    return alt.Chart(df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color=color).encode(
        x=alt.X(x, title=x_title, sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y, title=y_title),
        tooltip=[alt.Tooltip(x, title=x_title), alt.Tooltip(y, title=y_title, format=".2f")],
    )


def show_hero(menu: str, start: date, end: date, df: pd.DataFrame, source: str, is_demo: bool) -> None:
    descriptions = {
        "Overview": "Dari angka menjadi arah. Kenali kualitas udara, area prioritas, dan perubahan yang berarti.",
        "Tren PM2.5": "Ikuti perubahan konsentrasi partikel halus di setiap stasiun dari waktu ke waktu.",
        "Hubungan Iklim & Polusi": "Jelajahi keterkaitan kondisi meteorologi dengan konsentrasi polutan.",
        "Analisis RFM (Risiko)": "Petakan kapan polusi tinggi terakhir teramati, seberapa sering, dan seberapa besar.",
        "Perbandingan Stasiun": "Bandingkan konsentrasi polutan dan temukan stasiun yang perlu diprioritaskan.",
        "Pertanyaan Bisnis & Pola Waktu": "Ubah pola jam, jenis hari, kategori, dan bulan menjadi masukan operasional.",
    }
    tags = [f"{start:%d/%m/%Y} – {end:%d/%m/%Y}", f"{df['station'].nunique()} stasiun", "Demo sintetis" if is_demo else source]
    st.markdown(
        f'<div class="hero"><div class="hero-kicker">AirIndexx / Air quality intelligence</div>'
        f'<h1>{escape(menu)}</h1><p>{escape(descriptions[menu])}</p><div class="hero-meta">'
        + "".join(f'<span class="hero-tag">{escape(tag)}</span>' for tag in tags)
        + "</div></div>", unsafe_allow_html=True,
    )


def show_metrics(df: pd.DataFrame) -> None:
    valid = int(df["PM2.5"].notna().sum())
    a, b, c, d = st.columns(4)
    a.metric("Observasi terfilter", f"{len(df):,}", help="Jumlah baris setelah validasi serta filter tanggal dan stasiun.")
    b.metric("Stasiun aktif", f"{df['station'].nunique():,}")
    c.metric("Rerata PM2.5", number(df["PM2.5"].mean()), help=f"Satuan µg/m³. Dihitung dari {valid:,} observasi PM2.5 valid; tanpa imputasi.")
    pm10 = df["PM10"].mean() if "PM10" in df else np.nan
    d.metric("Rerata PM10", number(pm10), help="Satuan µg/m³. Tanda — berarti kolom atau nilai valid belum tersedia.")
    st.caption(f"PM2.5 valid: {valid:,}/{len(df):,} observasi ({valid / len(df):.1%}). Satuan konsentrasi mengikuti dataset; PM2.5 dan PM10 diasumsikan µg/m³.")
    if valid:
        label = str(category_of(pd.Series([df["PM2.5"].mean()])).iloc[0])
        color = CATEGORY_COLORS[CATEGORIES.index(label)]
        st.markdown(
            f'<span class="badge" style="color:#243b55;background:{color}14;border-color:{color}55">'
            f'Kategori konsentrasi rata-rata: {escape(label)}</span>', unsafe_allow_html=True,
        )
        st.caption(
            f"[Acuan breakpoint EPA 2024]({EPA_SOURCE}) berbasis konsentrasi 24 jam. "
            "Badge mengklasifikasikan rerata observasi terfilter; bukan AQI atau ISPU resmi."
        )


def show_quality(df: pd.DataFrame, report: dict) -> None:
    with st.expander("Kualitas data & metode analisis"):
        st.write(f"Baris input **{report['input_rows']:,}** · Baris siap analisis **{report['output_rows']:,}**.")
        for note in report["notes"]:
            st.write(f"• {note}")
        if report["missing_optional"]:
            st.info("Kolom opsional tidak tersedia: " + ", ".join(report["missing_optional"]) + ". Grafik terkait akan dilewati.")
        quality = pd.DataFrame([
            {"Kolom": c, "Nilai valid": int(df[c].notna().sum()), "Kosong (%)": round(df[c].isna().mean() * 100, 2)}
            for c in NUMERIC if c in df
        ])
        display_table(quality)
        st.caption(
            "Rata-rata menggunakan bobot per observasi valid. Stasiun dengan data lebih lengkap dapat memiliki bobot lebih besar. "
            "Tanggal dan jam mengikuti waktu lokal sumber. Hari kerja = Senin–Jumat; akhir pekan = Sabtu–Minggu, tanpa kalender hari libur. "
            "Hubungan statistik bersifat deskriptif; perbedaan tidak membuktikan sebab-akibat."
        )


def show_category_method() -> None:
    st.caption(
        "Kategori konsentrasi observasi mengadaptasi breakpoint PM2.5 EPA 2024. "
        "Breakpoint asli berbasis rata-rata 24 jam. Klasifikasi baris di sini bukan perhitungan AQI, NowCast, atau ISPU resmi. "
        "Nilai dipotong ke satu desimal sebelum klasifikasi; observasi kosong dikecualikan."
    )
    with st.expander("Lihat ambang kategori PM2.5"):
        display_table(pd.DataFrame({
            "Kategori": CATEGORIES,
            "PM2.5 (µg/m³) setelah pemotongan 1 desimal": [
                "0,0–9,0", "9,1–35,4", "35,5–55,4", "55,5–125,4", "125,5–225,4", "≥225,5",
            ],
        }))
        st.markdown(f"Acuan: [EPA — Final Updates to the Air Quality Index (2024)]({EPA_SOURCE}).")


# 5. ENAM MENU ANALISIS
def render_overview(df: pd.DataFrame) -> None:
    left, right = st.columns([1.8, 1])
    with left:
        st.subheader("Jejak harian PM2.5")
        daily = df.assign(day=df["date"].dt.normalize()).groupby("day", as_index=False).agg(
            pm25=("PM2.5", "mean"), observations=("PM2.5", "count"),
        )
        chart = alt.Chart(daily).mark_area(
            line={"color": PALETTE[0], "strokeWidth": 2},
            color=alt.Gradient(gradient="linear", stops=[alt.GradientStop(color="#0d948845", offset=0), alt.GradientStop(color="#0d948804", offset=1)], x1=0, y1=0, x2=0, y2=1),
        ).encode(
            x=alt.X("day:T", title="Tanggal"), y=alt.Y("pm25:Q", title="PM2.5 (µg/m³)"),
            tooltip=[alt.Tooltip("day:T", title="Tanggal", format="%d %b %Y"), alt.Tooltip("pm25:Q", title="PM2.5", format=".2f"), alt.Tooltip("observations:Q", title="Observasi valid")],
        ).interactive()
        display_chart(chart, 300)
    with right:
        st.subheader("Prioritas stasiun")
        stations = df.groupby("station", as_index=False).agg(pm25=("PM2.5", "mean"), observations=("PM2.5", "count"))
        stations = stations.dropna(subset=["pm25"]).nlargest(5, "pm25")
        chart = alt.Chart(stations).mark_bar(cornerRadiusEnd=5, color=PALETTE[0]).encode(
            x=alt.X("pm25:Q", title="PM2.5 (µg/m³)"), y=alt.Y("station:N", title=None, sort="-x"),
            tooltip=["station:N", alt.Tooltip("pm25:Q", format=".2f"), "observations:Q"],
        )
        display_chart(chart, 300)

    st.subheader("Peta korelasi")
    columns = [c for c in NUMERIC if c in df and df[c].count() >= 2 and df[c].nunique() > 1]
    if len(columns) < 2:
        st.info("Korelasi memerlukan setidaknya dua kolom numerik dengan variasi dan pasangan nilai yang cukup.")
        return
    corr = df[columns].corr(min_periods=3)
    if not corr.where(~np.eye(len(columns), dtype=bool)).notna().any().any():
        st.info("Tidak cukup pasangan nilai valid untuk menghitung korelasi antarvariabel.")
        return
    with plt.rc_context({"font.size": 10, "axes.facecolor": "white", "figure.facecolor": "white"}):
        fig, ax = plt.subplots(figsize=(12, 5.5))
        try:
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="vlag", center=0, vmin=-1, vmax=1, linewidths=.6, linecolor="white", ax=ax)
            ax.set_title("Korelasi Pearson · data terfilter", loc="left", pad=14, color="#182b46")
            plt.tight_layout()
            st.pyplot(fig, **({"width": "stretch"} if MODERN_STREAMLIT else {"use_container_width": True}))
        finally:
            plt.close(fig)
    st.caption("Setiap pasangan menggunakan baris yang valid pada kedua kolom, minimal tiga pasangan. Kotak kosong berarti korelasi tidak dapat dihitung.")


def render_trend(df: pd.DataFrame, threshold: float) -> None:
    a, b = st.columns([1, 2])
    aggregation = a.selectbox("Resolusi waktu", ["Harian", "Mingguan", "Bulanan"], key="trend_resolution")
    ranks = df.groupby("station")["PM2.5"].mean().dropna().sort_values(ascending=False)
    default = ranks.head(5).index.tolist()
    chosen = b.multiselect("Stasiun pada grafik", ranks.index.tolist(), default=default, key="trend_stations")
    if not chosen:
        st.info("Pilih minimal satu stasiun pada kontrol grafik tren.")
        return
    frequency = {"Harian": "D", "Mingguan": "W-MON", "Bulanan": "MS"}[aggregation]
    work = df.loc[df["station"].isin(chosen)].copy()
    aggregated = work.groupby([pd.Grouper(key="date", freq=frequency), "station"], observed=True).agg(
        pm25=("PM2.5", "mean"), observations=("PM2.5", "count"),
    ).reset_index()
    st.caption("Pilihan awal: lima stasiun dengan rata-rata observasi PM2.5 tertinggi dalam filter. Mingguan berakhir pada Senin; periode tepi dapat tidak lengkap.")
    lines = alt.Chart(aggregated).mark_line(strokeWidth=2.4, point=len(aggregated) <= 180).encode(
        x=alt.X("date:T", title="Periode"), y=alt.Y("pm25:Q", title="Rata-rata PM2.5 (µg/m³)"),
        color=alt.Color("station:N", title="Stasiun", scale=alt.Scale(range=PALETTE)),
        tooltip=["station:N", alt.Tooltip("date:T", title="Periode", format="%d %b %Y"), alt.Tooltip("pm25:Q", format=".2f", title="PM2.5"), alt.Tooltip("observations:Q", title="Observasi valid")],
    ).interactive()
    rule = alt.Chart(pd.DataFrame({"threshold": [threshold]})).mark_rule(color="#df627b", strokeDash=[6, 4]).encode(y="threshold:Q")
    display_chart(lines + rule, 420)
    st.caption(f"Garis putus-putus = ambang operasional RFM {threshold:g} µg/m³. Grafik menampilkan rata-rata periode; RFM mengevaluasi setiap observasi.")
    valid = aggregated.dropna(subset=["pm25"])
    if not valid.empty:
        peak = valid.loc[valid["pm25"].idxmax()]
        insight("Periode yang perlu ditinjau", f"Puncak rata-rata periode pada grafik terjadi di {peak['station']} ({peak['date']:%d/%m/%Y}), sebesar {peak['pm25']:.1f} µg/m³.")


def render_climate(df: pd.DataFrame) -> None:
    climates = [c for c in WEATHER if c in df and df[c].notna().any()]
    pollutants = [c for c in POLLUTANTS if c in df and df[c].notna().any()]
    if not climates:
        st.info("Analisis ini memerlukan minimal satu kolom iklim: DEWP, TEMP, PRES, RAIN, atau WSPM.")
        return
    a, b = st.columns(2)
    x = a.selectbox("Variabel iklim", climates, key="climate_x")
    y = b.selectbox("Polutan", pollutants, index=pollutants.index("PM10") if "PM10" in pollutants else 0, key="climate_y")
    pairs = df[[x, y, "station"]].dropna(subset=[x, y]).copy()
    valid_corr = len(pairs) >= 3 and pairs[x].nunique() > 1 and pairs[y].nunique() > 1
    correlation = pairs[x].corr(pairs[y]) if valid_corr else np.nan
    a, b, c = st.columns(3)
    a.metric(f"Korelasi Pearson · {x} vs {y}", number(correlation, 4))
    b.metric("Pasangan nilai valid", f"{len(pairs):,}")
    c.metric("Titik pada grafik", f"{min(2000, len(pairs)):,}")
    if pairs.empty:
        st.info("Tidak ada baris dengan pasangan nilai yang lengkap pada filter ini.")
        return
    sample = pairs.sample(n=min(2000, len(pairs)), random_state=42).rename(columns={x: "climate", y: "pollution"})
    points = alt.Chart(sample).mark_circle(size=35, opacity=.38, color=PALETTE[0]).encode(
        x=alt.X("climate:Q", title=f"{x} (satuan sumber)", scale=alt.Scale(zero=False)),
        y=alt.Y("pollution:Q", title=f"{y} (satuan sumber)", scale=alt.Scale(zero=False)),
        tooltip=["station:N", alt.Tooltip("climate:Q", title=x, format=".2f"), alt.Tooltip("pollution:Q", title=y, format=".2f")],
    )
    chart = points
    if valid_corr:
        slope = pairs[x].cov(pairs[y]) / pairs[x].var()
        xline = np.array([pairs[x].min(), pairs[x].max()])
        prediction = pairs[y].mean() + slope * (xline - pairs[x].mean())
        regression = alt.Chart(pd.DataFrame({"climate": xline, "pollution": prediction})).mark_line(color="#df627b", strokeWidth=2.5).encode(x="climate:Q", y="pollution:Q")
        chart += regression
    else:
        st.info("Korelasi dan garis regresi memerlukan minimal tiga pasangan dan variasi pada kedua variabel.")
    display_chart(chart.interactive(), 420)
    st.caption("Titik menggunakan sampel deterministik maksimal 2.000 baris. Korelasi dan regresi dihitung dari seluruh pasangan valid terfilter; tidak memerlukan statsmodels.")
    if pd.notna(correlation):
        strength = "kuat" if abs(correlation) >= .7 else "sedang" if abs(correlation) >= .4 else "lemah"
        direction = "positif" if correlation > 0 else "negatif" if correlation < 0 else "tanpa arah linear"
        insight("Interpretasi hubungan", f"Hubungan linear {x} dan {y} teramati {strength}, {direction} (r = {correlation:.3f}). Gunakan sebagai petunjuk eksplorasi; korelasi tidak menetapkan penyebab polusi.")


def render_rfm(df: pd.DataFrame, threshold: float) -> None:
    rfm = calculate_rfm(df, threshold)
    st.caption(
        f"Ambang tinggi: PM2.5 > {threshold:g} µg/m³ · Tanggal acuan: {df['date'].max():%d/%m/%Y}. "
        "Ubah ambang pada sidebar untuk memperbarui analisis."
    )
    a, b, c = st.columns(3)
    a.metric("Stasiun dengan observasi tinggi", int(rfm["Frequency"].gt(0).sum()))
    b.metric("Observasi polusi tinggi", f"{rfm['Frequency'].sum():,}")
    c.metric("Proporsi observasi tinggi", f"{rfm['Frequency'].sum() / df['PM2.5'].count():.1%}")
    with st.expander("Cara membaca RFM", expanded=True):
        st.write(
            "**Recency** = hari kalender sejak observasi tinggi terakhir hingga tanggal maksimum data terfilter; "
            "nilai lebih kecil berarti lebih baru. **Frequency** = jumlah observasi PM2.5 di atas ambang, "
            "bukan jumlah episode polusi yang independen. **Magnitude** = rata-rata PM2.5 hanya pada observasi tinggi. "
            "Stasiun tanpa observasi tinggi tetap ditampilkan; Recency dan Magnitude tidak didefinisikan."
        )
        st.caption("Proporsi tinggi membagi Frequency dengan observasi PM2.5 valid per stasiun, sehingga perbedaan cakupan data dapat terlihat.")
    display_table(rfm, column_config={
        "Recency": st.column_config.NumberColumn("Recency (hari)", format="%d"),
        "Magnitude": st.column_config.NumberColumn("Magnitude (µg/m³)", format="%.2f"),
        "Proporsi tinggi (%)": st.column_config.NumberColumn("Proporsi tinggi (%)", format="%.2f"),
    })
    high = rfm.loc[rfm["Frequency"].gt(0)].head(20).copy()
    if high.empty:
        st.success(f"Tidak ada observasi polusi tinggi (PM2.5 > {threshold:g} µg/m³) pada data terfilter.")
        return
    left, right = st.columns(2)
    for container, field, title, color in [
        (left, "Frequency", "Frekuensi observasi tinggi", PALETTE[0]),
        (right, "Magnitude", "Besaran PM2.5 saat tinggi", "#df627b"),
    ]:
        with container:
            st.subheader(title)
            chart = alt.Chart(high).mark_bar(cornerRadiusEnd=5, color=color).encode(
                x=alt.X(f"{field}:Q", title="Observasi" if field == "Frequency" else "PM2.5 (µg/m³)"),
                y=alt.Y("station:N", sort="-x", title=None),
                tooltip=["station:N", "Frequency:Q", alt.Tooltip("Magnitude:Q", format=".2f"), alt.Tooltip("Proporsi tinggi (%):Q", format=".2f")],
            )
            display_chart(chart, max(300, len(high) * 25))
    top = high.iloc[0]
    insight("Prioritas peninjauan", f"{top['station']} memiliki {int(top['Frequency']):,} observasi tinggi ({top['Proporsi tinggi (%)']:.1f}% dari data validnya). Tinjau bersama Recency dan Magnitude sebelum menentukan prioritas lapangan.")


def render_stations(df: pd.DataFrame, hourly_available: bool) -> None:
    cols = [c for c in ["PM2.5", "PM10"] if c in df and df[c].notna().any()]
    means = df.groupby("station")[cols].mean().sort_values("PM2.5", ascending=False)
    top = means.head(20).reset_index()
    st.subheader("Rata-rata polutan per stasiun")
    if len(means) > 20:
        st.caption("Grafik dibatasi ke 20 stasiun dengan rata-rata PM2.5 tertinggi; tabel memuat seluruh stasiun.")
    melted = top.melt(id_vars="station", var_name="pollutant", value_name="concentration").dropna()
    chart = alt.Chart(melted).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("station:N", title="Stasiun", sort=top["station"].tolist(), axis=alt.Axis(labelAngle=-35)),
        xOffset="pollutant:N", y=alt.Y("concentration:Q", title="Rata-rata (µg/m³)"),
        color=alt.Color("pollutant:N", title="Polutan", scale=alt.Scale(range=PALETTE[:2])),
        tooltip=["station:N", "pollutant:N", alt.Tooltip("concentration:Q", format=".2f")],
    )
    display_chart(chart, 380)
    counts = df.groupby("station")["PM2.5"].count().rename("Observasi PM2.5 valid")
    display_table(means.join(counts).reset_index().round(2))
    st.subheader("Pola jam lintas stasiun terpilih")
    if not hourly_available:
        st.info("Pola jam memerlukan kolom hour valid atau timestamp yang memuat jam.")
        return
    hourly = df.dropna(subset=["hour"]).groupby("hour")[cols].mean().reset_index()
    melted = hourly.melt(id_vars="hour", var_name="pollutant", value_name="concentration").dropna()
    if melted.empty:
        st.info("Tidak ada konsentrasi valid dengan informasi jam pada filter ini.")
        return
    chart = alt.Chart(melted).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("hour:Q", title="Jam lokal", scale=alt.Scale(domain=[0, 23]), axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("concentration:Q", title="Rata-rata (µg/m³)"),
        color=alt.Color("pollutant:N", title="Polutan", scale=alt.Scale(range=PALETTE[:2])),
        tooltip=["hour:Q", "pollutant:N", alt.Tooltip("concentration:Q", format=".2f")],
    ).interactive()
    display_chart(chart)


def render_business(df: pd.DataFrame, hourly_available: bool) -> None:
    hourly = hourly_statistics(df) if hourly_available else pd.DataFrame()
    daytypes, monthly = temporal_statistics(df)
    st.subheader("1. Kapan jam puncak polusi?")
    if hourly.empty:
        st.info("Jam puncak belum dapat dihitung: sumber tidak memuat informasi jam yang valid pada filter ini.")
    else:
        peak = hourly["pm25"].max()
        hourly["peak"] = np.isclose(hourly["pm25"], peak, atol=1e-9, rtol=0)
        chart = alt.Chart(hourly).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X("hour:O", title="Jam lokal", sort=list(range(24)), axis=alt.Axis(labelAngle=0)),
            y=alt.Y("pm25:Q", title="Rata-rata PM2.5 (µg/m³)"),
            color=alt.condition("datum.peak", alt.value("#ef963f"), alt.value(PALETTE[0])),
            tooltip=[alt.Tooltip("hour:O", title="Jam"), alt.Tooltip("pm25:Q", title="PM2.5", format=".2f"), alt.Tooltip("observations:Q", title="Observasi valid")],
        )
        display_chart(chart, 290)
        if len(hourly) < 24:
            st.caption(f"Hanya {len(hourly)} dari 24 jam memiliki observasi valid. Puncak berlaku pada jam yang tersedia.")

    left, right = st.columns(2)
    with left:
        st.subheader("2. Hari kerja vs akhir pekan")
        chart = bar_chart(daytypes, "day_type:N", "pm25:Q", "Jenis hari", "PM2.5 (µg/m³)")
        display_chart(chart, 310)
        display_table(daytypes.rename(columns={"day_type": "Jenis hari", "pm25": "PM2.5", "observations": "Observasi valid", "days": "Hari tercakup"}).round(2))
    with right:
        st.subheader("3. Proporsi kategori kualitas udara")
        categories = category_of(df["PM2.5"])
        counts = categories.value_counts(sort=False).reindex(CATEGORIES, fill_value=0)
        distribution = pd.DataFrame({"category": CATEGORIES, "observations": counts.to_numpy()})
        distribution["share"] = distribution["observations"] / distribution["observations"].sum()
        donut = alt.Chart(distribution).mark_arc(innerRadius=72, outerRadius=112, cornerRadius=3).encode(
            theta=alt.Theta("observations:Q"),
            color=alt.Color("category:N", title="Kategori", scale=alt.Scale(domain=CATEGORIES, range=CATEGORY_COLORS), sort=CATEGORIES, legend=alt.Legend(labelLimit=280)),
            order=alt.Order("category:N", sort="ascending"),
            tooltip=[alt.Tooltip("category:N", title="Kategori"), alt.Tooltip("observations:Q", title="Observasi valid"), alt.Tooltip("share:Q", title="Proporsi", format=".1%")],
        )
        display_chart(donut, 310)
        display_table(distribution.assign(share=(distribution["share"] * 100).round(2)).rename(columns={"category": "Kategori", "observations": "Observasi valid", "share": "Proporsi (%)"}))
    show_category_method()

    st.subheader("4. Bulan mana memiliki rata-rata PM2.5 tertinggi?")
    chart = alt.Chart(monthly).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, color="#4667dc").encode(
        x=alt.X("month_name:N", title="Bulan", sort=MONTHS, axis=alt.Axis(labelAngle=-30)),
        y=alt.Y("pm25:Q", title="Rata-rata PM2.5 (µg/m³)"),
        tooltip=[alt.Tooltip("month_name:N", title="Bulan"), alt.Tooltip("pm25:Q", title="PM2.5", format=".2f"), alt.Tooltip("observations:Q", title="Observasi valid"), alt.Tooltip("days:Q", title="Hari tercakup")],
    )
    display_chart(chart, 320)
    st.caption("Bulan yang sama digabung lintas tahun dalam filter. Bulan tanpa nilai valid tidak digambar. Perbedaan tahun, jumlah observasi, dan cakupan stasiun dapat memengaruhi perbandingan.")
    with st.expander("Rincian bulanan"):
        display_table(monthly[["month_name", "pm25", "observations", "days"]].rename(columns={"month_name": "Bulan", "pm25": "PM2.5", "observations": "Observasi valid", "days": "Hari tercakup"}).round(2))

    if not hourly.empty:
        st.subheader("Peta waktu · hari × jam")
        work = df.dropna(subset=["hour", "PM2.5"]).copy()
        work["weekday"] = work["date"].dt.dayofweek.map(dict(enumerate(DAYS)))
        grid = work.groupby(["weekday", "hour"], as_index=False).agg(pm25=("PM2.5", "mean"), observations=("PM2.5", "count"))
        chart = alt.Chart(grid).mark_rect(cornerRadius=3).encode(
            x=alt.X("hour:O", title="Jam lokal", sort=list(range(24)), axis=alt.Axis(labelAngle=0)),
            y=alt.Y("weekday:N", title=None, sort=DAYS),
            color=alt.Color("pm25:Q", title="PM2.5", scale=alt.Scale(scheme="tealblues")),
            tooltip=["weekday:N", "hour:O", alt.Tooltip("pm25:Q", format=".2f"), "observations:Q"],
        )
        display_chart(chart, 270)


# 6. SUMBER DATA, SIDEBAR, DAN APLIKASI UTAMA
def choose_source() -> tuple[pd.DataFrame, dict, str, bool, str]:
    panel = st.sidebar.expander("Sumber & format data")
    mode = panel.selectbox("Sumber data", ["Otomatis / unggahan", "Demo sintetis"], key="source_mode")
    upload = panel.file_uploader("Unggah CSV atau ZIP", type=["csv", "zip"], disabled=mode == "Demo sintetis")
    dayfirst = panel.checkbox("Format tanggal hari/bulan/tahun", value=False, help="Aktifkan untuk tanggal ambigu seperti 03/04/2024 = 3 April. Format ISO YYYY-MM-DD tetap disarankan.")
    if mode == "Demo sintetis":
        frame, report = demo_data()
        return frame, report, "Demo sintetis", True, "demo-v1"
    local_path = find_local_file() if upload is None else None
    if upload is not None:
        if upload.size > MAX_BYTES:
            raise DataValidationError("Unggahan melebihi batas 200 MB.")
        payload, filename = upload.getvalue(), upload.name
    elif local_path is not None:
        stat = local_path.stat()
        payload = read_local(str(local_path), stat.st_mtime_ns, stat.st_size)
        filename = local_path.name
    else:
        panel.caption("File lokal belum ditemukan. Demo sintetis diaktifkan agar aplikasi dapat dicoba.")
        frame, report = demo_data()
        return frame, report, "Demo sintetis", True, "demo-v1"
    member = None
    if filename.lower().endswith(".zip"):
        members = zip_members(payload)
        if not members:
            raise DataValidationError("Tidak ada file CSV di dalam ZIP.")
        preferred = next((x for x in members if Path(x).name.lower() == "final_df.csv"), members[0])
        member = panel.selectbox("CSV di dalam ZIP", members, index=members.index(preferred)) if len(members) > 1 else members[0]
    signature = hashlib.sha256(payload).hexdigest()[:16] + str(member) + str(dayfirst)
    with st.spinner("Memvalidasi data kualitas udara…"):
        frame, report = read_dataset(payload, filename, member, dayfirst)
    source = f"{filename} / {Path(member).name}" if member else filename
    return frame, report, source, False, signature


def main() -> None:
    st.set_page_config(page_title="AirIndexx · Kualitas Udara", page_icon="🌬️", layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    # Grafik menerima data agregat atau sampel <=2.000 baris, bukan jutaan baris mentah.
    alt.data_transformers.disable_max_rows()
    st.sidebar.markdown('<div class="brand">Air<span>Indexx</span></div><div class="brand-sub">Pahami udara. Tentukan langkah.</div>', unsafe_allow_html=True)
    try:
        raw_df, report, source, is_demo, signature = choose_source()
    except (DataValidationError, OSError, UnicodeError, ValueError, OverflowError) as exc:
        st.error(f"Data belum dapat diproses: {exc}")
        st.info("Periksa CSV/ZIP atau pilih Demo sintetis di sidebar. Kolom minimal: date dan PM2.5; station serta hour disarankan.")
        st.code("date,station,hour,PM2.5,PM10,DEWP\n2024-01-01,Aotizhongxin,8,42.5,66.0,-4.0\n2024-01-01,Aotizhongxin,9,38.0,59.2,-3.2", language="text")
        st.stop()

    minimum, maximum = raw_df["date"].min().date(), raw_df["date"].max().date()
    stations = sorted(raw_df["station"].unique().tolist())
    # Reset widget yang bergantung pada data ketika sumber atau parser tanggal berubah.
    if st.session_state.get("data_signature") != signature:
        for key in ["date_range", "stations", "trend_stations", "climate_x", "climate_y"]:
            st.session_state.pop(key, None)
        st.session_state["data_signature"] = signature

    st.sidebar.divider()
    st.sidebar.subheader("Jelajahi analisis")
    menu = st.sidebar.radio("Menu analisis", MENUS, key="menu", label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.subheader("Filter data")
    selection = st.sidebar.date_input("Rentang tanggal", value=(minimum, maximum), min_value=minimum, max_value=maximum, format="DD/MM/YYYY", key="date_range")
    start, end, date_note = resolve_date_range(selection, minimum, maximum)
    if date_note:
        st.sidebar.info(date_note)
    selected = st.sidebar.multiselect("Pilih stasiun", stations, default=stations, key="stations", help="Kosongkan pilihan untuk menampilkan nol baris.")
    with st.sidebar.expander("Pengaturan risiko"):
        threshold = float(st.number_input("Ambang tinggi PM2.5 (µg/m³)", min_value=1.0, value=100.0, step=5.0, key="risk_threshold"))
        st.caption("Ambang operasional untuk RFM, terpisah dari breakpoint kategori.")

    df = filter_data(raw_df, start, end, selected)
    st.sidebar.info(f"Data tersaring: {len(df):,} baris\n\n{len(df) / len(raw_df):.1%} dari {len(raw_df):,} baris siap analisis")
    st.sidebar.caption("Sumber: " + source)
    show_hero(menu, start, end, df, source, is_demo)
    if is_demo:
        st.info("Mode demo · Angka pada dasbor ini berasal dari simulasi sintetis, bukan pengukuran kualitas udara nyata. Unggah data Anda untuk analisis aktual.")
    if df.empty:
        st.warning("Tidak ada data pada kombinasi filter ini. Pilih setidaknya satu stasiun atau perluas rentang tanggal.")
        st.stop()
    show_metrics(df)
    show_quality(df, report)
    if not df["PM2.5"].notna().any():
        st.warning("Baris terfilter tersedia, tetapi seluruh nilai PM2.5 kosong atau tidak valid. Sesuaikan filter untuk melanjutkan analisis.")
        st.stop()

    st.subheader("Insight dari pilihan Anda")
    items = business_insights(df, report["hourly_available"])
    containers = st.columns(len(items))
    for container, (title, text) in zip(containers, items):
        with container:
            insight(title, text)
    st.caption("Insight merangkum observasi pada filter aktif. Rentang pendek atau cakupan data tidak merata membatasi generalisasi.")
    st.divider()

    if menu == "Overview":
        render_overview(df)
    elif menu == "Tren PM2.5":
        render_trend(df, threshold)
    elif menu == "Hubungan Iklim & Polusi":
        render_climate(df)
    elif menu == "Analisis RFM (Risiko)":
        render_rfm(df, threshold)
    elif menu == "Perbandingan Stasiun":
        render_stations(df, report["hourly_available"])
    else:
        render_business(df, report["hourly_available"])

    st.divider()
    with st.expander("Pratinjau & unduh data terfilter"):
        st.caption("Pratinjau maksimal 200 baris. Unduhan memuat seluruh baris terfilter yang sudah divalidasi.")
        display_table(df.head(200))
        st.download_button("Unduh CSV terfilter", data=df.to_csv(index=False).encode("utf-8-sig"), file_name=f"airindexx_{start:%Y%m%d}_{end:%Y%m%d}.csv", mime="text/csv")
    st.markdown('<div class="footer">AirIndexx · Analitik kualitas udara berbasis observasi · Python + Streamlit</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
