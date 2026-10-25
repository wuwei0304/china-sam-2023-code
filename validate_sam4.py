# -*- coding: utf-8 -*-
"""
SAM4 的技术验证，输出到 output/validation/。

1 balance.csv              行列平衡、负值单元格
2 official_totals.csv      SAM 与投入产出表、资金流量表、人民银行金融账户的总量对照
3 sector_accounts.csv      各部门可支配收入、储蓄、净贷出（实物与金融两侧）
4 discrepancy.csv          统计差异按来源分解，合计为 0
5 households.csv           十等分组：份额、储蓄率、人均收入（相对全国均值）
6 quintiles_vs_nbs.csv     五等分人均可支配收入与国家统计局住户调查对照
7 balancing.csv            联立配平前后各项组间份额的变化
8 reproducibility.csv      两次独立运行的最大差、输出文件的 SHA-256
"""
import hashlib

import numpy as np
import pandas as pd

import paths
from build_sam4 import GROUPS, INSTRUMENTS, ITEMS, aggregate_households, build

OUT = paths.OUTPUT / "validation"

# 国家统计局《2023 年国民经济和社会发展统计公报》：全国居民五等份收入分组的人均可支配收入（元）
NBS_QUINTILES = [9215, 20442, 32195, 50220, 95055]
NBS_MEAN = 39218
NBS_GINI = 0.465  # 《中国住户调查年鉴 2024》表 1-4-14，引用前须核对年鉴原表
POPULATION_2023 = 140967e4  # 年末全国人口，统计公报

CAPITAL = ["KTRF", "NPA", "GCF"]
FIN = list(INSTRUMENTS)


def sector_accounts(sam, coms):
    """由 SAM 单元格计算各机构部门的经常、资本、金融三段。"""
    rows = []
    agg = aggregate_households(sam)
    excluded = set(CAPITAL + FIN + ["DISC"])
    for s in ["NFC", "FC", "GOV", "HH", "ROW"]:
        rec, pay = agg.loc[s], agg[s]
        cur = [a for a in agg.index if a not in excluded]
        cur_rec, cur_pay = rec[cur].sum(), pay[cur].sum()
        cons = pay[coms].sum() if s != "ROW" else 0.0
        saving = cur_rec - cur_pay
        nl_real = saving + rec["KTRF"] - pay["KTRF"] + rec["NPA"] - pay["NPA"] - pay["GCF"]
        nl_fin = pay[FIN].sum() - rec[FIN].sum()
        disc = pay["DISC"] - rec["DISC"]
        rows.append({
            "sector": s,
            "disposable_income": np.nan if s == "ROW" else saving + cons,
            "saving": saving,
            "net_lending_real": nl_real,
            "net_lending_financial": nl_fin,
            "paid_to_discrepancy": disc,
            "identity_error": nl_real - nl_fin - disc,
        })
    return pd.DataFrame(rows).set_index("sector")


def official_totals(res, sec):
    sam, io, fof, fa = res["sam"], res["io"], res["fof"], res["fa"]
    acts = [f"P-{c}" for c in io["sections"]]
    coms = [f"C-{c}" for c in io["sections"]]
    groups = GROUPS
    va = sam.loc[["LAB", "CAP", "GOV"], acts].to_numpy().sum()
    rows = [
        ("GDP, income approach", va, io["labor"].sum() + io["tax"].sum() + io["capital"].sum(), "IO 2023"),
        ("GDP, income approach", va, fof.table.loc["二、增加值", [(s, "src") for s in ["NFC", "FC", "GOV", "HH"]]].sum(), "NBS FoF 2023"),
        ("Household final consumption", sam.loc[coms, groups].to_numpy().sum(), io["hh"].sum(), "IO 2023"),
        ("Household final consumption", sam.loc[coms, groups].to_numpy().sum(),
         fof.get("十一、实际最终消费", "HH", "use") - fof.get("九、实物社会转移", "HH", "src"), "NBS FoF 2023"),
        ("Government final consumption", sam.loc[coms, "GOV"].sum(), io["gov"].sum(), "IO 2023"),
        ("Government final consumption", sam.loc[coms, "GOV"].sum(),
         fof.get("十一、实际最终消费", "GOV", "use") + fof.get("九、实物社会转移", "GOV", "use"), "NBS FoF 2023"),
        ("Gross capital formation", sam.loc[coms, "GCF"].sum(), io["gcf"].sum(), "IO 2023"),
        ("Gross capital formation", sam.loc["GCF", ["NFC", "FC", "GOV"] + groups].sum(),
         sum(fof.get("十四、资本形成总额", s, "use") for s in ["NFC", "FC", "GOV", "HH"]), "NBS FoF 2023"),
        ("Exports", sam.loc[coms, "ROW"].sum(), io["exp"].sum(), "IO 2023"),
        ("Imports", sam.loc["ROW", coms].sum(), io["imp"].sum(), "IO 2023"),
        ("Net exports", sam.loc[coms, "ROW"].sum() - sam.loc["ROW", coms].sum(), -fof.get("一、净出口", "ROW", "src"), "NBS FoF 2023"),
        ("Compensation of employees received by households", sam.loc[groups, "LAB"].sum(), fof.get("三、劳动者报酬", "HH", "src"), "NBS FoF 2023"),
        ("Property income, total paid", sam.loc["PINC"].sum(),
         sum(fof.get("五、财产收入", s, "use") for s in ["NFC", "FC", "GOV", "HH", "ROW"]), "NBS FoF 2023"),
    ]
    for s in ["NFC", "FC", "GOV", "HH"]:
        rows.append((f"Disposable income, {s}", sec.loc[s, "disposable_income"], fof.get("八、可支配总收入", s, "src"), "NBS FoF 2023"))
        rows.append((f"Gross saving, {s}", sec.loc[s, "saving"], fof.get("十二、总储蓄", s, "src"), "NBS FoF 2023"))
    for s in ["NFC", "FC", "GOV", "HH", "ROW"]:
        rows.append((f"Net lending (real side), {s}", sec.loc[s, "net_lending_real"], fof.get("十六、净金融投资", s, "use"), "NBS FoF 2023"))
        rows.append((f"Net financial investment, {s}", sec.loc[s, "net_lending_financial"],
                     float(fa.table.loc["净金融投资", (s, "use")]), "PBC FA 2023"))
    for code in FIN:
        rows.append((f"Instrument {code}, total acquisitions", sam.loc[code].sum(),
                     fa.instrument(code, "TOTAL", "use"), "PBC FA 2023"))
    out = pd.DataFrame(rows, columns=["indicator", "sam", "official", "source"])
    out["difference"] = out["sam"] - out["official"]
    out["relative_difference"] = out["difference"] / out["official"].abs()
    return out


