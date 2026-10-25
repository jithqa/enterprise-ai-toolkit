"use strict";

const DATA_URL = "data/data.json";
const $ = (sel) => document.querySelector(sel);
const state = { data: null, view: "today", variant: null };

// ---------- helpers ----------

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const fmt = (v, digits = 2) => {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v !== "number") return esc(v);
  return v.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: digits });
};

const fmtDate = (iso, opts = { weekday: "short", day: "numeric", month: "short" }) => {
  if (!iso) return "—";
  const d = new Date(iso + "T00:00:00");
  return isNaN(d) ? esc(iso) : d.toLocaleDateString("en-IN", opts);
};

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => { el.hidden = true; }, 2600);
}

// ---------- data ----------

async function load(force = false) {
  const btn = $("#refresh");
  btn.classList.add("spin");
  try {
    const res = await fetch(DATA_URL, { cache: force ? "reload" : "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.data = await res.json();
    render();
    if (force) toast("Updated");
  } catch (err) {
    if (!state.data) {
      $("#asof").textContent = "Couldn't load data";
      $("#view-today").innerHTML = `<div class="empty">Couldn't load scan data (${esc(err.message)}).<br>Check your connection and tap refresh.</div>`;
    } else {
      toast("Offline — showing saved data");
    }
  } finally {
    btn.classList.remove("spin");
  }
}

// ---------- shared pieces ----------

function setupBadges(setup) {
  return String(setup || "").split("+").map((s) => s.trim()).filter(Boolean)
    .map((s) => `<span class="badge">${esc(s)}</span>`).join("");
}

function rangeBar(c) {
  const { Stop: stop, Entry: entry, Target_1to2: target, Price: price } = c;
  if (![stop, entry, target, price].every((v) => typeof v === "number") || target <= stop) return "";
  const pos = (v) => Math.min(100, Math.max(0, ((v - stop) / (target - stop)) * 100)).toFixed(1);
  return `
    <div class="range" style="--e:${pos(entry)}%" role="img"
         aria-label="Price ${fmt(price)} between stop ${fmt(stop)} and target ${fmt(target)}">
      <i style="left:${pos(price)}%"></i>
    </div>
    <div class="range-labels"><span>Stop</span><span>Price ${fmt(price)}</span><span>Target</span></div>`;
}

function candidateCard(c, i) {
  const sym = esc(c.Symbol);
  const enc = encodeURIComponent(c.Symbol);
  return `
    <article class="card">
      <div class="card-head">
        <span class="sym"><span class="rank">#${i + 1}</span>${sym}</span>
        <span class="price num">₹${fmt(c.Price)}</span>
      </div>
      <div class="badges">${setupBadges(c.Setup)}</div>
      <div class="levels num">
        <div class="entry"><small>Entry above</small><b>${fmt(c.Entry)}</b></div>
        <div class="stop"><small>Stop</small><b>${fmt(c.Stop)}</b></div>
        <div class="target"><small>Target (1:2)</small><b>${fmt(c.Target_1to2)}</b></div>
      </div>
      ${rangeBar(c)}
      <details class="more">
        <summary>Details · risk ${fmt(c["Risk_%"], 1)}%</summary>
        <dl class="stats num">
          <div><dt>RSI 14</dt><dd>${fmt(c.RSI14, 1)}</dd></div>
          <div><dt>Volume ×20d</dt><dd>${fmt(c.Vol_x20d)}</dd></div>
          <div><dt>Delivery %</dt><dd>${fmt(c["Deliv_%"], 1)}</dd></div>
          <div><dt>Risk %</dt><dd>${fmt(c["Risk_%"], 1)}</dd></div>
          <div><dt>ATR %</dt><dd>${fmt(c["ATR_%"])}</dd></div>
          <div><dt>Avg value ₹Cr</dt><dd>${fmt(c.AvgVal_Cr, 1)}</dd></div>
        </dl>
        <div class="links">
          <a href="https://www.nseindia.com/get-quotes/equity?symbol=${enc}" target="_blank" rel="noopener">NSE quote</a>
          <a href="https://www.tradingview.com/chart/?symbol=NSE%3A${enc}" target="_blank" rel="noopener">Chart</a>
        </div>
      </details>
    </article>`;
}

// ---------- views ----------

function renderToday() {
  const { latest = {}, scans = [] } = state.data;
  const today = scans.find((s) => s.date === latest.as_of) || scans[0];
  const filter = latest.market_filter;
  const bannerTitle = filter === "on" ? "Market filter ON — new longs allowed"
    : filter === "off" ? "Market filter OFF — no new longs"
    : "Market filter not checked";
  const bannerText = latest.nifty
    ? `Nifty 50 ${fmt(latest.nifty, 0)} vs 50-day EMA ${fmt(latest.nifty_ema50, 0)}.` +
      (filter === "off" ? " Candidates below are for reference only." : "")
    : "Nifty data was unavailable for this scan.";

  const cands = today?.candidates || [];
  const watch = latest.watchlist || [];

  $("#view-today").innerHTML = `
    <div class="banner ${filter === "on" ? "on" : filter === "off" ? "off" : ""}">
      <strong>${bannerTitle}</strong>
      <p>${bannerText}</p>
    </div>

    <h2>Candidates <span class="muted">· ${today ? fmtDate(today.date) : "—"}</span></h2>
    ${cands.length ? `<div class="cards">${cands.map(candidateCard).join("")}</div>`
      : `<div class="empty">No high-conviction setups in this scan.</div>`}

    <h2>Watchlist <span class="muted">· approaching setup</span></h2>
    ${watch.length ? `<div class="list">${watch.map((w) => `
      <div class="row">
        <div><b>${esc(w.Symbol)}</b><div class="sub">${esc(w.Note)}</div></div>
        <div class="right num">₹${fmt(w.Price)}<div class="sub">RSI ${fmt(w.RSI14, 1)} · Vol ×${fmt(w.Vol_x20d)}</div></div>
      </div>`).join("")}</div>`
      : `<div class="empty">Nothing on the watchlist.</div>`}
  `;
}

function renderHistory() {
  const scans = state.data.scans || [];
  const root = $("#view-history");
  const counts = {};
  scans.forEach((s) => s.candidates.forEach((c) => { counts[c.Symbol] = (counts[c.Symbol] || 0) + 1; }));
  const frequent = Object.entries(counts).filter(([, n]) => n > 1).sort((a, b) => b[1] - a[1]).slice(0, 12);

  root.innerHTML = `
    <input id="hist-search" class="search" type="search" placeholder="Filter by symbol" autocomplete="off"
           autocapitalize="characters" spellcheck="false" aria-label="Filter history by symbol">
    ${frequent.length ? `
      <h2>Repeat names <span class="muted">· last ${scans.length} scans</span></h2>
      <div class="freq">${frequent.map(([s, n]) =>
        `<button class="chip" data-sym="${esc(s)}">${esc(s)} ×${n}</button>`).join("")}</div>` : ""}
    <h2>Scans</h2>
    <div id="hist-list"></div>`;

  const list = $("#hist-list");
  const draw = (q) => {
    q = q.trim().toUpperCase();
    const days = scans.map((s) => ({ ...s, candidates: s.candidates.filter((c) => !q || String(c.Symbol).includes(q)) }))
      .filter((s) => !q || s.candidates.length);
    list.innerHTML = days.length ? days.map((s, i) => `
      <details class="day" ${i === 0 || q ? "open" : ""}>
        <summary><span>${fmtDate(s.date)}</span><span class="count">${s.candidates.length} pick${s.candidates.length === 1 ? "" : "s"}</span></summary>
        ${s.candidates.length ? `<div class="list">${s.candidates.map((c) => `
          <div class="row">
            <div><b>${esc(c.Symbol)}</b><div class="sub">${esc(c.Setup)}</div></div>
            <div class="right num">₹${fmt(c.Price)}<div class="sub">E ${fmt(c.Entry)} · S ${fmt(c.Stop)} · T ${fmt(c.Target_1to2)}</div></div>
          </div>`).join("")}</div>` : `<div class="list"><div class="row muted">No setups</div></div>`}
      </details>`).join("") : `<div class="empty">No scans match “${esc(q)}”.</div>`;
    root.querySelectorAll(".freq .chip").forEach((b) => b.classList.toggle("on", b.dataset.sym === q));
  };

  const input = $("#hist-search");
  input.addEventListener("input", () => draw(input.value));
  root.querySelectorAll(".freq .chip").forEach((b) => b.addEventListener("click", () => {
    input.value = input.value.toUpperCase() === b.dataset.sym ? "" : b.dataset.sym;
    draw(input.value);
  }));
  draw("");
}

function equityChart(curves) {
  const names = Object.keys(curves);
  if (!names.length) return "";
  const colors = ["var(--line-1)", "var(--line-2)", "var(--line-3)"];
  const series = names.map((n) => curves[n].map(([d, v]) => [Date.parse(d), v / 1e5]));
  const all = series.flat();
  const x0 = Math.min(...all.map((p) => p[0])), x1 = Math.max(...all.map((p) => p[0]));
  const y0 = 0, y1 = Math.ceil(Math.max(...all.map((p) => p[1])) / 5) * 5;
  const W = 340, H = 190, L = 30, R = 6, T = 8, B = 20;
  const sx = (x) => L + ((x - x0) / (x1 - x0 || 1)) * (W - L - R);
  const sy = (y) => T + (1 - (y - y0) / (y1 - y0 || 1)) * (H - T - B);
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => y0 + f * (y1 - y0));
  const startY = new Date(x0).getFullYear(), endY = new Date(x1).getFullYear();
  const step = Math.max(1, Math.ceil((endY - startY) / 5));
  const xTicks = [];
  for (let y = startY + 1; y <= endY; y += step) xTicks.push(y);

  return `
    <div class="chart">
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Portfolio equity curves in lakh rupees">
        ${yTicks.map((y) => `<line class="grid" x1="${L}" x2="${W - R}" y1="${sy(y)}" y2="${sy(y)}"/>
          <text x="${L - 4}" y="${sy(y) + 3}" text-anchor="end">${fmt(y, 0)}</text>`).join("")}
        ${xTicks.map((y) => `<text x="${sx(Date.UTC(y, 0, 1))}" y="${H - 5}" text-anchor="middle">${y}</text>`).join("")}
        <line x1="${L}" x2="${W - R}" y1="${sy(10)}" y2="${sy(10)}" stroke="var(--muted)" stroke-dasharray="3 3" stroke-width="1"/>
        ${series.map((pts, i) => `<polyline fill="none" stroke="${colors[i % colors.length]}" stroke-width="1.6"
          stroke-linejoin="round" points="${pts.map(([x, y]) => `${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join(" ")}"/>`).join("")}
      </svg>
      <div class="legend">${names.map((n, i) => `<span><i style="background:${colors[i % colors.length]}"></i>${esc(n)}</span>`).join("")}
        <span>Dashed: ₹10L start · values in ₹ lakh</span></div>
    </div>`;
}

function table(rows, signCols = /Avg R|Avg trade|CAGR/) {
  if (!rows?.length) return "";
  const cols = Object.keys(rows[0]);
  return `<div class="table-wrap"><table class="num">
    <thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${cols.map((c) => {
      const v = r[c];
      const cls = signCols.test(c) && typeof v === "number" ? (v > 0 ? "pos" : v < 0 ? "neg" : "") : "";
      return `<td class="${cls}">${fmt(v, 3)}</td>`;
    }).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function renderBacktest() {
  const bt = state.data.backtest;
  const root = $("#view-backtest");
  if (!bt) { root.innerHTML = `<div class="empty">No backtest report available yet.</div>`; return; }

  const t = bt.tables || {};
  const per = t["Per-trade results"] || [];
  const portKey = Object.keys(t).find((k) => k.startsWith("Portfolio simulation"));
  const port = portKey ? t[portKey] : [];
  const variants = per.map((r) => r.Variant);
  if (!variants.includes(state.variant)) state.variant = variants.includes("Nifty > 50 EMA") ? "Nifty > 50 EMA" : variants[0];
  const p = per.find((r) => r.Variant === state.variant) || {};
  const s = port.find((r) => r.Variant === state.variant) || {};

  root.innerHTML = `
    <h2>${esc(bt.title)}</h2>
    ${bt.notes.map((n) => `<p class="note">${esc(n)}</p>`).join("")}

    <h2>Variant</h2>
    <div class="seg">${variants.map((v) =>
      `<button class="chip ${v === state.variant ? "on" : ""}" data-variant="${esc(v)}">${esc(v)}</button>`).join("")}</div>

    <div class="kpis num" style="margin-top:10px">
      <div class="kpi"><small>Win rate</small><b>${fmt(p["Win %"], 1)}%</b><span> of ${fmt(p.Trades, 0)} trades</span></div>
      <div class="kpi"><small>Profit factor</small><b>${fmt(p["Profit factor"])}</b><span> avg ${fmt(p["Avg R"], 3)} R</span></div>
      <div class="kpi"><small>Portfolio CAGR</small><b>${fmt(s["CAGR %"], 1)}%</b><span> final ₹${fmt(s["Final equity (Rs L)"], 1)}L</span></div>
      <div class="kpi"><small>Max drawdown</small><b>${fmt(s["Max drawdown % (closed trades)"], 1)}%</b><span> closed trades</span></div>
    </div>

    <h2>Equity curves</h2>
    ${equityChart(bt.equity || {})}
    ${portKey ? `<p class="note">${esc(portKey)}</p>` : ""}

    ${Object.entries(t).filter(([k]) => k !== portKey).map(([k, rows]) => `<h2>${esc(k)}</h2>${table(rows)}`).join("")}

    ${bt.caveats ? `<div class="banner off" style="margin-top:20px"><strong>Read before relying on this</strong><p>${esc(bt.caveats.replace(/^Caveats:\s*/, ""))}</p></div>` : ""}
  `;

  root.querySelectorAll("[data-variant]").forEach((b) => b.addEventListener("click", () => {
    state.variant = b.dataset.variant;
    renderBacktest();
  }));
}

function render() {
  const { latest = {}, built } = state.data;
  $("#asof").textContent = latest.as_of
    ? `Data as of ${fmtDate(latest.as_of, { day: "numeric", month: "short", year: "numeric" })}`
    : `Built ${built || "—"}`;
  $("#asof").title = latest.generated ? `Scan generated ${latest.generated}` : "";
  renderToday();
  renderHistory();
  renderBacktest();
}

// ---------- navigation ----------

function show(view) {
  state.view = view;
  document.querySelectorAll(".view").forEach((v) => { v.hidden = v.id !== `view-${view}`; });
  document.querySelectorAll(".tabs button").forEach((b) => {
    const on = b.dataset.view === view;
    b.classList.toggle("active", on);
    if (on) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
  });
  if (location.hash !== `#${view}`) history.replaceState(null, "", `#${view}`);
  window.scrollTo(0, 0);
}

const VIEWS = ["today", "history", "backtest"];
const viewFromHash = () => (VIEWS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "today");

document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => show(b.dataset.view)));
window.addEventListener("hashchange", () => { if (viewFromHash() !== state.view) show(viewFromHash()); });
$("#refresh").addEventListener("click", () => load(true));

// ---------- install / offline ----------

let deferredPrompt = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  $("#install").hidden = false;
});
$("#install").addEventListener("click", async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  $("#install").hidden = true;
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && state.data) load();
});

$("#view-today").innerHTML = `<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>`;
show(viewFromHash());
load();
