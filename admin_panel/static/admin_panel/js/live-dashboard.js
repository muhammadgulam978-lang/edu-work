(function () {
  "use strict";

  var root = document.querySelector(".live-dashboard");
  if (!root) return;

  var initialNode = document.getElementById("reference-dashboard-data");
  var endpoint = root.getAttribute("data-dashboard-endpoint");
  var charts = {};
  var refreshTimer = null;
  var activeData = null;

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function setHidden(element, hidden) {
    if (element) element.hidden = hidden;
  }

  function renderKpis(kpis) {
    var grid = root.querySelector("[data-kpi-grid]");
    if (!grid) return;
    grid.innerHTML = (kpis || []).map(function (item) {
      var hasDelta = item.delta !== null && item.delta !== undefined;
      var delta = Number(item.delta || 0);
      var trendClass = !hasDelta || delta === 0 ? "neutral" : (delta > 0 ? "positive" : "negative");
      var trendIcon = !hasDelta || delta === 0 ? "fa-minus" : (delta > 0 ? "fa-arrow-up" : "fa-arrow-down");
      var trendValue = hasDelta ? Math.abs(delta).toFixed(1) + "%" : "Live";
      return '<a class="live-kpi ' + escapeHtml(item.tone) + '" href="' + escapeHtml(item.url) + '">' +
        '<span class="live-kpi-icon"><i class="fas ' + escapeHtml(item.icon) + '"></i></span>' +
        '<div class="live-kpi-copy"><span class="live-kpi-label">' + escapeHtml(item.label) + '</span>' +
        '<strong class="live-kpi-value">' + escapeHtml(item.display) + '</strong></div>' +
        '<span class="live-kpi-trend ' + trendClass + '"><i class="fas ' + trendIcon + '"></i><strong>' + trendValue + '</strong> ' + escapeHtml(item.trend_label) + '</span>' +
        '</a>';
    }).join("");
  }

  function renderMetrics(moduleName, moduleData) {
    var module = root.querySelector('[data-module="' + moduleName + '"]');
    if (!module || !moduleData) return;
    var metrics = module.querySelector("[data-metrics]");
    metrics.innerHTML = (moduleData.metrics || []).map(function (metric) {
      return '<div class="live-module-metric"><strong>' + escapeHtml(metric.value) + '</strong><span>' + escapeHtml(metric.label) + '</span></div>';
    }).join("");
    var primary = module.querySelector("[data-primary-url]");
    var report = module.querySelector("[data-report-url]");
    if (primary) primary.href = moduleData.primary_url || "#";
    if (report) report.href = moduleData.report_url || "#";
  }

  function destroyChart(key) {
    if (charts[key]) {
      charts[key].destroy();
      charts[key] = null;
    }
  }

  function lineChart(key, canvasId, labels, datasets, yPercent) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined") return;
    destroyChart(key);
    charts[key] = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: { labels: labels || [], datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        legend: { display: datasets.length > 1, position: "top", labels: { boxWidth: 9, fontSize: 9, fontColor: "#65736f" } },
        tooltips: { mode: "index", intersect: false },
        scales: {
          xAxes: [{ gridLines: { display: false }, ticks: { fontSize: 8, fontColor: "#7a8784", maxRotation: 0 } }],
          yAxes: [{ gridLines: { color: "#edf1f0" }, ticks: { beginAtZero: true, max: yPercent ? 100 : undefined, fontSize: 8, fontColor: "#7a8784" } }]
        },
        elements: { line: { tension: .32 }, point: { radius: 2, hoverRadius: 4 } }
      }
    });
  }

  function renderCharts(data) {
    lineChart("academics", "academicsChart", data.academics.chart.labels, [{
      label: "Attendance %", data: data.academics.chart.attendance,
      borderColor: "#1976d2", backgroundColor: "rgba(25,118,210,.08)", borderWidth: 2, fill: true
    }], true);

    var hrCanvas = document.getElementById("hrChart");
    if (hrCanvas && typeof Chart !== "undefined") {
      destroyChart("hr");
      charts.hr = new Chart(hrCanvas.getContext("2d"), {
        type: "doughnut",
        data: { labels: data.hr.chart.labels, datasets: [{ data: data.hr.chart.values, backgroundColor: ["#38b66a", "#f3a33b", "#e7555d"], borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: false, cutoutPercentage: 68, legend: { display: false }, tooltips: { bodyFontSize: 10 } }
      });
    }
    var legend = root.querySelector("[data-hr-legend]");
    if (legend) {
      var colors = ["#38b66a", "#f3a33b", "#e7555d"];
      legend.innerHTML = data.hr.chart.labels.map(function (label, index) {
        return '<div><i style="background:' + colors[index] + '"></i><span>' + escapeHtml(label) + '</span><strong>' + escapeHtml(data.hr.chart.values[index]) + '</strong></div>';
      }).join("");
    }

    lineChart("finance", "financeChart", data.finance.chart.labels, [
      { label: "Income", data: data.finance.chart.income, borderColor: "#38a85d", backgroundColor: "rgba(56,168,93,.05)", borderWidth: 2, fill: false },
      { label: "Expense", data: data.finance.chart.expense, borderColor: "#f0a01f", backgroundColor: "rgba(240,160,31,.05)", borderWidth: 2, fill: false }
    ], false);

    lineChart("procurement", "procurementChart", data.procurement.chart.labels, [{
      label: "Approved value", data: data.procurement.chart.spend,
      borderColor: "#0a9d63", backgroundColor: "rgba(10,157,99,.09)", borderWidth: 2, fill: true
    }], false);
  }

  function renderOperations(data) {
    var procurement = root.querySelector("[data-procurement-summary]");
    if (procurement) {
      procurement.innerHTML = '<div class="live-status-card"><span>Approved Value</span><strong>' + escapeHtml(data.procurement.summary.value) + '</strong></div>' +
        '<div class="live-status-card"><span>Received Requests</span><strong>' + escapeHtml(data.procurement.summary.received) + '</strong></div>' +
        '<div class="live-status-card"><span>Overdue Requests</span><strong>' + escapeHtml(data.procurement.summary.overdue) + '</strong></div>';
    }

    var routes = root.querySelector("[data-route-performance]");
    if (routes) {
      if (!data.fleet.routes.length) {
        routes.innerHTML = '<div class="live-empty-inline">No trips recorded for this range.</div>';
      } else {
        routes.innerHTML = data.fleet.routes.map(function (route) {
          return '<div class="live-route-row ' + (route.status === "Delayed" ? "delayed" : "") + '">' +
            '<span title="' + escapeHtml(route.name) + '">' + escapeHtml(route.name) + '</span>' +
            '<span class="live-route-track"><i style="width:' + Math.max(0, Math.min(100, Number(route.rate))) + '%"></i></span>' +
            '<strong>' + escapeHtml(route.rate) + '%</strong></div>';
        }).join("");
      }
    }

    var fleet = root.querySelector("[data-fleet-summary]");
    if (fleet) {
      fleet.innerHTML = '<div class="live-status-card"><span>On-time Rate</span><strong>' + escapeHtml(data.fleet.summary.on_time_rate) + '%</strong></div>' +
        '<div class="live-status-card"><span>On Time / Delayed</span><strong>' + escapeHtml(data.fleet.summary.on_time) + ' / ' + escapeHtml(data.fleet.summary.delayed) + '</strong></div>' +
        '<div class="live-status-card"><span>Active Fleet Capacity</span><strong>' + escapeHtml(data.fleet.summary.capacity) + '</strong></div>';
    }
  }

  function renderAlerts(alerts) {
    var grid = root.querySelector("[data-alert-grid]");
    var count = root.querySelector("[data-alert-count]");
    if (!grid) return;
    var activeCount = (alerts || []).filter(function (alert) { return Number(alert.count) > 0; }).length;
    if (count) count.textContent = activeCount + " active alert" + (activeCount === 1 ? "" : "s");
    grid.innerHTML = (alerts || []).map(function (alert) {
      return '<article class="live-alert ' + escapeHtml(alert.tone) + '"><span class="live-alert-icon"><i class="fas ' + escapeHtml(alert.icon) + '"></i></span>' +
        '<div><h3>' + escapeHtml(alert.title) + '</h3><p>' + escapeHtml(alert.detail) + '</p>' +
        '<a href="' + escapeHtml(alert.url) + '">' + escapeHtml(alert.action) + ' <i class="fas fa-arrow-right"></i></a></div></article>';
    }).join("");
  }

  function renderQuickActions(actions) {
    var grid = root.querySelector("[data-quick-grid]");
    if (!grid) return;
    grid.innerHTML = (actions || []).map(function (action) {
      return '<a class="live-quick-action" href="' + escapeHtml(action.url) + '"><i class="fas ' + escapeHtml(action.icon) + '"></i><span>' + escapeHtml(action.label) + '</span></a>';
    }).join("");
  }

  function render(data) {
    if (!data || !data.meta) return;
    activeData = data;
    renderKpis(data.kpis);
    ["academics", "hr", "finance", "procurement", "fleet"].forEach(function (name) { renderMetrics(name, data[name]); });
    renderCharts(data);
    renderOperations(data);
    renderAlerts(data.alerts);
    renderQuickActions(data.quick_actions);
    var generated = root.querySelector("[data-generated-at]");
    if (generated) generated.textContent = data.meta.generated_at;
    root.querySelectorAll("[data-range-label]").forEach(function (node) { node.textContent = data.meta.range_label; });
    var start = root.querySelector("[data-start-date]");
    var end = root.querySelector("[data-end-date]");
    if (start) start.value = data.meta.start_date;
    if (end) end.value = data.meta.end_date;
  }

  function queryString() {
    var period = root.querySelector("[data-period-select]").value;
    var params = new URLSearchParams({ period: period });
    if (period === "custom") {
      params.set("start_date", root.querySelector("[data-start-date]").value);
      params.set("end_date", root.querySelector("[data-end-date]").value);
    }
    return params.toString();
  }

  function refresh() {
    var loading = root.querySelector("[data-dashboard-loading]");
    var error = root.querySelector("[data-dashboard-error]");
    setHidden(loading, false);
    setHidden(error, true);
    return fetch(endpoint + "?" + queryString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(function (response) {
        if (!response.ok) throw new Error("Dashboard request failed");
        return response.json();
      })
      .then(function (data) { render(data); })
      .catch(function () {
        setHidden(error, false);
        window.setTimeout(function () { setHidden(error, true); }, 6000);
      })
      .finally(function () { setHidden(loading, true); });
  }

  var periodSelect = root.querySelector("[data-period-select]");
  var customRange = root.querySelector("[data-custom-range]");
  periodSelect.addEventListener("change", function () {
    var custom = periodSelect.value === "custom";
    setHidden(customRange, !custom);
    if (!custom) refresh();
  });
  root.querySelector("[data-apply-range]").addEventListener("click", function () {
    var start = root.querySelector("[data-start-date]").value;
    var end = root.querySelector("[data-end-date]").value;
    if (start && end) refresh();
  });
  root.querySelector("[data-refresh-dashboard]").addEventListener("click", refresh);

  try {
    render(JSON.parse(initialNode.textContent));
  } catch (error) {
    refresh();
  }
  refreshTimer = window.setInterval(refresh, 30000);
  window.addEventListener("beforeunload", function () {
    if (refreshTimer) window.clearInterval(refreshTimer);
    Object.keys(charts).forEach(destroyChart);
  });
})();
