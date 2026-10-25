# Reconstructing the SAM

Use Python 3.11 with the versions pinned in `requirements.txt`. Obtain the four authorised input
files in `inputs/README.md`, and use their original layouts. Put them below `inputs/` or set
`SAM4_INPUTS` to their containing folder. The code searches subfolders and selects the first sorted
matching filename, so retain only the intended version of each input there.

Run `python run_all.py`. The sequence is: weighted CFPS groups, consumption bridge, matrix build,
validation, multiplier diagnostics, sensitivity and figures. Generated directories are local and
ignored by Git. `H-1` is the lowest income group; the baseline uses household weights (`v1`),
a saving-rate floor of -0.25 and mortgage shares for household capital formation.

If no CFPS microdata are found but the internal decile workbook exists, `run_all.py` can reuse it.
That convenience mode is not reconstruction from raw inputs. A clean reconstruction must start
without an `intermediate/` cache and have authorised access to all four inputs.

Verify matrix dimensions (67 by 67), finite values, account labels and a maximum row-column gap
below 1e-6. Inspect `output/validation/`, the discrepancy decomposition and sensitivity scenarios.
Rows receive payments; columns pay; flows are in 100 million yuan. Negative financial entries are
net repayments or disposals, and household deposit acquisitions also serve as balancing residuals.

The variable roles and missing-value rules are documented in `data/variable_roles.md`. A balanced
matrix alone does not establish that allocation proxies or survey shares are unbiased. Comparisons
with household-survey income measures also differ in accounting concepts and aggregation.

For repeatability, compare the generated CSV files byte for byte across clean builds. Excel content
can be compared sheet by sheet, since container timestamps may differ. Survey-derived checks and
outputs must stay local unless a sharing arrangement permits their distribution; see `DATA_ACCESS.md`.
