"""
Bundle scanner output into one JSON file for the mobile app (app/data/data.json).

Reads results/*.csv, results/latest.md and results/backtest/*; stdlib only so the
Pages workflow needs no installs. Run: python nse-swing-scanner/build_app_data.py
"""
import csv
import datetime as dt
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
BT = os.path.join(RES, "backtest")
OUT = os.path.join(HERE, "app", "data", "data.json")
DATE_CSV = re.compile(r"^\d{4}-\d{2}-\d{2}\.csv$")


def num(v):
    if v is None or v == "":
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() and "." not in v else f
    except ValueError:
        return v


def read_csv(path):
    with open(path, newline="") as f:
        return [{k: num(v) for k, v in row.items()} for row in csv.DictReader(f) if any(row.values())]


def md_tables(text):
    """Return {section heading: [row dicts]} for every markdown table under a ## heading."""
    tables, heading, header = {}, None, None
    for line in text.splitlines():
        if line.startswith("## "):
            heading, header = line[3:].strip(), None
        elif line.startswith("|") and heading:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header is None:
                header = cells
            elif not all(set(c) <= set("-:") for c in cells):
                tables.setdefault(heading, []).append({h: num(c) for h, c in zip(header, cells)})
        else:
            header = None
    return tables


def latest():
    path = os.path.join(RES, "latest.md")
    if not os.path.exists(path):
        return {}
    text = open(path).read()
    as_of = re.search(r"data as of (\S+)", text)
    generated = re.search(r"Generated ([^.]+UTC)", text)
    regime = next((l for l in text.splitlines() if "MARKET FILTER" in l or "market filter not checked" in l), "")
    filt = "on" if "FILTER ON" in regime else "off" if "FILTER OFF" in regime else "unknown"
    nifty = re.search(r"Nifty 50 (\d+) vs 50 EMA (\d+)", regime)
    tables = md_tables(text)
    return {
        "as_of": as_of.group(1) if as_of else None,
        "generated": generated.group(1) if generated else None,
        "market_filter": filt,
        "nifty": int(nifty.group(1)) if nifty else None,
        "nifty_ema50": int(nifty.group(2)) if nifty else None,
        "regime": regime.replace("**", ""),
        "watchlist": next((v for k, v in tables.items() if k.startswith("Watchlist")), []),
    }


def scans():
    out = []
    for path in sorted(glob.glob(os.path.join(RES, "*.csv")), reverse=True):
        name = os.path.basename(path)
        if DATE_CSV.match(name):
            out.append({"date": name[:-4], "candidates": read_csv(path)})
    return out


def equity(path, step=5):
    """Downsample an equity curve (index,value CSV) to every `step`th row plus the last."""
    with open(path, newline="") as f:
        rows = [r for r in csv.reader(f)][1:]
    rows = [(d, round(float(v))) for d, v in rows if d and v]
    keep = rows[::step]
    if rows and keep[-1] != rows[-1]:
        keep.append(rows[-1])
    return keep


def backtest():
    path = os.path.join(BT, "report.md")
    if not os.path.exists(path):
        return None
    text = open(path).read()
    lines = text.splitlines()
    caveats = next((l for l in lines if l.startswith("Caveats")), "")
    curves = {}
    for p in sorted(glob.glob(os.path.join(BT, "equity_*.csv"))):
        label = os.path.basename(p)[7:-4].replace("_gt_", " > ").replace("_", " ")
        curves[label] = equity(p)
    return {
        "title": lines[0].lstrip("# ").strip() if lines else "",
        "notes": [l for l in lines[1:4] if l.strip()],
        "tables": md_tables(text),
        "caveats": caveats,
        "equity": curves,
    }


def main():
    data = {
        "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "latest": latest(),
        "scans": scans(),
        "backtest": backtest(),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"Wrote {OUT}: {len(data['scans'])} scans, {os.path.getsize(OUT) // 1024} KB")


if __name__ == "__main__":
    main()
