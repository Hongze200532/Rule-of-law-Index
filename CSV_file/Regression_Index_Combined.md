# Regression Output Explanation and World Bank Rule of Law Index Definition

This document replaces the earlier Ford Foundation qualitative ordinal proxy with the official World Bank Worldwide Governance Indicators (WGI) rule-of-law series. Unless stated otherwise, every rule-of-law reference below now refers to the World Bank indicator `RL.EST` (`Rule of Law: Estimate`).

---

## 1. Indicator Used in This Project

| Item | Value |
|------|-------|
| Official indicator | `RL.EST` |
| Indicator name | Rule of Law: Estimate |
| Producer | World Bank, Worldwide Governance Indicators (WGI) |
| Local CSV used by the project | `CSV_file/WB_index/API_RL.EST_DS2_en_csv_v2_5814.csv` |
| CSV header source label | World Development Indicators |
| CSV header last updated date | 2026-02-24 |
| Earliest year with actual `RL.EST` values in the bundled CSV | 1996 |
| Latest year with actual `RL.EST` values in the bundled CSV | 2023 |
| Project regression window | 1996-2015 |
| Countries in the plotted sample | Argentina, Brazil, China, India, Kenya, Mexico, Nigeria, South Africa, United States |

Important clarification:

- `RL.EST` is an official governance indicator published by the World Bank WGI program.
- It is not a Ford Foundation funding index.
- It is not the earlier 0-8 constructed ordinal proxy.
- It is not a direct measure of legal expenditure, grant size, or policy effort.

---

## 2. What the World Bank Rule of Law Indicator Measures

The World Bank defines Rule of Law as a governance dimension capturing perceptions of how far people and firms have confidence in, and comply with, the rules of society. In practice, the indicator focuses especially on:

- contract enforcement
- property rights
- the police
- the courts
- crime and violence

In other words, `RL.EST` is not asking whether a country has laws on paper. It is a perception-based composite indicator about how well legal and security institutions function in practice.

### How to read the values

- Higher values mean stronger perceived rule of law.
- Lower values mean weaker perceived rule of law.
- A value near `0` is roughly around the global average for the standardized WGI scale.
- Positive values indicate above-average perceived institutional quality on this dimension.
- Negative values indicate below-average perceived institutional quality on this dimension.

The traditional WGI estimate scale is approximately `-2.5` to `+2.5`, although exact extrema vary by year and country. This is a standardized governance score, not a percentage and not a 0-10 rating.

Two interpretation cautions matter:

1. `0` does not mean "no rule of law"; it means roughly average on the WGI comparison scale.
2. A difference such as `1.5` versus `0.5` is not a literal "three times better" relationship. It indicates a higher latent governance estimate on the WGI statistical scale.

---

## 3. Why This Project Switched to `RL.EST`

The earlier version of this project used a hand-constructed ordinal index derived from Ford Foundation reports. That approach was useful for internal exploratory coding, but it had three important limitations:

- it was not an official cross-country governance measure
- it mixed program interpretation with outcome measurement
- it did not provide formal uncertainty information such as standard errors or confidence intervals

Using the World Bank official series improves consistency because:

- the same statistical framework is applied across countries
- the indicator is designed specifically for cross-country governance comparison
- companion uncertainty and source-count indicators are available
- the project can now cite a standard external governance dataset instead of a custom proxy

---

## 4. How the World Bank WGI Rule of Law Estimate Is Built

The `RL.EST` series is part of the broader Worldwide Governance Indicators framework. The current WGI methodology paper explains that the revised WGI:

- reports six governance dimensions
- draws on 35 data sources
- uses household surveys, firm surveys, and expert assessments
- covers over 200 economies annually from 1996 onward

### Construction logic

| Step | What the WGI does | Why it matters |
|------|-------------------|----------------|
| 1. Source collection | Collects governance-relevant perception data from surveys and expert assessments | Reduces dependence on any single dataset |
| 2. Indicator rescaling | Rescales individual source variables to a common direction and scale | Makes heterogeneous questions comparable |
| 3. Source-dimension aggregation | Groups variables relevant to Rule of Law within each source | Preserves the source-specific rule-of-law signal |
| 4. Cross-source aggregation | Uses an unobserved components model (UCM) to estimate the latent governance score | Extracts a common signal while accounting for source noise |
| 5. Published outputs | Reports estimate, standard error, percentile rank, confidence bounds, and number of sources | Supports interpretation with uncertainty information |

