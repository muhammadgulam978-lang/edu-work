(function (window, document) {
  "use strict";

  var charts = {};
  var palette = {
    academics: "#1976d2",
    hr: "#7651c7",
    finance: "#e9960c",
    procurement: "#0a9d63",
    fleet: "#e24e55",
    ai: "#0e9380",
    teal: "#0e9380",
    green: "#38b66a",
    blue: "#327fe5",
    pink: "#e75578",
    yellow: "#f3a33b",
    orange: "#ed930d",
    danger: "#e7555d",
    lavender: "#7651c7"
  };

  function majorVersion() {
    return window.Chart && window.Chart.version ? parseInt(String(window.Chart.version).split(".")[0], 10) || 2 : 2;
  }

  function number(value) { return Number(value || 0); }
  function count(value) { return Math.round(number(value)).toLocaleString(); }
  function percent(value) { return number(value).toFixed(1) + "%"; }
  function compact(value) {
    var amount = number(value);
    if (Math.abs(amount) >= 1000000) return (amount / 1000000).toFixed(1) + "M";
    if (Math.abs(amount) >= 1000) return (amount / 1000).toFixed(1) + "K";
    return String(Math.round(amount * 10) / 10);
  }
  function currency(value, full) { return "PKR " + (full ? number(value).toLocaleString(undefined, {maximumFractionDigits: 2}) : compact(value)); }
  function rgba(hex, alpha) {
    var clean = String(hex || "").replace("#", "");
    if (clean.length === 3) clean = clean.split("").map(function (part) { return part + part; }).join("");
    var value = parseInt(clean, 16);
    if (isNaN(value)) return "rgba(14,147,128," + alpha + ")";
    return "rgba(" + ((value >> 16) & 255) + "," + ((value >> 8) & 255) + "," + (value & 255) + "," + alpha + ")";
  }
  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }
  function hasValues(datasets) {
    return (datasets || []).some(function (dataset) { return (dataset.data || []).some(function (value) { return number(value) !== 0; }); });
  }
  function canvasFor(id) { return typeof id === "string" ? document.getElementById(id) : id; }
  function boxFor(target) {
    var canvas = canvasFor(target);
    return canvas && canvas.closest ? (canvas.closest(".ep-chart-box") || canvas.parentElement) : null;
  }
  function stateNode(box) {
    if (!box) return null;
    var node = box.querySelector(".ep-chart-state");
    if (!node) {
      node = document.createElement("div");
      node.className = "ep-chart-state";
      node.setAttribute("role", "status");
      box.appendChild(node);
    }
    return node;
  }
  function setState(target, state, message) {
    var box = boxFor(target) || target;
    if (!box || !box.setAttribute) return;
    box.setAttribute("data-chart-state", state || "ready");
    var node = stateNode(box);
    if (node) node.textContent = message || "";
  }
  function setSummary(canvas, summary) {
    if (!canvas) return;
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", summary || "Live EduPilot chart");
    var box = boxFor(canvas);
    if (!box) return;
    var node = box.querySelector(".ep-chart-summary");
    if (!node) { node = document.createElement("p"); node.className = "ep-chart-summary"; box.appendChild(node); }
    node.textContent = summary || "Live EduPilot chart";
  }
  function destroy(id) {
    var key = typeof id === "string" ? id : id && id.id;
    if (key && charts[key]) { charts[key].destroy(); delete charts[key]; }
    if (majorVersion() >= 3 && window.Chart && typeof window.Chart.getChart === "function") {
      var current = window.Chart.getChart(key); if (current) current.destroy();
    }
  }
  function formatter(kind, full) {
    if (kind === "percent") return percent;
    if (kind === "currency") return function (value) { return currency(value, full); };
    return full ? function (value) { return number(value).toLocaleString(); } : compact;
  }
  function normalize(dataset, index, fillDefault) {
    var color = dataset.color || dataset.borderColor || Object.keys(palette).map(function (key) { return palette[key]; })[index % 8];
    var result = {};
    Object.keys(dataset || {}).forEach(function (key) { if (key !== "color" && key !== "format") result[key] = dataset[key]; });
    result.label = dataset.label || "Series";
    result.data = dataset.data || [];
    result.borderColor = dataset.borderColor || color;
    result.backgroundColor = dataset.backgroundColor || rgba(color, dataset.fill === false ? 0 : .1);
    result.pointBackgroundColor = dataset.pointBackgroundColor || color;
    result.pointBorderColor = "#fff";
    result.pointRadius = dataset.pointRadius == null ? 2 : dataset.pointRadius;
    result.pointHoverRadius = 4;
    result.borderWidth = dataset.borderWidth == null ? 2 : dataset.borderWidth;
    result.fill = dataset.fill == null ? fillDefault : dataset.fill;
    result.lineTension = dataset.lineTension == null ? .32 : dataset.lineTension;
    result.tension = dataset.tension == null ? .32 : dataset.tension;
    return result;
  }

  var valueLabels = {
    afterDatasetsDraw: function (chart) {
      var ctx = chart.ctx;
      ctx.save(); ctx.font = "600 9px sans-serif"; ctx.textAlign = "center";
      chart.data.datasets.forEach(function (dataset, datasetIndex) {
        if (!dataset.showValues) return;
        var meta = chart.getDatasetMeta(datasetIndex); if (meta.hidden) return;
        meta.data.forEach(function (element, index) {
          var value = number(dataset.data[index]); if (!value) return;
          var point = element.tooltipPosition();
          ctx.fillStyle = dataset.borderColor || dataset.backgroundColor || "#42514d";
          ctx.fillText(formatter(dataset.valueFormat)(value), point.x, point.y - 7);
        });
      });
      ctx.restore();
    }
  };

  function options(config) {
    config = config || {};
    var tickFormat = formatter(config.valueFormat);
    var tooltipFormat = formatter(config.valueFormat, true);
    var grid = "#edf1f0", tick = "#71807c";
    if (majorVersion() >= 3) {
      return {
        responsive: true, maintainAspectRatio: false,
        interaction: {mode: "index", intersect: false},
        plugins: {
          legend: {display: config.legend !== false, position: "top", align: "end", labels: {color: tick, usePointStyle: true, boxWidth: 8}},
          tooltip: {callbacks: {label: function (item) { var raw = config.horizontal ? item.parsed.x : item.parsed.y; return item.dataset.label + ": " + tooltipFormat(raw); }}}
        },
        scales: {
          x: {grid: {display: !!config.xGrid, drawBorder: false, color: grid}, ticks: {color: tick, maxRotation: 0}},
          y: {beginAtZero: true, suggestedMax: config.valueFormat === "percent" ? 100 : undefined, max: config.valueFormat === "percent" ? 100 : undefined, grid: {color: grid, drawBorder: false}, ticks: {color: tick, callback: tickFormat}}
        }
      };
    }
    return {
      responsive: true, maintainAspectRatio: false,
      legend: {display: config.legend !== false, position: "top", align: "end", labels: {fontColor: tick, usePointStyle: true, boxWidth: 8, fontSize: 10}},
      tooltips: {mode: "index", intersect: false, callbacks: {label: function (item, data) { var raw = config.horizontal ? item.xLabel : item.yLabel; return data.datasets[item.datasetIndex].label + ": " + tooltipFormat(raw); }}},
      scales: {
        xAxes: [{gridLines: {display: !!config.xGrid, drawBorder: false, color: grid}, ticks: {fontColor: tick, maxRotation: 0, fontSize: 9}}],
        yAxes: [{gridLines: {color: grid, drawBorder: false}, ticks: {fontColor: tick, beginAtZero: true, max: config.valueFormat === "percent" ? 100 : undefined, callback: tickFormat, fontSize: 9}}]
      }
    };
  }
  function merge(base, extra) {
    if (!extra) return base;
    Object.keys(extra).forEach(function (key) { base[key] = extra[key]; });
    return base;
  }
  function render(type, id, labels, datasets, config) {
    var canvas = canvasFor(id); if (!canvas || !window.Chart) return null;
    config = config || {}; destroy(canvas);
    if (!labels || !labels.length || !hasValues(datasets)) {
      setState(canvas, "empty", config.emptyMessage || "No data is available for the selected period.");
      setSummary(canvas, config.summary || "No chart data is available.");
      return null;
    }
    setState(canvas, "ready", ""); setSummary(canvas, config.summary);
    var chartOptions = merge(options(config), config.options);
    if (config.horizontal) {
      if (majorVersion() >= 3) {
        chartOptions.indexAxis = "y";
        chartOptions.scales.x.beginAtZero = true;
        chartOptions.scales.x.ticks.callback = formatter(config.valueFormat);
        chartOptions.scales.y.grid.display = false;
      } else {
        type = "horizontalBar";
        chartOptions.scales.xAxes[0].ticks.beginAtZero = true;
        chartOptions.scales.xAxes[0].ticks.callback = formatter(config.valueFormat);
        chartOptions.scales.xAxes[0].gridLines.display = true;
        chartOptions.scales.yAxes[0].gridLines.display = false;
        delete chartOptions.scales.yAxes[0].ticks.callback;
      }
    }
    charts[canvas.id] = new window.Chart(canvas.getContext("2d"), {type: type, data: {labels: labels, datasets: datasets}, plugins: [valueLabels], options: chartOptions});
    return charts[canvas.id];
  }
  function lineChart(id, labels, datasets, config) {
    return render("line", id, labels, (datasets || []).map(function (item, index) { return normalize(item, index, false); }), config);
  }
  function areaChart(id, labels, datasets, config) {
    return render("line", id, labels, (datasets || []).map(function (item, index) { return normalize(item, index, true); }), config);
  }
  function groupedBarChart(id, labels, datasets, config) {
    return render("bar", id, labels, (datasets || []).map(function (item, index) { return normalize(item, index, true); }), config);
  }
  function horizontalBarChart(id, labels, datasets, config) {
    config = config || {}; config.horizontal = true;
    return groupedBarChart(id, labels, datasets, config);
  }
  function mixedChart(id, labels, datasets, config) {
    return render("bar", id, labels, (datasets || []).map(function (item, index) { return normalize(item, index, item.type === "line"); }), config);
  }
  function doughnutChart(id, labels, values, colors, config) {
    var canvas = canvasFor(id); if (!canvas || !window.Chart) return null;
    config = config || {}; destroy(canvas);
    if (!labels || !labels.length || !(values || []).some(function (value) { return number(value) !== 0; })) {
      setState(canvas, "empty", config.emptyMessage || "No distribution data is available."); setSummary(canvas, config.summary || "No distribution data is available."); return null;
    }
    setState(canvas, "ready", ""); setSummary(canvas, config.summary);
    var chartOptions = majorVersion() >= 3 ? {
      responsive: true, maintainAspectRatio: false, cutout: "68%",
      plugins: {legend: {display: config.legend !== false, position: "bottom", labels: {color: "#71807c", usePointStyle: true, boxWidth: 8}}}
    } : {
      responsive: true, maintainAspectRatio: false, cutoutPercentage: 68,
      legend: {display: config.legend !== false, position: "bottom", labels: {fontColor: "#71807c", usePointStyle: true, boxWidth: 8, fontSize: 10}}
    };
    charts[canvas.id] = new window.Chart(canvas.getContext("2d"), {type: "doughnut", data: {labels: labels, datasets: [{data: values, backgroundColor: colors || [palette.green, palette.yellow, palette.danger], borderColor: "#fff", borderWidth: 2}]}, options: merge(chartOptions, config.options)});
    return charts[canvas.id];
  }
  function routePerformance(target, rows, emptyMessage) {
    var container = typeof target === "string" ? document.querySelector(target) : target;
    if (!container) return;
    if (!rows || !rows.length) { container.innerHTML = '<div class="ep-chart-state" style="display:grid;position:relative;inset:auto;min-height:140px">' + escapeHtml(emptyMessage || "No trips recorded for this period.") + "</div>"; return; }
    container.innerHTML = rows.map(function (row) {
      var rate = Math.max(0, Math.min(100, number(row.rate)));
      var delayed = String(row.status || "").toLowerCase() === "delayed";
      return '<div class="ep-route-row ' + (delayed ? "is-delayed" : "") + '"><span title="' + escapeHtml(row.name) + '">' + escapeHtml(row.name) + '</span><span class="ep-route-track"><i style="width:' + rate + '%"></i></span><strong>' + rate.toFixed(1) + '%</strong><em>' + escapeHtml(row.status || "On Time") + "</em></div>";
    }).join("");
  }
  function queryFromForm(form) {
    var params = new URLSearchParams(); if (!form) return params;
    new FormData(form).forEach(function (value, key) { if (value !== "") params.append(key, value); }); return params;
  }
  function liveController(config) {
    var timer = null, request = null, stopped = false, interval = config.interval || 30000;
    async function refresh() {
      if (stopped || document.hidden) return;
      if (request) request.abort(); request = new AbortController();
      if (config.target) setState(config.target, "loading", config.loadingMessage || "Refreshing live data...");
      try {
        var response = await fetch(typeof config.url === "function" ? config.url() : config.url, {headers: {"X-Requested-With": "XMLHttpRequest"}, signal: request.signal});
        var data = await response.json(); if (!response.ok) throw new Error(data.error || "Live chart data could not be refreshed.");
        config.render(data); if (config.target) setState(config.target, "ready", "");
      } catch (error) {
        if (error.name !== "AbortError") { if (config.target) setState(config.target, "error", error.message); if (config.onError) config.onError(error); }
      }
    }
    function visibility() { if (!document.hidden) refresh(); }
    document.addEventListener("visibilitychange", visibility);
    timer = window.setInterval(refresh, interval);
    return {refresh: refresh, destroy: function () { stopped = true; if (request) request.abort(); if (timer) window.clearInterval(timer); document.removeEventListener("visibilitychange", visibility); }};
  }

  window.EduPilotCharts = {
    palette: palette, formatCount: count, formatPercent: percent, formatCurrency: currency, compactNumber: compact,
    setState: setState, destroy: destroy, lineChart: lineChart, areaChart: areaChart,
    groupedBarChart: groupedBarChart, horizontalBarChart: horizontalBarChart, mixedChart: mixedChart,
    doughnutChart: doughnutChart, routePerformance: routePerformance, queryFromForm: queryFromForm,
    liveController: liveController
  };
})(window, document);
