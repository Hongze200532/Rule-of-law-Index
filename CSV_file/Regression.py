import csv
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
RESEARCH_ROOT = PROJECT_DIR.parent
MPLCONFIGDIR = SCRIPT_DIR / ".matplotlib"
MPLCONFIGDIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from scipy import stats

from country_metadata import (
    COUNTRY_COLORS_BY_CODE,
    COUNTRY_METADATA,
    COUNTRY_NAMES_BY_CODE,
    normalize_ford_recipient_name,
)

# =========================================================
# 1. USER SETTINGS
# =========================================================

# Sample countries for your report
countries = COUNTRY_NAMES_BY_CODE

start_year = 1945
end_year = 2025

OUTPUT_DIR = PROJECT_DIR
PROJECT_ROOT = RESEARCH_ROOT
CACHE_DIR = OUTPUT_DIR / "world_bank_cache"
CACHE_DIR.mkdir(exist_ok=True)
FORD_RAW_FILE = OUTPUT_DIR / "ford-foundation.csv"
WB_INDEX_DIR = SCRIPT_DIR / "WB_index"
WB_RULE_OF_LAW_FILE = WB_INDEX_DIR / "API_RL.EST_DS2_en_csv_v2_5814.csv"
WB_RULE_OF_LAW_INDICATOR_CODE = "RL.EST"
WB_RULE_OF_LAW_INDICATOR_NAME = "Rule of Law: Estimate"
WB_RULE_OF_LAW_AVAILABLE_START_YEAR = 1996
RULE_OF_LAW_PERIOD_BREAK_YEAR = 2005
RULE_OF_LAW_EARLY_PERIOD_LABEL = (
    f"{WB_RULE_OF_LAW_AVAILABLE_START_YEAR}-{RULE_OF_LAW_PERIOD_BREAK_YEAR}"
)
RULE_OF_LAW_LATE_PERIOD_LABEL = f"{RULE_OF_LAW_PERIOD_BREAK_YEAR + 1}-{end_year}"
RULE_OF_LAW_PERIOD_LABELS = [
    RULE_OF_LAW_EARLY_PERIOD_LABEL,
    RULE_OF_LAW_LATE_PERIOD_LABEL,
]
GDP_GROWTH_CLEAN_FILE = PROJECT_ROOT / "Statics_Analysis/CleanData/Clean_DATA.csv"
GDP_PER_CAPITA_CLEAN_FILE = PROJECT_ROOT / "Statics_Analysis/CleanData/Clean_GDP_Per_Capita.csv"
HISTORICAL_GDP_GROWTH_FILE = PROJECT_ROOT / "Statics_Analysis/CleanData/Clean_GDP_Growth_1945_1989.csv"
ALIGNMENT_REPORT_FILE = OUTPUT_DIR / "country_name_alignment_check.csv"
TREND_GDP_SOURCE_START_YEAR = 1945
TREND_GDP_SOURCE_END_YEAR = 2025
MODERN_GDP_SOURCE_START_YEAR = 1961
HISTORICAL_GDP_EXTENSION_END_YEAR = 1960

HISTORICAL_GDP_EXTENSION_COLUMN_BY_CODE = {
    "USA": "USA",
    "CHN": "China",
    "ARG": "Latin_America",
    "BRA": "Latin_America",
    "MEX": "Latin_America",
    "KEN": "Africa",
    "NGA": "Africa",
    "ZAF": "Africa",
}

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
        plt.savefig(temp_path, dpi=300, bbox_inches="tight")
        temp_path.replace(target_path)
        saved_files.append(target_path.name)
    finally:
        temp_path.unlink(missing_ok=True)
        plt.close()


def record_saved_file(filename):
    saved_files.append(Path(filename).name)


def save_dataframe_csv(dataframe, target_path, **kwargs):
    temp_path = build_temp_path(target_path)
    try:
        dataframe.to_csv(temp_path, **kwargs)
        temp_path.replace(target_path)
        record_saved_file(target_path.name)
    finally:
        temp_path.unlink(missing_ok=True)


