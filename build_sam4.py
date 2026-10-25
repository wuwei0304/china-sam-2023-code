# -*- coding: utf-8 -*-
"""
2023 年中国社会核算矩阵 SAM4：67 个账户，单位亿元，行是收入、列是支出，H-1 为最低收入组。

数据层次
  生产、商品、最终使用、进出口    2023 年投入产出表（211 产品按门类加总为 19 个活动、19 个商品）
  收入分配和资本账户的部门合计    国家统计局 2023 年资金流量表（非金融交易）
  金融工具的部门合计              中国人民银行 2023 年资金流量表（金融账户），归并为 7 类工具
  住户十等分组的结构              CFPS2022（build_cfps_deciles.py），消费按 build_consumption_bridge.py

住户组
  劳动报酬、经营盈余、财产收入（收）、财产收入（付）、经常转移（收）、所得税和社保缴款、
  其他经常转移（付）、消费这 8 项，以 CFPS 组间份额为先验，用最小交叉熵联立调整：
  每项全国合计等于官方数，各组储蓄率（储蓄 / 可支配收入）不低于 SAVING_FLOOR。
  消费总额调整后，门类 × 组的消费矩阵用 RAS 调整列，行合计仍等于投入产出表。
  资本形成、土地等非生产资产、金融工具按固定的分摊键分到组，存款是每组的余项。

统计差异（DISC）
  只有三类来源：投入产出表与资金流量表（实物）的口径差；资金流量表（实物）与人民银行（金融）的
  部门净贷出差；官方表的尾数。每个账户与 DISC 之间只有一个数，validate_sam4.py 给出分解。
"""
import re

import numpy as np
import pandas as pd
from scipy.optimize import minimize

import io2023
import paths
from build_consumption_bridge import GROUPS
from build_consumption_bridge import build as build_bridge

SAVING_FLOOR = -0.25

FOF_SECTORS = {"NFC": (1, 2), "FC": (3, 4), "GOV": (5, 6), "HH": (7, 8), "ROW": (11, 12)}
PBC_SECTORS = {"HH": 3, "NFC": 5, "GOV": 7, "FC": 9, "ROW": 13, "TOTAL": 15}
DOMESTIC = ["NFC", "FC", "GOV", "HH"]

INSTRUMENTS = {
    "F-CUR": ["通货"],
    "F-DEP": ["存款"],
    "F-LOAN": ["贷款", "未贴现的银行承兑汇票"],
    "F-INS": ["保险准备金"],
    "F-BOND": ["债券"],
    "F-EQ": ["股票", "证券投资基金份额"],
    "F-OTH": [
        "证券公司客户保证金", "金融机构往来", "存款准备金", "库存现金", "中央银行贷款",
        "其他（净）", "直接投资", "其他对外债权债务", "国际储备资产", "国际收支误差与遗漏",
    ],
}
INSTRUMENT_EN = {
    "通货": "Currency",
    "存款": "Deposits",
    "贷款": "Loans",
    "未贴现的银行承兑汇票": "Undiscounted bankers' acceptances",
    "保险准备金": "Insurance technical reserves",
    "债券": "Bonds",
    "股票": "Shares",
    "证券投资基金份额": "Investment fund shares",
    "证券公司客户保证金": "Customer margins at securities companies",
    "金融机构往来": "Inter-financial-institution accounts",
    "存款准备金": "Required reserves",
    "库存现金": "Cash in vault",
    "中央银行贷款": "Central bank loans",
    "其他（净）": "Miscellaneous (net)",
    "直接投资": "Direct investment",
    "其他对外债权债务": "Other foreign claims and debts",
    "国际储备资产": "International reserve assets",
    "国际收支误差与遗漏": "Errors and omissions in the balance of payments",
}

# 住户联立配平的 8 项。SIGN 是对可支配收入的贡献，消费单列。
ITEMS = ["LAB", "OS", "PIR", "PIP", "TRR", "TAX", "TRP", "CON"]
SIGN = np.array([1, 1, 1, -1, 1, -1, -1, 0], dtype=float)
PRIOR_VAR = {
    "LAB": "工资性收入",
    "OS": "经营性收入",
    "PIR": "财产性收入",
    "PIP": "房贷支出",
    "TRR": "转移性收入",
    "TAX": "工资性收入",
    "TRP": "转移性支出",
}


def _norm(text):
    return re.sub(r"\s+", "", str(text).replace("\u3000", "")).replace("（", "(").replace("）", ")")


