(function () {
    "use strict";

    var page = document.querySelector("[data-ai-overview]");
    if (!page) return;

    var graphs = window.EduPilotAIGraphs;
    var filterForm = document.getElementById("aiOverviewFilters");
    var loading = page.querySelector("[data-page-loading]");
    var errorBox = page.querySelector("[data-page-error]");
    var refreshInProgress = false;

    function initialData() {
        var node = document.getElementById("ai-overview-data");
        try { return JSON.parse(node ? node.textContent : "{}"); }
        catch (error) { return {}; }
    }

    function safeUrl(value) {
        var url = String(value || "#");
        return url.charAt(0) === "/" || url.charAt(0) === "#" ? url : "#";
    }

    function safeClass(value, fallback) {
        var result = String(value || "");
        return /^[a-zA-Z0-9 _-]+$/.test(result) ? result : fallback;
    }

    function clear(node) {
        while (node && node.firstChild) node.removeChild(node.firstChild);
    }

    function element(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = String(text);
        return node;
    }

    function icon(className) {
        return element("i", safeClass(className, "fas fa-circle"));
    }

    function setError(message) {
        if (!errorBox) return;
        errorBox.textContent = message || "Live analytics could not be refreshed. Existing data is still displayed.";
        errorBox.hidden = false;
    }

    function clearError() {
        if (errorBox) errorBox.hidden = true;
    }

    function renderKpis(items) {
        var grid = page.querySelector("[data-kpi-grid]");
        if (!grid || !Array.isArray(items)) return;
        clear(grid);
        items.forEach(function (item) {
            var card = element("article", "ai-kpi ai-tone-" + safeClass(item.tone, "teal"));
            card.dataset.kpiCard = item.key || "metric";
            var iconBox = element("span", "ai-icon");
            iconBox.appendChild(icon(item.icon));
            var body = element("div");
            body.appendChild(element("span", "ai-label", item.title));
            body.appendChild(element("strong", "", item.value));
            body.appendChild(element("small", "", item.label));
            card.appendChild(iconBox); card.appendChild(body); grid.appendChild(card);
        });
    }

    function renderSnapshot(items) {
        var grid = page.querySelector("[data-snapshot-grid]");
        if (!grid || !Array.isArray(items)) return;
        clear(grid);
        items.forEach(function (item) {
            var box = element("div"); box.dataset.snapshot = item.key || "item";
            box.appendChild(element("strong", "", item.value));
            box.appendChild(element("span", "", item.label));
            if (item.sublabel) box.appendChild(element("small", "", item.sublabel));
            grid.appendChild(box);
        });
    }

    function renderAlerts(items) {
        var grid = page.querySelector("[data-alert-list]");
        if (!grid || !Array.isArray(items)) return;
        clear(grid);
        items.forEach(function (item) {
            var link = element("a", "ai-alert ai-alert-" + safeClass(item.tone, "info"));
            link.href = safeUrl(item.url); link.appendChild(icon(item.icon));
            var body = element("span");
            body.appendChild(element("strong", "", item.title));
            body.appendChild(element("small", "", item.detail));
            body.appendChild(element("em", "", item.action || "Open"));
            link.appendChild(body); grid.appendChild(link);
        });
        var count = page.querySelector("[data-alert-count]");
        if (count) count.textContent = items.length + (items.length === 1 ? " live signal" : " live signals");
    }

    function renderModules(items) {
        var grid = page.querySelector("[data-module-grid]");
        if (!grid || !Array.isArray(items)) return;
        clear(grid);
        items.forEach(function (item) {
            var card = element("article", "ai-module-card");
            var title = element("div", "ai-module-title");
            var iconBox = element("span"); iconBox.appendChild(icon(item.icon));
            var titleText = element("div"); titleText.appendChild(element("h3", "", item.title));
            titleText.appendChild(element("small", item.status === "Needs Review" ? "review" : "", item.status));
            title.appendChild(iconBox); title.appendChild(titleText);
            var values = element("div", "ai-module-values");
            [[item.primary_value, item.primary_label], [item.secondary_value, item.secondary_label]].forEach(function (pair) {
                var metric = element("div"); metric.appendChild(element("strong", "", pair[0])); metric.appendChild(element("span", "", pair[1])); values.appendChild(metric);
            });
            var link = element("a", "", "Open module "); link.href = safeUrl(item.url); link.appendChild(icon("fas fa-arrow-right"));
            card.appendChild(title); card.appendChild(values); card.appendChild(link); grid.appendChild(card);
        });
    }

    function renderTrends(items) {
        var grid = page.querySelector("[data-trend-list]");
        if (!grid || !Array.isArray(items)) return;
        clear(grid);
        items.forEach(function (item) {
            var row = element("div", "ai-trend");
            var top = element("div"); top.appendChild(element("span", "", item.label)); top.appendChild(element("strong", "", item.value));
            var progress = element("div", "ai-progress ai-progress-" + safeClass(item.tone, "teal"));
            var bar = element("span");
            var width = Math.max(0, Math.min(100, (Number(item.value) || 0) / (Number(item.max) || 1) * 100));
            bar.style.width = width + "%"; progress.appendChild(bar); row.appendChild(top); row.appendChild(progress); grid.appendChild(row);
        });
    }

    function renderRisk(risk) {
        if (!risk) return;
        var score = page.querySelector("[data-risk-score]"); if (score) score.textContent = risk.score;
        var list = page.querySelector("[data-risk-list]"); if (!list || !Array.isArray(risk.breakdown)) return;
        clear(list);
        risk.breakdown.forEach(function (item) {
            var link = element("a"); link.href = safeUrl(item.url); link.appendChild(icon(item.icon));
            var text = element("span", "", item.label); text.appendChild(element("small", "", item.value + " live records"));
            link.appendChild(text); link.appendChild(element("strong", "", "+" + item.points)); list.appendChild(link);
        });
    }

    function renderHealth(health) {
        if (!health) return;
        var status = page.querySelector("[data-health-status]");
        if (status) { status.textContent = health.status; status.className = "ai-health-status ai-health-" + safeClass(health.tone, "warning"); }
        var grid = page.querySelector("[data-health-grid]"); if (!grid || !Array.isArray(health.items)) return;
        clear(grid);
        health.items.forEach(function (item) {
            var link = element("a"); link.href = safeUrl(item.url); link.appendChild(icon(item.icon));
            link.appendChild(element("strong", "", item.value)); link.appendChild(element("span", "", item.label)); grid.appendChild(link);
        });
    }

    function chartMajor() {
        return window.Chart && window.Chart.version ? parseInt(String(window.Chart.version).split(".")[0], 10) || 2 : 2;
    }

    function lightLineOptions(hideLegend) {
        var grid = "rgba(47,74,68,.10)", tick = "#657873";
        if (chartMajor() >= 3) return {
            responsive: true, maintainAspectRatio: false, interaction: { intersect: false, mode: "index" },
            plugins: { legend: { display: !hideLegend, position: "bottom", labels: { color: tick, usePointStyle: true, boxWidth: 7 } } },
            scales: { x: { grid: { color: grid }, ticks: { color: tick } }, y: { beginAtZero: true, grid: { color: grid }, ticks: { color: tick } } }
        };
        return {
            responsive: true, maintainAspectRatio: false,
            legend: { display: !hideLegend, position: "bottom", labels: { fontColor: tick, usePointStyle: true, boxWidth: 7, fontStyle: "normal" } },
            tooltips: { mode: "index", intersect: false, backgroundColor: "rgba(16,35,31,.92)" },
            scales: { xAxes: [{ gridLines: { color: grid, drawBorder: false }, ticks: { fontColor: tick } }], yAxes: [{ gridLines: { color: grid, drawBorder: false }, ticks: { fontColor: tick, beginAtZero: true } }] }
        };
    }

    function renderCharts(charts) {
        if (!charts || !graphs || !window.Chart) return;
        var colors = graphs.palette;
        graphs.lineChart("aiAttendanceChart", charts.attendance && charts.attendance.labels, [
            { label: "Present", data: charts.attendance && charts.attendance.present, color: colors.green, fill: false, borderWidth: 2 },
            { label: "Absent", data: charts.attendance && charts.attendance.absent, color: colors.pink, fill: false, borderWidth: 2 },
            { label: "Leave", data: charts.attendance && charts.attendance.leave, color: colors.yellow, fill: false, borderWidth: 2 }
        ], lightLineOptions(false));

        var feeLabels = charts.fees && charts.fees.labels || [];
        graphs.mixedChart("aiFeeChart", feeLabels, [
            { type: "bar", label: "Billed Amount (PKR)", data: charts.fees && charts.fees.total || [], backgroundColor: "rgba(50,127,229,.62)", borderColor: colors.blue, borderWidth: 1 },
            { type: "line", label: "Paid Amount (PKR)", data: charts.fees && charts.fees.paid || [], borderColor: colors.green, backgroundColor: "rgba(51,184,107,.10)", pointBackgroundColor: colors.green, borderWidth: 2, fill: false, lineTension: .32, tension: .32 }
        ], lightLineOptions(false));

        graphs.lineChart("aiAdmissionsChart", charts.admissions && charts.admissions.labels, [
            { label: "Admissions", data: charts.admissions && charts.admissions.values, color: colors.lavender, fill: false, borderWidth: 2 }
        ], lightLineOptions(true));

        var donutOptions = chartMajor() >= 3 ? { plugins: { legend: { position: "bottom", labels: { color: "#657873", usePointStyle: true, boxWidth: 7 } } } } : { legend: { position: "bottom", labels: { fontColor: "#657873", usePointStyle: true, boxWidth: 7 } } };
        graphs.doughnutChart("aiAttendanceDonutChart", charts.attendance_donut && charts.attendance_donut.labels, charts.attendance_donut && charts.attendance_donut.values, [colors.green, colors.pink, colors.yellow], donutOptions);
        graphs.lineChart("aiWorkloadChart", charts.teacher_workload && charts.teacher_workload.labels, [{ label: "Assigned Periods", data: charts.teacher_workload && charts.teacher_workload.values, color: colors.blue, fill: false }], lightLineOptions(true));
        graphs.lineChart("aiFixtureMixChart", charts.fixture_mix && charts.fixture_mix.labels, [
            { label: "Manual", data: charts.fixture_mix && charts.fixture_mix.manual, color: colors.orange, fill: false },
            { label: "Automated", data: charts.fixture_mix && charts.fixture_mix.auto, color: colors.teal, fill: false }
        ], lightLineOptions(false));
    }

    function renderAll(data) {
        if (!data) return;
        renderKpis(data.kpis); renderSnapshot(data.snapshot); renderAlerts(data.alerts);
        renderModules(data.modules); renderTrends(data.trends); renderRisk(data.risk); renderHealth(data.system_health); renderCharts(data.charts);
        var generated = page.querySelector("[data-generated-at]"); if (generated && data.generated_at) generated.textContent = data.generated_at;
        page.querySelectorAll("[data-period-label]").forEach(function (node) { node.textContent = data.meta && data.meta.period_label || "Selected range"; });
    }

    async function refreshAnalytics() {
        if (refreshInProgress) return;
        refreshInProgress = true; clearError(); if (loading) loading.hidden = false;
        try {
            var query = graphs && filterForm ? graphs.queryFromForm(filterForm).toString() : "";
            var response = await fetch(page.dataset.analyticsUrl + (query ? "?" + query : ""), { headers: { "X-Requested-With": "XMLHttpRequest" } });
            var data = await response.json();
            if (!response.ok) throw new Error(data.error || "Live analytics could not be refreshed.");
            renderAll(data);
        } catch (error) { setError(error.message); }
        finally { refreshInProgress = false; if (loading) loading.hidden = true; }
    }

    function updateCustomDates() {
        if (!filterForm) return;
        var custom = filterForm.querySelector("[name=period]").value === "custom";
        filterForm.querySelectorAll("[data-custom-date]").forEach(function (input) { input.disabled = !custom; input.required = custom; if (!custom) input.value = ""; });
    }

    function renderCopilotActions(actions) {
        var root = page.querySelector("[data-copilot-actions]"); if (!root) return;
        clear(root);
        (actions || []).forEach(function (action) {
            var node;
            if (action.kind === "auto_report") {
                node = element("button", "", action.label || "Generate report"); node.type = "button"; node.dataset.autoReport = "true";
                var meta = action.meta || {}; node.dataset.reportType = meta.report_type || "full"; node.dataset.period = meta.period || "today"; node.dataset.reportTitle = meta.title || action.label || "AI report"; node.dataset.source = meta.source || "ai_overview";
            } else { node = element("a", "", action.label || "Open"); node.href = safeUrl(action.url); }
            root.appendChild(node);
        });
    }

    async function submitCopilot(message) {
        var form = page.querySelector("[data-copilot-form]");
        var responseBox = page.querySelector("[data-copilot-response]");
        var reply = page.querySelector("[data-copilot-reply]");
        var button = form && form.querySelector("button[type=submit]");
        if (!form || !responseBox || !reply || !message) return;
        responseBox.hidden = false; responseBox.classList.remove("is-error"); reply.textContent = "Reviewing live ERP records..."; renderCopilotActions([]); button.disabled = true;
        try {
            var body = new FormData(form); body.set("message", message);
            var response = await fetch(form.action, { method: "POST", body: body, headers: { "X-Requested-With": "XMLHttpRequest" } });
            var data = await response.json(); if (!response.ok) throw new Error(data.error || "Copilot could not answer this question.");
            reply.textContent = data.reply || "No response was returned."; renderCopilotActions(data.actions);
        } catch (error) { responseBox.classList.add("is-error"); reply.textContent = error.message; }
        finally { button.disabled = false; }
    }

    if (filterForm) {
        filterForm.addEventListener("submit", function (event) { event.preventDefault(); refreshAnalytics(); });
        filterForm.querySelector("[name=period]").addEventListener("change", updateCustomDates);
        filterForm.querySelector("[data-filter-reset]").addEventListener("click", function () { filterForm.reset(); updateCustomDates(); refreshAnalytics(); });
        updateCustomDates();
    }

    var copilotForm = page.querySelector("[data-copilot-form]");
    if (copilotForm) copilotForm.addEventListener("submit", function (event) {
        event.preventDefault(); var input = copilotForm.querySelector("[name=message]"); var message = input.value.trim();
        if (!message) { input.focus(); return; } submitCopilot(message);
    });
    page.querySelectorAll("[data-command]").forEach(function (button) {
        button.addEventListener("click", function () { var input = copilotForm.querySelector("[name=message]"); input.value = button.dataset.command || ""; submitCopilot(input.value); });
    });

    renderCharts(initialData().charts || {});
    window.setInterval(refreshAnalytics, 30000);
})();
