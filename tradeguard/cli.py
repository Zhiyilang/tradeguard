"""Command line interface.

Usage:
    python -m tradeguard.cli trades.csv [--account account.csv]
                                       [--html report.html] [--question "..."]
"""
from __future__ import annotations

import argparse
import json
import sys

from . import core
from . import report


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="tradeguard",
        description="TradeGuard — 离线交易行为风险智能体（零依赖）")
    p.add_argument("trades",
                   help="交易流水 CSV（trade_id,ts,symbol,side,lots,notional,pnl,equity_after）")
    p.add_argument("--account", help="账户 CSV（name,value；可含 balance）")
    p.add_argument("--html", help="输出 HTML 报告路径")
    p.add_argument("--question", help="要回答的问题（可选）")
    p.add_argument("--json", action="store_true", help="同时打印 JSON 结果")
    args = p.parse_args(argv)

    result = core.analyze(args.trades, args.account, args.question)

    print("=" * 68)
    print("TradeGuard — 交易行为风险智能体（离线 · 零依赖）")
    print("=" * 68)
    if result["question"]:
        print(f"问题: {result['question']}")
    for name, line in result["steps"]:
        print(f"[{name}] {line}")
    print("-" * 68)
    for f in result["findings"]:
        print(f"[{f['severity']:7}] {f['title']}")
        print(f"          {f['detail']}")
        for ev in f["evidence"]:
            print(f"          证据: {ev}")
        print(f"          建议: {f['action']}")
        print()
    print(result["verdict"])
    if result["actions"]:
        print("\n行动清单:")
        for i, a in enumerate(result["actions"], 1):
            print(f"  {i}. {a}")
    print("\n免责声明：本工具仅作交易行为复盘参考，不构成投资建议。")

    if args.html:
        report.write_html(result, args.html)
        print(f"\nHTML 报告已生成: {args.html}")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
