const state = {
  payload: null,
  rows: [],
  selected: null,
  filter: "all",
  sector: "all",
  query: "",
  sortKey: "mcap",
  sortDir: -1,
};

const $ = (selector) => document.querySelector(selector);
const rowsBody = $("#rowsBody");
const statusText = $("#statusText");
const searchInput = $("#searchInput");
const sectorSelect = $("#sectorSelect");
const detailContent = $("#detailContent");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return entities[char];
  });
}

function number(value) {
  if (value === null || value === undefined || value === 0) return "-";
  return Number(value).toLocaleString("ko-KR", { maximumFractionDigits: 1 });
}

function mcap(value) {
  if (!value) return "-";
  if (value >= 10000) return `${(value / 10000).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}조`;
  return `${Math.round(value).toLocaleString("ko-KR")}억`;
}

function pct(value) {
  if (value === null || value === undefined) return "-";
  return `${Number(value).toFixed(1)}%`;
}

function ratio(value) {
  if (value === null || value === undefined) return "입력부족";
  return pct(value * 100);
}

function qualityLabel(row) {
  if (row.qualityPass) return "통과";
  if (row.ttmRev <= 0) return "재무없음";
  return "탈락";
}

function qualityClass(row) {
  if (row.qualityPass) return "pass";
  if (row.ttmRev <= 0) return "warn";
  return "fail";
}

function signedClass(value) {
  if (value === null || value === undefined || value === 0) return "";
  return value > 0 ? "positive" : "negative";
}

function renderSummary(payload) {
  const coverage = payload.summary.count
    ? Math.round((payload.summary.financialCount / payload.summary.count) * 100)
    : 0;
  $("#countMetric").textContent = payload.summary.count;
  $("#mcapMetric").textContent = `시총 합계 ${mcap(payload.summary.totalMcap)}`;
  $("#financialMetric").textContent = `${coverage}%`;
  $("#regimeMetric").textContent = payload.regime.tag;
  $("#regimeSubMetric").textContent = `3M ${pct(payload.regime.ret3m)} / 52W ${pct(payload.regime.off52w)}`;
  $("#hurdleMetric").textContent = ratio(payload.hurdle.hurdle);
  $("#hurdleSubMetric").textContent = payload.hurdle.top3.length ? payload.hurdle.top3.join(", ") : "품질 통과 3종목 미만";
  $("#railMeta").textContent = `${payload.summary.count} names`;
}

function renderSectors(payload) {
  const current = sectorSelect.value || "all";
  sectorSelect.innerHTML = `<option value="all">전체</option>${payload.sectors
    .map((sector) => `<option value="${escapeHtml(sector)}">${escapeHtml(sector)}</option>`)
    .join("")}`;
  sectorSelect.value = payload.sectors.includes(current) ? current : "all";
  state.sector = sectorSelect.value;
}

function filteredRows() {
  const query = state.query.trim().toLowerCase();
  return state.rows
    .filter((row) => state.sector === "all" || row.sector === state.sector)
    .filter((row) => !query || row.ticker.toLowerCase().includes(query) || row.sector.toLowerCase().includes(query))
    .filter((row) => {
      if (state.filter === "pass") return row.qualityPass;
      if (state.filter === "missing") return row.ttmRev <= 0;
      if (state.filter === "fail") return !row.qualityPass && row.ttmRev > 0;
      return true;
    })
    .sort((a, b) => {
      const left = state.sortKey === "quality" ? qualityLabel(a) : a[state.sortKey];
      const right = state.sortKey === "quality" ? qualityLabel(b) : b[state.sortKey];
      if (typeof left === "string" || typeof right === "string") {
        return String(left).localeCompare(String(right), "ko-KR") * state.sortDir;
      }
      return ((left || 0) - (right || 0)) * state.sortDir;
    });
}

function renderRail(rows) {
  const bars = rows.slice(0, 20).map((row) => {
    const raw = row.ret3m ?? 0;
    const height = Math.max(8, Math.min(72, Math.abs(raw) * 1.2 + 10));
    const tone = raw >= 15 ? "hot" : raw < 0 ? "cold" : "";
    return `<div class="railBar ${tone}" title="${row.ticker} ${pct(row.ret3m)}" style="height:${height}px"></div>`;
  });
  $("#momentumRail").innerHTML = bars.join("");
}

