# ================================
# Ford Foundation Data Visualization
# ================================

import os
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MPLCONFIGDIR = SCRIPT_DIR / ".matplotlib"
MPLCONFIGDIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from country_metadata import normalize_ford_recipient_name


DATA_FILE = SCRIPT_DIR / "ford-foundation.csv"
OUTPUT_DIR = SCRIPT_DIR
saved_files = []


def build_temp_path(target_path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        dir=target_path.parent,
        prefix=f".{target_path.stem}-",
        suffix=target_path.suffix,
    )
    os.close(fd)
    return Path(temp_name)


def save_current_figure(filename):
    target_path = OUTPUT_DIR / filename
    temp_path = build_temp_path(target_path)
    try:
        # Save via a temporary file to avoid leaving truncated images behind in synced folders.
        plt.tight_layout()
        plt.savefig(temp_path, bbox_inches="tight", dpi=300)
        temp_path.replace(target_path)
        saved_files.append(target_path.name)
    finally:
        temp_path.unlink(missing_ok=True)
        plt.close()

# ================================
# 1. Load the data
# ================================
file_path = DATA_FILE
try:
    df = pd.read_csv(file_path)
except (OSError, TimeoutError) as exc:
    raise RuntimeError(
        f"Could not read the Ford Foundation data file at {file_path}."
    ) from exc

print("Columns:", df.columns)

# ================================
# 2. Data cleaning (automatically adapts to different CSV formats)
# ================================

# Try to identify column names automatically while preferring real data columns
# over helper fields such as *_id.
def normalize_column_name(value):
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def find_column(possible_names):
    normalized_targets = [normalize_column_name(name) for name in possible_names]
    exact_matches = []
    prefix_matches = []
    substring_matches = []

    for col in df.columns:
        normalized_col = normalize_column_name(col)
        if normalized_col.endswith("id"):
            continue

        for target in normalized_targets:
            if normalized_col == target:
                exact_matches.append(col)
                break
            if normalized_col.startswith(target):
                prefix_matches.append(col)
                break
            if target in normalized_col:
                substring_matches.append(col)
                break

    for candidates in (exact_matches, prefix_matches, substring_matches):
        if candidates:
            return candidates[0]
    return None

year_col = find_column(["year_name", "year", "date"])
amount_col = find_column(["usd_commitment", "usd_disbursement", "grant_amount", "amount", "value", "fund"])
country_col = find_column(["recipient_name", "country", "nation"])
sector_col = find_column(["lvl_0_sector_name", "sector", "category", "theme"])
region_col = find_column(["region", "area"])

print("Detected columns:")
print(year_col, amount_col, country_col, sector_col, region_col)

if not year_col or not amount_col:
    raise ValueError("Could not identify the required year or amount columns from the CSV file.")

# Convert the year column.
# Use numeric years directly when available to avoid interpreting values like 2018 as Unix timestamps.
if pd.api.types.is_numeric_dtype(df[year_col]):
    df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
else:
    parsed_year = pd.to_datetime(df[year_col], errors='coerce')
    numeric_year = pd.to_numeric(df[year_col], errors='coerce')
    if numeric_year.notna().sum() > parsed_year.notna().sum():
        df[year_col] = numeric_year
    else:
        df[year_col] = parsed_year.dt.year

# Drop missing values
df = df.dropna(subset=[year_col, amount_col])

# Convert the amount column to numeric values
df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
df = df.dropna(subset=[amount_col])

if country_col:
    df[country_col] = df[country_col].map(normalize_ford_recipient_name)

# ================================
# 3. Time trend chart (most important)
# ================================
trend = df.groupby(year_col)[amount_col].sum()

plt.figure()
trend.plot()
plt.title("Ford Foundation Funding Over Time")
plt.xlabel("Year")
plt.ylabel("Total Funding")
plt.grid()
save_current_figure("funding_over_time.png")

# ================================
# 4. Regional comparison chart
# ================================
if region_col:
    region_sum = df.groupby(region_col)[amount_col].sum().sort_values(ascending=False)

    plt.figure()
    region_sum.plot(kind='bar')
    plt.title("Funding by Region")
    plt.xlabel("Region")
    plt.ylabel("Total Funding")
    plt.xticks(rotation=45)
    save_current_figure("funding_by_region.png")

# ================================
# 5. Sector distribution chart (e.g. Law / Education)
# ================================
if sector_col:
    sector_sum = df.groupby(sector_col)[amount_col].sum().sort_values(ascending=False)
    top_sectors = sector_sum.head(10)
    top_sector_total = top_sectors.sum()
    top_sector_percentages = (
        top_sectors / top_sector_total * 100 if top_sector_total else top_sectors * 0
    )

    plt.figure(figsize=(12, 6))
    ax = top_sectors.plot(kind='bar', color=plt.cm.tab10.colors[:len(top_sectors)])
    plt.title("Top 10 Sectors by Funding")
    plt.xlabel("Sector")
    plt.ylabel("Total Funding")
    plt.xticks(rotation=45, ha="right")

    ax.set_ylim(0, top_sectors.max() * 1.15)
    for bar, percentage in zip(ax.patches, top_sector_percentages):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{percentage:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    save_current_figure("top_10_sectors_distribution.png")

# ================================
# 6. Period comparison (key requirement for the assignment)
# ================================

def assign_period(year):
    if year >= 1945 and year <= 1989:
        return "1945-1989"
    elif year >= 1990 and year <= 2015:
        return "1990-2015"
    else:
        return "Other"

df["period"] = df[year_col].apply(assign_period)

period_sum = df.groupby("period")[amount_col].sum()
period_sum = period_sum.reindex(["1945-1989", "1990-2015", "Other"]).dropna()

plt.figure()
period_sum.plot(kind='bar')
plt.title("Funding Comparison by Period")
plt.xlabel("Period")
plt.ylabel("Total Funding")
plt.xticks(rotation=0)
save_current_figure("funding_comparison_by_period.png")

# ================================
# 7. Country comparison (top countries only)
# ================================
if country_col:
    country_mask = ~df[country_col].astype(str).str.contains(
        "regional|unspecified",
        case=False,
        regex=True,
    )
    country_sum = (
        df.loc[country_mask]
        .groupby(country_col)[amount_col]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    if not country_sum.empty:
        plt.figure()
        country_sum.plot(kind='bar')
        plt.title("Top 10 Countries by Funding")
        plt.xlabel("Country")
        plt.ylabel("Total Funding")
        plt.xticks(rotation=45)
        save_current_figure("top_10_countries_by_funding.png")

print("All visualizations generated successfully.")
print("Saved files:", ", ".join(saved_files))
