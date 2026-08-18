(function () {
  "use strict";

  var root = document.querySelector(".live-dashboard");
  if (!root) return;

  var initialNode = document.getElementById("reference-dashboard-data");
  var endpoint = root.getAttribute("data-dashboard-endpoint");
  var charts = {};
  var graphSystem = window.EduPilotCharts;
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
    var ids = {academics: "academicsChart", hr: "hrChart", finance: "financeChart", procurement: "procurementChart"};
    if (graphSystem && ids[key]) graphSystem.destroy(ids[key]);
    charts[key] = null;
  }

  function compactNumber(value) {
    var number = Number(value || 0);
    if (Math.abs(number) >= 1000000) return (number / 1000000).toFixed(number % 1000000 ? 1 : 0) + "M";
    if (Math.abs(number) >= 1000) return (number / 1000).toFixed(number % 1000 ? 1 : 0) + "K";
    return String(Math.round(number * 10) / 10);
  }

  var valueLabelPlugin = {
    afterDatasetsDraw: function (chart) {
      var ctx = chart.ctx;
      ctx.save();
      ctx.font = "600 8px sans-serif";
      ctx.textAlign = "center";
      chart.data.datasets.forEach(function (dataset, datasetIndex) {
        var meta = chart.getDatasetMeta(datasetIndex);
        if (meta.hidden) return;
        meta.data.forEach(function (element, index) {
          var raw = Number(dataset.data[index] || 0);
          if (!raw) return;
          var position = element.tooltipPosition();
          ctx.fillStyle = dataset.borderColor || dataset.backgroundColor || "#42514d";
          ctx.fillText((dataset.valueSuffix ? compactNumber(raw) + dataset.valueSuffix : compactNumber(raw)), position.x, position.y - 7);
        });
      });
      ctx.restore();
    }
  };

  function lineChart(key, canvasId, labels, datasets, yPercent) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || !graphSystem) return;
    destroyChart(key);
    charts[key] = (datasets[0] && datasets[0].fill) ? graphSystem.areaChart(canvasId, labels, datasets, {
      valueFormat: yPercent ? "percent" : "count", legend: datasets.length > 1,
      summary: yPercent ? "Student attendance percentage trend for the selected period." : "Live values for the selected period."
    }) : graphSystem.lineChart(canvasId, labels, datasets, {
      valueFormat: yPercent ? "percent" : "count", legend: datasets.length > 1,
      summary: yPercent ? "Student attendance percentage trend for the selected period." : "Live values for the selected period."
    });
  }

  function groupedBarChart(key, canvasId, labels, datasets) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || !graphSystem) return;
    destroyChart(key);
    charts[key] = graphSystem.groupedBarChart(canvasId, labels, datasets, {
      valueFormat: "currency", summary: "Income and expense amounts in PKR for the selected period."
    });
  }

  function renderCharts(data) {
    lineChart("academics", "academicsChart", data.academics.chart.labels, [{
      label: "Attendance %", data: data.academics.chart.attendance,
      borderColor: "#1976d2", backgroundColor: "rgba(25,118,210,.06)", borderWidth: 2, fill: false, valueSuffix: "%"
    }], true);

    var hrCanvas = document.getElementById("hrChart");
    if (hrCanvas && graphSystem) {
      destroyChart("hr");
      charts.hr = graphSystem.doughnutChart("hrChart", data.hr.chart.labels, data.hr.chart.values,
        ["#38b66a", "#f3a33b", "#e7555d"], {legend: false, summary: "Available, on leave, and absent workforce today."});
    }
    var legend = root.querySelector("[data-hr-legend]");
    if (legend) {
      var colors = ["#38b66a", "#f3a33b", "#e7555d"];
      var workforceTotal = data.hr.chart.values.reduce(function (total, value) { return total + Number(value || 0); }, 0);
      legend.innerHTML = data.hr.chart.labels.map(function (label, index) {
        var value = Number(data.hr.chart.values[index] || 0);
        var percentage = workforceTotal ? Math.round((value / workforceTotal) * 100) : 0;
        return '<div><i style="background:' + colors[index] + '"></i><span>' + escapeHtml(label) + '</span><strong>' + escapeHtml(value) + ' (' + percentage + '%)</strong></div>';
      }).join("");
      var centerValue = root.querySelector("[data-hr-center-value]");
      if (centerValue) centerValue.textContent = workforceTotal;
    }

    groupedBarChart("finance", "financeChart", data.finance.chart.labels, [
      { label: "Income", data: data.finance.chart.income, borderColor: "#38a85d", backgroundColor: "#38a85d", borderWidth: 0 },
      { label: "Expense", data: data.finance.chart.expense, borderColor: "#f0a01f", backgroundColor: "#f0a01f", borderWidth: 0 }
    ]);

    lineChart("procurement", "procurementChart", data.procurement.chart.labels, [{
      label: "Approved value", data: data.procurement.chart.spend,
      borderColor: "#0a9d63", backgroundColor: "rgba(10,157,99,.09)", borderWidth: 2, fill: true
    }], false);
  }

  function renderOperations(data) {
    var procurement = root.querySelector("[data-procurement-summary]");
    if (procurement) {
      procurement.innerHTML = '<h4>Delivery Status</h4>' +
        '<div class="live-status-card total"><span>Total Spend</span><strong>' + escapeHtml(data.procurement.summary.value) + '</strong></div>' +
        '<div class="live-status-card success"><i class="fas fa-truck"></i><span>On Time</span><strong>' + escapeHtml(data.procurement.summary.on_time) + '</strong></div>' +
        '<div class="live-status-card danger"><i class="far fa-clock"></i><span>Delayed</span><strong>' + escapeHtml(data.procurement.summary.delayed) + '</strong></div>' +
        (Number(data.procurement.summary.unclassified || 0) ? '<div class="live-status-note">' + escapeHtml(data.procurement.summary.unclassified) + ' received without a required date</div>' : '');
    }

    var routes = root.querySelector("[data-route-performance]");
    if (routes && graphSystem) graphSystem.routePerformance(routes, data.fleet.routes, "No trips recorded for this range.");

    var fleet = root.querySelector("[data-fleet-summary]");
    if (fleet) {
      fleet.innerHTML = '<h4>Route Status Summary</h4><div class="live-status-pair">' +
        '<div class="live-status-card success"><i class="fas fa-check-circle"></i><span>On Time</span><strong>' + escapeHtml(data.fleet.summary.on_time) + '</strong></div>' +
        '<div class="live-status-card danger"><i class="far fa-clock"></i><span>Delayed</span><strong>' + escapeHtml(data.fleet.summary.delayed) + '</strong></div></div>' +
        '<h4>Maintenance Status</h4><div class="live-status-card maintenance"><i class="fas fa-tools"></i><span>Under Maintenance</span><strong>' + escapeHtml(data.fleet.metrics[3].value) + '</strong></div>';
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
  refreshTimer = window.setInterval(function () { if (!document.hidden) refresh(); }, 30000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
  window.addEventListener("beforeunload", function () {
    if (refreshTimer) window.clearInterval(refreshTimer);
    Object.keys(charts).forEach(destroyChart);
  });
})();
