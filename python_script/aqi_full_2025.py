import re
import pandas as pd
from pathlib import Path

FOLDER = r"C:\Users\Keshav\Documents\py_project_delhi_pollution\excel_files\aqi_2025_excels"
OUTPUT = r"C:\Users\Keshav\Documents\py_project_delhi_pollution\csv_files\delhi_aqi_2025.csv"
CITY = "Delhi"           # city word between station name and authority

pattern = re.compile(r"Site_(\d+)_(.+)_([A-Za-z]+)_(\d{4})_Hourly")

def split_name(text):
    """'CRRI_Mathura_Road_Delhi_IITM' -> ('CRRI Mathura Road', 'Delhi', 'IITM'); city/authority empty if not present"""
    parts = text.split("_")
    city, authority = "", ""
    if CITY in parts:
        i = len(parts) - 1 - parts[::-1].index(CITY)
        city = CITY
        authority = " ".join(parts[i + 1:])
        parts = parts[:i]
    return " ".join(parts), city, authority

def clean_hour(col):
    """'00:00', '00:00:00', '0:00' or a real time value -> '00:00'. Other headers (like 'Date') stay as they are."""
    m = re.search(r"(\d{1,2}):(\d{2})", str(col))
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else col

files = sorted(Path(FOLDER).glob("*.xlsx"))
print("Folder:", FOLDER)
print("Excel files found:", len(files))
if not files:
    raise SystemExit("No .xlsx files found. Check the FOLDER path.")

frames = []
fixed_files = 0                  # files whose hour headers were not in the "00:00" style
odd_files = []                   # files that do not end up with exactly 24 hour columns
for f in files:
    m = pattern.search(f.stem)
    if m is None:
        print("Skipped, name does not match:", f.name)
        continue
    station_id, name_part, month, year = m.groups()
    station_name, city, authority = split_name(name_part)

    df = pd.read_excel(f)
    old_cols = list(df.columns)
    df.columns = [clean_hour(c) for c in old_cols]            # make every hour header "HH:MM"
    if [str(c) for c in old_cols] != [str(c) for c in df.columns]:
        fixed_files += 1
    n_hours = sum(1 for c in df.columns if c != "Date")
    if n_hours != 24 or df.columns.duplicated().any():
        odd_files.append(f.name)

    df["date"] = pd.to_datetime(year + "-" + month + "-" + df["Date"].astype(str),
                                format="%Y-%B-%d", errors="coerce")
    df["station_id"] = int(station_id)
    df["station_name"] = station_name
    df["city"] = city
    df["authority"] = authority
    frames.append(df.drop(columns="Date"))

if not frames:
    raise SystemExit("Files were found but none matched the name pattern. Check the file names.")

print("Files whose hour headers were converted to HH:MM:", fixed_files)
if odd_files:
    print("WARNING: these files do not have exactly 24 hour columns:")
    for name in odd_files:
        print("  ", name)

all_data = pd.concat(frames, ignore_index=True).dropna(subset=["date"])
all_data["date"] = all_data["date"].dt.strftime("%Y-%m-%d")

first = ["station_id", "station_name", "city", "authority", "date"]
hour_cols = [f"{h:02d}:00" for h in range(24)]
other = [c for c in all_data.columns if c not in first + hour_cols]     # anything unexpected is kept, not dropped
all_data = all_data[first + hour_cols + other]
all_data = all_data.sort_values(["station_id", "date"])
all_data = all_data.drop_duplicates(subset=["station_id", "date"])
Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
all_data.to_csv(OUTPUT, index=False)

print()
print("Files read:", len(frames))
print("Stations:", all_data["station_id"].nunique())
print("Table size:", all_data.shape)
print("Columns after the 5 label columns:", len(all_data.columns) - 5, "(should be 24)")
print("Saved to:", OUTPUT)
print()
print("Days per station:")
check = all_data.groupby(["station_id", "station_name", "authority"]).agg(
    days=("date", "size"), first=("date", "min"), last=("date", "max"))
print(check.to_string())