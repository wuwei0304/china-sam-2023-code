# -*- coding: utf-8 -*-
"""
2023 年居民消费的行业 × 收入组矩阵。

控制数：2023 年投入产出表（生产者价格）的居民消费列，经 211×19 转换矩阵加总到门类。
组间结构：CFPS2022 加权十等分（H-1 为最低收入组）的八类支出份额。
分类：《居民消费支出分类》（2013）。

一个行业若只落在一个消费大类里，它的组间分布就等于该类的调查份额。
采矿、电力热力、房地产因此会相同：调查的“居住”分不出房租和水电。
批发、零售是生产者价格表上的贸易加价，按居民购买的货物（不含服务）的组间结构分摊。
货币银行服务是虚拟服务，调查里没有对应支出，按家庭净资产的组间份额分摊。

行合计等于投入产出表。这里的列合计只是调查先验；build_sam4 联立配平后各组消费总额会变，
那时再用 RAS 把列调到配平结果，行合计保持不变。
"""
import numpy as np
import pandas as pd

import io2023
import paths

OUT = paths.INTERMEDIATE / "consumption_bridge_2023.xlsx"

GROUPS = [f"H-{i}" for i in range(1, 11)]
CATS = [
    "食品烟酒",
    "衣着",
    "居住",
    "生活用品及服务",
    "交通通信",
    "文教娱乐",
    "医疗保健",
    "其他用品及服务",
]
CATS_EN = {
    "食品烟酒": "Food, tobacco and liquor",
    "衣着": "Clothing",
    "居住": "Housing",
    "生活用品及服务": "Household articles and services",
    "交通通信": "Transport and communication",
    "文教娱乐": "Education, culture and recreation",
    "医疗保健": "Health care",
    "其他用品及服务": "Other goods and services",
    "贸易加价": "Trade margins",
    "银行服务（虚拟）": "FISIM",
    "无居民消费": "No household consumption",
}
CFPS_COL = {
    "食品烟酒": "食品支出",
    "衣着": "衣着鞋帽支出",
    "居住": "居住支出",
    "生活用品及服务": "家庭设备及日用品支出",
    "交通通信": "交通通讯支出",
    "文教娱乐": "文教娱乐支出",
    "医疗保健": "医疗保健支出",
    "其他用品及服务": "其他消费性支出",
}

# 代码 -> (大类, 类型, 说明)。类型：goods 货物，service 服务，margin 贸易加价，fisim 虚拟银行服务。
RULES = {}


def add(codes, category, kind, note=""):
    for code in codes:
        if code in RULES:
            raise ValueError(f"重复归类 {code}")
        RULES[code] = (category, kind, note)


add(
    ["01001", "01002", "02003", "03004", "03005", "04006", "04007",
     "13017", "13019", "13020", "13021", "13022", "13023", "13024",
     "14025", "14026", "14027", "14028", "15029", "15030", "15031", "16032",
     "62172"],
    "食品烟酒", "goods", "",
)
RULES["02003"] = ("食品烟酒", "goods", "林产品里木材和食品混在一起，居民消费按食品处理")
RULES["01002"] = ("食品烟酒", "goods", "其他农产品含棉麻，居民消费以菜果为主")
RULES["62172"] = ("食品烟酒", "service", "饮食服务，分类 0104")
RULES["13018"] = ("其他用品及服务", "goods", "饲料不是居民食品，金额小，放入其他")

add(
    ["17033", "17034", "17035", "17036", "17037", "18040", "18041", "18042", "19043", "19044"],
    "衣着", "goods", "",
)
RULES["19043"] = ("衣着", "goods", "皮革毛皮制品里衣着和鞋占居民消费的主要部分")

add(
    ["06009", "25055", "30073", "30074", "30075", "26059",
     "44141", "44142", "45143", "46144", "70183"],
    "居住", "goods", "",
)
for code in ["44141", "44142", "45143", "46144", "70183"]:
    RULES[code] = (RULES[code][0], "service", RULES[code][2])
RULES["70183"] = ("居住", "service", "投入产出表中的居民房地产消费主要是自有住房虚拟房租")
RULES["06009"] = ("居住", "goods", "居民购煤，归入居住中的水电燃料")
RULES["25055"] = ("居住", "goods", "居民用煤制品，归入水电燃料")
RULES["30073"] = ("居住", "goods", "住房维修材料，金额小")
RULES["30074"] = ("居住", "goods", "住房维修材料，金额小")
RULES["30075"] = ("居住", "goods", "住房维修材料，金额小")
RULES["26059"] = ("居住", "goods", "涂料用于住房维修，金额小")