def _num(value):
    value = pd.to_numeric(value, errors="coerce")
    return 0.0 if pd.isna(value) else float(value)


# ---------------------------------------------------------------- 官方表


class FlowOfFunds:
    """国家统计局资金流量表（非金融交易）。get(项目, 部门, 'use'|'src')。"""

    def __init__(self):
        raw = pd.read_excel(paths.fof_file(), header=None)
        body = raw.iloc[8:]
        keys = [_norm(x) for x in body.iloc[:, 0]]
        if len(set(keys)) != len(keys):
            raise RuntimeError("资金流量表项目名称有重复")
        self.table = pd.DataFrame(
            {(s, side): [_num(v) for v in body.iloc[:, j]]
             for s, (u, c) in FOF_SECTORS.items() for side, j in (("use", u), ("src", c))},
            index=keys,
        )

    def get(self, item, sector, side):
        return float(self.table.loc[_norm(item), (sector, side)])


class FinancialAccounts:
    """人民银行资金流量表（金融账户）。运用 = 获得金融资产，来源 = 发生负债，均为当年净流量。"""

    def __init__(self):
        raw = pd.read_excel(paths.pbc_file(), header=None)
        rows, top = {}, {}
        for i in range(9, len(raw)):
            text = raw.iloc[i, 0]
            if not isinstance(text, str) or not text.strip():
                continue
            key = re.match(r"[^A-Za-z]+", text.strip()).group(0).strip()
            rows[key] = {(s, side): _num(raw.iloc[i, j + k])
                         for s, j in PBC_SECTORS.items() for side, k in (("use", 0), ("src", 1))}
            top[key] = not text[0].isspace()
        self.table = pd.DataFrame(rows).T
        self.top = pd.Series(top)
        items = [k for k in self.table.index
                 if self.top[k] and k not in ("净金融投资", "资金运用合计", "资金来源合计")]
        mapped = [x for names in INSTRUMENTS.values() for x in names]
        if sorted(items) != sorted(mapped):
            raise RuntimeError(f"金融工具归类不完整: {set(items) ^ set(mapped)}")

    def item(self, key, sector, side):
        return float(self.table.loc[key, (sector, side)])

    def instrument(self, code, sector, side):
        return sum(self.item(k, sector, side) for k in INSTRUMENTS[code])

    def net_lending(self, sector):
        """按工具加总的 运用 − 来源。与表头"净金融投资"可差 1–2 个尾数。"""
        return sum(self.instrument(c, sector, "use") - self.instrument(c, sector, "src") for c in INSTRUMENTS)


# ---------------------------------------------------------------- 住户


def household_priors(version, bridge_matrix):
    share = pd.read_excel(paths.CFPS_DECILES, sheet_name=f"{version}_share", index_col=0).loc[GROUPS]
    prior = pd.DataFrame({k: share[v] for k, v in PRIOR_VAR.items()}).T
    prior.loc["CON"] = bridge_matrix.sum(axis=0) / bridge_matrix.to_numpy().sum()
    prior = prior.clip(lower=1e-6)
    prior = prior.div(prior.sum(axis=1), axis=0)
    keys = pd.DataFrame({"mortgage": share["房贷支出"] / share["房贷支出"].sum()})
    return prior.loc[ITEMS], keys


def balance_households(totals, prior, floor):
    """最小交叉熵：min Σ_i Σ_h s ln(s/q)，s 为第 i 项在各组的份额。返回各组金额和目标值。"""
    k, n = len(ITEMS), len(GROUPS)
    q = prior.to_numpy()
    t = totals.reindex(ITEMS).to_numpy()
    con = ITEMS.index("CON")
    scale = float((SIGN * t).sum())

    eq_jac = np.kron(np.eye(k), np.ones(n))
    cons = [{"type": "eq", "fun": lambda x: eq_jac @ x - 1.0, "jac": lambda x: eq_jac}]
    g = None
    if floor is not None:
        # (1 − floor) × 可支配收入 − 消费 ≥ 0，按全国可支配收入缩放
        g = np.zeros((n, k * n))
        for i in range(k):
            for h in range(n):
                g[h, i * n + h] = (-t[i] if i == con else (1 - floor) * SIGN[i] * t[i]) / scale
        cons.append({"type": "ineq", "fun": lambda x: g @ x, "jac": lambda x: g})

    x0 = q.ravel()
    if g is None or (g @ x0 >= 0).all():
        s, value = q, 0.0
    else:
        res = minimize(
            lambda x: float(np.sum(x * np.log(x / x0))),
            x0,
            jac=lambda x: np.log(x / x0) + 1.0,
            method="SLSQP",
            bounds=[(1e-10, 1.0)] * (k * n),
            constraints=cons,
            options={"maxiter": 2000, "ftol": 1e-15},
        )
        if not res.success:
            raise RuntimeError(f"住户联立配平没有收敛: {res.message}")
        s, value = res.x.reshape(k, n), float(res.fun)
    x = pd.DataFrame(s * t[:, None], index=ITEMS, columns=GROUPS)
    return x, value


