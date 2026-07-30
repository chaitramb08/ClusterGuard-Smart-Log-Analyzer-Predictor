const LEVEL_COLORS = {
  V: "#8B93A1",
  D: "#4FA3F7",
  I: "#4CD787",
  W: "#F5A623",
  E: "#F14C4C",
};
const LEVEL_ORDER = ["V", "D", "I", "W", "E"];

let currentLevel = "";

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// ---------- Hero status ----------

function renderStatus(prediction) {
  const word = document.getElementById("status-word");
  const detail = document.getElementById("status-detail");
  const score = document.getElementById("score-value");

  if (!prediction || prediction.error) {
    word.textContent = "NO MODEL YET";
    word.className = "status-word status-loading";
    detail.textContent = "Train the model (model/train_model.py) to enable predictions.";
    score.textContent = "—";
    return;
  }

  if (prediction.is_anomaly) {
    word.textContent = "AT RISK";
    word.className = "status-word status-risk";
    detail.textContent = "The most recent activity window looks abnormal — elevated error/warn traffic or unusual event diversity.";
  } else {
    word.textContent = "NORMAL";
    word.className = "status-word status-normal";
    detail.textContent = "The most recent activity window is within the range of normal log traffic.";
  }
  score.textContent = prediction.anomaly_score.toFixed(5);
}
// ---------- Forecast (trend-based) ----------

function renderForecast(trend) {
  const dot = document.getElementById("forecast-dot");
  const message = document.getElementById("forecast-message");

  if (!trend || trend.error) {
    dot.className = "forecast-dot";
    message.textContent = trend && trend.error === "not enough windows yet to compute a trend"
      ? "Not enough activity yet to forecast a trend."
      : "Forecast unavailable — train the model to enable it.";
    return;
  }

  dot.className = `forecast-dot ${trend.will_be_at_risk ? "risk" : "stable"}`;
  message.textContent = trend.message;
}

// ---------- Stat tiles ----------

// ---------- Stat tiles ----------

function renderStats(summary, windowFeatures) {
  const byLevel = summary.by_level || {};
  setText("stat-total", summary.total_logs.toLocaleString());
  setText("stat-info", (byLevel.I || 0).toLocaleString());
  setText("stat-warn", (byLevel.W || 0).toLocaleString());
  setText("stat-error", (byLevel.E || 0).toLocaleString());

  const anomalous = windowFeatures.filter(w => w.is_anomaly).length;
  setText("stat-anomalous", `${anomalous} / ${windowFeatures.length}`);
}

// ---------- Pulse strip (signature element) ----------

function renderPulse(windowFeatures) {
  const canvas = document.getElementById("pulse-canvas");
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 600;
  const height = 140;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  if (!windowFeatures.length) {
    ctx.fillStyle = "#4E5867";
    ctx.font = "12px 'JetBrains Mono', monospace";
    ctx.fillText("No window data yet — run analyze_logs.py", 8, height / 2);
    return;
  }

  const values = windowFeatures.map(w => w.error_warn_ratio);
  const maxVal = Math.max(...values, 0.05);
  const padding = 14;
  const plotW = width - padding * 2;
  const plotH = height - padding * 2;

  const points = values.map((v, i) => ({
    x: padding + (i / Math.max(values.length - 1, 1)) * plotW,
    y: padding + plotH - (v / maxVal) * plotH,
  }));

  // filled area under the line
  const grad = ctx.createLinearGradient(0, 0, 0, height);
  grad.addColorStop(0, "rgba(79, 216, 196, 0.28)");
  grad.addColorStop(1, "rgba(79, 216, 196, 0.0)");
  ctx.beginPath();
  ctx.moveTo(points[0].x, height - padding);
  points.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(points[points.length - 1].x, height - padding);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // glowing line
  ctx.beginPath();
  points.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
  ctx.strokeStyle = "#4FD8C4";
  ctx.lineWidth = 1.75;
  ctx.shadowColor = "rgba(79, 216, 196, 0.6)";
  ctx.shadowBlur = 8;
  ctx.stroke();
  ctx.shadowBlur = 0;

  // anomaly markers
  windowFeatures.forEach((w, i) => {
    if (!w.is_anomaly) return;
    const p = points[i];
    ctx.beginPath();
    ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#F14C4C";
    ctx.shadowColor = "rgba(241, 76, 76, 0.8)";
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.shadowBlur = 0;
  });
}

