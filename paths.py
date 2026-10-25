# -*- coding: utf-8 -*-
"""
输入、输出位置。

官方表格和 CFPS 原始数据不随代码发布，放在 inputs/ 下（或用环境变量 SAM4_INPUTS 指定），
文件名见 inputs/README.md。
"""
import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
INPUTS = pathlib.Path(os.environ.get("SAM4_INPUTS", HERE / "inputs"))
DATA = HERE / "data"
INTERMEDIATE = HERE / "intermediate"
OUTPUT = HERE / "output"
FIGURES = HERE / "figures"

CONCORDANCE = DATA / "concordance_io2023_products_to_sections.csv"
CONSUMPTION_CONCORDANCE = DATA / "concordance_io2023_products_to_consumption_categories.csv"
INSTRUMENT_CONCORDANCE = DATA / "concordance_pbc_instruments_to_accounts.csv"
CFPS_DECILES = INTERMEDIATE / "cfps2022_deciles.xlsx"


def _find(pattern, extra=()):
    for base in (INPUTS, *extra):
        if base.exists():
            hits = sorted(base.rglob(pattern))
            if hits:
                return hits[0]
    raise FileNotFoundError(f"找不到 {pattern}，请按 inputs/README.md 放置文件（搜索位置 {INPUTS}）")


def io_file():
    return _find("2023投入产出表*.xlsx")


def fof_file():
    return _find("2023国家统计局资金流量表.xlsx")


def pbc_file():
    return _find("2023中国人民银行资金流量表.xlsx")


def cfps_dta():
    return _find("cfps2022famecon_202410.dta", extra=(HERE / "_cfps_work",))


def ensure_dirs():
    for d in (DATA, INTERMEDIATE, OUTPUT, FIGURES):
        d.mkdir(exist_ok=True)
