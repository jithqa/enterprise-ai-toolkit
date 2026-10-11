"""
Backtest of the daily swing scan rules on the current Nifty 500 list (EOD, Yahoo data).

Rules mirror scan.py (delivery % is not tested: no free history).
Execution: signal at close of day t -> buy-stop at entry (high*1.002) valid on day t+1 only
(gap above entry fills at open). Exit on stop / 1:2 target / 20-day time stop.
Stop and target hit on the same day -> assume stop (conservative). Gaps fill at open.
Costs: 0.30% round trip (brokerage + STT + slippage, approximate).

Known biases: survivorship (today's Nifty 500 only), Yahoo data quality, no liquidity impact.
"""
import os, sys
import numpy as np
import pandas as pd
import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "backtest")
START, WARM = "2015-01-01", "2013-06-01"
COST, MAX_HOLD = 0.003, 20
CAPITAL, RISK_PCT, MAX_POS, MAX_ALLOC = 1_000_000, 0.01, 10, 0.20


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def atr(h, l, c, n=14):
    pc = c.shift()
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def signals(sym, df):
    df = df.dropna()
    if len(df) < 260:
        return []
    c, h, l, o, v = (df[k].values for k in ["Close", "High", "Low", "Open", "Volume"])
    C = df["Close"]
    e50 = C.ewm(span=50, adjust=False).mean().values
    e200 = C.ewm(span=200, adjust=False).mean().values
    r = rsi(C).values
    a = atr(df["High"], df["Low"], C).values
    vol20 = pd.Series(v).rolling(20).mean().shift(1).values
    val20 = pd.Series(c * v).rolling(20).mean().values
    hi20 = pd.Series(h).rolling(20).max().shift(1).values
    lo3 = pd.Series(l).rolling(3).min().values
    dates = df.index
    start_i = max(220, int(np.searchsorted(dates, pd.Timestamp(START))))
    trades, i, n = [], start_i, len(df)
    while i < n - 1:
        px = c[i]
        ok = (px > e50[i] > e200[i] and 40 <= r[i] <= 65 and a[i] / px >= 0.015
              and val20[i] >= 1e8 and vol20[i] > 0 and v[i] / vol20[i] > 1)
        if not ok:
            i += 1
            continue
        vol_x = v[i] / vol20[i]
        setups, stop = [], None
        if px > hi20[i]:
            setups.append("Breakout"); stop = min(l[i], hi20[i] - 0.5 * a[i])
        body = px - o[i]
        wick = min(o[i], px) - l[i]
        bull = (body > 0 and px > h[i - 1]) or (wick > 2 * abs(body) and px > o[i])
        if l[i] <= e50[i] * 1.02 and px > e50[i] and bull:
            setups.append("Pullback"); s = min(lo3[i], e50[i] - 0.5 * a[i]); stop = s if stop is None else min(stop, s)
        if r[i - 1] < 60 <= r[i]:
            setups.append("RSI breakout"); s = l[i] - 0.5 * a[i]; stop = s if stop is None else min(stop, s)
        if not setups:
            i += 1
            continue
        entry = h[i] * 1.002
        target = entry + 2 * (entry - stop)
        j = i + 1
        if h[j] < entry:                       # order not triggered
            i += 1
            continue
        fill = max(entry, o[j])
        if fill <= stop:
            i += 1
            continue
        exit_px, reason, k = None, None, j
        while True:
            if k > j:
                if o[k] <= stop: exit_px, reason = o[k], "stop"; break
                if o[k] >= target: exit_px, reason = o[k], "target"; break
            if l[k] <= stop: exit_px, reason = stop, "stop"; break
            if h[k] >= target and not (k == j and fill >= target): exit_px, reason = target, "target"; break
            if k - j + 1 >= MAX_HOLD or k == n - 1:
                exit_px, reason = c[k], "time" if k - j + 1 >= MAX_HOLD else "open"; break
            k += 1
        ret = exit_px / fill - 1 - COST
        trades.append({
            "symbol": sym, "signal_date": dates[i], "entry_date": dates[j], "exit_date": dates[k],
            "setup": " + ".join(setups), "rsi": round(r[i], 1), "vol_x": round(vol_x, 2),
            "entry": round(fill, 2), "stop": round(stop, 2), "target": round(target, 2),
            "exit": round(exit_px, 2), "reason": reason, "ret": ret,
            "R": (exit_px - fill - COST * fill) / (fill - stop), "risk_pct": (fill - stop) / fill,
            "days": k - j + 1,
            "score": min(vol_x, 3) / 3 * 0.6 + (1 - abs(r[i] - 57) / 17) * 0.4 + 0.1 * (len(setups) - 1),
        })
        i = k + 1                              # one position per symbol at a time
    return trades