// ---------- Bar charts ----------

let levelChart, componentChart;

function renderLevelChart(byLevel) {
  const ctx = document.getElementById("level-chart");
  const labels = LEVEL_ORDER;
  const data = labels.map(l => byLevel[l] || 0);
  const colors = labels.map(l => LEVEL_COLORS[l]);

  if (levelChart) levelChart.destroy();
  levelChart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: colors, borderRadius: 4, maxBarThickness: 42 }] },
    options: chartOptions(false),
  });
}

function renderComponentChart(components) {
  const ctx = document.getElementById("component-chart");
  const labels = components.map(c => c.component);
  const data = components.map(c => c.count);

  if (componentChart) componentChart.destroy();
  componentChart = new Chart(ctx, {
    type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: "#4FD8C4", borderRadius: 4, maxBarThickness: 18 }] },
    options: { ...chartOptions(true), indexAxis: "y" },
  });
}

function chartOptions(horizontal) {
  const gridColor = "rgba(33, 43, 54, 0.7)";
  const tickColor = "#7C8797";
  const font = { family: "'JetBrains Mono', monospace", size: 11 };
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: horizontal ? gridColor : "transparent" }, ticks: { color: tickColor, font } },
      y: { grid: { color: gridColor }, ticks: { color: tickColor, font }, beginAtZero: true },
    },
  };
}

// ---------- Logs table ----------

function levelChip(level) {
  return `<span class="level-chip ${level}">${level}</span>`;
}

function levelSelectHtml(current) {
  return `<select class="edit-input">${LEVEL_ORDER.map(l =>
    `<option value="${l}" ${l === current ? "selected" : ""}>${l}</option>`).join("")}</select>`;
}

function renderLogsTable(logs) {
  const body = document.getElementById("logs-body");
  if (!logs.length) {
    body.innerHTML = `<tr><td colspan="5" class="empty">No logs match this filter.</td></tr>`;
    return;
  }
  body.innerHTML = logs.slice(0, 50).map(log => `
    <tr data-id="${log.id}">
      <td>${log.log_time || ""}</td>
      <td class="level-cell">${levelChip(log.level)}</td>
      <td class="component-cell">${escapeHtml(log.component || "")}</td>
      <td class="content-cell" title="${escapeHtml(log.content || "")}">${escapeHtml(log.content || "")}</td>
      <td class="actions-cell">
        <button class="btn btn-ghost btn-sm edit-btn">Edit</button>
        <button class="btn btn-danger btn-sm delete-btn">Delete</button>
      </td>
    </tr>
  `).join("");

  body.querySelectorAll(".edit-btn").forEach(btn => btn.addEventListener("click", onEditClick));
  body.querySelectorAll(".delete-btn").forEach(btn => btn.addEventListener("click", onDeleteClick));
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function loadLogs(level) {
  const url = level ? `/api/logs?limit=50&level=${level}` : "/api/logs?limit=50";
  const logs = await fetchJSON(url);
  renderLogsTable(logs);
}

function setupLevelTabs() {
  const tabs = document.querySelectorAll("#level-tabs .tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentLevel = tab.dataset.level;
      loadLogs(currentLevel);
    });
  });
}

// ---------- Create ----------

function setupCreateForm() {
  const form = document.getElementById("create-form");
  const status = document.getElementById("create-status");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const level = document.getElementById("f-level").value;
    const component = document.getElementById("f-component").value.trim();
    const content = document.getElementById("f-content").value.trim();

    status.textContent = "Adding…";
    status.className = "create-status";

    try {
      const res = await fetch("/api/logs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ level, component, content }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `request failed (${res.status})`);
      }
      form.reset();
      document.getElementById("f-level").value = "I";
      status.textContent = "Log added.";
      status.className = "create-status ok";
      await refreshDashboard();
    } catch (err) {
      status.textContent = `Couldn't add log: ${err.message}`;
      status.className = "create-status error";
    }
  });
}

