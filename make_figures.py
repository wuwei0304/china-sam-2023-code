# -*- coding: utf-8 -*-
"""
论文插图，输出到 figures/。先运行 build_sam4.py、validate_sam4.py、sensitivity.py。

Fig1 数据与处理流程
Fig2 宏观 SAM（按账户块加总，万亿元）
Fig3 统计误差分解（按账户）
Fig4 住户十等分组：人均可支配收入与统计局五等分对照；储蓄率敏感性

所有图同一字体、同一字号（期刊要求）。Fig1–3 不含 CFPS 信息，Fig4 含十等分组结果。
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import FuncFormatter

import paths

FONT = 7
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": FONT,
    "axes.titlesize": FONT + 1,
    "legend.fontsize": FONT,
    "axes.spines.top": False,
    "axes.spines.right": False,
})
VAL = paths.OUTPUT / "validation"
SEN = paths.OUTPUT / "sensitivity"
GROUPS = [f"H-{i}" for i in range(1, 11)]
THOUSANDS = FuncFormatter(lambda v, _: f"{v:,.0f}".replace("-", "\u2212"))
SCENARIOS = [
    ("base", "Base (floor \u221225%)", "k", "-"),
    ("floor_-10", "Floor \u221210%", "#4c78a8", "--"),
    ("floor_-50", "Floor \u221250%", "#e45756", "--"),
    ("person_deciles", "Person-weighted deciles", "#54a24b", ":"),
]


def panel(ax, letter):
    ax.set_title(letter, loc="left", fontweight="bold")


def box(ax, xy, w, h, text, color):
    ax.add_patch(FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.01,rounding_size=0.015",
                                fc=color, ec="0.3", lw=0.8))
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center")


def arrow(ax, a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9, lw=0.8, color="0.25"))


def fig1():
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    src = "#dbe9f6"
    step = "#fdf2d0"
    out = "#d9f0d3"
    sources = [
        (0.01, "Input-output table 2023\n211 products\n(NBS)"),
        (0.26, "Flow of funds 2023\nnon-financial\n(NBS)"),
        (0.51, "Flow of funds 2023\nfinancial accounts\n(PBC)"),
        (0.76, "CFPS 2022\nfamily economics\n(ISSS, PKU)"),
    ]
    for x, t in sources:
        box(ax, (x, 0.82), 0.23, 0.15, t, src)
    steps = [
        (0.01, "211 products to\n19 sections\n(0/1 concordance)"),
        (0.26, "Sector income\ndistribution and\ncapital accounts"),
        (0.51, "18 instruments\ngrouped into 7\nby sector"),
        (0.76, "Weighted income\ndeciles; 8-category\nconsumption bridge"),
    ]
    for x, t in steps:
        box(ax, (x, 0.56), 0.23, 0.17, t, step)
        arrow(ax, (x + 0.115, 0.82), (x + 0.115, 0.73))
    box(ax, (0.51, 0.31), 0.48, 0.17,
        "Household block\n"
        "cross-entropy on group shares of 8 items,\n"
        "national totals fixed, saving rate \u2265 floor;\n"
        "RAS for consumption; deposits residual", step)
    box(ax, (0.01, 0.31), 0.44, 0.17,
        "Assemble the matrix\n"
        "each account's row\u2013column gap\n"
        "posted to one discrepancy account", step)
    arrow(ax, (0.115, 0.56), (0.17, 0.48))
    arrow(ax, (0.375, 0.56), (0.30, 0.48))
    arrow(ax, (0.375, 0.56), (0.62, 0.48))
    arrow(ax, (0.625, 0.56), (0.40, 0.48))
    arrow(ax, (0.625, 0.56), (0.70, 0.48))
    arrow(ax, (0.875, 0.56), (0.85, 0.48))
    arrow(ax, (0.51, 0.395), (0.45, 0.395))
    box(ax, (0.08, 0.05), 0.64, 0.17,
        "Social accounting matrix 2023, 67 accounts\n"
        "19 activities, 19 commodities, 2 factors, 10 household deciles,\n"
        "4 institutions, 4 distribution accounts, capital formation,\n"
        "7 financial instruments, statistical discrepancy", out)
    arrow(ax, (0.23, 0.31), (0.30, 0.22))
    box(ax, (0.78, 0.05), 0.21, 0.17, "Validation and\nsensitivity\ntables", out)
    arrow(ax, (0.72, 0.135), (0.78, 0.135))
    fig.savefig(paths.FIGURES / "fig1_workflow.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


BLOCKS = [
    ("Activities", "activity"),
    ("Commodities", "commodity"),
    ("Labour", ["LAB"]),
    ("Capital", ["CAP"]),
    ("Households", "household"),
    ("Non-financial corporations", ["NFC"]),
    ("Financial corporations", ["FC"]),
    ("Government", ["GOV"]),
    ("Rest of the world", ["ROW"]),
    ("Distribution", "distribution"),
    ("Capital formation", ["GCF"]),
    ("Financial instruments", "financial"),
    ("Discrepancy", ["DISC"]),
]


def macro_sam():
    sam = pd.read_csv(paths.OUTPUT / "SAM4_2023.csv", index_col=0)
    acc = pd.read_csv(paths.OUTPUT / "SAM4_2023_accounts.csv")
    members = {}
    for name, rule in BLOCKS:
        members[name] = acc.loc[acc["type"] == rule, "code"].tolist() if isinstance(rule, str) else rule
    names = [b for b, _ in BLOCKS]
    out = pd.DataFrame(0.0, index=names, columns=names)
    for r in names:
        for c in names:
            out.loc[r, c] = sam.loc[members[r], members[c]].to_numpy().sum()
    return out / 1e4  # 万亿元


def fig2():
    m = macro_sam()
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    data = m.abs().replace(0, np.nan)
    im = ax.imshow(data, cmap="Blues", norm=LogNorm(vmin=0.05, vmax=data.max().max()))
    for i in range(len(m)):
        for j in range(len(m)):
            v = m.iloc[i, j]
            if abs(v) >= 0.05:
                ax.text(j, i, f"{v:.1f}".replace("-", "\u2212"), ha="center", va="center",
                        color="white" if abs(v) > 30 else "black")
    ax.set_xticks(range(len(m)), m.columns, rotation=60, ha="right")
    ax.set_yticks(range(len(m)), m.index)
    ax.set_xlabel("Paying account (column)")
    ax.set_ylabel("Receiving account (row)")
    ax.spines[:].set_visible(True)
    cb = fig.colorbar(im, ax=ax, shrink=0.75)
    cb.set_label("Absolute value of flow (trillion yuan, log scale)")
    fig.savefig(paths.FIGURES / "fig2_macro_sam.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    m.round(3).to_csv(paths.OUTPUT / "macro_sam_trillion_yuan.csv", encoding="utf-8-sig")


DISC_LABELS = {
    "NFC": "Non-financial corporations",
    "FC": "Financial corporations",
    "GOV": "Government",
    "HH": "Households",
    "ROW": "Rest of the world",
    "CAP": "Capital (operating surplus)",
    "GCF": "Gross capital formation",
}


def fig3():
    disc = pd.read_csv(VAL / "discrepancy.csv", index_col=0).drop(index="TOTAL")
    # 只有尾数差（每个账户不超过 2）的账户画不出来，图注里说明
    disc = disc.loc[(disc["IO_vs_FoF"].abs() >= 0.5) | (disc["FoF_real_vs_PBC_financial"].abs() >= 0.5)]
    disc.index = [DISC_LABELS.get(a, a) for a in disc.index]
    fig, ax = plt.subplots(figsize=(4.8, 2.8))
    y = np.arange(len(disc))
    left_pos = np.zeros(len(disc))
    left_neg = np.zeros(len(disc))
    parts = [("IO_vs_FoF", "Input-output table vs flow of funds", "#4c78a8"),
             ("FoF_real_vs_PBC_financial", "Non-financial vs financial accounts", "#f58518")]
    for col, lab, c in parts:
        v = disc[col].to_numpy()
        start = np.where(v >= 0, left_pos, left_neg)
        ax.barh(y, v, left=start, color=c, label=lab, height=0.7)
        left_pos += np.where(v >= 0, v, 0)
        left_neg += np.where(v < 0, v, 0)
    ax.set_yticks(y, disc.index)
    ax.invert_yaxis()
    ax.axvline(0, color="0.3", lw=0.6)
    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.set_xlabel("Paid to the discrepancy account (100 million yuan)")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    fig.savefig(paths.FIGURES / "fig3_discrepancy.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig4():
    hh = pd.read_csv(VAL / "households.csv", index_col=0)
    qt = pd.read_csv(VAL / "quintiles_vs_nbs.csv", index_col=0)
    rates = pd.read_csv(SEN / "saving_rates.csv", index_col=0)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    x = np.arange(1, 11)
    q = np.arange(1.5, 10.6, 2)

    ax = axes[0]
    ax.bar(x, hh["per_capita_relative_to_mean"], color="#9ecae1", label="Matrix, deciles")
    ax.plot(q, qt["sam_relative_to_mean"], "o", color="#08519c", mfc="white", label="Matrix, quintiles")
    ax.plot(q, qt["nbs_relative_to_mean"], "s", color="#e45756", label="NBS survey, quintiles")
    ax.set_xticks(x, [str(i) for i in x])
    ax.set_xlabel("Income decile (1 = lowest)")
    ax.set_ylabel("Per-capita disposable income / national mean")
    ax.legend(frameon=False, loc="upper left")
    panel(ax, "a")

    ax = axes[1]
    for name, label, c, ls in SCENARIOS:
        ax.plot(x, rates[name], color=c, ls=ls, marker="o", ms=2.5, lw=1, label=label)
    ax.axhline(0, color="0.6", lw=0.6)
    ax.set_xticks(x, [str(i) for i in x])
    ax.set_xlabel("Income decile (1 = lowest)")
    ax.set_ylabel("Saving / disposable income")
    ax.legend(frameon=False, loc="upper left")
    panel(ax, "b")
    fig.tight_layout()
    fig.savefig(paths.FIGURES / "fig4_households.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    paths.ensure_dirs()
    fig1()
    fig2()
    fig3()
    fig4()
    print("figures written to", paths.FIGURES)


if __name__ == "__main__":
    main()
