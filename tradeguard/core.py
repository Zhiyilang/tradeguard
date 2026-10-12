"""TradeGuard core — offline trading-behaviour risk agent (zero dependencies).

Agent loop: PERCEIVE -> INDEX -> RETRIEVE -> REASON -> EXPLAIN -> ACT
Every finding carries citations: source file, row number, trade ids and the
exact numbers behind the verdict. No network, no third-party packages.
"""
from __future__ import annotations

import csv
import datetime as _dt

DEFAULTS = {
    "max_leverage": 15.0,          # notional / equity_before
    "risk_per_trade": 0.03,        # |pnl| / equity_before
    "max_drawdown": 0.08,          # drawdown from running peak
    "martingale_factor": 2.0,      # next lots >= factor * losing lots
    "revenge_minutes": 15,         # re-entry window after a loss
    "revenge_factor": 1.5,         # re-entry size factor
    "loss_streak": 3,              # consecutive losses -> CAUTION
    "loss_streak_high": 5,         # consecutive losses -> HIGH
    "concentration": 0.50,         # single-symbol notional share
    "overtrading_per_day": 8,      # trades per day
    "overtrading_loss_rate": 0.60, # loss rate on a heavy day
}

SEV_WEIGHT = {"HIGH": 25, "CAUTION": 10}


def _f(x, default=0.0):
    try:
        return float(str(x).strip().replace(",", ""))
    except (TypeError, ValueError):
        return default


def _ts(x):
    x = str(x).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
                "%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(x, fmt)
        except ValueError:
            continue
    return None


def _cite(t):
    when = f"{t['ts']:%m-%d %H:%M}" if t["ts"] else t["ts_raw"]
    return (f"{t['src']} L{t['row']} {t['tid']} {when} {t['symbol']} {t['side']} "
            f"lots={t['lots']:g} notional={t['notional']:,.0f} "
            f"pnl={t['pnl']:+,.0f} equity={t['equity_after']:,.0f}")


def load_trades(path):
    trades = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            trades.append({
                "src": path.replace("\\", "/").split("/")[-1],
                "row": i,
                "tid": (row.get("trade_id") or f"R{i}").strip(),
                "ts_raw": (row.get("ts") or "").strip(),
                "ts": _ts(row.get("ts")),
                "symbol": (row.get("symbol") or "?").strip().upper(),
                "side": (row.get("side") or "?").strip().upper(),
                "lots": _f(row.get("lots")),
                "notional": _f(row.get("notional")),
                "pnl": _f(row.get("pnl")),
                "equity_after": _f(row.get("equity_after")),
            })
    return trades


def load_account(path):
    acc = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            k = (row.get("name") or "").strip()
            if k:
                acc[k] = (row.get("value") or "").strip()
    return acc


def _prepare(trades, start_equity):
    ordered = sorted(trades, key=lambda t: (t["ts"] or _dt.datetime.min, t["row"]))
    prev = start_equity
    for t in ordered:
        t["equity_before"] = prev
        if t["equity_after"]:
            prev = t["equity_after"]
    return ordered


def _finding(rule, severity, title, detail, evidence, action, metric=None):
    return {"rule": rule, "severity": severity, "title": title, "detail": detail,
            "evidence": evidence, "action": action, "metric": metric}


