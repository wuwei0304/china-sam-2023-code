# -*- coding: utf-8 -*-
"""
由 CFPS2022 家庭经济表生成十等分组汇总。只写出组均值和组份额，不写出任何家庭记录。

数据：cfps2022famecon_202410.dta（2024年10月发布）
排序：H-1 = 最低收入组，H-10 = 最高收入组

两个版本：
  v1  论文建议版。按家庭人均纯收入 fincome1_per 排序，用横截面权数 fswt_natcs22n
      做加权十等分。份额 = 各组加权合计 / 全部加权合计。
  v2  敏感性版。排序变量同 v1，但分组权数为 户权数 × 家庭人口，各组人口约各占 10%。
      组内合计仍按户权数加总。
  v0  对照版。按家庭纯收入 fincome1 排序，户数尽量均等，不加权。
      这是现有 SAM4（data/CFPS/CFPS2022.xlsx）最接近的算法。

国家统计局五等分按户分组（各组户数相等），五组人均收入的简单平均高于全国人均，
与"低收入户人口多"一致，所以 v1 与官方口径对应。

缺失：构造变量里的缺失已经是空值。净资产可以为负，保留。
某一变量在组内的均值只对非缺失户计算。
"""
import numpy as np
import pandas as pd

import paths

OLD = paths.HERE.parent / "sam" / "data" / "CFPS" / "CFPS2022.xlsx"
OUT = paths.CFPS_DECILES

VARS = [
    ("fincome1", "全部家庭纯收入"),
    ("fwage_1", "工资性收入"),
    ("foperate_1", "经营性收入"),
    ("fproperty_1", "财产性收入"),
    ("felse_1", "其他收入"),
    ("ftransfer_1", "转移性收入"),
    ("house", "居住支出"),
    ("trco", "交通通讯支出"),
    ("other", "其他消费性支出"),
    ("eec", "文教娱乐支出"),
    ("dress", "衣着鞋帽支出"),
    ("med", "医疗保健支出"),
    ("food", "食品支出"),
    ("daily", "家庭设备及日用品支出"),
    ("pce", "居民消费性支出-加总"),
    ("eptran", "转移性支出"),
    ("epwelf", "福利性支出"),
    ("mortage", "房贷支出"),
    ("expense", "家庭总支出"),
    ("total_asset", "家庭净资产"),
]
CODES = [c for c, _ in VARS]
LABEL = dict(VARS)
GROUPS = [f"H-{i}" for i in range(1, 11)]


def load():
    cols = CODES + ["fincome1_per", "fswt_natcs22n", "familysize22"]
    df = pd.read_stata(paths.cfps_dta(), columns=cols, convert_categoricals=False)
    return df


def weighted_decile(value, weight):
    """按 value 从低到高，使各组权数之和约为总权数的 10%。返回 1..10，1 为最低。"""
    out = pd.Series(np.nan, index=value.index)
    ok = value.notna() & weight.notna() & (weight > 0)
    v = value[ok].to_numpy()
    w = weight[ok].to_numpy()
    order = np.argsort(v, kind="mergesort")
    share = np.cumsum(w[order]) / w.sum()
    group = np.minimum((share * 10).astype(int) + 1, 10)
    # 累计份额恰好为 0.1、0.2… 时，边界户会被划进下一组；份额为 1 的最后一户留在第 10 组
    group = np.where(share >= 1, 10, group)
    out.iloc[np.flatnonzero(ok.to_numpy())[order]] = group
    return out


def equal_count_decile(value):
    rank = value.rank(method="first")
    return pd.qcut(rank, 10, labels=False) + 1


def aggregate(df, group, weight=None):
    """行是 H-1..H-10。均值、加权合计、非缺失户数。"""
    means, totals, counts = [], [], []
    for g in range(1, 11):
        part = df.loc[group == g, CODES]
        if weight is None:
            ww = pd.Series(1.0, index=part.index)
        else:
            ww = weight.loc[part.index]
        wsum = part.mul(ww, axis=0).sum(min_count=1)
        wden = pd.DataFrame({c: ww.where(part[c].notna()) for c in CODES}).sum()
        means.append(wsum / wden.replace(0, np.nan))
        totals.append(wsum)
        counts.append(part.notna().sum())
    mean_df = pd.DataFrame(means, index=GROUPS)
    total_df = pd.DataFrame(totals, index=GROUPS)
    count_df = pd.DataFrame(counts, index=GROUPS)
    mean_df.columns = [LABEL[c] for c in CODES]
    total_df.columns = mean_df.columns
    count_df.columns = mean_df.columns
    share = total_df / total_df.sum()
    return mean_df, total_df, share, count_df