def write_json_atomic(payload, target_path):
    temp_path = build_temp_path(target_path)
    try:
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        temp_path.replace(target_path)
    finally:
        temp_path.unlink(missing_ok=True)


def load_clean_chart_columns(csv_path):
    if not csv_path.exists():
        return set()

    header = pd.read_csv(csv_path, nrows=0)
    return {column for column in header.columns if column != "Year"}


def collect_raw_ford_name_usage(raw_ford_file):
    if not raw_ford_file.exists():
        return {}, {}

    try:
        raw_ford = pd.read_csv(raw_ford_file, usecols=["recipient_name"])
    except (OSError, TimeoutError, ValueError) as exc:
        print(
            f"Could not read {raw_ford_file}; skipping Ford raw-name alignment audit: {exc}"
        )
        return {}, {}

    raw_ford["canonical_name"] = raw_ford["recipient_name"].map(normalize_ford_recipient_name)

    canonical_counts = raw_ford["canonical_name"].value_counts(dropna=True).to_dict()

    alias_rows = raw_ford.dropna(subset=["recipient_name"]).copy()
    alias_rows["recipient_name"] = alias_rows["recipient_name"].astype(str).str.strip()
    alias_map = (
        alias_rows.groupby("canonical_name")["recipient_name"]
        .agg(lambda values: sorted(set(values)))
        .to_dict()
    )

    return canonical_counts, alias_map


def export_country_alignment_check(index_df, world_bank_names):
    gdp_growth_columns = load_clean_chart_columns(GDP_GROWTH_CLEAN_FILE)
    gdp_per_capita_columns = load_clean_chart_columns(GDP_PER_CAPITA_CLEAN_FILE)
    raw_counts, raw_aliases = collect_raw_ford_name_usage(FORD_RAW_FILE)

    rows = []
    for code, metadata in COUNTRY_METADATA.items():
        canonical_name = metadata["canonical_name"]
        gdp_chart_label = metadata["gdp_chart_label"]
        rule_of_law_years = (
            index_df.loc[index_df["country_code"] == code, "year"]
            .sort_values()
            .astype(int)
            .tolist()
        )
        matched_aliases = raw_aliases.get(canonical_name, [])
        world_bank_name = world_bank_names.get(code, "")
        notes = []

        if world_bank_name and world_bank_name != canonical_name:
            notes.append(
                f"World Bank returned '{world_bank_name}', normalized to '{canonical_name}'"
            )

        if rule_of_law_years:
            notes.append(
                f"Official World Bank WGI series {WB_RULE_OF_LAW_INDICATOR_CODE} available for "
                f"{len(rule_of_law_years)} sampled years"
            )
        else:
            notes.append(
                f"No {WB_RULE_OF_LAW_INDICATOR_CODE} observations found for the selected period"
            )

        raw_ford_record_count = int(raw_counts.get(canonical_name, 0))
        if raw_ford_record_count == 0:
            notes.append("No direct raw Ford recipient_name match in the current grants CSV")
        elif any(alias != canonical_name for alias in matched_aliases):
            notes.append("Raw Ford recipient_name normalized to canonical country name")

        if gdp_chart_label:
            if (
                gdp_chart_label in gdp_growth_columns
                and gdp_chart_label in gdp_per_capita_columns
            ):
                notes.append(f"Matches GDP and CSV_Processing label '{gdp_chart_label}'")
            else:
                notes.append(
                    f"GDP/CSV_Processing label '{gdp_chart_label}' missing in cleaned GDP files"
                )
        else:
            notes.append(
                "Not present in aggregate GDP clean-data charts; regression uses World Bank API directly"
            )

        rows.append(
            {
                "country_code": code,
                "canonical_name": canonical_name,
                "world_bank_name": world_bank_name,
                "rule_of_law_indicator_code": WB_RULE_OF_LAW_INDICATOR_CODE,
                "ford_raw_aliases_found": ", ".join(matched_aliases),
                "raw_ford_record_count": raw_ford_record_count,
                "rule_of_law_years": ", ".join(str(year) for year in rule_of_law_years),
                "gdp_chart_label": gdp_chart_label,
                "in_gdp_growth_clean_data": gdp_chart_label in gdp_growth_columns if gdp_chart_label else False,
                "in_gdp_per_capita_clean_data": (
                    gdp_chart_label in gdp_per_capita_columns if gdp_chart_label else False
                ),
                "notes": " | ".join(notes),
            }
        )

    alignment_report = pd.DataFrame(rows)
    save_dataframe_csv(alignment_report, ALIGNMENT_REPORT_FILE, index=False)

    print("\n================ COUNTRY ALIGNMENT CHECK ================\n")
    print(
        alignment_report[
            [
                "country_code",
                "canonical_name",
                "world_bank_name",
                "ford_raw_aliases_found",
                "raw_ford_record_count",
                "gdp_chart_label",
                "in_gdp_growth_clean_data",
                "in_gdp_per_capita_clean_data",
            ]
        ].to_string(index=False)
    )