def run_rules(trades, cfg=None):
    if not trades:
        return []
    cfg = {**DEFAULTS, **(cfg or {})}
    out = []

    # 1. over-leverage ------------------------------------------------------
    flagged = [t for t in trades if t["equity_before"] > 0
               and t["notional"] / t["equity_before"] > cfg["max_leverage"]]
    if flagged:
        worst = max(flagged, key=lambda t: t["notional"] / t["equity_before"])
        ratio = worst["notional"] / worst["equity_before"]
        out.append(_finding(
            "OVER_LEVERAGE", "HIGH", "过度杠杆",
            f"{len(flagged)}/{len(trades)} 笔交易的名义本金/权益超过 {cfg['max_leverage']:g}x，"
            f"最高 {ratio:.1f}x（{worst['tid']}）。一次反向波动就可能爆仓。",
            [_cite(t) for t in flagged[:6]],
            "把单笔名义本金/权益压到 10x 以内；按固定风险比例（如 1%）反推手数。",
            ratio))

    # 2. martingale (doubling down after a loss) ------------------------------
    events = []
    for a, b in zip(trades, trades[1:]):
        if a["pnl"] < 0 and b["lots"] >= cfg["martingale_factor"] * max(a["lots"], 1e-9):
            gap = ((b["ts"] - a["ts"]).total_seconds() / 60
                   if a["ts"] and b["ts"] else None)
            events.append((a, b, gap))
    if events:
        out.append(_finding(
            "MARTINGALE", "HIGH", "马丁格尔（亏损后加倍下注）",
            f"检测到 {len(events)} 次「亏损后手数 ≥ {cfg['martingale_factor']:g}x」的加码行为，"
            "这是爆仓最快路径之一。",
            [f"{_cite(a)}  ->  {_cite(b)}" for a, b, _ in events[:4]],
            "启用固定手数：亏损后绝不加大仓位，让止损而不是加码来兜底。",
            float(len(events))))

    # 3. revenge trading ------------------------------------------------------
    events = []
    for a, b in zip(trades, trades[1:]):
        if a["pnl"] < 0 and a["ts"] and b["ts"]:
            gap = (b["ts"] - a["ts"]).total_seconds() / 60
            if gap <= cfg["revenge_minutes"] and \
                    b["lots"] >= cfg["revenge_factor"] * max(a["lots"], 1e-9):
                events.append((a, b, gap))
    if events:
        a, b, gap = events[0]
        out.append(_finding(
            "REVENGE_TRADING", "HIGH", "报复性交易",
            f"{len(events)} 次在亏损后 {cfg['revenge_minutes']:g} 分钟内以更大手数立刻重返市场"
            f"（首次：{a['tid']} 亏损 {a['pnl']:+,.0f} 后 {gap:.0f} 分钟，"
            f"手数 {a['lots']:g}->{b['lots']:g}）。",
            [f"{_cite(a)}  ->  {_cite(b)}（间隔 {g:.0f} 分钟）" for a, b, g in events[:4]],
            "设「亏损后冷静期」：单笔亏损超过 1% 权益当日停止交易 30 分钟。",
            float(len(events))))

    # 4. risk per trade -------------------------------------------------------
    events = [t for t in trades if t["equity_before"] > 0
              and abs(t["pnl"]) / t["equity_before"] > cfg["risk_per_trade"]]
    if events:
        worst = max(events, key=lambda t: abs(t["pnl"]) / t["equity_before"])
        r = abs(worst["pnl"]) / worst["equity_before"]
        sev = "HIGH" if r > 0.05 else "CAUTION"
        out.append(_finding(
            "RISK_PER_TRADE", sev, "单笔风险超标",
            f"{len(events)} 笔交易单笔亏损/权益超过 {cfg['risk_per_trade']:.0%}，"
            f"最高 {r:.1%}（{worst['tid']}，亏 {abs(worst['pnl']):,.0f}）。",
            [_cite(t) for t in events[:6]],
            "单笔风险硬顶 1–2% 权益：开仓前就算好止损距离与手数。",
            r))

    # 5. drawdown from running peak -------------------------------------------
    peak, max_dd, worst, dd_events = None, 0.0, None, []
    for t in trades:
        eq = t["equity_after"] or t["equity_before"]
        if peak is None or eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd, worst = dd, t
            if dd > cfg["max_drawdown"]:
                dd_events.append((t, dd))
    if dd_events and worst is not None:
        sev = "HIGH" if max_dd > 0.15 else "CAUTION"
        out.append(_finding(
            "DRAWDOWN", sev, "回撤越界",
            f"权益自峰值 {peak:,.0f} 最大回撤 {max_dd:.1%}（阈值 {cfg['max_drawdown']:.0%}），"
            f"共 {len(dd_events)} 笔交易处于深度回撤中。",
            [f"{_cite(t)}（距峰值回撤 {d:.1%}）" for t, d in dd_events[:6]],
            "设日内/每周最大回撤线（如 6%/15%），触线即停手复盘。",
            max_dd))

    # 6. loss streak -----------------------------------------------------------
    best = (0, [])
    cur = []
    for t in trades:
        if t["pnl"] < 0:
            cur.append(t)
            if len(cur) > len(best[1]):
                best = (len(cur), list(cur))
        else:
            cur = []
    if best[0] >= cfg["loss_streak"]:
        sev = "HIGH" if best[0] >= cfg["loss_streak_high"] else "CAUTION"
        streak = best[1]
        out.append(_finding(
            "LOSS_STREAK", sev, "连续亏损",
            f"最长连续亏损 {best[0]} 笔（{streak[0]['tid']}..{streak[-1]['tid']}），"
            f"合计 {sum(t['pnl'] for t in streak):+,.0f}。连亏期最易触发加码冲动。",
            [_cite(t) for t in streak[:6]],
            "连亏 3 笔强制降半仓/停手，先复盘再交易。",
            float(best[0])))

    # 7. symbol concentration ---------------------------------------------------
    vol = {}
    for t in trades:
        vol[t["symbol"]] = vol.get(t["symbol"], 0.0) + t["notional"]
    total = sum(vol.values())
    if total > 0:
        sym, amt = max(vol.items(), key=lambda kv: kv[1])
        share = amt / total
        if share > cfg["concentration"]:
            out.append(_finding(
                "CONCENTRATION", "CAUTION", "品种过度集中",
                f"{sym} 占总名义本金 {share:.1%}（阈值 {cfg['concentration']:.0%}），"
                "单一品种的相关性风险被放大。",
                [f"{sym} 名义本金合计 {amt:,.0f} / 全部 {total:,.0f}"
                 f"（{sum(1 for t in trades if t['symbol'] == sym)} 笔）"],
                "单品种名义本金占比控制在 40% 以内，分散到低相关标的。",
                share))

    # 8. overtrading -------------------------------------------------------------
    by_day = {}
    for t in trades:
        day = t["ts"].date().isoformat() if t["ts"] else "unknown"
        by_day.setdefault(day, []).append(t)
    for day, ts_ in sorted(by_day.items()):
        if len(ts_) > cfg["overtrading_per_day"]:
            losses = sum(1 for t in ts_ if t["pnl"] < 0)
            rate = losses / len(ts_)
            if rate > cfg["overtrading_loss_rate"]:
                out.append(_finding(
                    "OVERTRADING", "CAUTION", "过度交易",
                    f"{day} 交易 {len(ts_)} 笔（阈值 {cfg['overtrading_per_day']}），"
                    f"亏损率 {rate:.0%}——高频+低胜率是费用与滑点的双重失血。",
                    [f"{day}: {len(ts_)} 笔，其中亏损 {losses} 笔，"
                     f"净盈亏 {sum(t['pnl'] for t in ts_):+,.0f}"],
                    "给每日交易次数设上限（如 5 笔），宁可错过不可做错。",
                    float(len(ts_))))
    return out


