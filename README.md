# TradeGuard — An Offline Trading-Behavior Risk Agent

Paste in a trading log CSV and TradeGuard runs a full **explainable agent loop** —
PERCEIVE → INDEX → RETRIEVE → REASON → EXPLAIN → ACT — to surface the behavior
patterns that are quietly losing you money. **Every finding carries an evidence
citation** (which file, which row, which trade, which numbers), followed by an
actionable checklist.

- **Zero dependencies**: pure Python standard library. Nothing to `pip install`.
- **100% offline**: trading data never leaves your machine — built for prop-firm
  traders, fund reviews, and mentoring.
- **Not a black box**: a transparent rule engine, so judges and users can audit
  exactly why every judgment fired.

## Quick Start

```bash
# Python 3.8+, no third-party packages needed
python -m tradeguard.cli examples/trades.csv --account examples/account.csv --html report.html

# run the reproducible evaluation (16 assertions)
python eval.py
```

Trades CSV columns: `trade_id,ts,symbol,side,lots,notional,pnl,equity_after`
Account CSV columns: `name,value` (must include at least `balance`).

## 8 Risk Rules

| Rule | Default threshold | Severity |
|---|---|---|
| `OVER_LEVERAGE` | notional / equity > 15x | HIGH |
| `MARTINGALE` | lots after a loss ≥ 2x previous trade | HIGH |
| `REVENGE_TRADING` | re-entry within 15 min of a loss with lots ≥ 1.5x | HIGH |
| `RISK_PER_TRADE` | single-trade loss / equity > 3% (>5% escalates to HIGH) | HIGH |
| `DRAWDOWN` | drawdown from peak > 8% (>15% escalates to HIGH) | HIGH |
| `LOSS_STREAK` | ≥3 consecutive losses (≥5 escalates to HIGH) | HIGH |
| `CONCENTRATION` | single-symbol notional share > 50% | CAUTION |
| `OVERTRADING` | >8 trades/day with loss rate > 60% | CAUTION |

Score = min(100, HIGH×25 + CAUTION×10); ≥70 `HIGH` / ≥40 `ELEVATED` /
≥15 `GUARDED` / otherwise `LOW`.

## Real Demo Output (examples/trades.csv)

```
[PERCEIVE] read 9 trades | symbols EURUSD, GBPUSD, XAUUSD | date 2026-10-09 | net PnL -1,980
[RETRIEVE] ran 8 risk rules over 9 trades, 8 hits
[REASON]  severity-weighted scoring: 100/100 -> HIGH

[HIGH   ] Over-leverage — 8 of 9 trades exceeded 15x notional/equity, max 61.5x (T005)
[HIGH   ] Martingale — 2 lot-doublings after losses (T002→T003: 3.0→6.0; T006→T007: 1.5→3.0)
[HIGH   ] Revenge trading — T002 lost -260, then 13 minutes later re-entered at 3.0→6.0 lots
[HIGH   ] Risk per trade — max 5.3% (T003, -520 loss)
[HIGH   ] Drawdown — max drawdown 20.3% from peak of 10,060
[HIGH   ] Loss streak — longest 5-trade losing streak (T005..T009), totaling -1,570
[CAUTION] Concentration — EURUSD is 55.1% of total notional
[CAUTION] Overtrading — 9 trades on 2026-10-09, loss rate 78%
==> Risk score 100/100 (HIGH): 6 high-severity findings, 2 cautions.
```

Every finding ships with an evidence line like:
`trades.csv L4 T003 10-09 10:18 EURUSD BUY lots=6 notional=600,000 pnl=-520 equity=9,280`
— numbers a human can re-verify by hand.

## The Agent Loop

```
PERCEIVE  read the trade log and account info; tally symbols / dates / net PnL
INDEX     sort by time, link the equity chain (equity_before → equity_after)
RETRIEVE  run the 8 rules over every trade
REASON    severity-weighted scoring, risk band assignment
EXPLAIN   emit explainable findings, each with an evidence citation
ACT       aggregate a de-duplicated action checklist
```

## Typical Uses

- **Trader self-audit**: export a week of trades, see in 5 minutes whether you are
  martingaling or revenge-sizing.
- **Prop firm / fund reviews**: objective behavioral evidence instead of impressions.
- **Mentors & community leads**: send the report to students; evidence lines are
  directly checkable.
- **Risk-control prototype**: transparent rules with tunable thresholds, ready to
  embed in a monitoring dashboard.

## Contest Entry

Built for **Deriv × Internshala "The Rise of AI Agents Hackathon 2026"**
($60,000+ prize pool, 2026-10-26 ~ 11-02, fully online): a multi-step reasoning
agent that can explain *why*, with zero dependencies, offline-capable, and fully
traceable conclusions. See `eval.py` (16 assertions, all PASS).

## Disclaimer

This tool is for trading-behavior review only and is not investment advice.
Trading carries risk.

## License

MIT

中文说明见 [README.zh.md](README.zh.md)。