### Key methodological details

- The WGI revised methodology paper states that more than 400 individual indicators are first rescaled to `0-1`, with higher values representing better governance outcomes.
- These rescaled source signals are then combined using an unobserved components model rather than a simple arithmetic average.
- The published `RL.EST` series is the estimated latent governance score on the traditional WGI standardized scale.
- The 2025 methodology revision also introduced an absolute `0-100` scale, but this project continues to use `RL.EST` because the bundled World Bank CSV and the regression code are based on that official estimate series.

### Why some early years are missing

The bundled CSV contains year columns from 1960 onward, but `RL.EST` values only begin in 1996. For the countries used in this project, the actual observation pattern is:

- `1996`
- `1998`
- `2000`
- annual data from `2002` onward

So the absence of 1995 or 2001 values is normal for the official WGI release pattern and should not be treated as a data-cleaning error.

---

## 5. How `Regression.py` Uses the Official Indicator

The current regression script already reads the official World Bank file directly:

- it loads `CSV_file/WB_index/API_RL.EST_DS2_en_csv_v2_5814.csv`
- it skips the first four metadata rows
- it filters `Indicator Code == "RL.EST"`
- it reshapes the wide World Bank export into long country-year format
- it stores the final regression variable in `rule_of_law_estimate`

This project now merges that official rule-of-law estimate with:

- GDP growth (`NY.GDP.MKTP.KD.ZG`)
- GDP level (`NY.GDP.MKTP.KD`)
- life expectancy (`SP.DYN.LE00.IN`)

The code also now uses periods aligned with the official rule-of-law coverage rather than the old proxy periods:

- `1996-2005`
- `2006-2015`

That change avoids the misleading earlier split in which the pre-1990 period had no official `RL.EST` observations at all.

---

## 6. Representative `RL.EST` Values Used in the Plots

The following table reports official World Bank `RL.EST` values from the bundled CSV for the countries used in the regression figures. These are sample anchor points for interpretation and replace the earlier hand-coded "index score used in plot" tables.

| Country | Code | 1996 | 2000 | 2005 | 2010 | 2015 | 1996 -> 2015 reading |
|--------|------|------|------|------|------|------|-----------------------|
| Argentina | ARG | 0.076 | -0.214 | -0.558 | -0.598 | -0.749 | clear decline |
| Brazil | BRA | -0.224 | -0.245 | -0.476 | 0.056 | -0.187 | broadly stable, modest fluctuation |
| China | CHN | -0.546 | -0.516 | -0.650 | -0.473 | -0.408 | mild improvement from a negative base |
| India | IND | 0.313 | 0.348 | 0.133 | -0.036 | -0.071 | gradual decline toward the global midpoint |
| Kenya | KEN | -1.022 | -0.922 | -0.881 | -0.954 | -0.507 | noticeable improvement, still below average |
| Mexico | MEX | -0.727 | -0.427 | -0.383 | -0.552 | -0.455 | moderate improvement, still negative |
| Nigeria | NGA | -1.290 | -1.161 | -1.354 | -1.159 | -0.983 | weak throughout, some improvement by 2015 |
| United States | USA | 1.500 | 1.565 | 1.528 | 1.631 | 1.563 | consistently high positive level |
| South Africa | ZAF | 0.088 | 0.149 | -0.012 | 0.098 | 0.016 | near global average, slight softening overall |

Interpretation note:

- Positive values do not mean "perfect rule of law"; they mean above-average perceived rule of law in the WGI statistical framework.
- Negative values do not mean "absence of law"; they mean below-average perceived rule of law relative to the WGI comparison set.

---

## 7. Cross-Country Regression Figures

### GDP Growth vs Rule of Law Estimate Scatter

![GDP Growth vs Rule of Law Scatter](gdp_vs_rule_of_law_scatter.png)