def discrepancy(res, sec):
    """每个与 DISC 有往来的账户：SAM 中付给 DISC 的净额，分为 投入产出 vs 资金流量表、实物 vs 金融、尾数。"""
    sam, fof, fa = res["sam"], res["fof"], res["fa"]
    agg = aggregate_households(sam)
    rows = []
    for s in ["NFC", "FC", "GOV", "HH", "ROW"]:
        fof_nl = fof.get("十六、净金融投资", s, "use")
        rows.append({
            "account": s,
            "paid_to_DISC": sec.loc[s, "paid_to_discrepancy"],
            "IO_vs_FoF": sec.loc[s, "net_lending_real"] - fof_nl,
            "FoF_real_vs_PBC_financial": fof_nl - fa.net_lending(s),
            "rounding": 0.0,
        })
    for a in agg.index:
        if a in ("NFC", "FC", "GOV", "HH", "ROW", "DISC"):
            continue
        net = agg.loc["DISC", a] - agg.loc[a, "DISC"]
        if abs(net) < 1e-6:
            continue
        big = a in ("CAP", "GCF", "LAB")
        rows.append({
            "account": a,
            "paid_to_DISC": net,
            "IO_vs_FoF": net if big else 0.0,
            "FoF_real_vs_PBC_financial": 0.0,
            "rounding": 0.0 if big else net,
        })
    out = pd.DataFrame(rows).set_index("account")
    out["rounding"] += out["paid_to_DISC"] - out[["IO_vs_FoF", "FoF_real_vs_PBC_financial", "rounding"]].sum(axis=1)
    out.loc["TOTAL"] = out.sum()
    out["share_of_total_flows"] = out["paid_to_DISC"].abs() / sam.to_numpy().sum()
    return out


def households(res):
    x, hh = res["household_items"], res["households"]
    groups = pd.read_excel(paths.CFPS_DECILES, sheet_name=f"{res['settings']['cfps_version']}_groups", index_col=0)
    out = pd.DataFrame(index=GROUPS)
    out["population_share"] = groups["population_share"]
    out["household_share"] = groups["household_share"]
    out["disposable_income"] = hh["disposable_income"]
    out["disposable_share"] = hh["disposable_income"] / hh["disposable_income"].sum()
    out["consumption_share"] = x.loc["CON"] / x.loc["CON"].sum()
    out["saving_rate"] = hh["saving_rate"]
    out["per_capita_relative_to_mean"] = out["disposable_share"] / out["population_share"]
    out["per_capita_yuan"] = out["per_capita_relative_to_mean"] * hh["disposable_income"].sum() * 1e8 / POPULATION_2023
    return out


def gini(pop, income):
    order = np.argsort(income / pop)
    p, y = pop[order] / pop.sum(), income[order] / income.sum()
    cum = np.concatenate([[0.0], np.cumsum(y)])
    return 1.0 - float(np.sum(p * (cum[1:] + cum[:-1])))