def stats(t):
    t = t[t["reason"] != "open"]
    if len(t) == 0:
        return {"Trades": 0}
    wins, losses = t[t["ret"] > 0], t[t["ret"] <= 0]
    pf = wins["ret"].sum() / -losses["ret"].sum() if len(losses) and losses["ret"].sum() < 0 else np.nan
    return {
        "Trades": len(t), "Win %": round(100 * len(wins) / len(t), 1),
        "Avg R": round(t["R"].mean(), 3), "Avg trade %": round(100 * t["ret"].mean(), 2),
        "Avg win %": round(100 * wins["ret"].mean(), 2) if len(wins) else 0,
        "Avg loss %": round(100 * losses["ret"].mean(), 2) if len(losses) else 0,
        "Profit factor": round(pf, 2), "Avg days": round(t["days"].mean(), 1),
        "Target %": round(100 * (t["reason"] == "target").mean(), 1),
        "Stop %": round(100 * (t["reason"] == "stop").mean(), 1),
        "Time-exit %": round(100 * (t["reason"] == "time").mean(), 1),
    }


def portfolio(t):
    """Max 10 positions, risk 1% of equity per trade, position <= 20% of equity, best score first."""
    t = t.sort_values(["entry_date", "score"], ascending=[True, False])
    equity, open_pos, curve, taken = CAPITAL, [], [], 0
    days = sorted(set(t["entry_date"]).union(set(t["exit_date"])))
    by_entry = {d: g for d, g in t.groupby("entry_date")}
    for d in days:
        # positions that exited on an earlier day free their slot before today's entries
        still = []
        for p in open_pos:
            if p["exit_date"] < d:
                equity += p["size"] * p["ret"]
            else:
                still.append(p)
        open_pos = still
        if d in by_entry:
            held = {p["symbol"] for p in open_pos}
            for _, row in by_entry[d].iterrows():
                if len(open_pos) >= MAX_POS:
                    break
                if row["symbol"] in held:
                    continue
                size = min(equity * RISK_PCT / row["risk_pct"], equity * MAX_ALLOC)
                p = row.to_dict(); p["size"] = size
                open_pos.append(p)
                taken += 1
        curve.append((d, equity))          # realized equity
    for p in open_pos:
        equity += p["size"] * p["ret"]
    s = pd.Series(dict(curve)).sort_index()
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    dd = (s / s.cummax() - 1).min()
    return {"Trades taken": taken, "Final equity (Rs L)": round(equity / 1e5, 1),
            "CAGR %": round(100 * ((equity / CAPITAL) ** (1 / yrs) - 1), 1),
            "Max drawdown % (closed trades)": round(100 * dd, 1)}, s