def ras(prior, row_target, col_target, tol=1e-9, max_iter=1000):
    a = prior.to_numpy(dtype=float).clip(min=0)
    rt = row_target.to_numpy(dtype=float)
    ct = col_target.to_numpy(dtype=float)
    for _ in range(max_iter):
        rs = a.sum(axis=1)
        a *= np.divide(rt, rs, out=np.zeros_like(rt), where=rs > 0)[:, None]
        cs = a.sum(axis=0)
        a *= np.divide(ct, cs, out=np.zeros_like(ct), where=cs > 0)[None, :]
        if np.abs(a.sum(axis=1) - rt).max() < tol and np.abs(a.sum(axis=0) - ct).max() < tol:
            break
    else:
        raise RuntimeError("RAS 没有收敛")
    return pd.DataFrame(a, index=prior.index, columns=prior.columns)


def household_capital_and_finance(x, keys, totals, fa, gcf_key):
    """资本形成、非生产资产、金融工具分到组。存款是每组的余项，使该组行列平衡。"""
    disp = (SIGN[:, None] * x.to_numpy()).sum(axis=0)
    disp = pd.Series(disp, index=GROUPS)
    saving = disp - x.loc["CON"]
    s_disp = disp / disp.sum()
    s_cons = x.loc["CON"] / x.loc["CON"].sum()
    s_os = x.loc["OS"] / x.loc["OS"].sum()
    pos = saving.clip(lower=0)
    s_pos = pos / pos.sum()
    s_mort = keys["mortgage"]
    s_gcf = {"mortgage": s_mort, "saving": s_pos}[gcf_key]

    out = pd.DataFrame(index=GROUPS)
    out["disposable_income"] = disp
    out["saving"] = saving
    out["GCF"] = totals["GCF"] * s_gcf
    out["NPA_disposal"] = totals["NPA"] * s_os
    out["net_lending_real"] = out["saving"] + out["NPA_disposal"] - out["GCF"]

    use_key = {"F-CUR": s_cons, "F-INS": s_disp, "F-BOND": s_pos, "F-EQ": s_pos, "F-OTH": s_pos}
    src_key = {"F-OTH": s_mort}
    short = fa.item("短期贷款与票据融资", "HH", "src")
    for code in INSTRUMENTS:
        if code == "F-DEP":
            continue
        out[f"{code}_use"] = fa.instrument(code, "HH", "use") * use_key.get(code, s_disp)
        if code == "F-LOAN":
            rest = fa.instrument(code, "HH", "src") - short
            out[f"{code}_src"] = short * s_os + rest * s_mort
        else:
            out[f"{code}_src"] = fa.instrument(code, "HH", "src") * src_key.get(code, s_disp)
    out["F-DEP_src"] = fa.instrument("F-DEP", "HH", "src") * s_disp

    disc_total = out["net_lending_real"].sum() - fa.net_lending("HH")
    out["discrepancy"] = disc_total * s_disp
    uses = [f"{c}_use" for c in INSTRUMENTS if c != "F-DEP"]
    srcs = [f"{c}_src" for c in INSTRUMENTS]
    out["F-DEP_use"] = (out["net_lending_real"] - out["discrepancy"]
                        - out[uses].sum(axis=1) + out[srcs].sum(axis=1))
    out["saving_rate"] = out["saving"] / out["disposable_income"]
    return out


# ---------------------------------------------------------------- 账户