def find_statics_gdp_growth_source():
    candidates = sorted(
        PROJECT_ROOT.glob(
            "Statics_Analysis/API_NY.GDP.MKTP.KD.ZG_DS2_en_csv_v2_107*/"
            "API_NY.GDP.MKTP.KD.ZG_DS2_en_csv_v2_107.csv"
        )
    )
    if not candidates:
        raise FileNotFoundError(
            "Could not find the Statics_Analysis GDP growth source CSV."
        )
    return candidates[0]


def load_statics_annual_gdp_growth(country_name_by_code, start_year, end_year):
    source_file = find_statics_gdp_growth_source()
    years = [str(year) for year in range(start_year, end_year + 1)]
    target_name_to_code = {
        country_name: code for code, country_name in country_name_by_code.items()
    }
    rows = []

    with source_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = None

        for row in reader:
            if row and row[0] == "Country Name":
                header = row
                break

        if header is None:
            raise ValueError(
                "Could not locate the data header row in the Statics_Analysis GDP source CSV."
            )

        row_reader = csv.DictReader(handle, fieldnames=header)
        for row in row_reader:
            country_name = (row.get("Country Name") or "").strip()
            country_code = target_name_to_code.get(country_name)
            if not country_code:
                continue

            for year in years:
                value = (row.get(year) or "").strip()
                if value == "":
                    continue

                rows.append(
                    {
                        "country_code": country_code,
                        "country": country_name,
                        "year": int(year),
                        "gdp_growth": float(value),
                    }
                )

    return pd.DataFrame(rows)


def load_statics_historical_gdp_extension(start_year, end_year):
    if not HISTORICAL_GDP_GROWTH_FILE.exists():
        raise FileNotFoundError(
            f"Could not find the historical GDP growth file: {HISTORICAL_GDP_GROWTH_FILE}"
        )

    historical_df = pd.read_csv(HISTORICAL_GDP_GROWTH_FILE)
    historical_df["Year"] = pd.to_numeric(historical_df["Year"], errors="coerce")
    historical_df = historical_df[
        historical_df["Year"].between(start_year, end_year, inclusive="both")
    ].copy()

    rows = []
    for code, column_name in HISTORICAL_GDP_EXTENSION_COLUMN_BY_CODE.items():
        if column_name not in historical_df.columns:
            continue

        temp = historical_df[["Year", column_name]].copy()
        temp[column_name] = pd.to_numeric(temp[column_name], errors="coerce")
        temp = temp.dropna(subset=[column_name])

        for _, row in temp.iterrows():
            rows.append(
                {
                    "country_code": code,
                    "country": countries.get(code, code),
                    "year": int(row["Year"]),
                    "gdp_growth": float(row[column_name]),
                }
            )

    return pd.DataFrame(rows)


# =========================================================
# 2. LOAD GDP DATA FROM WORLD BANK API OR LOCAL CACHE
# =========================================================
# Indicator:
# NY.GDP.MKTP.KD.ZG = GDP growth (annual %)
# NY.GDP.MKTP.KD    = GDP constant 2015 US$
# SP.DYN.LE00.IN    = Life expectancy at birth, total (years)


