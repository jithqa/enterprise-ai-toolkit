"""
NSE swing-trade scanner (EOD). Runs daily via GitHub Actions; writes results/latest.md and a dated CSV.

Filters: close > EMA50 > EMA200; RSI14 40-65; ATR14 >= 1.5% of price;
20d avg traded value > Rs10 cr; latest volume > 20d avg volume.
Setups: A Breakout (close > prior 20-day high), B Pullback (low within 2% of EMA50 +
bullish reversal candle), C RSI cross above 60.
Bonus: delivery % from NSE's full bhavcopy (best effort; blank if NSE blocks the download).
Market filter: only take new longs when Nifty 50 closes above its 50 EMA (see backtest.py and
results/backtest/report.md; the edge is thin, so treat signals as a shortlist, not a system).
Data is end-of-day from Yahoo Finance and can be delayed or wrong; verify on your broker chart.
"""
import io, os, sys, datetime as dt
import pandas as pd
import requests
import yfinance as yf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
CACHE = os.path.join(HERE, "symbols.txt")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "*/*"}
UNIVERSE_URLS = [
    "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
]


def load_universe():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            return [s.strip().upper() for s in f if s.strip()], "file"
    for url in UNIVERSE_URLS:
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            syms = pd.read_csv(io.StringIO(r.text))["Symbol"].str.strip().tolist()
            if len(syms) > 400:
                with open(CACHE, "w") as f:
                    f.write("\n".join(syms))
                return syms, url
        except Exception:
            continue
    if os.path.exists(CACHE):
        with open(CACHE) as f:
            return [s.strip() for s in f if s.strip()], "cached symbols.txt"
    raise SystemExit("Could not load Nifty 500 list from NSE and no cached symbols.txt")


