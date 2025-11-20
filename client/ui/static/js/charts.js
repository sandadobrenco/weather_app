let tempChart, humChart;

function toISOFromDateInput(dateStr, endOfDay = false) {
  if (!dateStr) return null;
  const [y, m, d] = dateStr.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d, endOfDay ? 23 : 0, endOfDay ? 59 : 0, endOfDay ? 59 : 0, endOfDay ? 999 : 0));
  return dt.toISOString();
}

function setDefaultRangeIfEmpty() {
  const start = document.getElementById("start");
  const end = document.getElementById("end");
  if (!start.value && !end.value) {
    const now = new Date();
    const prior = new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000); // ultimele 7 zile
    // cu type="date" putem seta direct valueAsDate
    start.valueAsDate = new Date(prior.getFullYear(), prior.getMonth(), prior.getDate());
    end.valueAsDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }
}

function setLoading(isLoading) {
  const loadBtn = document.getElementById("load");
  const refBtn = document.getElementById("refresh");
  loadBtn.disabled = refBtn.disabled = isLoading;
  if (isLoading) {
    loadBtn.dataset.prev = loadBtn.textContent;
    loadBtn.textContent = "Loading…";
  } else if (loadBtn.dataset.prev) {
    loadBtn.textContent = loadBtn.dataset.prev;
  }
}

async function fetchHistory(city, startDate, endDate, limit = 200) {
  const p = new URLSearchParams({ city, limit });
  const startISO = toISOFromDateInput(startDate, false);
  const endISO = toISOFromDateInput(endDate, true);
  if (startISO) p.set("start", startISO);
  if (endISO) p.set("end", endISO);

  const r = await fetch(`/api/history?${p.toString()}`);
  if (!r.ok) throw new Error(`History failed: ${r.status}`);
  return r.json();
}

function ensureCharts(ctx1, ctx2) {
  const baseOpts = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { labels: { boxWidth: 12 } },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}`,
        },
      },
    },
    scales: {
      x: { grid: { color: "rgba(0,0,0,.05)" } },
      y: { grid: { color: "rgba(0,0,0,.05)" } },
    },
  };
  if (!tempChart) {
    tempChart = new Chart(ctx1, {
      type: "line",
      data: { labels: [], datasets: [{ label: "Temperature °C", data: [] }] },
      options: baseOpts,
    });
  }
  if (!humChart) {
    humChart = new Chart(ctx2, {
      type: "line",
      data: { labels: [], datasets: [{ label: "Humidity %", data: [] }] },
      options: baseOpts,
    });
  }
}

function clearOrRender(items) {
  const el = document.getElementById("table");
  if (!items.length) {
    // curățăm graficele și afișăm mesaj
    tempChart.data.labels = [];
    tempChart.data.datasets[0].data = [];
    tempChart.update();
    humChart.data.labels = [];
    humChart.data.datasets[0].data = [];
    humChart.update();
    el.innerHTML = "<p>No data for the selected interval.</p>";
    return false;
  }
  // tabel
  const rows = items
    .map(
      (x) => `
    <tr>
      <td>${x.timestamp}</td>
      <td>${x.city_name}</td>
      <td>${x.temperature.toFixed(2)}</td>
      <td>${x.humidity}</td>
      <td>${x.description}</td>
      <td>${x.wind_speed ?? "-"}</td>
    </tr>`
    )
    .join("");
  el.innerHTML = `
    <table>
      <thead><tr>
        <th>Timestamp</th><th>City</th><th>Temp °C</th><th>Humidity %</th><th>Description</th><th>Wind m/s</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  return true;
}

async function load() {
  const city = document.getElementById("city").value;
  const start = document.getElementById("start").value; // yyyy-mm-dd
  const end = document.getElementById("end").value; // yyyy-mm-dd

  setLoading(true);
  try {
    const data = await fetchHistory(city, start, end, 300);
    const items = Array.isArray(data.items) ? [...data.items].reverse() : [];
    const ctx1 = document.getElementById("tempChart").getContext("2d");
    const ctx2 = document.getElementById("humChart").getContext("2d");
    ensureCharts(ctx1, ctx2);

    if (!clearOrRender(items)) return;

    // grafice
    tempChart.data.labels = items.map((x) => x.timestamp);
    tempChart.data.datasets[0].data = items.map((x) => x.temperature);
    tempChart.update();

    humChart.data.labels = items.map((x) => x.timestamp);
    humChart.data.datasets[0].data = items.map((x) => x.humidity);
    humChart.update();
  } catch (e) {
    console.error(e);
    alert("Failed to load history. Please try again.");
  } finally {
    setLoading(false);
  }
}

async function refreshNow() {
  const city = document.getElementById("city").value;
  setLoading(true);
  try {
    const r = await fetch(`/api/refresh?city=${encodeURIComponent(city)}`, { method: "POST" });
    const j = await r.json();
    if (!j.ok) {
      alert(`Refresh failed: ${j.code}\n${j.details || ""}`);
      return;
    }
    await load();
  } catch (e) {
    console.error(e);
    alert("Refresh failed. Please try again.");
  } finally {
    setLoading(false);
  }
}

document.getElementById("load").addEventListener("click", load);
document.getElementById("refresh").addEventListener("click", refreshNow);
window.addEventListener("DOMContentLoaded", () => {
  setDefaultRangeIfEmpty();
  load();
});