def indicator_cache_path(indicator):
    return CACHE_DIR / f"{indicator.replace('.', '_')}.json"


def parse_world_bank_payload(payload, country_codes, start, end):
    rows = []
    valid_country_codes = set(country_codes)

    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return pd.DataFrame(columns=["country_code", "country", "year", "value"])

    for entry in payload[1]:
        year = entry.get("date")
        if year is None:
            continue

        year = int(year)
        if not start <= year <= end:
            continue

        country_code = entry.get("countryiso3code")
        if country_code not in valid_country_codes:
            continue

        rows.append(
            {
                "country_code": country_code,
                "country": entry.get("country", {}).get("value"),
                "year": year,
                "value": entry.get("value"),
            }
        )

    return pd.DataFrame(rows)


def fetch_world_bank_indicator(indicator, country_codes, start, end):
    cache_file = indicator_cache_path(indicator)

    if cache_file.exists():
        print(f"Loading {indicator} from cache: {cache_file}")
        try:
            with cache_file.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return parse_world_bank_payload(payload, country_codes, start, end)
        except (OSError, TimeoutError, json.JSONDecodeError) as exc:
            print(
                f"Could not read cache {cache_file}; falling back to the live World Bank API: {exc}"
            )

    url = (
        f"https://api.worldbank.org/v2/country/{';'.join(country_codes)}/indicator/{indicator}"
        f"?format=json&per_page=2000"
    )

    print(f"Downloading {indicator} from World Bank API...")
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not download {indicator} from the World Bank API and no local cache was found at "
            f"{cache_file}. Populate the cache first or rerun in an environment with network access."
        ) from exc

    write_json_atomic(payload, cache_file)

    return parse_world_bank_payload(payload, country_codes, start, end)


def load_world_bank_rule_of_law_estimate(country_codes, start, end):
    if not WB_RULE_OF_LAW_FILE.exists():
        raise FileNotFoundError(
            f"Could not find the downloaded World Bank Rule of Law file: {WB_RULE_OF_LAW_FILE}"
        )

    raw_df = pd.read_csv(WB_RULE_OF_LAW_FILE, skiprows=4)
    indicator_df = raw_df[
        (raw_df["Indicator Code"] == WB_RULE_OF_LAW_INDICATOR_CODE)
        & (raw_df["Country Code"].isin(country_codes))
    ].copy()

    if indicator_df.empty:
        raise ValueError(
            f"No rows matching indicator {WB_RULE_OF_LAW_INDICATOR_CODE} were found in {WB_RULE_OF_LAW_FILE}."
        )

    year_columns = [
        column
        for column in indicator_df.columns
        if column.isdigit() and start <= int(column) <= end
    ]
    if not year_columns:
        raise ValueError(
            f"No year columns between {start} and {end} were found in {WB_RULE_OF_LAW_FILE}."
        )

    long_df = indicator_df.melt(
        id_vars=["Country Name", "Country Code", "Indicator Name", "Indicator Code"],
        value_vars=year_columns,
        var_name="year",
        value_name="rule_of_law_estimate",
    )
    long_df["year"] = pd.to_numeric(long_df["year"], errors="coerce")
    long_df["rule_of_law_estimate"] = pd.to_numeric(
        long_df["rule_of_law_estimate"],
        errors="coerce",
    )
    long_df = long_df.dropna(subset=["year", "rule_of_law_estimate"]).copy()
    long_df["year"] = long_df["year"].astype(int)
    long_df = long_df.rename(
        columns={
            "Country Name": "country",
            "Country Code": "country_code",
            "Indicator Name": "indicator_name",
            "Indicator Code": "indicator_code",
        }
    )

    matched_codes = set(long_df["country_code"].unique())
    missing_codes = sorted(set(country_codes) - matched_codes)
    if missing_codes:
        raise ValueError(
            "The World Bank rule-of-law file is missing selected countries: "
            + ", ".join(missing_codes)
        )

    return (
        long_df[
            [
                "country_code",
                "country",
                "year",
                "indicator_name",
                "indicator_code",
                "rule_of_law_estimate",
            ]
        ]
        .sort_values(["country_code", "year"])
        .reset_index(drop=True)
    )