add(
    ["17038", "20045", "20046", "20047", "21048", "22049", "22050",
     "26062", "29069", "29071", "30077", "30079", "33093", "33096", "33097",
     "38123", "38124", "38125", "80198"],
    "生活用品及服务", "goods", "",
)
RULES["80198"] = ("生活用品及服务", "service", "家政归入本类，理发美容洗浴归入其他；同一产品无法拆开，整项放在本类")
RULES["38123"] = ("生活用品及服务", "goods", "家用电池与车用电池未拆开")

add(
    ["25054", "29068", "36113", "36114", "36115", "36116", "37118", "37119",
     "39129", "53158", "53159", "54160", "54161", "55162", "55163",
     "56164", "56165", "57166", "58167", "59168", "59169", "60170",
     "63173", "64175", "65177", "71184", "81199"],
    "交通通信", "service", "",
)
for code in ["25054", "29068", "36113", "36114", "36115", "36116", "37118", "37119", "39129"]:
    RULES[code] = ("交通通信", "goods", RULES[code][2])
RULES["25054"] = ("交通通信", "goods", "居民购买的成品油主要是交通燃料，取暖用油未拆出")
RULES["53159"] = ("交通通信", "service", "居民支付的货物运输，含搬家；不是贸易加价")
RULES["54161"] = ("交通通信", "service", "居民支付的货物运输，含搬家；不是贸易加价")
RULES["55163"] = ("交通通信", "service", "居民支付的货物运输")
RULES["56165"] = ("交通通信", "service", "居民支付的货物运输，金额小")
RULES["57166"] = ("交通通信", "service", "管道运输；燃气本身在居住类")
RULES["71184"] = ("交通通信", "service", "租赁业中居民部分含交通工具租赁，与物品租赁未拆开")
RULES["81199"] = ("交通通信", "service", "机动车修理归入交通；日用品修理混在同一产品里")

add(
    ["23051", "24052", "24053", "34104", "39126", "39127", "39130", "39131", "39134",
     "63174", "65176", "78196", "83201", "86204", "87205", "88206", "89207", "90208"],
    "文教娱乐", "goods", "",
)
for code in ["63174", "65176", "78196", "83201", "86204", "87205", "88206", "89207", "90208"]:
    RULES[code] = ("文教娱乐", "service", "")
RULES["24052"] = ("文教娱乐", "goods", "工艺美术品；金银珠宝若单列应归入其他，这里无法拆")
RULES["39126"] = ("文教娱乐", "goods", "计算机按文化耐用品，不归入通信终端")
RULES["39127"] = ("文教娱乐", "goods", "计算机零部件，随计算机")
RULES["39134"] = ("文教娱乐", "goods", "智能消费设备；通信终端已单独归入交通通信")
RULES["78196"] = ("文教娱乐", "service", "公园等公共设施，金额相对房地产很小")

add(
    ["27064", "27065", "27066", "35111", "84202", "85203"],
    "医疗保健", "goods", "",
)
RULES["84202"] = ("医疗保健", "service", "")
RULES["85203"] = ("医疗保健", "service", "")
RULES["35111"] = ("医疗保健", "goods", "")

add(
    ["17039", "26057", "26058", "26061", "34105", "40135", "41136",
     "61171", "66179", "67180", "68181", "69182",
     "72185", "72186", "74189", "77195", "79197", "82200", "91209", "95211"],
    "其他用品及服务", "goods", "",
)
for code in ["61171", "66179", "67180", "68181", "69182", "72185", "72186", "74189", "77195", "79197", "82200", "91209", "95211"]:
    RULES[code] = ("其他用品及服务", "service", "")
RULES["61171"] = ("其他用品及服务", "service", "旅馆住宿归入 080201，不是居住里的房租")
RULES["68181"] = ("其他用品及服务", "service", "保险服务费归入 080204；调查中的其他消费远小于这项")
RULES["66179"] = ("其他用品及服务", "service", "金融服务费归入 080205")
RULES["67180"] = ("其他用品及服务", "service", "金融服务费归入 080205")
RULES["69182"] = ("其他用品及服务", "service", "金融服务费归入 080205")
RULES["17039"] = ("其他用品及服务", "goods", "产业用纺织品，居民消费金额小")
RULES["26057"] = ("其他用品及服务", "goods", "肥料不是居民消费分类中的项目，金额小")
RULES["26058"] = ("其他用品及服务", "goods", "农药不是居民消费分类中的项目，金额小")
RULES["26061"] = ("其他用品及服务", "goods", "专用化学产品，居民消费金额小")
RULES["74189"] = ("其他用品及服务", "service", "质检服务无直接对应的调查大类，金额小")
RULES["91209"] = ("其他用品及服务", "service", "公共管理被居民购买的部分，无对应调查大类")

add(["51156", "52157"], "贸易加价", "margin", "生产者价格表中，居民对批发和零售的消费是货物加价，不是一个调查大类")
add(["66178"], "银行服务（虚拟）", "fisim", "虚拟银行服务不在住户调查的现金支出里，按净资产份额分摊")


