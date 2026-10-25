# -*- coding: utf-8 -*-
"""
敏感性分析，输出到 output/sensitivity/。

情景
  base            储蓄率下限 −25%，按户加权十等分（v1），住户资本形成按房贷份额
  floor_-10       储蓄率下限 −10%
  floor_-50       储蓄率下限 −50%
  no_floor        不设下限（各项份额等于 CFPS 先验）
  person_deciles  按人口加权十等分（v2），各组人口相等
  gcf_by_saving   住户资本形成按正储蓄份额分摊
"""
import numpy as np
import pandas as pd

import paths
import sam_multipliers
from build_sam4 import GROUPS, build
from validate_sam4 import gini

OUT = paths.OUTPUT / "sensitivity"

SCENARIOS = {
    "base": {},
    "floor_-10": {"saving_floor": -0.10},
    "floor_-50": {"saving_floor": -0.50},
    "no_floor": {"saving_floor": None},
    "person_deciles": {"cfps_version": "v2"},
    "gcf_by_saving": {"gcf_key": "saving"},
}


def summarise(name, res):
    hh = res["households"]
    version = res["settings"]["cfps_version"]
    groups = pd.read_excel(paths.CFPS_DECILES, sheet_name=f"{version}_groups", index_col=0)
    pop = groups["population_share"].to_numpy()
    disp = hh["disposable_income"].to_numpy()
    share = disp / disp.sum()
    mult = sam_multipliers.run(res["sam"], res["accounts"])
    tr = mult["household_transfer"]
    row = {
        "scenario": name,
        "cross_entropy": res["objective"],
        "gini_between_groups": gini(pop, disp),
        "bottom_20pct_households_share": share[:2].sum(),
        "top_10pct_share": share[-1],
        "min_saving_rate": hh["saving_rate"].min(),
        "max_saving_rate": hh["saving_rate"].max(),
        "groups_with_negative_deposits": int((hh["F-DEP_use"] < 0).sum()),
        "disc_total": float(res["sam"].loc["DISC"].sum()),
        "spectral_radius": float(mult["diagnostics"].iloc[0, 1]),
        "gdp_multiplier_H-1": tr.loc["H-1", "gdp"],
        "gdp_multiplier_H-10": tr.loc["H-10", "gdp"],
    }
    return row, hh["saving_rate"].rename(name), pd.Series(share, index=GROUPS, name=name), tr["gdp"].rename(name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, rates, shares, gdp = [], [], [], []
    for name, kw in SCENARIOS.items():
        res = build(**kw)
        if (res["sam"].sum(axis=1) - res["sam"].sum(axis=0)).abs().max() > 1e-6:
            raise RuntimeError(f"{name} 不平衡")
        r, s, d, g = summarise(name, res)
        rows.append(r)
        rates.append(s)
        shares.append(d)
        gdp.append(g)
        print(f"{name:15s} CE={r['cross_entropy']:.4f} gini={r['gini_between_groups']:.3f} "
              f"min_s={r['min_saving_rate']:.3f} gdp_H1={r['gdp_multiplier_H-1']:.3f} gdp_H10={r['gdp_multiplier_H-10']:.3f}")
    summary = pd.DataFrame(rows).set_index("scenario")
    summary.to_csv(OUT / "summary.csv", encoding="utf-8-sig")
    pd.concat(rates, axis=1).to_csv(OUT / "saving_rates.csv", encoding="utf-8-sig")
    pd.concat(shares, axis=1).to_csv(OUT / "disposable_income_shares.csv", encoding="utf-8-sig")
    pd.concat(gdp, axis=1).to_csv(OUT / "gdp_multiplier_of_transfers.csv", encoding="utf-8-sig")
    print(pd.concat(rates, axis=1).round(3).to_string())


if __name__ == "__main__":
    main()