print("Preparing World Bank indicators...")
gdp_growth = fetch_world_bank_indicator(
    "NY.GDP.MKTP.KD.ZG",
    list(countries.keys()),
    start_year,
    end_year,
).rename(columns={"value": "gdp_growth"})

gdp_level = fetch_world_bank_indicator(
    "NY.GDP.MKTP.KD",
    list(countries.keys()),
    start_year,
    end_year,
).rename(columns={"value": "gdp_constant_2015_usd"})

life_exp = fetch_world_bank_indicator(
    "SP.DYN.LE00.IN",
    list(countries.keys()),
    start_year,
    end_year,
).rename(columns={"value": "life_expectancy"})

rule_of_law_index = load_world_bank_rule_of_law_estimate(
    list(countries.keys()),
    WB_RULE_OF_LAW_AVAILABLE_START_YEAR,
    end_year,
)

world_bank_name_by_code = (
    rule_of_law_index.dropna(subset=["country"])
    .drop_duplicates(subset=["country_code"])
    .set_index("country_code")["country"]
    .to_dict()
)


# =========================================================
# 4. LIGHTWEIGHT OLS IMPLEMENTATION
# =========================================================


@dataclass
class OLSResult:
    model_name: str
    formula_text: str
    nobs: int
    df_resid: int
    r_squared: float
    adj_r_squared: float
    coefficient_table: pd.DataFrame

    def summary(self):
        formatted = self.coefficient_table.copy()
        for column in formatted.columns:
            formatted[column] = formatted[column].map(
                lambda value: "nan" if pd.isna(value) else f"{value:0.4f}"
            )

        lines = [
            f"Model: {self.model_name}",
            f"Formula: {self.formula_text}",
            f"Observations: {self.nobs}",
            f"Residual DoF: {self.df_resid}",
            f"R-squared: {self.r_squared:0.4f}" if not pd.isna(self.r_squared) else "R-squared: nan",
            f"Adj. R-squared: {self.adj_r_squared:0.4f}"
            if not pd.isna(self.adj_r_squared)
            else "Adj. R-squared: nan",
            "Std. errors: HC3 robust",
            "",
            formatted.to_string(),
        ]
        return "\n".join(lines)