def md(df):
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for idx, row in df.iterrows():
        cells = []
        for x in row:
            if pd.isna(x): cells.append("")
            elif isinstance(x, float) and x.is_integer() and abs(x) >= 100: cells.append(str(int(x)))
            else: cells.append(str(x))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(HERE, "symbols.txt")) as f:
        syms = [s.strip() for s in f if s.strip()]
    if len(sys.argv) > 1:
        syms = syms[: int(sys.argv[1])]
    data = yf.download([s + ".NS" for s in syms], start=WARM, interval="1d", group_by="ticker",
                       auto_adjust=True, threads=True, progress=False)
    nifty = yf.download("^NSEI", start=WARM, interval="1d", auto_adjust=True, progress=False)
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)
    nc = nifty["Close"].dropna()
    n50 = nc.ewm(span=50, adjust=False).mean()
    n200 = nc.ewm(span=200, adjust=False).mean()
    regime = pd.DataFrame({"above50": nc > n50, "trend": (nc > n50) & (n50 > n200)})

    all_t = []
    for s in syms:
        try:
            all_t += signals(s, data[s + ".NS"])
        except Exception:
            continue
    t = pd.DataFrame(all_t)
    t = t.join(regime, on="signal_date")
    t[["above50", "trend"]] = t[["above50", "trend"]].fillna(False)
    t.to_csv(os.path.join(OUT, "trades.csv"), index=False)

    variants = {
        "No market filter": t,
        "Nifty > 50 EMA": t[t["above50"]],
        "Nifty > 50 EMA > 200 EMA": t[t["trend"]],
    }
    rows, prows = [], []
    for name, sub in variants.items():
        rows.append({"Variant": name, **stats(sub)})
        p, curve = portfolio(sub)
        prows.append({"Variant": name, **p})
        curve.to_csv(os.path.join(OUT, f"equity_{name.replace(' ', '_').replace('>', 'gt')}.csv"))

    setup_rows = []
    for name in ["Breakout", "Pullback", "RSI breakout"]:
        for vname, sub in [("No filter", t), ("Nifty>50EMA", t[t["above50"]])]:
            setup_rows.append({"Setup": name, "Filter": vname, **stats(sub[sub["setup"].str.contains(name)])})

    deliv_proxy = []
    for lo, hi in [(1, 1.5), (1.5, 2), (2, 3), (3, 99)]:
        sub = t[(t["vol_x"] > lo) & (t["vol_x"] <= hi)]
        deliv_proxy.append({"Volume x": f"{lo}-{hi if hi < 99 else '+'}", **stats(sub)})

    t["year"] = pd.to_datetime(t["entry_date"]).dt.year
    yr = []
    for y, g in t.groupby("year"):
        a, b = stats(g), stats(g[g["above50"]])
        yr.append({"Year": y, "Trades": a.get("Trades"), "Win %": a.get("Win %"), "Avg R": a.get("Avg R"),
                   "Filtered trades": b.get("Trades"), "Filtered Win %": b.get("Win %"), "Filtered Avg R": b.get("Avg R")})

    nb = nc[nc.index >= START]
    nyrs = (nb.index[-1] - nb.index[0]).days / 365.25
    ncagr = 100 * ((nb.iloc[-1] / nb.iloc[0]) ** (1 / nyrs) - 1)
    ndd = 100 * (nb / nb.cummax() - 1).min()

    rep = [
        f"# Swing strategy backtest — {START} to {t['exit_date'].max().date()}",
        f"Universe: {len(syms)} current Nifty 500 symbols. Costs {COST*100:.2f}% round trip. "
        f"Max hold {MAX_HOLD} days. Delivery % not tested (no free history).",
        f"Benchmark Nifty 50 (price index, no dividends): CAGR {ncagr:.1f}%, max drawdown {ndd:.1f}%.",
        "", "## Per-trade results", md(pd.DataFrame(rows)),
        "", "## Portfolio simulation (Rs 10L start, 1% risk/trade, max 10 positions, max 20% per position)",
        md(pd.DataFrame(prows)),
        "", "## By setup", md(pd.DataFrame(setup_rows)),
        "", "## By volume strength (all trades)", md(pd.DataFrame(deliv_proxy)),
        "", "## By year", md(pd.DataFrame(yr)),
        "", "Caveats: survivorship bias (stocks that left the Nifty 500 are excluded, which flatters results); "
            "Yahoo data errors; fills assume liquidity at the stop/target price; past results do not predict future returns.",
    ]
    with open(os.path.join(OUT, "report.md"), "w") as f:
        f.write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
