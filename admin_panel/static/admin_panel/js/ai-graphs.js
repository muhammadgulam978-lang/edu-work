(function (window) {
    "use strict";

    var registry = {};
    var palette = {
        teal: "#88D0C5",
        green: "#8BC740",
        blue: "#6EA8FE",
        pink: "#ff5fa2",
        yellow: "#f7d64a",
        orange: "#ff9f45",
        danger: "#ff7a68",
        lavender: "#b8a9ff"
    };

    function chartMajor() {
        if (!window.Chart || !window.Chart.version) return 2;
        return parseInt(String(window.Chart.version).split(".")[0], 10) || 2;
    }

    function hexToRgba(hex, alpha) {
        var clean = String(hex || "").replace("#", "");
        if (clean.length === 3) clean = clean.split("").map(function (c) { return c + c; }).join("");
        var num = parseInt(clean, 16);
        if (isNaN(num)) return "rgba(136,208,197," + alpha + ")";
        return "rgba(" + ((num >> 16) & 255) + "," + ((num >> 8) & 255) + "," + (num & 255) + "," + alpha + ")";
    }

    function hasData(datasets) {
        return (datasets || []).some(function (dataset) {
            return (dataset.data || []).some(function (value) { return Number(value) !== 0; });
        });
    }

    function setEmpty(canvas, empty) {
        if (!canvas || !canvas.parentElement) return;
        var box = canvas.parentElement;
        box.setAttribute("data-empty", empty ? "true" : "false");
        if (!box.querySelector(".ai-graph-empty")) {
            var emptyNode = document.createElement("div");
            emptyNode.className = "ai-graph-empty";
            emptyNode.textContent = "No chart data for selected filters";
            box.appendChild(emptyNode);
        }
    }

    function normalizeDataset(dataset, index, fillDefault) {
        var color = dataset.color || dataset.borderColor || Object.values(palette)[index % Object.values(palette).length];
        return {
            label: dataset.label || "Series",
            data: dataset.data || [],
            borderColor: color,
            backgroundColor: dataset.backgroundColor || hexToRgba(color, dataset.fill === false ? 0 : .16),
            pointBackgroundColor: color,
            pointBorderColor: "#ffffff",
            pointHoverBackgroundColor: "#ffffff",
            pointHoverBorderColor: color,
            pointRadius: dataset.pointRadius == null ? 3 : dataset.pointRadius,
            pointHoverRadius: 6,
            borderWidth: dataset.borderWidth || 3,
            fill: dataset.fill == null ? fillDefault : dataset.fill,
            lineTension: dataset.lineTension == null ? .42 : dataset.lineTension,
            tension: dataset.tension == null ? .42 : dataset.tension
        };
    }

    function lineOptions(extra) {
        var darkGrid = "rgba(255,255,255,.09)";
        var tick = "#d7d9ef";
        if (chartMajor() >= 3) {
            return Object.assign({
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: "index" },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: tick, usePointStyle: true, boxWidth: 8, font: { weight: "400" } }
                    },
                    tooltip: {
                        backgroundColor: "rgba(18,17,36,.96)",
                        borderColor: "rgba(136,208,197,.36)",
                        borderWidth: 1,
                        cornerRadius: 10,
                        titleFont: { weight: "500" },
                        bodyFont: { weight: "400" }
                    }
                },
                scales: {
                    x: { grid: { color: darkGrid, drawBorder: false }, ticks: { color: tick } },
                    y: { beginAtZero: true, grid: { color: darkGrid, drawBorder: false }, ticks: { color: tick } }
                }
            }, extra || {});
        }
        return Object.assign({
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                position: "bottom",
                labels: { fontColor: tick, usePointStyle: true, boxWidth: 8, fontStyle: "normal" }
            },
            tooltips: {
                mode: "index",
                intersect: false,
                backgroundColor: "rgba(18,17,36,.96)",
                borderColor: "rgba(136,208,197,.36)",
                borderWidth: 1,
                cornerRadius: 10,
                titleFontStyle: "normal",
                bodyFontStyle: "normal"
            },
            scales: {
                xAxes: [{ gridLines: { color: darkGrid, drawBorder: false }, ticks: { fontColor: tick } }],
                yAxes: [{ gridLines: { color: darkGrid, drawBorder: false }, ticks: { fontColor: tick, beginAtZero: true } }]
            }
        }, extra || {});
    }

    function destroy(id) {
        if (registry[id]) {
            registry[id].destroy();
            delete registry[id];
        }
        if (window.Chart && typeof window.Chart.getChart === "function") {
            var existing = window.Chart.getChart(id);
            if (existing) existing.destroy();
        }
    }

    function lineChart(id, labels, datasets, options) {
        var canvas = document.getElementById(id);
        if (!canvas || !window.Chart) return null;
        var normalized = (datasets || []).map(function (dataset, index) {
            return normalizeDataset(dataset, index, true);
        });
        setEmpty(canvas, !labels || !labels.length || !hasData(normalized));
        destroy(id);
        registry[id] = new window.Chart(canvas.getContext("2d"), {
            type: "line",
            data: { labels: labels || [], datasets: normalized },
            options: lineOptions(options)
        });
        return registry[id];
    }

    function doughnutChart(id, labels, values, colors, extraOptions) {
        var canvas = document.getElementById(id);
        if (!canvas || !window.Chart) return null;
        var datasets = [{ data: values || [] }];
        setEmpty(canvas, !labels || !labels.length || !hasData(datasets));
        destroy(id);
        var opts = chartMajor() >= 3 ? {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "62%",
            plugins: {
                legend: { position: "bottom", labels: { color: "#d7d9ef", usePointStyle: true, boxWidth: 8 } },
                tooltip: { backgroundColor: "rgba(18,17,36,.96)", borderColor: "rgba(136,208,197,.36)", borderWidth: 1 }
            }
        } : {
            responsive: true,
            maintainAspectRatio: false,
            cutoutPercentage: 62,
            legend: { position: "bottom", labels: { fontColor: "#d7d9ef", usePointStyle: true, boxWidth: 8 } },
            tooltips: { backgroundColor: "rgba(18,17,36,.96)", borderColor: "rgba(136,208,197,.36)", borderWidth: 1 }
        };
        opts = Object.assign(opts, extraOptions || {});
        registry[id] = new window.Chart(canvas.getContext("2d"), {
            type: "doughnut",
            data: {
                labels: labels || [],
                datasets: [{
                    data: values || [],
                    backgroundColor: colors || [palette.green, palette.pink, palette.yellow],
                    borderColor: "rgba(255,255,255,.18)",
                    borderWidth: 2
                }]
            },
            options: opts
        });
        return registry[id];
    }

    function mixedChart(id, labels, datasets, options) {
        var canvas = document.getElementById(id);
        if (!canvas || !window.Chart) return null;
        setEmpty(canvas, !labels || !labels.length || !hasData(datasets));
        destroy(id);
        registry[id] = new window.Chart(canvas.getContext("2d"), {
            type: "bar",
            data: { labels: labels || [], datasets: datasets || [] },
            options: options || {}
        });
        return registry[id];
    }

    function queryFromForm(form) {
        var params = new URLSearchParams();
        if (!form) return params;
        var data = new FormData(form);
        if (typeof data.forEach === "function") {
            data.forEach(function (value, key) {
                if (value !== "") params.append(key, value);
            });
        } else {
            Array.from(data.entries()).forEach(function (entry) {
                if (entry[1] !== "") params.append(entry[0], entry[1]);
            });
        }
        return params;
    }

    window.EduPilotAIGraphs = {
        palette: palette,
        lineChart: lineChart,
        doughnutChart: doughnutChart,
        mixedChart: mixedChart,
        destroy: destroy,
        queryFromForm: queryFromForm
    };
})(window);
