# -*- coding: utf-8 -*-
"""
使用示例：SAM 账户乘数（Pyatt & Round 1979）。

内生账户：活动、商品、劳动、资本、10 个住户组。其余账户（企业、政府、国外、资本形成、
分配和金融账户、统计差异）为外生。M = (I − A)^-1，A 为内生块除以各列合计。

输出 output/multipliers/：
  household_transfer.csv  向每个住户组注入 1 亿元经常转移的 GDP、总产出、住户收入效应
  export_demand.csv       每个商品出口需求增加 1 亿元的效应
  diagnostics.csv         谱半径、M 的最小元素
只读 output/SAM4_2023.csv 和 SAM4_2023_accounts.csv，不需要原始数据。
"""
import numpy as np
import pandas as pd

import paths

ENDOGENOUS = ["activity", "commodity", "factor", "household"]
OUT = paths.OUTPUT / "multipliers"


def load(sam_file=None, accounts_file=None):
    sam = pd.read_csv(sam_file or paths.OUTPUT / "SAM4_2023.csv", index_col=0)
    accounts = pd.read_csv(accounts_file or paths.OUTPUT / "SAM4_2023_accounts.csv")
    return sam, accounts


def multipliers(sam, accounts):
    endo = accounts.loc[accounts["type"].isin(ENDOGENOUS), "code"].tolist()
    totals = sam.sum(axis=0)
    a = sam.loc[endo, endo].div(totals[endo], axis=1)
    m = np.linalg.inv(np.eye(len(endo)) - a.to_numpy())
    radius = float(np.max(np.abs(np.linalg.eigvals(a.to_numpy()))))
    return pd.DataFrame(m, index=endo, columns=endo), radius


def effects(sam, accounts, m, injected):
    """对 injected 中每个账户注入 1 单位，返回 GDP、活动总产出、住户收入的变化。"""
    acts = accounts.loc[accounts["type"] == "activity", "code"].tolist()
    groups = accounts.loc[accounts["type"] == "household", "code"].tolist()
    output = sam[acts].sum(axis=0)
    va_rate = sam.loc[["LAB", "CAP", "GOV"], acts].sum(axis=0) / output
    rows = []
    for acc in injected:
        d = m[acc]
        row = {
            "injected": acc,
            "gdp": float((va_rate * d[acts]).sum()),
            "gross_output": float(d[acts].sum()),
            "household_income": float(d[groups].sum()),
        }
        for g in groups:
            row[f"income_{g}"] = float(d[g])
        rows.append(row)
    return pd.DataFrame(rows).set_index("injected")


def run(sam, accounts):
    m, radius = multipliers(sam, accounts)
    groups = accounts.loc[accounts["type"] == "household", "code"].tolist()
    coms = accounts.loc[accounts["type"] == "commodity", "code"].tolist()
    return {
        "M": m,
        "household_transfer": effects(sam, accounts, m, groups),
        "export_demand": effects(sam, accounts, m, coms),
        "diagnostics": pd.DataFrame(
            [["spectral radius of A", radius], ["min element of M", float(m.to_numpy().min())],
             ["endogenous accounts", len(m)]],
            columns=["check", "value"],
        ),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sam, accounts = load()
    res = run(sam, accounts)
    res["household_transfer"].to_csv(OUT / "household_transfer.csv", encoding="utf-8-sig")
    res["export_demand"].to_csv(OUT / "export_demand.csv", encoding="utf-8-sig")
    res["diagnostics"].to_csv(OUT / "diagnostics.csv", index=False, encoding="utf-8-sig")
    print(res["diagnostics"].to_string(index=False))
    print(res["household_transfer"][["gdp", "gross_output", "household_income"]].round(3).to_string())
    print(res["export_demand"][["gdp", "gross_output", "household_income"]].round(3).to_string())


if __name__ == "__main__":
    main()