def load_delivery(day):
    """NSE full bhavcopy with DELIV_PER. Returns {symbol: pct} or {} on failure."""
    url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{day:%d%m%Y}.csv"
    try:
        r = requests.get(url, headers=UA, timeout=30)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = df.columns.str.strip()
        df = df[df["SERIES"].str.strip() == "EQ"]
        return dict(zip(df["SYMBOL"].str.strip(), pd.to_numeric(df["DELIV_PER"], errors="coerce")))
    except Exception:
        return {}


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def atr(df, n=14):
    pc = df["Close"].shift()
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - pc).abs(), (df["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def analyse(sym, df, watch):
    df = df.dropna()
    if len(df) < 210:
        return None
    c, h, l, o, v = df["Close"], df["High"], df["Low"], df["Open"], df["Volume"]
    e50, e200 = c.ewm(span=50, adjust=False).mean(), c.ewm(span=200, adjust=False).mean()
    r, a = rsi(c), atr(df)
    avg_vol20 = v.rolling(20).mean().shift(1)
    avg_val20 = (c * v).rolling(20).mean()
    px = c.iloc[-1]
    if avg_vol20.iloc[-1] == 0 or pd.isna(avg_vol20.iloc[-1]):
        return None
    vol_x = v.iloc[-1] / avg_vol20.iloc[-1]

    trend = px > e50.iloc[-1] > e200.iloc[-1]
    liquid = avg_val20.iloc[-1] >= 10e7
    atr_ok = a.iloc[-1] / px * 100 >= 1.5
    if not (trend and liquid and atr_ok):
        return None
    hi20 = h.iloc[-21:-1].max()

    if not (40 <= r.iloc[-1] <= 65 and vol_x > 1):
        # Watchlist: trend/liquidity/ATR pass, RSI 55-65, within 3% of 20-day high
        if 55 <= r.iloc[-1] <= 65 and px >= hi20 * 0.97:
            watch.append({"Symbol": sym, "Price": round(px, 2), "RSI14": round(r.iloc[-1], 1),
                          "Vol_x20d": round(vol_x, 2), "Note": f"{(hi20/px-1)*100:.1f}% below 20d high {hi20:.2f}"})
        return None

    setups, stop = [], None
    if px > hi20:
        setups.append("Breakout")
        stop = min(l.iloc[-1], hi20 - 0.5 * a.iloc[-1])
    near_ema = l.iloc[-1] <= e50.iloc[-1] * 1.02 and px > e50.iloc[-1]
    body = px - o.iloc[-1]
    lower_wick = min(o.iloc[-1], px) - l.iloc[-1]
    bullish = (body > 0 and px > h.iloc[-2]) or (lower_wick > 2 * abs(body) and px > o.iloc[-1])
    if near_ema and bullish:
        setups.append("Pullback")
        s = min(l.iloc[-3:].min(), e50.iloc[-1] - 0.5 * a.iloc[-1])
        stop = s if stop is None else min(stop, s)
    if r.iloc[-2] < 60 <= r.iloc[-1]:
        setups.append("RSI breakout")
        s = l.iloc[-1] - 0.5 * a.iloc[-1]
        stop = s if stop is None else min(stop, s)
    if not setups:
        return None

    entry = round(h.iloc[-1] * 1.002, 2)
    risk = entry - stop
    if risk <= 0:
        return None
    rsi_score = 1 - abs(r.iloc[-1] - 57) / 17
    return {
        "Symbol": sym, "Price": round(px, 2), "Setup": " + ".join(setups),
        "RSI14": round(r.iloc[-1], 1), "Vol_x20d": round(vol_x, 2),
        "Entry": entry, "Stop": round(stop, 2), "Target_1to2": round(entry + 2 * risk, 2),
        "Risk_%": round(risk / entry * 100, 1), "ATR_%": round(a.iloc[-1] / px * 100, 2),
        "AvgVal_Cr": round(avg_val20.iloc[-1] / 1e7, 1),
        "Score": round(min(vol_x, 3) / 3 * 0.6 + rsi_score * 0.4 + 0.1 * (len(setups) - 1), 3),
        "Date": str(df.index[-1].date()),
    }


def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(x) else str(x) for x in row) + " |")
    return "\n".join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    syms, src = load_universe()
    data = yf.download([s + ".NS" for s in syms], period="18mo", interval="1d",
                       group_by="ticker", auto_adjust=True, threads=True, progress=False)
    rows, watch, ok, last_date = [], [], 0, None
    for s in syms:
        try:
            d = data[s + ".NS"].dropna()
            if len(d):
                ok += 1
                last_date = max(last_date, d.index[-1]) if last_date is not None else d.index[-1]
            out = analyse(s, d, watch)
            if out:
                rows.append(out)
        except Exception:
            continue

    bar = last_date.date() if last_date is not None else None
    deliv = load_delivery(bar) if bar else {}
    now = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Market filter: Nifty 50 close above its 50 EMA (backtest 2015-2026 favoured this)
    market_on, regime = None, "Nifty data unavailable — market filter not checked"
    try:
        n = yf.download("^NSEI", period="2y", interval="1d", auto_adjust=True, progress=False)
        if isinstance(n.columns, pd.MultiIndex):
            n.columns = n.columns.get_level_values(0)
        nc = n["Close"].dropna()
        ne50 = nc.ewm(span=50, adjust=False).mean()
        market_on = bool(nc.iloc[-1] > ne50.iloc[-1])
        regime = (f"Nifty 50 {nc.iloc[-1]:.0f} vs 50 EMA {ne50.iloc[-1]:.0f} ({nc.index[-1].date()}) — "
                  + ("**MARKET FILTER ON: new longs allowed**" if market_on
                     else "**MARKET FILTER OFF: no new longs; candidates below are for reference only**"))
    except Exception:
        pass

    md = [f"# NSE swing scan — data as of {bar}",
          f"Generated {now}. Universe: {len(syms)} symbols ({src}); price data for {ok}. "
          f"Delivery %: {'loaded' if deliv else 'unavailable (NSE download blocked)'}.", "", regime, ""]

    if rows:
        res = pd.DataFrame(rows).sort_values("Score", ascending=False).head(10)
        res.insert(5, "Deliv_%", res["Symbol"].map(deliv).round(1) if deliv else None)
        res.drop(columns="Score").to_csv(os.path.join(OUT, f"{bar}.csv"), index=False)
        md += ["## Candidates (ranked)", md_table(res.drop(columns=["Score", "Date"]))]
    else:
        md += ["## No high-conviction setups today"]
        pd.DataFrame().to_csv(os.path.join(OUT, f"{bar}.csv"), index=False)
    if watch:
        w = pd.DataFrame(watch).sort_values("RSI14", ascending=False).head(5)
        md += ["", "## Watchlist (approaching setup)", md_table(w)]

    with open(os.path.join(OUT, "latest.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