def account_table(sections):
    rows = []
    for code in sections:
        zh, en = io2023.SECTIONS[code]
        rows.append((f"P-{code}", f"Activity: {en}", f"活动：{zh}", "activity"))
    for code in sections:
        zh, en = io2023.SECTIONS[code]
        rows.append((f"C-{code}", f"Commodity: {en}", f"商品：{zh}", "commodity"))
    rows += [
        ("LAB", "Factor: labour (compensation of employees)", "要素：劳动者报酬", "factor"),
        ("CAP", "Factor: capital (gross operating surplus and mixed income)", "要素：资本（总营业盈余）", "factor"),
    ]
    for i, h in enumerate(GROUPS, start=1):
        rows.append((h, f"Households, income decile {i} (1 = lowest)", f"住户第 {i} 组（1 为最低收入）", "household"))
    rows += [
        ("NFC", "Non-financial corporations", "非金融企业", "institution"),
        ("FC", "Financial corporations", "金融机构", "institution"),
        ("GOV", "General government", "广义政府", "institution"),
        ("ROW", "Rest of the world", "国外", "institution"),
        ("PINC", "Property income (interest, dividends, rent, other)", "财产收入", "distribution"),
        ("OTRF", "Other current transfers", "其他经常转移", "distribution"),
        ("KTRF", "Capital transfers", "资本转移", "distribution"),
        ("NPA", "Acquisitions less disposals of non-produced non-financial assets", "其他非金融资产获得减处置", "distribution"),
        ("GCF", "Gross capital formation", "资本形成总额", "capital"),
        ("F-CUR", "Currency", "通货", "financial"),
        ("F-DEP", "Deposits", "存款", "financial"),
        ("F-LOAN", "Loans and undiscounted bankers' acceptances", "贷款与未贴现银行承兑汇票", "financial"),
        ("F-INS", "Insurance technical reserves", "保险准备金", "financial"),
        ("F-BOND", "Bonds", "债券", "financial"),
        ("F-EQ", "Shares and investment fund shares", "股票与证券投资基金份额", "financial"),
        ("F-OTH", "Other financial instruments (net)", "其他金融工具", "financial"),
        ("DISC", "Statistical discrepancy", "统计差异", "discrepancy"),
    ]
    return pd.DataFrame(rows, columns=["code", "label_en", "label_zh", "type"])


# ---------------------------------------------------------------- 主体


