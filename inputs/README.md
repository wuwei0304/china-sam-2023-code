# Input files (not redistributed)

The build reads four third-party files from this folder (or from the folder given by the
environment variable `SAM4_INPUTS`). None of them is included in the data release. The code
searches sub-folders, so the files may sit anywhere under `inputs/`.

| File name the code looks for | Content | Where to obtain it |
| :-- | :-- | :-- |
| `2023投入产出表*.xlsx` | 2023 national input-output table, 211 products, producer prices, unit 10,000 yuan. The **first sheet** must be the table as published (product codes in the sixth row and third column; final-use codes `THC`, `FU103`, `GCF`, `EX`, `IM`, `GO`; value-added codes `VA001`–`VA004`). | National Bureau of Statistics (NBS) data portal: <https://data.stats.gov.cn/dg/website/page.html#/pc/national/home/report?reportId=41a5187ae4114d50aeb6288a54d25234&catalogId=2ab4dc96a65a4c5192478c9798c77f7b&type=inOut> |
| `2023国家统计局资金流量表.xlsx` | 2023 flow of funds, non-financial transactions (资金流量表（非金融交易）), unit 100 million yuan | NBS data portal: <https://data.stats.gov.cn/dg/website/page.html#/pc/national/home/report?reportId=21f858a5747f4dfb96bad926daf1fa9c&catalogId=aba37576fa944feb9c7eec3ab2c8d5be&type=fundFlow> |
| `2023中国人民银行资金流量表.xlsx` | 2023 flow of funds, financial accounts (资金流量表（金融账户）), unit 100 million yuan | People's Bank of China, Survey and Statistics Department: <https://www.pbc.gov.cn/diaochatongjisi/116219/116319/4780803/4780809/index.html> |
| `cfps2022famecon_202410.dta` | China Family Panel Studies 2022, family economics file, release of October 2024 | Institute of Social Science Survey (ISSS), Peking University, after registration and acceptance of the CFPS user agreement: <https://www.isss.pku.edu.cn/cfps/> |

Exact filenames and input layouts are listed above. The manuscript/data record will document the author's download dates and platform-version citation once confirmed; each user should record their own input versions and access dates.

The 211-product to 19-section concordance is not an input; it is released as
`data/concordance_io2023_products_to_sections.csv`.

The first step writes `intermediate/cfps2022_deciles.xlsx` (decile-level aggregates). It is a
CFPS-derived product and is not distributed unless ISSS permits it; users need their own CFPS
access to rebuild the household deciles.

No download date or platform version is inferred from a file's modification time or filename.
The exact CFPS input filename is fixed by the code; the author's download platform, date and
corresponding platform-version citation still need to be checked. The filename suffix `202410`
is not, by itself, proof of the Dataverse version used.
