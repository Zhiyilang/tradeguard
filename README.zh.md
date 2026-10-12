# TradeGuard — 交易行为风险智能体（离线 · 零依赖）

粘贴一份交易流水 CSV，TradeGuard 以**可解释智能体**的方式跑完
「感知 → 索引 → 检索 → 推理 → 解释 → 行动」闭环，揪出正在让你亏钱的行为模式，
**每条结论都带证据引用**（哪个文件、哪一行、哪笔交易、算了什么数字），
再给一份可执行的行动清单。

- **零依赖**：纯 Python 标准库，`pip install` 什么都不需要
- **100% 离线**：交易数据不出本机，适合 prop firm 交易员、资管复盘、导师督导
- **非黑箱**：透明规则引擎，评委/用户能看到每一条判断的来龙去脉

English version: [README.md](README.md)

## 快速开始

```bash
# 无需安装任何第三方包，Python 3.8+ 直接跑
python -m tradeguard.cli examples/trades.csv --account examples/account.csv --html report.html

# 跑可复现评测（16 条断言）
python eval.py
```

交易流水 CSV 列：`trade_id,ts,symbol,side,lots,notional,pnl,equity_after`
账户 CSV 列：`name,value`（至少包含 `balance`）。

## 8 类风险规则

| 规则 | 默认阈值 | 严重度 |
|---|---|---|
| `OVER_LEVERAGE` 过度杠杆 | 名义本金/权益 > 15x | HIGH |
| `MARTINGALE` 马丁格尔 | 亏损后手数 ≥ 2x 上一笔 | HIGH |
| `REVENGE_TRADING` 报复性交易 | 亏损后 15 分钟内、手数 ≥ 1.5x 重返 | HIGH |
| `RISK_PER_TRADE` 单笔风险超标 | 单笔亏损/权益 > 3%（>5% 升 HIGH） | HIGH |
| `DRAWDOWN` 回撤越界 | 距峰值回撤 > 8%（>15% 升 HIGH） | HIGH |
| `LOSS_STREAK` 连续亏损 | ≥3 笔（≥5 笔升 HIGH） | HIGH |
| `CONCENTRATION` 品种过度集中 | 单品种名义本金占比 > 50% | CAUTION |
| `OVERTRADING` 过度交易 | 单日 > 8 笔且亏损率 > 60% | CAUTION |

评分 = min(100, HIGH×25 + CAUTION×10)；≥70 `HIGH` / ≥40 `ELEVATED` /
≥15 `GUARDED` / 其余 `LOW`。

## 真实 demo 输出（examples/trades.csv）

```
[PERCEIVE] 读取 9 笔交易 | 标的 EURUSD, GBPUSD, XAUUSD | 日期 2026-10-09 | 净盈亏 -1,980
[RETRIEVE] 对 9 笔交易执行 8 类风险规则检索，命中 8 项
[REASON]  按严重度加权计分：100/100 -> HIGH

[HIGH   ] 过度杠杆 — 9 笔中 8 笔名义本金/权益超 15x，最高 61.5x（T005）
[HIGH   ] 马丁格尔 — 2 次亏损后手数加倍（T002→T003：3.0→6.0；T006→T007：1.5→3.0）
[HIGH   ] 报复性交易 — T002 亏损 -260 后 13 分钟，手数 3.0→6.0 立刻重返
[HIGH   ] 单笔风险超标 — 最高 5.3%（T003，亏 520）
[HIGH   ] 回撤越界 — 自峰值 10,060 最大回撤 20.3%
[HIGH   ] 连续亏损 — 最长 5 笔连亏（T005..T009），合计 -1,570
[CAUTION] 品种过度集中 — EURUSD 占名义本金 55.1%
[CAUTION] 过度交易 — 2026-10-09 交易 9 笔，亏损率 78%
==> 风险评分 100/100（HIGH）：6 项高危 + 2 项待留意。
```

每条发现都附带形如
`trades.csv L4 T003 10-09 10:18 EURUSD BUY lots=6 notional=600,000 pnl=-520 equity=9,280`
的证据行，数字可手工复核。

## 智能体闭环

```
PERCEIVE  读取交易流水与账户信息，统计标的/日期/净盈亏
INDEX     按时间排序，链接权益链（equity_before → equity_after）
RETRIEVE  对每笔交易执行 8 类规则检索
REASON    按严重度加权计分，划分风险带
EXPLAIN   生成可解释发现，每条附证据引用
ACT       汇总去重后的行动清单
```

## 典型用途

- **交易员自查**：导出一周流水，5 分钟看到自己是不是在马丁格尔/报复性加码
- **prop firm / 资管复盘**：客观行为证据，替代主观印象
- **导师 / 社区督导**：把报告发给学员，证据行可直接核对
- **风控原型**：规则透明、可按需调阈值，适合嵌入监控看板

## 参赛信息

为 **Deriv × Internshala「The Rise of AI Agents Hackathon 2026」**（$60,000+ 奖池，
2026-10-26 ~ 11-02，全球在线）构建：一个能解释「为什么」的多步推理智能体，
零依赖、可离线、结论可溯源。评测见 `eval.py`（16 条断言全 PASS）。

## 免责声明

本工具仅作交易行为复盘参考，不构成投资建议。交易有风险，入市需谨慎。

## License

MIT
