(function () {
  "use strict";
  var root = document.querySelector("[data-operations-dashboard]");
  var graphs = window.EduPilotCharts;
  if (!root || !graphs) return;

  var module = root.dataset.module;
  var period = root.querySelector("[data-ops-period]");
  var start = root.querySelector("[data-ops-start]");
  var end = root.querySelector("[data-ops-end]");

  function initialData() {
    var node = document.getElementById("operations-live-data");
    try { return JSON.parse(node ? node.textContent : "{}"); } catch (error) { return {}; }
  }
  function url() {
    var params = new URLSearchParams({period: period.value});
    if (period.value === "custom") { if (start.value) params.set("start_date", start.value); if (end.value) params.set("end_date", end.value); }
    return root.dataset.summaryUrl + "?" + params.toString();
  }
  function renderMetrics(metrics) {
    root.querySelectorAll("[data-ops-metric]").forEach(function (card) {
      var metric = metrics[Number(card.dataset.opsMetric)]; if (!metric) return;
      card.querySelector("span:not(.ops-stat-icon)").textContent = metric.label;
      card.querySelector("strong").textContent = metric.value;
    });
  }
  function render(data) {
    renderMetrics(data.metrics || []);
    var generated = root.querySelector("[data-ops-generated]"); if (generated && data.meta) generated.textContent = data.meta.generated_at;
    var range = root.querySelector("[data-ops-range]"); if (range && data.meta) range.textContent = data.meta.range_label;
    if (module === "procurement") {
      graphs.areaChart("operationsChart", data.chart && data.chart.labels || [], [{
        label: "Approved Value", data: data.chart && data.chart.spend || [], color: graphs.palette.procurement, fill: true, showValues: true, valueFormat: "currency"
      }], {valueFormat: "currency", legend: false, summary: "Approved procurement request value in PKR for the selected period."});
    } else {
      graphs.routePerformance(root.querySelector("[data-ops-routes]"), data.routes || [], "No transport trips are recorded for this period.");
    }
  }
  function toggleCustom() {
    var custom = period.value === "custom";
    root.querySelectorAll("[data-ops-custom]").forEach(function (node) { node.hidden = !custom; });
    if (!custom) live.refresh();
  }

  var target = module === "procurement" ? document.getElementById("operationsChart") : null;
  var live = graphs.liveController({url: url, render: render, target: target, interval: 30000});
  period.addEventListener("change", toggleCustom);
  root.querySelector("[data-ops-refresh]").addEventListener("click", live.refresh);
  render(initialData());
})();