// ---------- Edit / Delete ----------

function onEditClick(e) {
  const row = e.target.closest("tr");
  const id = row.dataset.id;
  const levelCell = row.querySelector(".level-cell");
  const componentCell = row.querySelector(".component-cell");
  const contentCell = row.querySelector(".content-cell");
  const actionsCell = row.querySelector(".actions-cell");

  const currentLevelVal = levelCell.textContent.trim();
  const currentComponent = componentCell.textContent;
  const currentContent = contentCell.getAttribute("title") || "";

  levelCell.innerHTML = levelSelectHtml(currentLevelVal);
  componentCell.innerHTML = `<input class="edit-input" value="${escapeHtml(currentComponent)}">`;
  contentCell.innerHTML = `<input class="edit-input" value="${escapeHtml(currentContent)}">`;
  actionsCell.innerHTML = `
    <button class="btn btn-primary btn-sm save-btn">Save</button>
    <button class="btn btn-ghost btn-sm cancel-btn">Cancel</button>
  `;

  actionsCell.querySelector(".save-btn").addEventListener("click", () => onSaveClick(id));
  actionsCell.querySelector(".cancel-btn").addEventListener("click", () => loadLogs(currentLevel));
}

async function onSaveClick(id) {
  const row = document.querySelector(`tr[data-id="${id}"]`);
  const level = row.querySelector(".level-cell select").value;
  const component = row.querySelector(".component-cell input").value.trim();
  const content = row.querySelector(".content-cell input").value.trim();

  try {
    const res = await fetch(`/api/logs/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level, component, content }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `request failed (${res.status})`);
    }
    await refreshDashboard();
  } catch (err) {
    alert(`Couldn't save changes: ${err.message}`);
    loadLogs(currentLevel);
  }
}

async function onDeleteClick(e) {
  const row = e.target.closest("tr");
  const id = row.dataset.id;
  if (!confirm("Delete this log entry? This can't be undone.")) return;

  try {
    const res = await fetch(`/api/logs/${id}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `request failed (${res.status})`);
    }
    await refreshDashboard();
  } catch (err) {
    alert(`Couldn't delete log: ${err.message}`);
  }
}

// ---------- Init ----------

function safeCall(fn, label) {
  try {
    fn();
  } catch (err) {
    console.error(`${label} failed:`, err);
  }
}

async function refreshDashboard() {
  let summary, windowFeatures, trend;
  try {
    [summary, windowFeatures] = await Promise.all([
      fetchJSON("/api/summary"),
      fetchJSON("/api/window-features"),
    ]);
  } catch (err) {
    console.error("Dashboard data fetch failed:", err);
    setText("last-updated", "update failed — is the server running?");
    return;
  }

  try {
    trend = await fetchJSON("/api/predict/trend");
  } catch (err) {
    console.error("Trend fetch failed:", err);
    trend = { error: "fetch failed" };
  }

  safeCall(() => renderStatus(summary.prediction), "renderStatus");
  safeCall(() => renderForecast(trend), "renderForecast");
  safeCall(() => renderStats(summary, windowFeatures), "renderStats");
  safeCall(() => renderPulse(windowFeatures), "renderPulse");
  safeCall(() => renderLevelChart(summary.by_level || {}), "renderLevelChart");
  safeCall(() => renderComponentChart(summary.top_components || []), "renderComponentChart");
  try {
    await loadLogs(currentLevel);
  } catch (err) {
    console.error("loadLogs failed:", err);
  }

  setText("last-updated", `updated ${new Date().toLocaleTimeString()}`);
}
setupLevelTabs();
setupCreateForm();
refreshDashboard();
setInterval(refreshDashboard, 30000); // auto-refresh every 30s