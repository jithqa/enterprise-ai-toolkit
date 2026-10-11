# Swing strategy backtest — 2015-01-01 to 2026-10-09
Universe: 501 current Nifty 500 symbols. Costs 0.30% round trip. Max hold 20 days. Delivery % not tested (no free history).
Benchmark Nifty 50 (price index, no dividends): CAGR 8.7%, max drawdown -38.4%.

## Per-trade results
| Variant | Trades | Win % | Avg R | Avg trade % | Avg win % | Avg loss % | Profit factor | Avg days | Target % | Stop % | Time-exit % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No market filter | 10957 | 43.8 | 0.052 | 0.37 | 8.49 | -5.96 | 1.11 | 12.4 | 23.2 | 44.7 | 32.1 |
| Nifty > 50 EMA | 8033 | 44.5 | 0.076 | 0.55 | 8.45 | -5.78 | 1.17 | 12.3 | 24.5 | 44.5 | 30.9 |
| Nifty > 50 EMA > 200 EMA | 7293 | 44.0 | 0.068 | 0.51 | 8.52 | -5.78 | 1.16 | 12.2 | 24.6 | 45.1 | 30.3 |

## Portfolio simulation (Rs 10L start, 1% risk/trade, max 10 positions, max 20% per position)
| Variant | Trades taken | Final equity (Rs L) | CAGR % | Max drawdown % (closed trades) |
|---|---|---|---|---|
| No market filter | 2135 | 17.6 | 4.9 | -40.4 |
| Nifty > 50 EMA | 1638 | 29.2 | 9.6 | -39.9 |
| Nifty > 50 EMA > 200 EMA | 1406 | 23.6 | 8.0 | -34.5 |

## By setup
| Setup | Filter | Trades | Win % | Avg R | Avg trade % | Avg win % | Avg loss % | Profit factor | Avg days | Target % | Stop % | Time-exit % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Breakout | No filter | 1390 | 42.2 | -0.014 | -0.05 | 8.2 | -6.08 | 0.99 | 13.3 | 18.6 | 44.0 | 37.4 |
| Breakout | Nifty>50EMA | 1051 | 43.7 | 0.027 | 0.22 | 8.14 | -5.92 | 1.07 | 13.1 | 20.4 | 43.7 | 36.0 |
| Pullback | No filter | 7571 | 44.3 | 0.052 | 0.37 | 8.3 | -5.94 | 1.11 | 13.1 | 21.3 | 42.6 | 36.2 |
| Pullback | Nifty>50EMA | 5306 | 44.9 | 0.072 | 0.57 | 8.29 | -5.72 | 1.18 | 13.0 | 22.6 | 42.4 | 35.0 |
| RSI breakout | No filter | 4411 | 43.6 | 0.045 | 0.35 | 8.82 | -6.18 | 1.1 | 12.0 | 24.1 | 46.0 | 30.0 |
| RSI breakout | Nifty>50EMA | 3531 | 44.4 | 0.076 | 0.52 | 8.72 | -6.03 | 1.15 | 12.0 | 25.2 | 45.4 | 29.4 |

## By volume strength (all trades)
| Volume x | Trades | Win % | Avg R | Avg trade % | Avg win % | Avg loss % | Profit factor | Avg days | Target % | Stop % | Time-exit % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1-1.5 | 5547 | 43.2 | 0.05 | 0.34 | 8.11 | -5.57 | 1.11 | 11.8 | 25.2 | 47.4 | 27.3 |
| 1.5-2 | 2337 | 44.1 | 0.066 | 0.52 | 8.77 | -5.99 | 1.16 | 12.3 | 23.5 | 44.8 | 31.7 |
| 2-3 | 1719 | 44.4 | 0.046 | 0.36 | 8.77 | -6.36 | 1.1 | 13.2 | 21.0 | 41.3 | 37.7 |
| 3-+ | 1261 | 45.4 | 0.043 | 0.27 | 9.29 | -7.22 | 1.07 | 14.3 | 16.4 | 37.0 | 46.6 |

## By year
| Year | Trades | Win % | Avg R | Filtered trades | Filtered Win % | Filtered Avg R |
|---|---|---|---|---|---|---|
| 2015 | 556 | 37.2 | -0.133 | 310 | 35.5 | -0.155 |
| 2016 | 500 | 43.0 | -0.027 | 359 | 49.9 | 0.13 |
| 2017 | 798 | 47.4 | 0.161 | 732 | 45.8 | 0.124 |
| 2018 | 502 | 35.9 | -0.165 | 323 | 30.7 | -0.301 |
| 2019 | 455 | 45.9 | 0.031 | 348 | 44.8 | 0.0 |
| 2020 | 673 | 48.3 | 0.171 | 566 | 50.0 | 0.233 |
| 2021 | 1454 | 46.1 | 0.147 | 1226 | 46.6 | 0.162 |
| 2022 | 973 | 40.0 | -0.051 | 623 | 38.0 | -0.104 |
| 2023 | 1377 | 54.2 | 0.34 | 960 | 55.2 | 0.39 |
| 2024 | 1778 | 42.0 | 0.029 | 1463 | 42.8 | 0.049 |
| 2025 | 1109 | 39.0 | -0.112 | 763 | 40.5 | -0.072 |
| 2026 | 782 | 38.7 | -0.106 | 360 | 38.3 | -0.113 |

Caveats: survivorship bias (stocks that left the Nifty 500 are excluded, which flatters results); Yahoo data errors; fills assume liquidity at the stop/target price; past results do not predict future returns.
