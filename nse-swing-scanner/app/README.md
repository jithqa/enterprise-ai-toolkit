# Swing Scan — mobile app

An installable web app (PWA) for the NSE swing scanner. It shows:

- **Today**: market-filter status (Nifty 50 vs its 50 EMA), ranked candidates with entry / stop / target, and the watchlist.
- **History**: every dated scan, a symbol filter, and names that keep reappearing.
- **Backtest**: headline stats per market-filter variant, equity curves, and the full report tables with caveats.

It works offline (last loaded data is cached) and follows the phone's light/dark setting.

## How it's published

`.github/workflows/nse-app-pages.yml` runs `build_app_data.py`, which bundles `results/` into
`app/data/data.json`, then deploys this folder to GitHub Pages. It runs after each scan or backtest
workflow, on pushes that touch the app or results, and on demand.

**One-time setup:** in the repo go to *Settings → Pages* and set *Source* to **GitHub Actions**,
then run the "NSE app (GitHub Pages)" workflow once. The app will be at
`https://<owner>.github.io/<repo>/`.

## Install on your phone

- **Android (Chrome):** open the URL, then tap *Install* in the app header or *⋮ → Add to Home screen*.
- **iPhone (Safari):** open the URL, tap *Share → Add to Home Screen*.

## Run locally

```sh
python nse-swing-scanner/build_app_data.py
cd nse-swing-scanner/app && python -m http.server 8000
# open http://localhost:8000
```

`app/data/` is generated and git-ignored.