def build(saving_floor=SAVING_FLOOR, cfps_version="v1", gcf_key="mortgage"):
    io = io2023.load_io()
    fof = FlowOfFunds()
    fa = FinancialAccounts()
    sections = io["sections"]
    acts = [f"P-{c}" for c in sections]
    coms = [f"C-{c}" for c in sections]
    accounts = account_table(sections)
    codes = accounts["code"].tolist()
    sam = pd.DataFrame(0.0, index=codes, columns=codes)

    def add(row, col, value):
        sam.loc[row, col] += float(value)

    def pay(payer, receiver, value):
        """payer 列向 receiver 行支付；负数改记为反向支付。"""
        if value >= 0:
            add(receiver, payer, value)
        else:
            add(payer, receiver, -value)

    # 生产与商品
    for i, c in enumerate(sections):
        add(acts[i], coms[i], io["output"][c])
        add("LAB", acts[i], io["labor"][c])
        add("CAP", acts[i], io["capital"][c])
        add("GOV", acts[i], io["tax"][c])
        add(coms[i], "GOV", io["gov"][c])
        add(coms[i], "GCF", io["gcf"][c])
        add(coms[i], "ROW", io["exp"][c])
        add("ROW", coms[i], io["imp"][c])
        for j, d in enumerate(sections):
            add(coms[i], acts[j], io["Z"].loc[c, d])

    # 部门合计（资金流量表）
    os_ = {s: fof.get("二、增加值", s, "src") - fof.get("三、劳动者报酬", s, "use")
           - fof.get("四、生产税净额", s, "use") for s in DOMESTIC}
    ben = fof.get("(三)社会保险福利", "GOV", "use") + fof.get("(四)社会补助", "GOV", "use")
    hh_assist = fof.get("(四)社会补助", "HH", "use")  # 住户之间的社会补助，并入其他经常转移
    totals = pd.Series({
        "LAB": fof.get("三、劳动者报酬", "HH", "src"),
        "OS": os_["HH"],
        "PIR": fof.get("五、财产收入", "HH", "src"),
        "PIP": fof.get("五、财产收入", "HH", "use"),
        "TRR": fof.get("七、经常转移", "HH", "src"),
        "TAX": fof.get("(一)所得税、财产税等经常税", "HH", "use") + fof.get("(二)社会保险缴款", "HH", "use"),
        "TRP": fof.get("(五)其他", "HH", "use") + hh_assist,
        "CON": float(io["hh"].sum()),
        "GCF": fof.get("十四、资本形成总额", "HH", "use"),
        "NPA": -fof.get("十五、其他非金融资产获得减处置", "HH", "use"),
    })
    if abs(totals["TAX"] + totals["TRP"] - fof.get("七、经常转移", "HH", "use")) > 0.05:
        raise RuntimeError("住户经常转移支出拆分与合计不一致")

    # 住户：联立配平、消费矩阵、资本和金融
    bridge = build_bridge(cfps_version, io)
    prior, keys = household_priors(cfps_version, bridge["matrix"])
    x, objective = balance_households(totals, prior, saving_floor)
    cons = ras(bridge["matrix"], io["hh"], x.loc["CON"])
    hh = household_capital_and_finance(x, keys, totals, fa, gcf_key)
    ben_ratio = ben / totals["TRR"]

    for h in GROUPS:
        add(h, "LAB", x.loc["LAB", h])
        add(h, "CAP", x.loc["OS", h])
        add(h, "PINC", x.loc["PIR", h])
        add("PINC", h, x.loc["PIP", h])
        add(h, "GOV", x.loc["TRR", h] * ben_ratio)
        add(h, "OTRF", x.loc["TRR", h] * (1 - ben_ratio))
        add("GOV", h, x.loc["TAX", h])
        add("OTRF", h, x.loc["TRP", h])
        for i, c in enumerate(sections):
            add(coms[i], h, cons.loc[c, h])
        add("GCF", h, hh.loc[h, "GCF"])
        add(h, "NPA", hh.loc[h, "NPA_disposal"])
        for code in INSTRUMENTS:
            add(code, h, hh.loc[h, f"{code}_use"])
            add(h, code, hh.loc[h, f"{code}_src"])
        pay(h, "DISC", hh.loc[h, "discrepancy"])

    # 劳动：国外付给本国居民、本国付给非居民
    add("LAB", "ROW", fof.get("三、劳动者报酬", "ROW", "use"))
    add("ROW", "LAB", fof.get("三、劳动者报酬", "ROW", "src"))

    # 企业、政府、国外
    for s in ["NFC", "FC", "GOV"]:
        add(s, "CAP", os_[s])
    for s in ["NFC", "FC", "GOV", "ROW"]:
        add("PINC", s, fof.get("五、财产收入", s, "use"))
        add(s, "PINC", fof.get("五、财产收入", s, "src"))
        add("OTRF", s, fof.get("(五)其他", s, "use"))
        add(s, "OTRF", fof.get("(五)其他", s, "src"))
        add("KTRF", s, fof.get("十三、资本转移", s, "use"))
        add(s, "KTRF", fof.get("十三、资本转移", s, "src"))
        for code in INSTRUMENTS:
            add(code, s, fa.instrument(code, s, "use"))
            add(s, code, fa.instrument(code, s, "src"))
    for s in ["NFC", "FC", "GOV"]:
        add("GCF", s, fof.get("十四、资本形成总额", s, "use"))
        pay(s, "NPA", fof.get("十五、其他非金融资产获得减处置", s, "use"))
    for s in ["NFC", "FC"]:
        add("GOV", s, fof.get("(一)所得税、财产税等经常税", s, "use"))
    # 住户之间的社会补助：付出方和收入方都是住户，经其他经常转移账户
    # （已在 TRP、TRR 中；这里只核对住户收到的其他转移等于官方数）
    hh_otr_src = fof.get("(五)其他", "HH", "src") + hh_assist
    if abs(totals["TRR"] * (1 - ben_ratio) - hh_otr_src) > 0.05:
        raise RuntimeError("住户经常转移收入拆分与合计不一致")

    # 统计差异：每个账户的行列差记入 DISC
    for a in sam.index:
        if a == "DISC":
            continue
        gap = sam.loc[a].sum() - sam[a].sum()
        if abs(gap) > 1e-6:
            pay(a, "DISC", gap)
    gap = sam.sum(axis=1) - sam.sum(axis=0)
    if gap.abs().max() > 1e-6:
        raise RuntimeError(f"SAM 不平衡，最大差 {gap.abs().max()}")

    return {
        "sam": sam,
        "accounts": accounts,
        "households": hh,
        "household_items": x,
        "prior": prior,
        "consumption": cons,
        "objective": objective,
        "totals": totals,
        "io": io,
        "fof": fof,
        "fa": fa,
        "settings": {"saving_floor": saving_floor, "cfps_version": cfps_version, "gcf_key": gcf_key},
    }


