"""Reproducible assertions for the bundled demo scenario.

Run:  python eval.py
Exits non-zero if any assertion fails.
"""
from tradeguard import core

r = core.analyze("examples/trades.csv", "examples/account.csv",
                 question="我的交易行为有哪些风险？为什么？")

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))


rules = {f["rule"] for f in r["findings"]}
check("检出全部 8 类风险规则", len(r["findings"]) >= 8)
for rule in ("OVER_LEVERAGE", "MARTINGALE", "REVENGE_TRADING", "RISK_PER_TRADE",
             "DRAWDOWN", "LOSS_STREAK", "CONCENTRATION", "OVERTRADING"):
    check(f"命中 {rule}", rule in rules)
check("风险评分 100 / HIGH", r["score"] == 100 and r["band"] == "HIGH")
check("每条发现都有证据与建议", all(f["evidence"] and f["action"] for f in r["findings"]))
dd = next((f["metric"] for f in r["findings"] if f["rule"] == "DRAWDOWN"), 0)
check("最大回撤 ≈ 20.3%", abs(dd - 0.203) < 0.005)
check("行动清单含固定手数建议", any("固定手数" in a for a in r["actions"]))
check("智能体闭环 6 步", len(r["steps"]) == 6)
mg = next((f for f in r["findings"] if f["rule"] == "MARTINGALE"), None)
check("马丁格尔证据引用 T002/T003",
      bool(mg) and any("T002" in e and "T003" in e for e in mg["evidence"]))
check("高危 ≥ 5 项", sum(1 for f in r["findings"] if f["severity"] == "HIGH") >= 5)

failed = [n for n, ok in checks if not ok]
for n, ok in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {n}")
print(f"\n{len(checks) - len(failed)}/{len(checks)} passed")
raise SystemExit(1 if failed else 0)
