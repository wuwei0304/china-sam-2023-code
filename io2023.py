# -*- coding: utf-8 -*-
"""
2023 年全国投入产出表（211 个产品，生产者价格，万元）的读取，以及按国民经济行业门类加总。

列和行按表中代码定位（THC、FU103、GCF、EX、IM、GO；VA001–VA004），不按位置。
金额除以 10000，单位为亿元。
"""
import warnings

import numpy as np
import pandas as pd

import paths

SECTIONS = {
    "A": ("农、林、牧、渔业", "Agriculture, forestry, animal husbandry and fishery"),
    "B": ("采矿业", "Mining"),
    "C": ("制造业", "Manufacturing"),
    "D": ("电力、热力、燃气及水生产和供应业", "Electricity, heat, gas and water supply"),
    "E": ("建筑业", "Construction"),
    "F": ("批发和零售业", "Wholesale and retail trade"),
    "G": ("交通运输、仓储和邮政业", "Transport, storage and postal services"),
    "H": ("住宿和餐饮业", "Accommodation and catering"),
    "I": ("信息传输、软件和信息技术服务业", "Information transmission, software and IT services"),
    "J": ("金融业", "Finance"),
    "K": ("房地产业", "Real estate"),
    "L": ("租赁和商务服务业", "Leasing and business services"),
    "M": ("科学研究和技术服务业", "Scientific research and technical services"),
    "N": ("水利、环境和公共设施管理业", "Water conservancy, environment and public facilities"),
    "O": ("居民服务、修理和其他服务业", "Resident services, repair and other services"),
    "P": ("教育", "Education"),
    "Q": ("卫生和社会工作", "Health and social work"),
    "R": ("文化、体育和娱乐业", "Culture, sports and entertainment"),
    "S": ("公共管理、社会保障和社会组织", "Public administration, social security and social organizations"),
}
CODES = list(SECTIONS)
N_PRODUCTS = 211
CODE_ROW = 5
FIRST_ROW = 6
FIRST_COL = 3


def _code(value):
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(5) if text.isdigit() else text


def read_sheet():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return pd.read_excel(paths.io_file(), sheet_name=0, header=None)


def products(raw):
    rows = range(FIRST_ROW, FIRST_ROW + N_PRODUCTS)
    out = pd.DataFrame(
        {
            "code": [_code(raw.iloc[i, 2]) for i in rows],
            "name": [str(raw.iloc[i, 1]).strip() for i in rows],
        }
    )
    head = [_code(raw.iloc[CODE_ROW, j]) for j in range(FIRST_COL, FIRST_COL + N_PRODUCTS)]
    if head != out["code"].tolist():
        raise RuntimeError("投入产出表行、列的产品代码顺序不一致")
    return out


def export_concordance():
    """把工作簿 m 表（211×19 的 0/1 转换矩阵）导出为长表。"""
    raw = read_sheet()
    prod = products(raw)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        m = pd.read_excel(paths.io_file(), sheet_name="m", index_col=0).fillna(0.0)
    if [str(i).strip() for i in m.index] != prod["name"].tolist():
        raise RuntimeError("转换矩阵的产品名称与投入产出表不一致")
    values = m.to_numpy()
    if not np.allclose(values.sum(axis=1), 1.0) or not np.isin(values, [0.0, 1.0]).all():
        raise RuntimeError("转换矩阵每个产品应恰好归入一个门类")
    section = [str(m.columns[k]).split(">")[0] for k in values.argmax(axis=1)]
    out = prod.rename(columns={"code": "product_code", "name": "product_name_zh"})
    out["section"] = section
    out["section_name_zh"] = [SECTIONS[s][0] for s in section]
    out["section_name_en"] = [SECTIONS[s][1] for s in section]
    paths.ensure_dirs()
    out.to_csv(paths.CONCORDANCE, index=False, encoding="utf-8-sig")
    return out


def load_concordance():
    if not paths.CONCORDANCE.exists():
        export_concordance()
    conc = pd.read_csv(paths.CONCORDANCE, dtype=str)
    return conc


def load_io():
    """返回门类层面的投入产出流量（亿元）和产品层面的居民消费。"""
    raw = read_sheet()
    prod = products(raw)
    conc = load_concordance()
    if conc["product_code"].tolist() != prod["code"].tolist():
        raise RuntimeError("转换表与投入产出表的产品代码不一致")
    m = pd.get_dummies(conc["section"]).reindex(columns=CODES, fill_value=0).to_numpy(dtype=float)

    col_of = {str(raw.iloc[CODE_ROW, j]).strip(): j for j in range(raw.shape[1])}
    row_of = {str(raw.iloc[i, 2]).strip(): i for i in range(raw.shape[0])}
    rows = slice(FIRST_ROW, FIRST_ROW + N_PRODUCTS)
    cols = slice(FIRST_COL, FIRST_COL + N_PRODUCTS)

    def num(block):
        return block.apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float) / 10000.0

    z = num(raw.iloc[rows, cols])
    final = {k: num(raw.iloc[rows, col_of[c]]) for k, c in
             [("hh", "THC"), ("gov", "FU103"), ("gcf", "GCF"), ("exp", "EX"), ("imp", "IM"), ("go", "GO")]}
    va = {k: num(raw.iloc[row_of[c], cols]) for k, c in
          [("labor", "VA001"), ("tax", "VA002"), ("dep", "VA003"), ("surplus", "VA004")]}

    output = z.sum(axis=0) + va["labor"] + va["tax"] + va["dep"] + va["surplus"]
    if np.max(np.abs(output - final["go"])) > 1e-3:
        raise RuntimeError("总投入与总产出不一致")
    use = z.sum(axis=1) + final["hh"] + final["gov"] + final["gcf"] + final["exp"]
    if np.max(np.abs(output + final["imp"] - use)) > 1e-3:
        raise RuntimeError("产品供给与使用不平衡")

    def agg(v):
        return pd.Series(m.T @ v, index=CODES)

    io = {
        "sections": CODES,
        "Z": pd.DataFrame(m.T @ z @ m, index=CODES, columns=CODES),
        "hh": agg(final["hh"]),
        "gov": agg(final["gov"]),
        "gcf": agg(final["gcf"]),
        "exp": agg(final["exp"]),
        "imp": agg(final["imp"]),
        "labor": agg(va["labor"]),
        "tax": agg(va["tax"]),
        "capital": agg(va["dep"] + va["surplus"]),
        "output": agg(output),
        "products": prod.assign(section=conc["section"].to_numpy(), hh=final["hh"]),
    }
    return io
