# Household variables, allocation proxies and missing values

Source: CFPS 2022 family economics file `cfps2022famecon_202410.dta`. This is documentation of the
implementation; it contains no household records or group-level survey values.

## Group definition and aggregation

`fincome1_per` ranks households by per-capita net family income. `fswt_natcs22n` is the baseline
cross-sectional household weight. In the person-decile sensitivity case the grouping weight is
`fswt_natcs22n * familysize22`; totals within each group still use the household weight.
`familysize22` supplies the population shares used to form per-capita group comparisons.

Sorting is stable, so tied incomes retain their input-file order. Cumulative weights assign whole
households to deciles; the groups are approximately, rather than exactly, equal in weighted size.
Ranking income and weight must be non-missing, and weight must be positive. No household is removed
from all items because one allocation variable is missing. Observed values are summed with weights
separately for each variable. No missing-value imputation or missingness adjustment is applied.
Negative net worth is retained. Grouped Gini coefficients omit within-group inequality.

## Eight balanced national-accounts items

- `LAB`: wage income `fwage_1` provides the prior for compensation of employees received.
- `OS`: operating income `foperate_1` provides the prior for household gross operating surplus.
- `PIR`: property income `fproperty_1` provides the prior for property income received.
- `PIP`: mortgage payments `mortage` proxy the distribution of property income paid.
- `TRR`: transfer income `ftransfer_1` provides the prior for current transfers received.
- `TAX`: wage income `fwage_1` proxies current income taxes and social insurance contributions paid.
- `TRP`: transfer expenditure `eptran` provides the prior for other current transfers paid.
- `CON`: the consumption bridge combines survey category shares with official product expenditure.

These are allocation proxies for macroeconomic transactions, not claims that the survey variables
are identical to the corresponding national-accounts concepts. Prior shares are floored at 1e-6
and renormalised before the cross-entropy step; the national totals remain fixed.

## Consumption and capital/financial allocation

The consumption bridge uses `food`, `dress`, `house`, `daily`, `trco`, `eec`, `med` and `other`.
The concordance file documents how each IO product is mapped. Trade margins follow the combined
goods-consumption shares. FISIM follows `total_asset` (net worth) shares. The aggregate survey
consumption variable `pce` is available for diagnostics but does not replace the product bridge.

Mortgage shares also allocate household capital formation and selected loan liabilities.
Positive calibrated saving, disposable income, calibrated consumption and operating surplus
provide the other allocation keys listed in the manuscript. Deposits acquired are a balancing
residual. Decile financial flows are modelled allocations, not directly observed survey flows.

## Internal diagnostics

The internal decile workbook also retains `fincome1`, `felse_1`, `epwelf` and `expense` for comparisons.
These variables are not additional balancing constraints. The workbook and any survey-derived
sample or missingness audit remain local unless a permitted sharing arrangement is confirmed.