def fit_ols(data, outcome, numeric_predictors, categorical_predictors=None, model_name="OLS"):
    categorical_predictors = categorical_predictors or []
    required_columns = [outcome] + numeric_predictors + categorical_predictors
    work = data[required_columns].dropna().copy()

    if work.empty:
        raise ValueError(f"No observations available for {model_name}.")

    x_parts = [pd.DataFrame({"Intercept": np.ones(len(work))}, index=work.index)]

    for column in numeric_predictors:
        x_parts.append(pd.DataFrame({column: pd.to_numeric(work[column], errors="coerce")}, index=work.index))

    for column in categorical_predictors:
        dummies = pd.get_dummies(work[column], prefix=column, drop_first=True, dtype=float)
        x_parts.append(dummies)

    x_df = pd.concat(x_parts, axis=1)
    y = pd.to_numeric(work[outcome], errors="coerce")

    valid_rows = y.notna() & x_df.notna().all(axis=1)
    x_df = x_df.loc[valid_rows]
    y = y.loc[valid_rows]

    nobs = len(y)
    nparams = x_df.shape[1]
    if nobs <= nparams:
        raise ValueError(
            f"Not enough observations for {model_name}: {nobs} rows for {nparams} parameters."
        )

    x = x_df.to_numpy(dtype=float)
    y_values = y.to_numpy(dtype=float)

    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y_values
    fitted = x @ beta
    residuals = y_values - fitted

    leverage = np.sum((x @ xtx_inv) * x, axis=1)
    leverage_gap = np.clip(1.0 - leverage, 1e-8, None)
    scaled_residuals = residuals / leverage_gap
    meat = (x * (scaled_residuals[:, None] ** 2)).T @ x
    robust_cov = xtx_inv @ meat @ xtx_inv

    std_err = np.sqrt(np.maximum(np.diag(robust_cov), 0))
    t_values = np.divide(beta, std_err, out=np.full_like(beta, np.nan), where=std_err > 0)

    df_resid = nobs - nparams
    if df_resid > 0:
        p_values = 2 * stats.t.sf(np.abs(t_values), df=df_resid)
        critical_value = stats.t.ppf(0.975, df=df_resid)
        ci_lower = beta - critical_value * std_err
        ci_upper = beta + critical_value * std_err
    else:
        p_values = np.full_like(beta, np.nan)
        ci_lower = np.full_like(beta, np.nan)
        ci_upper = np.full_like(beta, np.nan)

    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_values - y_values.mean()) ** 2)
    r_squared = np.nan if ss_tot == 0 else 1 - ss_res / ss_tot
    adj_r_squared = (
        np.nan
        if pd.isna(r_squared) or df_resid <= 0
        else 1 - (1 - r_squared) * (nobs - 1) / df_resid
    )

    coefficient_table = pd.DataFrame(
        {
            "coef": beta,
            "std_err": std_err,
            "t": t_values,
            "p_value": p_values,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
        },
        index=x_df.columns,
    )

    formula_terms = numeric_predictors + [f"C({column})" for column in categorical_predictors]
    formula_text = f"{outcome} ~ {' + '.join(formula_terms)}"

    return OLSResult(
        model_name=model_name,
        formula_text=formula_text,
        nobs=nobs,
        df_resid=df_resid,
        r_squared=r_squared,
        adj_r_squared=adj_r_squared,
        coefficient_table=coefficient_table,
    )


# =========================================================
# 5. MERGE DATA
# =========================================================

df = rule_of_law_index.merge(
    gdp_growth[["country_code", "country", "year", "gdp_growth"]],
    on=["country_code", "year"],
    how="left",
    suffixes=("_rule_of_law", "_gdp"),
)

df = df.merge(
    gdp_level[["country_code", "year", "gdp_constant_2015_usd"]],
    on=["country_code", "year"],
    how="left",
)

df = df.merge(
    life_exp[["country_code", "year", "life_expectancy"]],
    on=["country_code", "year"],
    how="left",
)

# Add a single canonical country column after merge collisions.
df["country"] = df["country_code"].map(countries)
for source_column in ["country_rule_of_law", "country_gdp", "country"]:
    if source_column in df.columns:
        df["country"] = df["country"].fillna(df[source_column])

df = df.drop(
    columns=[
        column
        for column in ["country_rule_of_law", "country_gdp"]
        if column in df.columns
    ]
)

# Period split
def assign_rule_of_law_period(year):
    if WB_RULE_OF_LAW_AVAILABLE_START_YEAR <= year <= RULE_OF_LAW_PERIOD_BREAK_YEAR:
        return RULE_OF_LAW_EARLY_PERIOD_LABEL
    if RULE_OF_LAW_PERIOD_BREAK_YEAR < year <= end_year:
        return RULE_OF_LAW_LATE_PERIOD_LABEL
    return "Outside RL.EST coverage"


df["period"] = df["year"].apply(assign_rule_of_law_period)

# Log GDP level
df["log_gdp"] = np.where(df["gdp_constant_2015_usd"] > 0, np.log(df["gdp_constant_2015_usd"]), np.nan)

print("\nMerged data preview:")
print(df.head())

export_country_alignment_check(rule_of_law_index, world_bank_name_by_code)


# =========================================================
# 6. BASIC CLEANING
# =========================================================

