(function () {
    "use strict";

    function closeMenus(except) {
        document.querySelectorAll("[data-edu-menu].is-open").forEach(function (menu) {
            if (menu !== except) menu.classList.remove("is-open");
        });
    }

    function setupMenus() {
        document.addEventListener("click", function (event) {
            var toggle = event.target.closest("[data-edu-menu-toggle]");
            if (toggle) {
                var key = toggle.getAttribute("data-edu-menu-toggle");
                var root = toggle.closest("[data-edu-portal-header]");
                var menu = root ? root.querySelector('[data-edu-menu="' + key + '"]') : null;
                if (menu) {
                    event.preventDefault();
                    var willOpen = !menu.classList.contains("is-open");
                    closeMenus(menu);
                    menu.classList.toggle("is-open", willOpen);
                }
                return;
            }
            if (!event.target.closest("[data-edu-menu]")) closeMenus();
        });
    }

    function setupClock() {
        function update() {
            var now = new Date();
            var text = now.toLocaleString(undefined, {
                year: "numeric",
                month: "long",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit"
            });
            document.querySelectorAll("[data-edu-portal-clock]").forEach(function (node) {
                node.textContent = text;
            });
        }
        update();
        window.setInterval(update, 30000);
    }

    function setupLanguage() {
        var key = "edupilot_portal_language";
        document.querySelectorAll("[data-edu-portal-language]").forEach(function (select) {
            var saved = window.localStorage.getItem(key);
            if (saved) select.value = saved;
            select.addEventListener("change", function () {
                window.localStorage.setItem(key, select.value);
            });
        });
    }

    function setupNavActive() {
        var path = window.location.pathname.replace(/\/+$/, "") || "/";
        document.querySelectorAll("[data-edu-nav-link]").forEach(function (link) {
            var href = new URL(link.getAttribute("href"), window.location.origin).pathname.replace(/\/+$/, "") || "/";
            var active = href === "/" ? path === href : path === href || path.indexOf(href + "/") === 0;
            link.classList.toggle("is-active", active);
        });
    }

    function setupPortalSearch() {
        document.querySelectorAll("[data-edu-portal-search-form]").forEach(function (form) {
            var input = form.querySelector("[data-edu-portal-search]");
            var results = form.querySelector("[data-edu-portal-search-results]");
            var header = form.closest("[data-edu-portal-header]");
            var links = header ? Array.prototype.slice.call(header.querySelectorAll("[data-edu-nav-link]")) : [];
            if (!input || !results) return;

            function render(items) {
                if (!input.value.trim()) {
                    results.classList.remove("is-open");
                    results.innerHTML = "";
                    return;
                }
                if (!items.length) {
                    results.innerHTML = '<div class="edu-portal-empty">No matching portal page.</div>';
                    results.classList.add("is-open");
                    return;
                }
                results.innerHTML = items.map(function (link) {
                    return '<a href="' + link.href + '">' + link.textContent.trim() + "</a>";
                }).join("");
                results.classList.add("is-open");
            }

            input.addEventListener("input", function () {
                var q = input.value.trim().toLowerCase();
                render(links.filter(function (link) {
                    return link.textContent.toLowerCase().indexOf(q) !== -1;
                }).slice(0, 8));
            });

            form.addEventListener("submit", function (event) {
                event.preventDefault();
                var first = results.querySelector("a");
                if (first) window.location.href = first.href;
            });
        });

        document.addEventListener("click", function (event) {
            document.querySelectorAll("[data-edu-portal-search-results].is-open").forEach(function (box) {
                if (!box.closest("form").contains(event.target)) box.classList.remove("is-open");
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setupMenus();
        setupClock();
        setupLanguage();
        setupNavActive();
        setupPortalSearch();
    });
})();
