# Data access

This repository shares construction code. The complete final SAM and processed group-level
outputs are available in a separate public Dataset; original inputs and internal household-level
or decile workbooks are not redistributed here.

## Public Dataset

Dataset version 1.0.0, published 26 October 2026:
- DOI: [10.5281/zenodo.23654134](https://doi.org/10.5281/zenodo.23654134).
- Data repository: [china-sam-2023-data](https://github.com/wuwei0304/china-sam-2023-data).
- [Direct Zenodo download](https://zenodo.org/records/23654134/files/china-sam-2023-data-1.0.0.zip?download=1).
- Licence: CC BY 4.0 for the author-created SAM, aggregate/modelled outputs and project documentation.

The archive contains 40 files (801,555 bytes), including the full 67-account income-decile SAM,
an optional household aggregation, validation, sensitivity and multiplier tables, concordances,
figures and documentation. Anonymous downloads from GitHub and Zenodo have been checked against
SHA-256 `fb7f1a5acc89007d83737ea763d8e93b041ce9943753f6c7d053b9c2461fa06e`.

The authors confirm that CFPS permitted the relevant group-level aggregate parameters to accompany
the paper in public repositories under its user agreement, without prior review or filing.
That permission and the CC BY 4.0 licence do not cover original CFPS records or original provider
workbooks. Reading the published aggregates does not require CFPS registration.

## Original inputs for reconstruction

Acquire the 2023 national input-output table and non-financial flow-of-funds accounts from the
National Bureau of Statistics, financial accounts from the People's Bank of China, and the CFPS
2022 family economics file through the Institute of Social Science Survey, Peking University.
Expected filenames, input layouts and provider links are in [inputs/README.md](inputs/README.md).
Follow each provider's terms; CFPS registration and acceptance of its user agreement are required
to obtain the microdata and reconstruct the aggregates.

Official CFPS guidance:
https://www.isss.pku.edu.cn/cfps/en/faq/PublishwithCFPSData/index.htm

## Separate software archive

The fixed 24-file software version 1.0.0 is archived under MIT at
[10.5281/zenodo.23642715](https://doi.org/10.5281/zenodo.23642715).
It contains no generated numerical outputs. Cite the Dataset DOI for data and the software DOI
for code. These documentation updates do not change that archived software snapshot.

## Files excluded from this code repository

Original inputs, `.dta`/`.sav` files, credentials, internal decile workbooks, `intermediate/`,
`output/`, `figures/`, manuscript files and local logs remain excluded. Only the audited aggregate
release is distributed through the separate data repository. Running the code alone does not
grant rights to redistribute source data or other outputs.