def classify(products):
    missing = products.loc[(products["hh"] > 0) & ~products["code"].isin(RULES), "code"]
    if len(missing):
        raise RuntimeError(f"有居民消费但未归类: {missing.tolist()}")
    meta = [RULES.get(code, ("无居民消费", "none", "")) for code in products["code"]]
    out = products.copy()
    out[["category", "kind", "note"]] = pd.DataFrame(meta, index=out.index)
    return out


def load_shares(version="v1"):
    share = pd.read_excel(paths.CFPS_DECILES, sheet_name=f"{version}_share", index_col=0)
    share = share.loc[GROUPS]
    out = pd.DataFrame({cat: share[col] for cat, col in CFPS_COL.items()})
    out["净资产"] = share["家庭净资产"]
    if out.isna().any().any():
        raise RuntimeError("调查份额有缺失")
    return out


def build(version="v1", io=None):
    """返回门类 × 收入组的居民消费矩阵（亿元）及中间结果。行合计等于投入产出表。"""
    io = io2023.load_io() if io is None else io
    products = classify(io["products"])
    shares = load_shares(version)
    sections = io["sections"]
    matrix = pd.DataFrame(0.0, index=sections, columns=GROUPS)

    goods = products[products["kind"] == "goods"]
    goods_by_h = pd.Series(0.0, index=GROUPS)
    for rec in goods.itertuples(index=False):
        goods_by_h += rec.hh * shares[rec.category]
    goods_share = goods_by_h / goods_by_h.sum()

    for rec in products.itertuples(index=False):
        if rec.hh == 0:
            continue
        if rec.kind == "margin":
            weights = goods_share
        elif rec.kind == "fisim":
            weights = shares["净资产"] / shares["净资产"].sum()
        elif rec.kind in ("goods", "service"):
            weights = shares[rec.category] / shares[rec.category].sum()
        else:
            raise RuntimeError(rec.code)
        matrix.loc[rec.section] += rec.hh * weights.to_numpy()

    gap = matrix.sum(axis=1) - io["hh"]
    if gap.abs().max() > 1e-6:
        raise RuntimeError(f"行合计与投入产出表不一致，最大差 {gap.abs().max()}")

    cat_totals = products.groupby("category")["hh"].sum().reindex(
        CATS + ["贸易加价", "银行服务（虚拟）"]
    ).fillna(0.0)
    return {
        "matrix": matrix,
        "products": products,
        "shares": shares,
        "goods_share": goods_share,
        "category_totals": cat_totals,
    }


def write_concordance(products):
    out = products[["code", "name", "section", "category", "kind", "note"]].rename(
        columns={"code": "product_code", "name": "product_name_zh", "category": "category_zh", "note": "note_zh"}
    )
    out.insert(4, "category_en", out["category_zh"].map(CATS_EN))
    out.to_csv(paths.CONSUMPTION_CONCORDANCE, index=False, encoding="utf-8-sig")


def main():
    res = build("v1")
    matrix = res["matrix"]
    percent = matrix.div(matrix.sum(axis=1).replace(0, np.nan), axis=0) * 100
    notes = pd.DataFrame(
        [
            ["单位", "矩阵为亿元；行百分数每行合计为 100"],
            ["组序", "H-1 最低收入，H-10 最高收入"],
            ["行控制", "2023 年投入产出表居民消费，211 产品按门类加总"],
            ["组间结构", "CFPS2022 人均纯收入加权十等分（v1）的八类支出份额"],
            ["贸易加价", "批发和零售按货物消费的组间结构分摊，服务不计入货物"],
            ["虚拟银行服务", "货币银行按净资产份额分摊"],
            ["住宿", "归入其他用品及服务，不归入居住"],
            ["餐饮", "归入食品烟酒"],
            ["列合计", "这里是调查先验。SAM 配平后各组消费总额改变，再用 RAS 调整列"],
            ["相同的行", "只含居住类的门类，行百分数相同。这是调查分不开房租和水电，不是代填"],
        ],
        columns=["item", "value"],
    )
    paths.ensure_dirs()
    write_concordance(res["products"])
    with pd.ExcelWriter(OUT) as writer:
        notes.to_excel(writer, sheet_name="notes", index=False)
        res["category_totals"].to_excel(writer, sheet_name="category_totals", header=["亿元"])
        matrix.to_excel(writer, sheet_name="matrix_yi")
        percent.to_excel(writer, sheet_name="row_percent")
        res["shares"].to_excel(writer, sheet_name="cfps_shares")
        res["goods_share"].to_excel(writer, sheet_name="goods_margin_share", header=["share"])

    print(f"wrote {OUT}")
    print(f"wrote {paths.CONSUMPTION_CONCORDANCE}")
    print("category totals 亿元")
    print(res["category_totals"].round(1).to_string())
    print("total", round(matrix.to_numpy().sum(), 2))


if __name__ == "__main__":
    main()
