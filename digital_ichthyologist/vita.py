"""Vita – interactive HTML dashboard for Digital Ichthyologist metrics.

Generates a self-contained HTML page with charts and tables that visualise
every metric the ecosystem analysis produces.  The dashboard uses Chart.js
(loaded from a CDN) for interactive charts and vanilla CSS / JS for
layout, styling, and table sorting – no extra Python dependencies are
needed.
"""

from __future__ import annotations

import html
import json
from typing import List

from .fish import DigitalFish

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _alive(population: List[DigitalFish]) -> List[DigitalFish]:
    return [f for f in population if f.is_alive]


def _extinct(population: List[DigitalFish]) -> List[DigitalFish]:
    return [f for f in population if not f.is_alive]


def _esc(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(text, quote=True)


# ---------------------------------------------------------------------------
# Vita dashboard generator
# ---------------------------------------------------------------------------

class Vita:
    """Generates an interactive HTML dashboard from the fish population.

    Args:
        population: The full list of :class:`~digital_ichthyologist.DigitalFish`
            objects returned by :meth:`~digital_ichthyologist.Analyzer.run`.
        total_commits: The total number of commits analysed.
        top_n: How many entries to show in ranked lists (default 20).
    """

    def __init__(
        self,
        population: List[DigitalFish],
        total_commits: int = 0,
        *,
        top_n: int = 20,
    ) -> None:
        self.population = population
        self.total_commits = total_commits
        self.top_n = top_n

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Return a self-contained HTML page with the full dashboard.

        Returns:
            A complete HTML document as a string.
        """
        fish_data = self._fish_data_json()
        ecosystem = self._ecosystem_metrics()

        return _HTML_TEMPLATE.format(
            fish_data_json=fish_data,
            ecosystem_json=json.dumps(ecosystem),
            top_n=self.top_n,
        )

    # ------------------------------------------------------------------
    # Internal data preparation
    # ------------------------------------------------------------------

    def _fish_data_json(self) -> str:
        """Serialise fish data for the JavaScript side."""
        records = []
        for fish in self.population:
            records.append({
                "name": fish.display_name,
                "age": fish.age,
                "mutation_rate": round(fish.mutation_rate, 4),
                "is_alive": fish.is_alive,
                "lazarus_count": fish.lazarus_count,
                "line_count": fish.line_count,
                "birth_commit": fish.birth_commit[:8],
                "file_path": fish.file_path,
                "start_line": fish.start_line,
                "end_line": fish.end_line,
            })
        return json.dumps(records)

    def _ecosystem_metrics(self) -> dict:
        """Compute the ecosystem-level summary metrics."""
        total_fish = len(self.population)
        alive_count = len(_alive(self.population))
        extinct_count = len(_extinct(self.population))
        lazarus_events = sum(f.lazarus_count for f in self.population)

        if self.total_commits > 0:
            births_per_100 = round((total_fish / self.total_commits) * 100, 1)
            extinctions_per_100 = round(
                (extinct_count / self.total_commits) * 100, 1
            )
        else:
            births_per_100 = 0.0
            extinctions_per_100 = 0.0

        survival_ratio = round(
            (alive_count / total_fish * 100) if total_fish else 0.0, 1
        )
        avg_age = round(
            sum(f.age for f in self.population) / total_fish if total_fish else 0.0,
            1,
        )
        avg_mutation = round(
            sum(f.mutation_rate for f in self.population) / total_fish
            if total_fish
            else 0.0,
            3,
        )

        return {
            "total_commits": self.total_commits,
            "total_fish": total_fish,
            "alive": alive_count,
            "extinct": extinct_count,
            "lazarus_events": lazarus_events,
            "births_per_100": births_per_100,
            "extinctions_per_100": extinctions_per_100,
            "survival_ratio": survival_ratio,
            "avg_age": avg_age,
            "avg_mutation": avg_mutation,
        }


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Digital Ichthyologist &ndash; Vita Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --accent: #58a6ff;
    --green: #3fb950;
    --red: #f85149;
    --orange: #d29922;
    --purple: #bc8cff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica,
                 Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }}
  header {{
    background: var(--card);
    border-bottom: 1px solid var(--border);
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
  }}
  header h1 {{ font-size: 1.4rem; font-weight: 600; }}
  header h1 span {{ color: var(--accent); }}
  .dashboard {{
    max-width: 1280px;
    margin: 2rem auto;
    padding: 0 1rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
  }}
  .card h2 {{
    font-size: 1.1rem;
    margin-bottom: 1rem;
    color: var(--accent);
    border-bottom: 1px solid var(--border);
    padding-bottom: .5rem;
  }}
  /* stats grid */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
  }}
  .stat {{
    background: var(--bg);
    border-radius: 6px;
    padding: 1rem;
    text-align: center;
  }}
  .stat .value {{
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--accent);
  }}
  .stat .label {{
    font-size: 0.8rem;
    color: #8b949e;
    margin-top: .25rem;
  }}
  /* charts row */
  .chart-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }}
  @media (max-width: 800px) {{
    .chart-row {{ grid-template-columns: 1fr; }}
  }}
  .chart-container {{
    position: relative;
    width: 100%;
    max-height: 400px;
  }}
  /* table */
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }}
  th, td {{
    padding: .5rem .75rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }}
  th {{
    cursor: pointer;
    user-select: none;
    color: var(--accent);
    font-weight: 600;
    white-space: nowrap;
  }}
  th:hover {{ text-decoration: underline; }}
  tr:hover td {{ background: rgba(88,166,255,.06); }}
  .alive {{ color: var(--green); }}
  .extinct {{ color: var(--red); }}
  .bar-bg {{
    background: var(--bg);
    border-radius: 4px;
    overflow: hidden;
    height: 8px;
    width: 100%;
  }}
  .bar-fill {{
    height: 100%;
    border-radius: 4px;
    transition: width .3s;
  }}
  footer {{
    text-align: center;
    padding: 2rem;
    color: #484f58;
    font-size: 0.75rem;
  }}
</style>
</head>
<body>
<header>
  <h1>🐟 Digital Ichthyologist &ndash; <span>Vita</span> Dashboard</h1>
</header>

<main class="dashboard">

  <!-- Ecosystem Health -->
  <section class="card" id="ecosystem">
    <h2>🌊 Ecosystem Health</h2>
    <div class="stats-grid" id="stats-grid"></div>
  </section>

  <!-- Charts -->
  <section class="chart-row">
    <div class="card">
      <h2>📊 Population Status</h2>
      <div class="chart-container">
        <canvas id="statusChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>📈 Age Distribution</h2>
      <div class="chart-container">
        <canvas id="ageChart"></canvas>
      </div>
    </div>
  </section>

  <section class="chart-row">
    <div class="card">
      <h2>🧬 Mutation Rate vs Age</h2>
      <div class="chart-container">
        <canvas id="scatterChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>🔄 Lazarus Events</h2>
      <div class="chart-container">
        <canvas id="lazarusChart"></canvas>
      </div>
    </div>
  </section>

  <!-- Survival Heatmap -->
  <section class="card">
    <h2>🗺️ Survival Heatmap (Top {top_n})</h2>
    <table id="heatmap-table">
      <thead>
        <tr>
          <th data-sort="name">Fish Name</th>
          <th data-sort="age">Age</th>
          <th>Stability</th>
          <th data-sort="mutation_rate">Mutation Rate</th>
          <th data-sort="line_count">Lines</th>
          <th data-sort="status">Status</th>
        </tr>
      </thead>
      <tbody id="heatmap-body"></tbody>
    </table>
  </section>

  <!-- Full Fish Table -->
  <section class="card">
    <h2>🐠 All Fish</h2>
    <table id="fish-table">
      <thead>
        <tr>
          <th data-sort="name">Name</th>
          <th data-sort="age">Age</th>
          <th data-sort="mutation_rate">Mut. Rate</th>
          <th data-sort="line_count">Lines</th>
          <th data-sort="lazarus_count">Lazarus</th>
          <th data-sort="status">Status</th>
          <th>Birth Commit</th>
        </tr>
      </thead>
      <tbody id="fish-body"></tbody>
    </table>
  </section>

</main>

<footer>
  Digital Ichthyologist &ndash; Vita Dashboard &bull; generated by
  <code>digital-ichthyologist</code>
</footer>

<script>
// ------- data injected by Python -------
const fishData = {fish_data_json};
const eco      = {ecosystem_json};
const TOP_N    = {top_n};

// ------- ecosystem stats -------
(function renderStats() {{
  const items = [
    ["Commits Analysed", eco.total_commits],
    ["Total Fish", eco.total_fish],
    ["Alive", eco.alive],
    ["Extinct", eco.extinct],
    ["Lazarus Events", eco.lazarus_events],
    ["Births / 100 commits", eco.births_per_100],
    ["Extinctions / 100", eco.extinctions_per_100],
    ["Survival Ratio", eco.survival_ratio + "%"],
    ["Avg Age", eco.avg_age],
    ["Avg Mutation Rate", eco.avg_mutation],
  ];
  const grid = document.getElementById("stats-grid");
  items.forEach(([label, value]) => {{
    const d = document.createElement("div");
    d.className = "stat";
    d.innerHTML = '<div class="value">' + value + '</div><div class="label">' + label + '</div>';
    grid.appendChild(d);
  }});
}})();

// ------- status doughnut -------
new Chart(document.getElementById("statusChart"), {{
  type: "doughnut",
  data: {{
    labels: ["Alive", "Extinct"],
    datasets: [{{
      data: [eco.alive, eco.extinct],
      backgroundColor: ["#3fb950", "#f85149"],
      borderColor: "#161b22",
      borderWidth: 2,
    }}],
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: true,
    plugins: {{
      legend: {{ labels: {{ color: "#c9d1d9" }} }},
    }},
  }},
}});

// ------- age histogram -------
(function ageHist() {{
  const ages = fishData.map(f => f.age);
  if (ages.length === 0) return;
  const maxAge = Math.max(...ages, 1);
  const buckets = 10;
  const step = Math.max(Math.ceil(maxAge / buckets), 1);
  const labels = [];
  const counts = [];
  for (let i = 0; i < buckets; i++) {{
    const lo = i * step;
    const hi = lo + step - 1;
    labels.push(lo + "–" + hi);
    counts.push(ages.filter(a => a >= lo && a <= hi).length);
  }}
  new Chart(document.getElementById("ageChart"), {{
    type: "bar",
    data: {{
      labels: labels,
      datasets: [{{
        label: "Fish count",
        data: counts,
        backgroundColor: "#58a6ff",
        borderRadius: 4,
      }}],
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: true,
      scales: {{
        x: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "#21262d" }} }},
        y: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "#21262d" }}, beginAtZero: true }},
      }},
      plugins: {{ legend: {{ display: false }} }},
    }},
  }});
}})();

// ------- scatter: mutation vs age -------
(function scatter() {{
  const alive = fishData.filter(f => f.is_alive).map(f => ({{ x: f.age, y: f.mutation_rate }}));
  const dead  = fishData.filter(f => !f.is_alive).map(f => ({{ x: f.age, y: f.mutation_rate }}));
  new Chart(document.getElementById("scatterChart"), {{
    type: "scatter",
    data: {{
      datasets: [
        {{ label: "Alive", data: alive, backgroundColor: "#3fb950" }},
        {{ label: "Extinct", data: dead, backgroundColor: "#f85149" }},
      ],
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: true,
      scales: {{
        x: {{ title: {{ display: true, text: "Age (commits)", color: "#8b949e" }}, ticks: {{ color: "#8b949e" }}, grid: {{ color: "#21262d" }} }},
        y: {{ title: {{ display: true, text: "Mutation Rate", color: "#8b949e" }}, ticks: {{ color: "#8b949e" }}, grid: {{ color: "#21262d" }}, beginAtZero: true }},
      }},
      plugins: {{ legend: {{ labels: {{ color: "#c9d1d9" }} }} }},
    }},
  }});
}})();

// ------- lazarus bar chart -------
(function lazarus() {{
  const laz = fishData.filter(f => f.lazarus_count > 0)
      .sort((a, b) => b.lazarus_count - a.lazarus_count)
      .slice(0, TOP_N);
  if (laz.length === 0) {{
    const c = document.getElementById("lazarusChart").parentElement;
    c.innerHTML += "<p style='color:#8b949e;text-align:center'>No Lazarus events detected.</p>";
    return;
  }}
  new Chart(document.getElementById("lazarusChart"), {{
    type: "bar",
    data: {{
      labels: laz.map(f => f.name),
      datasets: [{{
        label: "Resurrections",
        data: laz.map(f => f.lazarus_count),
        backgroundColor: "#bc8cff",
        borderRadius: 4,
      }}],
    }},
    options: {{
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: true,
      scales: {{
        x: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "#21262d" }}, beginAtZero: true }},
        y: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "#21262d" }} }},
      }},
      plugins: {{ legend: {{ display: false }} }},
    }},
  }});
}})();

// ------- survival heatmap table -------
(function heatmap() {{
  const sorted = [...fishData].sort((a, b) => b.age - a.age).slice(0, TOP_N);
  const maxAge = Math.max(...sorted.map(f => f.age), 1);
  const tbody = document.getElementById("heatmap-body");
  sorted.forEach(f => {{
    const pct = (f.age / maxAge * 100).toFixed(1);
    const color = f.is_alive ? "#3fb950" : "#f85149";
    const cls = f.is_alive ? "alive" : "extinct";
    const status = f.is_alive ? "alive" : "extinct";
    const tr = document.createElement("tr");
    tr.innerHTML =
      '<td>' + escHtml(f.name) + '</td>' +
      '<td>' + f.age + '</td>' +
      '<td><div class="bar-bg"><div class="bar-fill" style="width:' + pct + '%;background:' + color + '"></div></div></td>' +
      '<td>' + f.mutation_rate.toFixed(3) + '</td>' +
      '<td>' + f.line_count + '</td>' +
      '<td class="' + cls + '">' + status + '</td>';
    tbody.appendChild(tr);
  }});
}})();

// ------- full fish table -------
(function allFish() {{
  const tbody = document.getElementById("fish-body");
  fishData.forEach(f => {{
    const cls = f.is_alive ? "alive" : "extinct";
    const status = f.is_alive ? "alive" : "extinct";
    const tr = document.createElement("tr");
    tr.innerHTML =
      '<td>' + escHtml(f.name) + '</td>' +
      '<td>' + f.age + '</td>' +
      '<td>' + f.mutation_rate.toFixed(4) + '</td>' +
      '<td>' + f.line_count + '</td>' +
      '<td>' + f.lazarus_count + '</td>' +
      '<td class="' + cls + '">' + status + '</td>' +
      '<td><code>' + escHtml(f.birth_commit) + '</code></td>';
    tbody.appendChild(tr);
  }});
}})();

// ------- table sorting -------
document.querySelectorAll("th[data-sort]").forEach(th => {{
  th.addEventListener("click", function() {{
    const table = this.closest("table");
    const tbody = table.querySelector("tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));
    const idx = Array.from(this.parentElement.children).indexOf(this);
    const key = this.dataset.sort;
    const asc = this.dataset.dir !== "asc";
    this.dataset.dir = asc ? "asc" : "desc";
    rows.sort((a, b) => {{
      let va = a.children[idx].textContent.trim();
      let vb = b.children[idx].textContent.trim();
      const na = parseFloat(va), nb = parseFloat(vb);
      if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
      return asc ? va.localeCompare(vb) : vb.localeCompare(va);
    }});
    rows.forEach(r => tbody.appendChild(r));
  }});
}});

function escHtml(s) {{
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(s));
  return d.innerHTML;
}}
</script>
</body>
</html>
"""
