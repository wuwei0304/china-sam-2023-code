# -*- coding: utf-8 -*-
"""
按顺序运行全部步骤。没有 CFPS 原始数据时，若 intermediate/cfps2022_deciles.xlsx 已存在则跳过第一步。

python run_all.py
"""
import importlib

import paths

STEPS = [
    "build_cfps_deciles",
    "build_consumption_bridge",
    "build_sam4",
    "validate_sam4",
    "sam_multipliers",
    "sensitivity",
    "make_figures",
]


def main():
    paths.ensure_dirs()
    for name in STEPS:
        if name == "build_cfps_deciles":
            try:
                paths.cfps_dta()
            except FileNotFoundError:
                if not paths.CFPS_DECILES.exists():
                    raise
                print(f"[skip] {name}: CFPS microdata not found, using {paths.CFPS_DECILES.name}")
                continue
        print(f"[run] {name}")
        importlib.import_module(name).main()


if __name__ == "__main__":
    main()
