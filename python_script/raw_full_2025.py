import re
import pandas as pd
from pathlib import Path

FOLDER = r"C:\Users\Keshav\Documents\py_project_delhi_pollution\excel_files\raw_2025_excels"
OUTPUT = r"C:\Users\Keshav\Documents\py_project_delhi_pollution\csv_files\delhi_raw_2025.csv"
CITY = "delhi"           # city word between station name and authority (lowercase, as in file names)

# columns to keep: original name -> short name
KEEP = {
    "Timestamp": "datetime",
    "PM2.5 (µg/m³)": "pm25",
    "PM10 (µg/m³)": "pm10",
    "NO2 (µg/m³)": "no2",
    "Ozone (µg/m³)": "ozone",
    "AT (°C)": "temp",
    "RH (%)": "rh",
    "WS (m/s)": "wind_speed",
    "WD (deg)": "wind_dir",
    "SR (W/mt2)": "solar_rad",
}

pattern = re.compile(r"Raw_Data_(\d{4})_site_(\d+)_(.+)_1Hr", re.IGNORECASE)

def split_name(text):
    """'anand_vihar_delhi_dpcc' -> ('Anand Vihar', 'Delhi', 'DPCC'); city/authority empty if not present"""
    parts = text.split("_")
    city, authority = "", ""
    if CITY in parts:
        i = len(parts) - 1 - parts[::-1].index(CITY)
        city = CITY.title()
        authority = " ".join(parts[i + 1:]).upper()
        parts = parts[:i]
    return " ".join(parts).title(), city, authority

files = sorted(Path(FOLDER).glob("*.csv"))
print("Folder:", FOLDER)
print("CSV files found:", len(files))
if not files:
    raise SystemExit("No CSV files found. Check the FOLDER path and that the files end with .csv")

frames = []
for f in files:
    m = pattern.search(f.stem)
    if m is None:
        print("Skipped, name does not match:", f.name)
        continue
    year, station_id, name_part = m.groups()
    station_name, city, authority = split_name(name_part)

    df = pd.read_csv(f, usecols=lambda c: c in KEEP, parse_dates=["Timestamp"])
    df = df.rename(columns=KEEP).reindex(columns=list(KEEP.values()))   # missing columns become empty

    df["date"] = df["datetime"].dt.strftime("%Y-%m-%d")
    df["time"] = df["datetime"].dt.strftime("%H:%M")
    df["station_id"] = int(station_id)
    df["station_name"] = station_name
    df["city"] = city
    df["authority"] = authority
    frames.append(df)

if not frames:
    raise SystemExit("Files were found but none matched the name pattern. Check the file names.")

all_data = pd.concat(frames, ignore_index=True)
all_data = all_data.sort_values(["station_id", "datetime"])
all_data = all_data.drop_duplicates(subset=["station_id", "datetime"])

first = ["station_id", "station_name", "city", "authority", "datetime", "date", "time"]
all_data = all_data[first + [c for c in all_data.columns if c not in first]]
all_data.to_csv(OUTPUT, index=False)

print()
print("Files read:", len(frames))
print("Stations:", all_data["station_id"].nunique())
print("Table size:", all_data.shape)
print("Saved to:", OUTPUT)
print()
print("Rows and weather coverage per station:")
check = all_data.groupby(["station_id", "station_name"]).agg(
    rows=("datetime", "size"),
    first=("datetime", "min"),
    last=("datetime", "max"),
    temp_filled=("temp", lambda s: round(s.notna().mean(), 2)),
)
print(check.to_string())