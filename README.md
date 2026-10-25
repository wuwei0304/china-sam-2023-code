# Code for the 2023 China social accounting matrix

Construction and validation code for a 2023 China social accounting matrix (SAM) with ten household
income groups and financial accounts. The code combines national input-output, flow-of-funds and
financial accounts, using CFPS 2022 aggregate shares to allocate household totals.

This repository contains software, structural concordances and documentation. The complete final
SAM and CFPS-derived group outputs are being prepared separately for a CFPS-approved deposit
arrangement. No data repository approval, DOI or access arrangement is asserted here.

## Run locally

1. Use Python 3.11 and install the tested packages:

   ```sh
   python -m pip install -r requirements.txt
   ```

2. Obtain the four authorised inputs listed in [inputs/README.md](inputs/README.md), including
   CFPS data accessed through the official registration and user-agreement process. Put them
   under `inputs/`, or set `SAM4_INPUTS` to their folder. These inputs are not included here.

3. Run the complete pipeline:

   ```sh
   python run_all.py
   ```

It constructs the decile summaries and consumption bridge, builds the SAM, and generates validation,
sensitivity, multiplier and figure outputs. Generated files remain local and are ignored by Git.
Running the code does not confer permission to redistribute inputs or CFPS-derived outputs.

## Files and parameters

- `paths.py` resolves local inputs and generated-file locations; `io2023.py` reads and aggregates
  the input-output table.
- `build_cfps_deciles.py` constructs weighted household groups;
  `build_consumption_bridge.py` maps consumption categories and products;
  `build_sam4.py` constructs and balances the matrix.
- `validate_sam4.py`, `sensitivity.py`, `sam_multipliers.py` and `make_figures.py` generate checks
  and technical outputs. `run_all.py` runs them in order.
- `data/` contains structural concordances and [variable-role documentation](data/variable_roles.md).

The baseline is `build_sam4.build(saving_floor=-0.25, cfps_version="v1", gcf_key="mortgage")`.
The alternatives in `sensitivity.py` vary the saving floor, grouping weight and capital-allocation
key. Rows receive payments, columns pay, and matrix flows are in 100 million yuan. See
[REPRODUCING.md](REPRODUCING.md) for full reconstruction and checks.

## Data access and code licence

See [DATA_ACCESS.md](DATA_ACCESS.md) for input acquisition and the status of the final dataset.
Original provider workbooks, survey microdata, internal decile workbooks and generated SAM files
are excluded from this code repository. The licence is MIT for the software and project-authored
documentation; it does not grant rights to third-party inputs or CFPS-derived data products.

Version 1.0.0 is archived on Zenodo: [10.5281/zenodo.23642715](https://doi.org/10.5281/zenodo.23642715).
It preserves the 24-file snapshot at commit `245a17a707061151f41652efc329aa7cfa2e4d9e`.
The DOI identifies software, concordances and documentation; the archive contains no generated
SAM or CFPS-derived group output. `CITATION.cff` provides citation metadata for this fixed version.

## Contributing

Describe the issue and include a minimal example using synthetic or independently shareable data.
Do not attach survey records or restricted provider files. New publishable files must be explicitly
allowed in `.gitignore`; generated results and inputs should remain ignored.
