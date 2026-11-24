"""Join hourly AQI (wide, one row per station-day) onto the raw hourly data (long).

Key: station_id + date (YYYY-MM-DD) + time (HH:MM). Left join keeps every raw row.
Usage: python join_aqi.py  (edit the three paths below if your files live elsewhere)
"""
import pandas as pd

RAW_PATH = r"C:\Users\Keshav\Documents\py_project_delhi_pollution\csv_files\delhi_raw_2025.csv" 
AQI_PATH = r"C:\Users\Keshav\Documents\py_project_delhi_pollution\csv_files\delhi_aqi_2025.csv"    # the corrected AQI file
OUT_PATH = r"C:\Users\Keshav\Documents\py_project_delhi_pollution\csv_files\delhi_merged_2025.csv"

raw = pd.read_csv(RAW_PATH)
aqi = pd.read_csv(AQI_PATH)

# 1. Drop the empty unnamed columns left over from the old second set of hour columns
aqi = aqi.loc[:, ~aqi.columns.str.startswith("Unnamed")]

# 2. Wide -> long: one row per station per hour
hour_cols = [c for c in aqi.columns if ":" in c]
long = aqi.melt(id_vars=["station_id", "date"], value_vars=hour_cols,
                var_name="time", value_name="aqi")

# 3. Standardise key formats to match the raw file
#    date: accept YYYY-MM-DD (your corrected file) or M/D/YYYY (older files) -> YYYY-MM-DD
#    time: 0:00 -> 00:00
d_iso = pd.to_datetime(long["date"], format="%Y-%m-%d", errors="coerce")
d_us = pd.to_datetime(long["date"], format="%m/%d/%Y", errors="coerce")
long["date"] = d_iso.fillna(d_us).dt.strftime("%Y-%m-%d")
assert long["date"].notna().all(), "Some dates in the AQI file could not be read"
long["time"] = long["time"].str.strip().str.zfill(5)

# 4. Safety checks on the key before joining
key = ["station_id", "date", "time"]
assert not long.duplicated(key).any(), "AQI key not unique"
assert not raw.duplicated(key).any(), "Raw key not unique"
assert set(long["time"]) == set(raw["time"]), "Hour labels differ"

# 5. Left join: keep every raw row, add AQI
out = raw.merge(long, on=key, how="left", validate="one_to_one")
assert len(out) == len(raw), "Row count changed"

out.to_csv(OUT_PATH, index=False)

print(f"Rows: raw={len(raw):,}  output={len(out):,}")
print(f"Rows with AQI: {out['aqi'].notna().sum():,}  without: {out['aqi'].isna().sum():,}")
print(f"AQI values in the AQI file: {long['aqi'].notna().sum():,}  carried into the output: {out['aqi'].notna().sum():,}")