def _band(score):
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "ELEVATED"
    if score >= 15:
        return "GUARDED"
    return "LOW"


def analyze(trades_path, account_path=None, question=None, cfg=None):
    trades = load_trades(trades_path)
    account = load_account(account_path) if account_path else {}
    start_equity = _f(account.get("balance"), 10000.0)
    trades = _prepare(trades, start_equity)

    stats = {
        "trades": len(trades),
        "symbols": sorted({t["symbol"] for t in trades}),
        "days": sorted({t["ts"].date().isoformat() for t in trades if t["ts"]}),
        "net_pnl": sum(t["pnl"] for t in trades),
        "wins": sum(1 for t in trades if t["pnl"] > 0),
        "losses": sum(1 for t in trades if t["pnl"] < 0),
        "total_notional": sum(t["notional"] for t in trades),
        "start_equity": start_equity,
        "end_equity": trades[-1]["equity_after"] if trades else start_equity,
    }

    findings = run_rules(trades, cfg)
    order = {"HIGH": 0, "CAUTION": 1}
    findings.sort(key=lambda f: (order.get(f["severity"], 2), -(f["metric"] or 0)))

    score = min(100, sum(SEV_WEIGHT.get(f["severity"], 0) for f in findings))
    band = _band(score)
    actions = []
    for f in findings:
        if f["action"] not in actions:
            actions.append(f["action"])

    n_high = sum(1 for f in findings if f["severity"] == "HIGH")
    n_cau = sum(1 for f in findings if f["severity"] == "CAUTION")
    verdict = (f"风险评分 {score}/100（{band}）：{n_high} 项高危 + {n_cau} 项待留意。"
               if findings else "未发现已知风险模式，继续保持当前纪律。")

    steps = [
        ("PERCEIVE", f"读取 {stats['trades']} 笔交易 | 标的 {', '.join(stats['symbols']) or 'N/A'}"
                     f" | 日期 {', '.join(stats['days']) or 'N/A'}"
                     f" | 净盈亏 {stats['net_pnl']:+,.0f}"),
        ("INDEX", f"按时间排序并链接权益链（起始 {start_equity:,.0f}），"
                  "建立 trade_id / 时间 / 品种索引"),
        ("RETRIEVE", f"对 {len(trades)} 笔交易执行 8 类风险规则检索，命中 {len(findings)} 项"),
        ("REASON", f"按严重度加权计分：{score}/100 -> {band}"),
        ("EXPLAIN", f"生成 {len(findings)} 条可解释发现，每条附证据引用"
                    "（文件/行号/交易ID/数字）"),
        ("ACT", f"汇总 {len(actions)} 条可执行建议"),
    ]

    return {"question": question, "stats": stats, "steps": steps,
            "findings": findings, "score": score, "band": band,
            "actions": actions, "verdict": verdict}
