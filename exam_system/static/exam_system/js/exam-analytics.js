(function () {
  "use strict";
  var root = document.querySelector("[data-exam-analytics]");
  var graphs = window.EduPilotCharts;
  if (!root || !graphs) return;

  function initialData() { var node = document.getElementById("exam-analytics-data"); try { return JSON.parse(node ? node.textContent : "{}"); } catch (error) { return {}; } }
  function render(data) {
    var generated = root.querySelector("[data-exam-generated]"); if (generated && data.meta) generated.textContent = data.meta.generated_at;
    var kpis = root.querySelectorAll("[data-exam-kpis] > div");
    (data.kpis || []).forEach(function (item, index) { if (!kpis[index]) return; kpis[index].querySelector("strong").textContent = graphs.formatCount(item.value); kpis[index].querySelector("span").textContent = item.label; });
    graphs.horizontalBarChart("examSubjectChart", data.subject_performance && data.subject_performance.labels || [], [{label: "Average Result", data: data.subject_performance && data.subject_performance.averages || [], color: graphs.palette.academics, showValues: true, valueFormat: "percent"}], {valueFormat: "percent", legend: false, summary: "Average compiled result percentage for each examined subject."});
    graphs.doughnutChart("examGradeChart", data.grade_distribution && data.grade_distribution.labels || [], data.grade_distribution && data.grade_distribution.values || [], ["#38b66a", "#1976d2", "#7651c7", "#f3a33b", "#e7555d", "#8b9894"], {summary: "Compiled student results grouped by grade."});
  }
  var live = graphs.liveController({url: root.dataset.endpoint, render: render, target: document.getElementById("examSubjectChart"), interval: 30000});
  render(initialData());
})();