This scatter plot now shows the official World Bank `RL.EST` variable on the horizontal axis and GDP growth on the vertical axis. Each point is one country-year observation.

Compared with the earlier hand-coded index interpretation, the horizontal axis now has a very different meaning:

- it is a standardized governance estimate
- it is centered around the WGI global comparison scale
- it includes both positive and negative values

The fitted sample does not show a positive unconditional relationship. In the refreshed regression output, the simple OLS slope on `rule_of_law_estimate` is negative (`-1.178`) with `p = 0.0001`, but the explanatory power remains limited (`R² = 0.059`). That means the sample contains a statistically visible negative cross-country association, but it still leaves most GDP-growth variation unexplained.

### GDP Growth vs Rule of Law Regression Line

![GDP Growth vs Rule of Law Regression Line](gdp_vs_rule_of_law_regression_line.png)

The fitted line summarizes the average linear association between GDP growth and the World Bank rule-of-law estimate. In the refreshed outputs, the line slopes downward rather than upward.

That result should still be read descriptively rather than causally. A negative fitted slope does not mean that improving rule of law lowers growth. It means that, in this selected country-year sample, countries with higher `RL.EST` values also tend to have lower contemporaneous GDP growth, largely because high-growth emerging economies and high-rule-of-law advanced economies occupy different parts of the sample.

### Overall Sample Pattern

Across the sample:

- the United States is the only country consistently far into the positive `RL.EST` range
- Kenya and Nigeria remain the weakest rule-of-law cases in the sample, although both improve relative to 1996
- China and Mexico remain negative but move modestly upward
- Argentina and India deteriorate over the selected benchmark years

### Refreshed Regression Summary

The rerun of `Regression.py` using the official bundled `RL.EST` CSV produced the following headline results:

| Model | Coefficient on `RL.EST` | p-value | R-squared | Reading |
|------|--------------------------|---------|-----------|---------|
| Simple OLS | -1.178 | 0.0001 | 0.059 | negative cross-country association, low explanatory power |
| OLS with controls (`log_gdp`, `life_expectancy`) | -2.481 | <0.0001 | 0.220 | negative association remains after adding controls |
| Country fixed effects | -1.176 | 0.564 | 0.405 | within-country effect is not statistically significant |
| Period regression `1996-2005` | -0.919 | 0.0648 | 0.037 | negative, marginal significance |
| Period regression `2006-2015` | -1.368 | 0.0001 | 0.079 | stronger negative association in the later period |

The key takeaway is that the negative sign is driven mainly by cross-country differences in the sample rather than a strong within-country result over time. Once country fixed effects are added, the coefficient remains negative but loses statistical significance.

---

## 8. Country Visual Notes

### Argentina

![Argentina Trend](ARG_trend.png)

Argentina moves from slightly above zero in 1996 to clearly negative values by 2015. In the plot, this means the official rule-of-law estimate trends downward over the period even as GDP growth remains highly cyclical.

### Brazil

![Brazil Trend](BRA_trend.png)

Brazil stays close to the global midpoint but mostly below zero. The rule-of-law estimate fluctuates rather than rising steadily, which is very different from the old monotonic hand-coded proxy.

### China

![China Trend](CHN_trend.png)

China remains below zero throughout the sample but improves modestly between 1996 and 2015. The trend plot therefore combines persistently negative rule-of-law estimates with comparatively strong GDP growth.

### India

![India Trend](IND_trend.png)

India starts from a positive rule-of-law estimate in the late 1990s and trends downward toward zero and slightly negative territory by 2015. The GDP series remains much more volatile than the governance estimate.

### Kenya

![Kenya Trend](KEN_trend.png)

Kenya remains well below the global midpoint for the entire sample, but the official rule-of-law estimate improves materially by 2015. This is an example of relative improvement from a weak starting point rather than convergence to a high governance level.

### Mexico

![Mexico Trend](MEX_trend.png)

Mexico stays negative throughout the benchmark years. There is some long-run improvement relative to 1996, but the path is not smooth and remains below the WGI midpoint.

### Nigeria

