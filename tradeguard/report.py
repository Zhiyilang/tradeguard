"""Self-contained HTML report (inline CSS, no external assets)."""
from __future__ import annotations

import html

_SEV_COLOR = {"HIGH": "#d64545", "CAUTION": "#d98e04"}
_BAND_COLOR = {"HIGH": "#d64545", "ELEVATED": "#d98e04",
               "GUARDED": "#3b7dd8", "LOW": "#2e9e5b"}

_CSS = """
* { box-sizing: border-box; }
body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; background: #f4f6fa;
       color: #1f2933; margin: 0; padding: 32px; }
.wrap { max-width: 880px; margin: 0 auto; }
h1 { font-size: 24px; margin: 0 0 4px; }
.sub { color: #64748b; font-size: 13px; margin-bottom: 24px; }
.top { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.gauge { background: #fff; border-radius: 14px; padding: 20px 28px; text-align: center;
         box-shadow: 0 1px 3px rgba(15,23,42,.08); min-width: 180px; }
.gauge .num { font-size: 44px; font-weight: 700; }
.gauge .band { display: inline-block; margin-top: 6px; padding: 3px 14px;
               border-radius: 999px; color: #fff; font-size: 13px; font-weight: 600; }
.gauge .cnt { margin: 8px 0 0; }
.stats { flex: 1; display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
         gap: 12px; }
.stat { background: #fff; border-radius: 12px; padding: 14px 16px;
        box-shadow: 0 1px 3px rgba(15,23,42,.08); }
.stat .k { font-size: 12px; color: #64748b; }
.stat .v { font-size: 18px; font-weight: 700; margin-top: 2px; }
.neg { color: #d64545; }
.pos { color: #2e9e5b; }
h2 { font-size: 17px; margin: 28px 0 12px; }
table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px;
        overflow: hidden; box-shadow: 0 1px 3px rgba(15,23,42,.08); }
td { padding: 9px 14px; font-size: 13px; border-bottom: 1px solid #eef2f7;
     vertical-align: top; }
tr:last-child td { border-bottom: none; }
.st { font-weight: 700; color: #3b7dd8; white-space: nowrap; width: 90px; }
.card { background: #fff; border-radius: 12px; padding: 18px 20px; margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(15,23,42,.08); border-left: 4px solid #cbd5e1; }
.card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.sev { color: #fff; font-size: 11px; font-weight: 700; padding: 2px 10px;
       border-radius: 999px; }
.title { font-size: 15px; font-weight: 700; }
.detail { font-size: 13.5px; line-height: 1.6; margin: 0 0 10px; }
.lbl { font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: .05em;
       margin: 8px 0 4px; }
ul.ev { margin: 0 0 6px; padding-left: 18px; }
ul.ev li { font-family: Consolas, monospace; font-size: 12px; color: #475569;
           line-height: 1.7; word-break: break-all; }
.act { font-size: 13.5px; margin: 0; color: #0f766e; font-weight: 600; }
.actions { background: #fff; border-radius: 12px; padding: 18px 22px;
           box-shadow: 0 1px 3px rgba(15,23,42,.08); }
.actions ol { margin: 0; padding-left: 20px; }
.actions li { font-size: 13.5px; line-height: 1.8; }
.foot { margin-top: 28px; font-size: 12px; color: #94a3b8; }
"""


def _esc(x):
    return html.escape(str(x))


def write_html(result: dict, path: str) -> None:
    s = result["stats"]
    band_color = _BAND_COLOR.get(result["band"], "#666")
    cards = []
    for f in result["findings"]:
        color = _SEV_COLOR.get(f["severity"], "#666")
        ev = "".join(f"<li>{_esc(e)}</li>" for e in f["evidence"])
        cards.append(
            "<div class='card'>"
            f"<div class='card-head'><span class='sev' style='background:{color}'>"
            f"{_esc(f['severity'])}</span>"
            f"<span class='title'>{_esc(f['title'])}</span></div>"
            f"<p class='detail'>{_esc(f['detail'])}</p>"
            "<div class='lbl'>证据引用</div>"
            f"<ul class='ev'>{ev}</ul>"
            "<div class='lbl'>建议</div>"
            f"<p class='act'>{_esc(f['action'])}</p>"
            "</div>")
    actions = "".join(f"<li>{_esc(a)}</li>" for a in result["actions"])
    steps = "".join(
        f"<tr><td class='st'>{_esc(n)}</td><td>{_esc(l)}</td></tr>"
        for n, l in result["steps"])
    win_rate = (s["wins"] / s["trades"] * 100) if s["trades"] else 0.0
    n_high = sum(1 for f in result["findings"] if f["severity"] == "HIGH")
    n_cau = sum(1 for f in result["findings"] if f["severity"] == "CAUTION")
    pnl_cls = "neg" if s["net_pnl"] < 0 else "pos"
    symbols = _esc(", ".join(s["symbols"]) or "N/A")

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TradeGuard 风险报告</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>TradeGuard — 交易行为风险报告</h1>
  <div class="sub">离线 · 零依赖 · 每条结论均可溯源（文件/行号/交易ID/数字）</div>
  <div class="top">
    <div class="gauge">
      <div class="num" style="color:{band_color}">{result['score']}</div>
      <div class="band" style="background:{band_color}">{_esc(result['band'])}</div>
      <div class="sub cnt">{n_high} 高危 · {n_cau} 留意</div>
    </div>
    <div class="stats">
      <div class="stat"><div class="k">交易笔数</div><div class="v">{s['trades']}</div></div>
      <div class="stat"><div class="k">胜率</div><div class="v">{win_rate:.0f}%</div></div>
      <div class="stat"><div class="k">净盈亏</div>
        <div class="v {pnl_cls}">{s['net_pnl']:+,.0f}</div></div>
      <div class="stat"><div class="k">名义本金合计</div>
        <div class="v">{s['total_notional']:,.0f}</div></div>
      <div class="stat"><div class="k">标的</div>
        <div class="v" style="font-size:14px">{symbols}</div></div>
      <div class="stat"><div class="k">期末权益</div>
        <div class="v">{s['end_equity']:,.0f}</div></div>
    </div>
  </div>
  <h2>智能体闭环</h2>
  <table>{steps}</table>
  <h2>风险发现（{len(result['findings'])}）</h2>
  {''.join(cards)}
  <h2>行动清单</h2>
  <div class="actions"><ol>{actions}</ol></div>
  <div class="foot">TradeGuard v1.0 · 本报告仅作交易行为复盘参考，不构成投资建议。</div>
</div>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