analysis_df = df.dropna(subset=["rule_of_law_estimate", "gdp_growth"]).copy()
trend_gdp_direct_df = (
    gdp_growth[
        gdp_growth["year"].between(
            MODERN_GDP_SOURCE_START_YEAR,
            TREND_GDP_SOURCE_END_YEAR,
            inclusive="both",
        )
    ][["country_code", "country", "year", "gdp_growth"]]
    .dropna(subset=["gdp_growth"])
    .copy()
)
trend_gdp_historical_df = load_statics_historical_gdp_extension(
    TREND_GDP_SOURCE_START_YEAR,
    HISTORICAL_GDP_EXTENSION_END_YEAR,
)
trend_gdp_df = (
    pd.concat([trend_gdp_historical_df, trend_gdp_direct_df], ignore_index=True)
    .sort_values(["country_code", "year"])
    .drop_duplicates(subset=["country_code", "year"], keep="last")
)

if analysis_df.empty:
    raise ValueError("No rows remain after merging the World Bank rule-of-law series with GDP growth.")

print("\nMissing values by column:")
print(analysis_df.isna().sum())


# =========================================================
# 7. SCATTER PLOT: GDP GROWTH VS RULE-OF-LAW ESTIMATE
# =========================================================

plt.figure(figsize=(10, 6))
plt.scatter(
    analysis_df["rule_of_law_estimate"],
    analysis_df["gdp_growth"],
)

for _, row in analysis_df.iterrows():
    plt.text(
        row["rule_of_law_estimate"] + 0.03,
        row["gdp_growth"] + 0.03,
        f"{row['country_code']}-{row['year']}",
        fontsize=7,
    )

plt.xlabel("Rule of Law Estimate (World Bank WGI, RL.EST)")
plt.ylabel("GDP Growth (%)")
plt.title("GDP Growth vs World Bank Rule of Law Estimate")
plt.grid(True)
save_current_figure("gdp_vs_rule_of_law_scatter.png")


# =========================================================
# 8. SIMPLE OLS REGRESSION
# =========================================================

model1 = fit_ols(
    analysis_df,
    outcome="gdp_growth",
    numeric_predictors=["rule_of_law_estimate"],
    model_name="Simple OLS",
)

print("\n================ SIMPLE OLS ================\n")
print(model1.summary())


# =========================================================
# 9. OLS WITH CONTROLS
# =========================================================

controls_df = analysis_df.dropna(subset=["log_gdp", "life_expectancy"]).copy()
model2 = fit_ols(
    controls_df,
    outcome="gdp_growth",
    numeric_predictors=["rule_of_law_estimate", "log_gdp", "life_expectancy"],
    model_name="OLS with Controls",
)

print("\n================ OLS WITH CONTROLS ================\n")
print(model2.summary())


# =========================================================
# 10. COUNTRY FIXED EFFECTS REGRESSION
# =========================================================

fe_df = analysis_df.dropna(subset=["log_gdp"]).copy()
model3 = fit_ols(
    fe_df,
    outcome="gdp_growth",
    numeric_predictors=["rule_of_law_estimate", "log_gdp"],
    categorical_predictors=["country_code"],
    model_name="Country Fixed Effects",
)

print("\n================ COUNTRY FIXED EFFECTS ================\n")
print(model3.summary())


# =========================================================
# 11. PERIOD-BY-PERIOD REGRESSIONS
# =========================================================

for period_name in RULE_OF_LAW_PERIOD_LABELS:
    temp = analysis_df[analysis_df["period"] == period_name].copy()
    if len(temp) >= 5 and temp["rule_of_law_estimate"].nunique() > 1:
        model_p = fit_ols(
            temp,
            outcome="gdp_growth",
            numeric_predictors=["rule_of_law_estimate"],
            model_name=f"Period Regression: {period_name}",
        )
        print(f"\n================ PERIOD REGRESSION: {period_name} ================\n")
        print(model_p.summary())
    else:
        print(f"\nNot enough observations for period {period_name} with the World Bank rule-of-law dataset.")


# =========================================================
# 12. REGRESSION LINE PLOT
# =========================================================

x = analysis_df["rule_of_law_estimate"]
y = analysis_df["gdp_growth"]