![Nigeria Trend](NGA_trend.png)

Nigeria is the weakest case in the sample on `RL.EST`. The estimate improves somewhat by 2015, but it remains strongly negative, so the figure should be read as persistent institutional weakness rather than normalization.

### United States

![United States Trend](USA_trend.png)

The United States remains consistently high and positive on the World Bank rule-of-law estimate, with values around `1.5` across the benchmark years. This produces a very different scale from the old 5-8 ordinal narrative and should now be interpreted on the WGI statistical metric.

### South Africa

![South Africa Trend](ZAF_trend.png)

South Africa sits close to zero over most of the sample, with mild improvement in some middle years and slight deterioration overall by 2015. The result is better described as near-average performance with fluctuation rather than a strong one-direction trend.

---

## 9. Interpretation Rules for This Document

To keep the analysis aligned with the official World Bank indicator, the following interpretation rules now apply:

- Do not describe `RL.EST` as "investment intensity."
- Do not describe `RL.EST` as a Ford Foundation program score.
- Do not treat positive and negative values as spending levels.
- Do not compare the values as if they were percentages.
- Do treat the indicator as a perception-based latent governance estimate.
- Do interpret the sign, direction, and relative position on the WGI scale.

---

## 10. Limits of the World Bank Rule of Law Estimate

`RL.EST` is stronger than the old hand-built proxy for standardized comparison, but it still has important limits.

### 1. It is perception-based

The indicator reflects perceptions from surveys and expert assessments, not a direct administrative audit of courts, police, or property-rights enforcement.

### 2. It contains uncertainty

The WGI publishes companion uncertainty measures such as:

- `RL.STD.ERR` for the standard error
- percentile-rank confidence bounds
- `RL.NO.SRC` for the number of underlying sources

For close country comparisons or small year-to-year changes, those uncertainty measures should be checked before drawing strong conclusions.

### 3. It is not a causal treatment variable

In this project, `RL.EST` should be interpreted as a contextual governance variable. It should not be read as direct evidence that one unit of rule-of-law improvement causes a fixed change in GDP growth.

### 4. It is not designed for project attribution

The indicator is appropriate for broad country-level governance comparison. It is not designed to isolate the effect of a specific Ford Foundation program, legal reform package, or single policy event.

### 5. Historical comparability requires care

The WGI is a consistent long-run dataset, but source composition and uncertainty still matter. Small differences across nearby years should be interpreted more cautiously than large, persistent gaps.

---

## 11. Recommended Companion Indicators

If the project later needs a richer official rule-of-law measurement set, the most useful companion WGI series are:

| Indicator | Meaning | Use case |
|----------|---------|----------|
| `RL.EST` | Rule of Law: Estimate | Main regression variable now used in the project |
| `RL.STD.ERR` | Standard error of the estimate | Uncertainty / robustness checks |
| `RL.PER.RNK` | Percentile rank | Easier non-technical presentation |
| `RL.NO.SRC` | Number of underlying sources | Data-density / reliability context |
| `RL.PER.RNK.LOWER` / `UPPER` | 90% confidence interval bounds in percentile terms | Formal uncertainty intervals |

For the current regression workflow, `RL.EST` remains the primary explanatory variable, but the others are the correct official supplements if a robustness appendix is added later.

---

## 12. Source Note

This revision is based on the following official World Bank materials:

- World Bank Data indicator page for `RL.EST`
- World Bank DataBank metadata glossary for the Worldwide Governance Indicators
- The World Bank WGI methodology revision paper (December 2025)

Project-specific note:

- the bundled CSV used by this repository was exported through the World Bank data system and, in its header, reports `World Development Indicators` as the source label and `2026-02-24` as the last updated date
- the regression code uses the local CSV export directly rather than a hand-entered country scoring table

---

## 13. Bottom-Line Definition for This Project

In this repository, the rule-of-law variable should now be defined as follows:

> The project uses the official World Bank Worldwide Governance Indicators rule-of-law estimate (`RL.EST`) for each country-year observation, not a custom Ford Foundation ordinal index.

That is the correct short definition to use in the report, charts, regression notes, and any later methodology appendix.