def aggregate_households(sam):
    """把 H-1..H-10 合并为一个住户账户 HH。不含 CFPS 信息。"""
    order = list(sam.index)
    first = order.index(GROUPS[0])
    keep = [a for a in order if a not in GROUPS]
    keep.insert(first, "HH")
    out = sam.copy()
    out.loc["HH"] = out.loc[GROUPS].sum(axis=0)
    out["HH"] = out[GROUPS].sum(axis=1)
    out.loc["HH", "HH"] = sam.loc[GROUPS, GROUPS].to_numpy().sum()
    return out.loc[keep, keep]


def long_format(sam):
    stacked = sam.stack()
    stacked = stacked[stacked != 0]
    stacked.index.names = ["row_receiver", "col_payer"]
    return stacked.rename("value_100m_yuan").reset_index()


NOTES = [
    ["unit", "100 million yuan (亿元), current prices, 2023"],
    ["convention", "rows receive, columns pay; every row total equals its column total"],
    ["households", "H-1 = lowest income decile, H-10 = highest; deciles of household per-capita net income, CFPS2022 cross-sectional household weights"],
    ["production", "2023 national input-output table (211 products, producer prices) aggregated to 19 GB/T 4754 sections"],
    ["institutions", "NBS 2023 flow of funds (non-financial transactions) for sector totals"],
    ["financial", "PBC 2023 flow of funds (financial accounts); row = acquisition of assets (uses), column = incurrence of liabilities (sources)"],
    ["household balancing", "minimum cross-entropy on group shares of 8 items with national totals fixed and saving rate >= floor"],
    ["consumption by group", "CFPS 8-category shares bridged to IO products; RAS to balanced group totals"],
    ["discrepancy", "DISC collects IO vs flow-of-funds differences, real vs financial net lending differences and rounding"],
    ["sign", "negative cells are published net flows (net production taxes, net disposals, net repayments)"],
]


def main():
    paths.ensure_dirs()
    res = build()
    sam, hh = res["sam"], res["households"]
    out_xlsx = paths.OUTPUT / "SAM4_2023.xlsx"
    balance = pd.DataFrame({"row_total": sam.sum(axis=1), "col_total": sam.sum(axis=0)})
    balance["gap"] = balance["row_total"] - balance["col_total"]
    disc = pd.DataFrame({"pays_to_DISC": sam.loc["DISC"], "receives_from_DISC": sam["DISC"]})
    disc = disc[(disc.abs() > 1e-6).any(axis=1)]
    notes = pd.DataFrame(
        NOTES + [
            ["saving floor", str(res["settings"]["saving_floor"])],
            ["cross-entropy objective", f"{res['objective']:.6f}"],
            ["accounts", str(len(sam))],
        ],
        columns=["item", "value"],
    )
    with pd.ExcelWriter(out_xlsx) as w:
        notes.to_excel(w, sheet_name="notes", index=False)
        res["accounts"].to_excel(w, sheet_name="accounts", index=False)
        sam.to_excel(w, sheet_name="sam")
        balance.to_excel(w, sheet_name="balance")
        res["household_items"].T.to_excel(w, sheet_name="household_income")
        hh.to_excel(w, sheet_name="household_capital_finance")
        res["consumption"].to_excel(w, sheet_name="household_consumption")
        disc.to_excel(w, sheet_name="discrepancy")
    sam.to_csv(paths.OUTPUT / "SAM4_2023.csv", encoding="utf-8-sig")
    long_format(sam).to_csv(paths.OUTPUT / "SAM4_2023_long.csv", index=False, encoding="utf-8-sig")
    res["accounts"].to_csv(paths.OUTPUT / "SAM4_2023_accounts.csv", index=False, encoding="utf-8-sig")
    agg = aggregate_households(sam)
    agg.to_csv(paths.OUTPUT / "SAM4_2023_aggregate_households.csv", encoding="utf-8-sig")
    long_format(agg).to_csv(paths.OUTPUT / "SAM4_2023_aggregate_households_long.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [(code, zh, INSTRUMENT_EN[zh]) for code, names in INSTRUMENTS.items() for zh in names],
        columns=["account", "pbc_item_zh", "pbc_item_en"],
    ).to_csv(paths.INSTRUMENT_CONCORDANCE, index=False, encoding="utf-8-sig")

    print(f"wrote {out_xlsx}")
    print("accounts", len(sam), "max gap", float(balance["gap"].abs().max()))
    print("objective", round(res["objective"], 6))
    print("saving rate", hh["saving_rate"].round(3).tolist())
    print("disposable share", (hh["disposable_income"] / hh["disposable_income"].sum()).round(3).tolist())
    print("deposits", hh["F-DEP_use"].round(0).tolist())
    print(disc.round(1).to_string())


if __name__ == "__main__":
    main()
