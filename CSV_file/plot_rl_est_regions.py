import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
MPLCONFIGDIR = SCRIPT_DIR / ".matplotlib"
MPLCONFIGDIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from country_metadata import COUNTRY_COLORS_BY_CODE


WB_RULE_OF_LAW_FILE = SCRIPT_DIR / "WB_index" / "API_RL.EST_DS2_en_csv_v2_5814.csv"
WB_COUNTRY_METADATA_FILE = SCRIPT_DIR / "WB_index" / "Metadata_Country_API_RL.EST_DS2_en_csv_v2_5814.csv"
OUTPUT_PNG = PROJECT_DIR / "rl_est_us_china_japan_africa_latam_euro_area_1990_2025.png"
OUTPUT_CSV = PROJECT_DIR / "rl_est_us_china_japan_africa_latam_euro_area_1990_2025.csv"

START_YEAR = 1990
END_YEAR = 2025

SINGLE_SERIES = {
    "United States": "USA",
    "China": "CHN",
    "Japan": "JPN",
}

EURO_AREA_MEMBERS_2015 = {
    "AUT",
    "BEL",
    "CYP",
    "DEU",
    "ESP",
    "EST",
    "FIN",
    "FRA",
    "GRC",
    "IRL",
    "ITA",
    "LTU",
    "LUX",
    "LVA",
    "MLT",
    "NLD",
    "PRT",
    "SVK",
    "SVN",
}

SERIES_STYLES = {
    "United States": {"color": COUNTRY_COLORS_BY_CODE["USA"], "linewidth": 2},
    "China": {"color": COUNTRY_COLORS_BY_CODE["CHN"], "linewidth": 2},
    "Japan": {"color": "#8c564b", "linewidth": 2},
    "Africa": {"color": "#2ca02c", "linewidth": 2},
    "Latin America": {"color": "#ff7f0e", "linewidth": 2},
    "Euro area": {"color": "#9467bd", "linewidth": 2},
}


def load_rule_of_law_long():
    raw_df = pd.read_csv(WB_RULE_OF_LAW_FILE, skiprows=4)
    year_columns = [str(year) for year in range(START_YEAR, END_YEAR + 1) if str(year) in raw_df.columns]
    rule_of_law_df = raw_df[raw_df["Indicator Code"] == "RL.EST"].copy()
    long_df = rule_of_law_df.melt(
        id_vars=["Country Name", "Country Code", "Indicator Code"],
        value_vars=year_columns,
        var_name="year",
        value_name="rl_est",
    )
    long_df["year"] = pd.to_numeric(long_df["year"], errors="coerce")
    long_df["rl_est"] = pd.to_numeric(long_df["rl_est"], errors="coerce")
    long_df = long_df.dropna(subset=["year"]).copy()
    long_df["year"] = long_df["year"].astype(int)
    return long_df


def load_country_metadata():
    metadata = pd.read_csv(WB_COUNTRY_METADATA_FILE)
    metadata = metadata.rename(
        columns={
            "Country Code": "country_code",
            "Region": "region",
            "IncomeGroup": "income_group",
            "SpecialNotes": "special_notes",
            "TableName": "country_name",
        }
    )
    metadata["country_code"] = metadata["country_code"].astype(str).str.strip()
    metadata["region"] = metadata["region"].fillna("").astype(str).str.strip()
    return metadata


def build_series(long_df, metadata_df):
    records = []

    for label, code in SINGLE_SERIES.items():
        temp = long_df[long_df["Country Code"] == code][["year", "rl_est"]].copy()
        temp["series"] = label
        records.append(temp)

    region_map = metadata_df.set_index("country_code")["region"].to_dict()
    country_rows = long_df[long_df["Country Code"].isin(region_map.keys())].copy()
    country_rows["region"] = country_rows["Country Code"].map(region_map)

    africa = (
        country_rows[country_rows["region"] == "Sub-Saharan Africa"]
        .groupby("year", as_index=False)["rl_est"]
        .mean()
    )
    africa["series"] = "Africa"
    records.append(africa)

    latam = (
        country_rows[country_rows["region"] == "Latin America & Caribbean"]
        .groupby("year", as_index=False)["rl_est"]
        .mean()
    )
    latam["series"] = "Latin America"
    records.append(latam)

    euro_area = (
        country_rows[country_rows["Country Code"].isin(EURO_AREA_MEMBERS_2015)]
        .groupby("year", as_index=False)["rl_est"]
        .mean()
    )
    euro_area["series"] = "Euro area"
    records.append(euro_area)

    combined = pd.concat(records, ignore_index=True)
    combined = combined[combined["year"].between(START_YEAR, END_YEAR, inclusive="both")].copy()
    return combined.sort_values(["series", "year"]).reset_index(drop=True)


def plot_series(series_df):
    plt.figure(figsize=(12, 7))

    order = [
        "United States",
        "China",
        "Japan",
        "Africa",
        "Latin America",
        "Euro area",
    ]

    for label in order:
        temp = (
            series_df[series_df["series"] == label]
            .dropna(subset=["rl_est"])
            .sort_values("year")
        )
        style = SERIES_STYLES[label]
        plt.plot(
            temp["year"],
            temp["rl_est"],
            marker="o",
            label=label,
            **style,
        )

    plt.title("World Bank Rule of Law Estimate Over Time by Country")
    plt.xlabel("Year")
    plt.ylabel("Rule of Law Estimate (RL.EST)")
    plt.xlim(START_YEAR, END_YEAR + 1)
    plt.xticks(range(START_YEAR, END_YEAR + 1, 5))
    plt.grid(True)
    plt.legend(title="Country", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")
    plt.close()


def main():
    long_df = load_rule_of_law_long()
    metadata_df = load_country_metadata()
    series_df = build_series(long_df, metadata_df)
    series_df.to_csv(OUTPUT_CSV, index=False)
    plot_series(series_df)

    first_available = (
        series_df.dropna(subset=["rl_est"])
        .groupby("series")["year"]
        .min()
        .sort_index()
    )
    print("Saved:")
    print(f"- {OUTPUT_PNG}")
    print(f"- {OUTPUT_CSV}")
    print("First available year by series:")
    for label, year in first_available.items():
        print(f"- {label}: {year}")


if __name__ == "__main__":
    main()
