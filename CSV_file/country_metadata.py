from __future__ import annotations

COUNTRY_METADATA = {
    "USA": {
        "canonical_name": "United States",
        "gdp_chart_label": "USA",
        "chart_color": "#1f77b4",
        "ford_aliases": ["United States", "United States of America", "USA"],
    },
    "CHN": {
        "canonical_name": "China",
        "gdp_chart_label": "China",
        "chart_color": "#d62728",
        "ford_aliases": ["China", "China (People's Republic of)"],
    },
    "IND": {
        "canonical_name": "India",
        "gdp_chart_label": "",
        "chart_color": "#9467bd",
        "ford_aliases": ["India"],
    },
    "BRA": {
        "canonical_name": "Brazil",
        "gdp_chart_label": "",
        "chart_color": "#2ca02c",
        "ford_aliases": ["Brazil"],
    },
    "MEX": {
        "canonical_name": "Mexico",
        "gdp_chart_label": "",
        "chart_color": "#e377c2",
        "ford_aliases": ["Mexico"],
    },
    "KEN": {
        "canonical_name": "Kenya",
        "gdp_chart_label": "",
        "chart_color": "#8c564b",
        "ford_aliases": ["Kenya"],
    },
    "NGA": {
        "canonical_name": "Nigeria",
        "gdp_chart_label": "",
        "chart_color": "#7f7f7f",
        "ford_aliases": ["Nigeria"],
    },
    "ZAF": {
        "canonical_name": "South Africa",
        "gdp_chart_label": "",
        "chart_color": "#bcbd22",
        "ford_aliases": ["South Africa"],
    },
    "ARG": {
        "canonical_name": "Argentina",
        "gdp_chart_label": "",
        "chart_color": "#ff7f0e",
        "ford_aliases": ["Argentina"],
    },
}

COUNTRY_NAMES_BY_CODE = {
    code: metadata["canonical_name"]
    for code, metadata in COUNTRY_METADATA.items()
}

GDP_CHART_LABEL_BY_CODE = {
    code: metadata["gdp_chart_label"]
    for code, metadata in COUNTRY_METADATA.items()
}

COUNTRY_COLORS_BY_CODE = {
    code: metadata["chart_color"]
    for code, metadata in COUNTRY_METADATA.items()
}

FORD_RAW_NAME_TO_CODE = {}
for code, metadata in COUNTRY_METADATA.items():
    for alias in metadata["ford_aliases"]:
        FORD_RAW_NAME_TO_CODE[alias] = code

FORD_RAW_NAME_TO_CANONICAL = {
    alias: COUNTRY_NAMES_BY_CODE[code]
    for alias, code in FORD_RAW_NAME_TO_CODE.items()
}


def normalize_ford_recipient_name(value: object) -> object:
    if value is None:
        return value

    if isinstance(value, str):
        clean_value = value.strip()
        return FORD_RAW_NAME_TO_CANONICAL.get(clean_value, clean_value)

    return value