function renderRows() {
  const rows = filteredRows();
  if (!state.selected && rows.length) state.selected = rows[0].ticker;
  rowsBody.innerHTML = rows
    .map((row) => {
    const selected = row.ticker === state.selected ? "selected" : "";
      const ticker = escapeHtml(row.ticker);
      return `<tr class="${selected}" data-ticker="${ticker}">
        <td><button class="tickerButton" type="button" data-ticker="${ticker}">${ticker}</button></td>
        <td>${mcap(row.mcap)}</td>
        <td class="${signedClass(row.ret3m)}">${pct(row.ret3m)}</td>
        <td class="${signedClass(row.off52w)}">${pct(row.off52w)}</td>
        <td><span class="pill ${qualityClass(row)}">${qualityLabel(row)}</span></td>
        <td>${ratio(row.rStar)}</td>
      </tr>`;
    })
    .join("");
  renderDetail(rows.find((row) => row.ticker === state.selected) || rows[0]);
}

function renderDetail(row) {
  if (!row) {
    detailContent.innerHTML = `<p class="empty">표시할 종목이 없습니다.</p>`;
    return;
  }
  const fails = row.qualityFails.length ? row.qualityFails.join(", ") : "없음";
  detailContent.innerHTML = `<div class="detailTitle">
    <strong>${escapeHtml(row.ticker)}</strong>
    <span class="pill ${qualityClass(row)}">${qualityLabel(row)}</span>
  </div>
  <div class="factGrid">
    <div class="fact"><span>시총</span><strong>${mcap(row.mcap)}</strong></div>
    <div class="fact"><span>r*</span><strong>${ratio(row.rStar)}</strong></div>
    <div class="fact"><span>3M</span><strong class="${signedClass(row.ret3m)}">${pct(row.ret3m)}</strong></div>
    <div class="fact"><span>52W 고점비</span><strong class="${signedClass(row.off52w)}">${pct(row.off52w)}</strong></div>
    <div class="fact"><span>TTM 매출</span><strong>${number(row.ttmRev)}</strong></div>
    <div class="fact"><span>ROIC</span><strong>${pct(row.roic)}</strong></div>
  </div>
  <p class="empty">섹터 ${escapeHtml(row.sector || "-")} · 실패 사유 ${escapeHtml(fails)}</p>`;
}

function render(payload) {
  state.payload = payload;
  state.rows = payload.rows;
  renderSummary(payload);
  renderSectors(payload);
  renderRail(payload.rows);
  renderRows();
}

async function loadState() {
  statusText.textContent = "데이터 로딩";
  const response = await fetch("/api/state");
  if (!response.ok) throw new Error("state request failed");
  render(await response.json());
  statusText.textContent = "대기";
}

async function postState(path, fallbackMessage) {
  const response = await fetch(path, { method: "POST" });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || fallbackMessage);
  return payload;
}

async function refreshUniverse() {
  const button = $("#refreshButton");
  button.disabled = true;
  statusText.textContent = "Yahoo 갱신 중";
  const payload = await postState("/api/refresh", "refresh request failed");
  render(payload);
  const kept = payload.refresh ? payload.refresh.preservedCount : 0;
  statusText.textContent = `갱신 완료 · 재무 보존 ${kept}`;
  button.disabled = false;
}

async function fillFinancials() {
  const button = $("#financialsButton");
  button.disabled = true;
  statusText.textContent = "DART 재무 입력 중";
  const payload = await postState("/api/financials", "financial request failed");
  render(payload);
  const count = payload.financials ? payload.financials.filledCount : 0;
  statusText.textContent = `재무 입력 완료 · ${count}건`;
  button.disabled = false;
}

function bindEvents() {
  $("#reloadButton").addEventListener("click", () => loadState().catch(showError));
  $("#refreshButton").addEventListener("click", () => refreshUniverse().catch(showError));
  $("#financialsButton").addEventListener("click", () => fillFinancials().catch(showError));
  searchInput.addEventListener("input", (event) => {
    state.query = event.target.value;
    renderRows();
  });
  sectorSelect.addEventListener("change", (event) => {
    state.sector = event.target.value;
    renderRows();
  });
  document.querySelectorAll(".segment").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".segment").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      state.filter = button.dataset.filter;
      renderRows();
    });
  });
  document.querySelectorAll("th button").forEach((button) => {
    button.addEventListener("click", () => {
      const next = button.dataset.sort;
      state.sortDir = state.sortKey === next ? state.sortDir * -1 : -1;
      state.sortKey = next;
      renderRows();
    });
  });
  rowsBody.addEventListener("click", (event) => {
    const ticker = event.target.closest("[data-ticker]")?.dataset.ticker;
    if (!ticker) return;
    state.selected = ticker;
    renderRows();
  });
}

function showError(error) {
  $("#refreshButton").disabled = false;
  $("#financialsButton").disabled = false;
  statusText.textContent = "오류";
  detailContent.innerHTML = `<p class="empty">${error.message}</p>`;
}

bindEvents();
loadState().catch(showError);