def quintiles(hh_table):
    q = np.repeat(np.arange(1, 6), 2)
    grp = hh_table.groupby(q)[["population_share", "household_share", "disposable_share"]].sum()
    grp.index = [f"Q{i}" for i in grp.index]
    grp["sam_relative_to_mean"] = grp["disposable_share"] / grp["population_share"]
    grp["nbs_per_capita_yuan"] = NBS_QUINTILES
    grp["nbs_relative_to_mean"] = np.array(NBS_QUINTILES) / NBS_MEAN
    grp["ratio_sam_to_nbs"] = grp["sam_relative_to_mean"] / grp["nbs_relative_to_mean"]
    return grp


def balancing(res):
    x, prior = res["household_items"], res["prior"]
    post = x.div(x.sum(axis=1), axis=0)
    rows = []
    for item in ITEMS:
        d = post.loc[item] - prior.loc[item]
        rows.append({
            "item": item,
            "national_total": x.loc[item].sum(),
            "max_abs_share_change": d.abs().max(),
            "group_with_max_change": d.abs().idxmax(),
            "cross_entropy": float(np.sum(post.loc[item] * np.log(post.loc[item] / prior.loc[item]))),
        })
    return pd.DataFrame(rows).set_index("item")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = build()
    sam = res["sam"]
    coms = [f"C-{c}" for c in res["io"]["sections"]]

    bal = pd.DataFrame({"row_total": sam.sum(axis=1), "col_total": sam.sum(axis=0)})
    bal["gap"] = bal["row_total"] - bal["col_total"]
    bal.to_csv(OUT / "balance.csv", encoding="utf-8-sig")
    neg = sam.stack()
    neg = neg[neg < 0].rename("value").reset_index()
    neg.columns = ["row_receiver", "col_payer", "value"]
    neg.to_csv(OUT / "negative_cells.csv", index=False, encoding="utf-8-sig")

    sec = sector_accounts(sam, coms)
    sec.to_csv(OUT / "sector_accounts.csv", encoding="utf-8-sig")
    tot = official_totals(res, sec)
    tot.to_csv(OUT / "official_totals.csv", index=False, encoding="utf-8-sig")
    disc = discrepancy(res, sec)
    disc.to_csv(OUT / "discrepancy.csv", encoding="utf-8-sig")
    hh = households(res)
    hh.to_csv(OUT / "households.csv", encoding="utf-8-sig")
    qt = quintiles(hh)
    qt.to_csv(OUT / "quintiles_vs_nbs.csv", encoding="utf-8-sig")
    bl = balancing(res)
    bl.to_csv(OUT / "balancing.csv", encoding="utf-8-sig")

    again = build()["sam"]
    files = ["SAM4_2023.csv", "SAM4_2023_long.csv", "SAM4_2023_accounts.csv", "SAM4_2023_aggregate_households.csv"]
    rep = pd.DataFrame(
        [{"check": "max abs difference between two runs", "value": float((again - sam).abs().to_numpy().max())}]
        + [{"check": f"sha256 {f}", "value": sha256(paths.OUTPUT / f)} for f in files if (paths.OUTPUT / f).exists()]
    )
    rep.to_csv(OUT / "reproducibility.csv", index=False, encoding="utf-8-sig")

    g = gini(hh["population_share"].to_numpy(), hh["disposable_income"].to_numpy())
    summary = [
        f"accounts: {len(sam)}; non-zero cells: {int((sam != 0).to_numpy().sum())}; negative cells: {len(neg)}",
        f"max |row - column|: {bal['gap'].abs().max():.2e}",
        f"identity error (real NL - financial NL - discrepancy), max: {sec['identity_error'].abs().max():.2e}",
        f"total flows: {sam.to_numpy().sum():,.1f}; DISC row total: {sam.loc['DISC'].sum():,.1f} "
        f"({sam.loc['DISC'].sum() / sam.to_numpy().sum():.4%} of total flows)",
        f"max |relative difference| vs IO totals: {tot.loc[tot['source'] == 'IO 2023', 'relative_difference'].abs().max():.2e}",
        f"between-decile Gini of per-capita disposable income: {g:.3f} (NBS household survey 2023: {NBS_GINI})",
        f"Q5/Q1 per-capita disposable income: SAM {qt['sam_relative_to_mean'].iloc[-1] / qt['sam_relative_to_mean'].iloc[0]:.2f}, "
        f"NBS {NBS_QUINTILES[-1] / NBS_QUINTILES[0]:.2f}",
        f"national-accounts per-capita disposable income: {hh['disposable_income'].sum() * 1e8 / POPULATION_2023:,.0f} yuan "
        f"(survey mean {NBS_MEAN:,})",
        f"two-run max difference: {rep['value'].iloc[0]}",
    ]
    (OUT / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    print()
    print(sec.round(1).to_string())
    print()
    print(disc.round(1).to_string())
    print()
    print(qt.round(3).to_string())
    print()
    print(tot[["indicator", "sam", "official", "source", "difference"]].round(1).to_string())


if __name__ == "__main__":
    main()