coef = np.polyfit(x, y, 1)
poly1d_fn = np.poly1d(coef)

plt.figure(figsize=(10, 6))
plt.scatter(x, y)
plt.plot(np.sort(x), poly1d_fn(np.sort(x)))

plt.xlabel("Rule of Law Estimate (World Bank WGI, RL.EST)")
plt.ylabel("GDP Growth (%)")
plt.title("Regression Line: GDP Growth vs World Bank Rule of Law Estimate")
plt.grid(True)
save_current_figure("gdp_vs_rule_of_law_regression_line.png")


# =========================================================
# 13. COUNTRY TRENDS OVER TIME
# =========================================================

for code in sorted(analysis_df["country_code"].unique()):
    gdp_temp = trend_gdp_df[trend_gdp_df["country_code"] == code].sort_values("year")
    rol_temp = df[df["country_code"] == code].dropna(subset=["rule_of_law_estimate"]).sort_values("year")
    if len(gdp_temp) > 1 and len(rol_temp) > 1:
        country_name = countries.get(code, code)
        plt.figure(figsize=(9, 5))
        plt.plot(
            gdp_temp["year"],
            gdp_temp["gdp_growth"],
            color=COUNTRY_COLORS_BY_CODE.get(code),
            linewidth=2,
            label="GDP Growth",
        )
        plt.plot(
            rol_temp["year"],
            rol_temp["rule_of_law_estimate"],
            marker="s",
            linestyle="--",
            color="#222222",
            linewidth=2,
            label="Rule of Law Estimate",
        )
        plt.title(f"{country_name}: GDP Growth and Rule of Law Estimate Over Time")
        plt.xlabel("Year")
        plt.ylabel("Value")
        plt.xlim(TREND_GDP_SOURCE_START_YEAR, TREND_GDP_SOURCE_END_YEAR)
        plt.xticks(range(TREND_GDP_SOURCE_START_YEAR, TREND_GDP_SOURCE_END_YEAR + 1, 10))
        plt.legend()
        plt.grid(True)
        save_current_figure(f"{code}_trend.png")


# =========================================================
# 14. COMBINED RULE-OF-LAW ESTIMATE TREND
# =========================================================

rule_of_law_df = df.dropna(subset=["rule_of_law_estimate"]).copy()
country_codes = sorted(rule_of_law_df["country_code"].unique())

plt.figure(figsize=(12, 7))
for code in country_codes:
    temp = rule_of_law_df[rule_of_law_df["country_code"] == code].sort_values("year")
    if len(temp) > 1:
        country_name = temp["country"].iloc[0] if "country" in temp.columns else countries.get(code, code)
        plt.plot(
            temp["year"],
            temp["rule_of_law_estimate"],
            marker="o",
            linewidth=2,
            color=COUNTRY_COLORS_BY_CODE.get(code),
            label=country_name,
        )

plt.title("World Bank Rule of Law Estimate Over Time by Country")
plt.xlabel("Year")
plt.ylabel("Rule of Law Estimate (RL.EST)")
plt.grid(True)
plt.legend(title="Country", bbox_to_anchor=(1.02, 1), loc="upper left")
save_current_figure("rule_of_law_estimate_over_time_by_country.png")


# =========================================================
# 15. PERIOD AVERAGES TABLE
# =========================================================

period_table = (
    analysis_df.groupby(["country_code", "period"])[["gdp_growth", "rule_of_law_estimate"]]
    .mean()
    .reset_index()
)

print("\n================ PERIOD AVERAGES ================\n")
print(period_table)

save_dataframe_csv(
    period_table,
    OUTPUT_DIR / "period_averages_gdp_rule_of_law.csv",
    index=False,
)


# =========================================================
# 16. EXPORT FINAL MERGED DATA
# =========================================================

save_dataframe_csv(
    analysis_df,
    OUTPUT_DIR / "merged_gdp_rule_of_law_dataset.csv",
    index=False,
)

print("\nFiles saved:")
for filename in saved_files:
    print(f"- {filename}")