def group_sizes(df, group, weight):
    """各组户数份额、人口份额、样本户数、户均人口。"""
    persons = weight * df["familysize22"]
    rows = []
    for g in range(1, 11):
        m = group == g
        rows.append(
            {
                "household_share": weight[m].sum() / weight[group.notna()].sum(),
                "population_share": persons[m].sum() / persons[group.notna()].sum(),
                "n_sample": int(m.sum()),
                "mean_size": persons[m].sum() / weight[m].sum(),
            }
        )
    return pd.DataFrame(rows, index=GROUPS)


def main():
    df = load()
    wt = df["fswt_natcs22n"]
    g_v1 = weighted_decile(df["fincome1_per"], wt)
    g_v2 = weighted_decile(df["fincome1_per"], wt * df["familysize22"])
    g_v0 = equal_count_decile(df["fincome1"])
    m1, t1, s1, n1 = aggregate(df, g_v1, wt)
    m2, t2, s2, n2 = aggregate(df, g_v2, wt)
    m0, t0, s0, n0 = aggregate(df, g_v0, None)
    z1 = group_sizes(df, g_v1, wt)
    z2 = group_sizes(df, g_v2, wt)

    # 旧版 SAM4 的十分组表只在作者本机存在，用于说明 v0 与旧表一致
    old = rel = None
    if OLD.exists():
        old = pd.read_excel(OLD, index_col=0)
        old = old.loc[::-1]
        old.index = GROUPS
        old = old[[LABEL[c] for c in CODES]]
        rel = (m0 - old) / old.replace(0, np.nan)

    notes = pd.DataFrame(
        [
            ["source_file", paths.cfps_dta().name],
            ["households", str(len(df))],
            ["v1_rule", "deciles of fincome1_per, weight fswt_natcs22n, H-1 lowest"],
            ["v2_rule", "deciles of fincome1_per, weight fswt_natcs22n*familysize22 (equal persons), totals by household weight"],
            ["v0_rule", "deciles of fincome1, equal household counts, unweighted, H-1 lowest"],
            ["group_order", "H-1 lowest income, H-10 highest income"],
            ["income_year", "CFPS2022 interview asks for income over the past 12 months"],
            ["v0_vs_old_median_abs_rel", "" if rel is None else f"{rel.abs().stack().median():.4f}"],
            ["do_not_publish", "aggregated table only; do not deposit until ISSS confirms"],
        ],
        columns=["item", "value"],
    )

    paths.ensure_dirs()
    with pd.ExcelWriter(OUT) as w:
        notes.to_excel(w, sheet_name="notes", index=False)
        m1.to_excel(w, sheet_name="v1_weighted_mean")
        s1.to_excel(w, sheet_name="v1_share")
        z1.to_excel(w, sheet_name="v1_groups")
        n1.to_excel(w, sheet_name="v1_n_nonmissing")
        m2.to_excel(w, sheet_name="v2_weighted_mean")
        s2.to_excel(w, sheet_name="v2_share")
        z2.to_excel(w, sheet_name="v2_groups")
        m0.to_excel(w, sheet_name="v0_unweighted_mean")
        s0.to_excel(w, sheet_name="v0_share")
        if rel is not None:
            old.to_excel(w, sheet_name="old_reordered_H1lowest")
            rel.to_excel(w, sheet_name="v0_vs_old_rel")

    print(f"wrote {OUT}")
    print("v1 income share H-1..H-10", s1["全部家庭纯收入"].round(3).tolist())
    print("v1 bottom/top 20% income", round(s1['全部家庭纯收入'].iloc[:2].sum(), 3), round(s1['全部家庭纯收入'].iloc[-2:].sum(), 3))
    print("v1 population share", z1["population_share"].round(3).tolist())
    print("v2 income share H-1..H-10", s2["全部家庭纯收入"].round(3).tolist())
    print("v2 household share", z2["household_share"].round(3).tolist())
    if rel is not None:
        print("v0 vs old median abs rel", round(rel.abs().stack().median(), 4))


if __name__ == "__main__":
    main()
