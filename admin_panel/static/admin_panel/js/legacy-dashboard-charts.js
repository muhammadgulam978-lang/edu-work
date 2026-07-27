(function () {
  "use strict";
  var root = document.querySelector("[data-legacy-live-charts]");
  var graphs = window.EduPilotCharts;
  if (!root || !graphs) return;

  function render(data) {
    graphs.lineChart("exchangeRates", data.academics && data.academics.chart.labels || [], [{label: "Attendance", data: data.academics && data.academics.chart.attendance || [], color: graphs.palette.academics, showValues: true, valueFormat: "percent"}], {valueFormat: "percent", legend: false, summary: "Student attendance percentage for the last seven days."});
    graphs.groupedBarChart("last_costs", data.finance && data.finance.chart.labels || [], [
      {label: "Income", data: data.finance && data.finance.chart.income || [], color: graphs.palette.green},
      {label: "Expense", data: data.finance && data.finance.chart.expense || [], color: graphs.palette.finance}
    ], {valueFormat: "currency", summary: "Income and expense amounts in PKR for the last seven days."});
    graphs.doughnutChart("efficiency", data.hr && data.hr.chart.labels || [], data.hr && data.hr.chart.values || [], [graphs.palette.green, graphs.palette.yellow, graphs.palette.danger], {summary: "Available, on leave, and absent workforce today."});
  }
  var live = graphs.liveController({url: root.dataset.endpoint + "?period=last_7_days", render: render, target: document.getElementById("exchangeRates"), interval: 30000});
  live.refresh();

  window.toggleDropdown = function (name, event) {
    if (event) event.stopPropagation();
    document.querySelectorAll(".dropdown-menu").forEach(function (menu) { if (menu.id !== "dropdownMenu" + name) menu.style.display = "none"; });
    var menu = document.getElementById("dropdownMenu" + name); if (menu) menu.style.display = menu.style.display === "block" ? "none" : "block";
  };
  window.toggleNavbar = function () { document.body.classList.toggle("nav-collapsed"); };
})();
