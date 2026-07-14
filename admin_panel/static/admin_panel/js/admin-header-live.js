(function () {
    "use strict";

    var HEADER_URL = "/admin_panel/header-data/";
    var SUGGEST_URL = "/admin_panel/search-suggestions/";
    var SEARCH_URL = "/admin_panel/search/";
    var styleId = "admin-header-live-style";

    function injectStyles() {
        if (document.getElementById(styleId)) return;
        var style = document.createElement("style");
        style.id = styleId;
        style.textContent = [
            ".admin-header-search-results{position:absolute;top:calc(100% + 8px);left:0;right:0;background:#fff;border:1px solid #e9ecef;border-radius:12px;box-shadow:0 8px 22px rgba(0,0,0,.08);z-index:9999;display:none;overflow:hidden;min-width:310px}",
            ".admin-header-search-results.is-open{display:block}",
            ".admin-header-search-item{display:block;padding:10px 14px;color:#222;text-decoration:none;border-bottom:1px solid #f0f0f0}",
            ".admin-header-search-item:last-child{border-bottom:0}",
            ".admin-header-search-item:hover{background:#F5F5FD;color:#111;text-decoration:none}",
            ".admin-header-search-title{display:block;font-size:14px;font-weight:500;line-height:1.25}",
            ".admin-header-search-meta{display:block;font-size:12px;font-weight:400;color:#6c757d;margin-top:2px}",
            ".admin-header-empty{padding:12px 14px;color:#6c757d;font-size:13px}",
            ".admin-header-notification-empty{padding:12px 8px;color:#6c757d;font-size:13px;text-align:center}",
            ".admin-header-notification-link{color:inherit;text-decoration:none;display:block}",
            ".admin-header-notification-link:hover{text-decoration:none;color:inherit}",
            ".admin-header-status-warning{background:#FFF4E5!important;color:#a35f00!important}",
            ".admin-header-status-success{background:#EEF9E5!important;color:#4b7a18!important}",
            ".admin-header-status-info{background:#DDF7F2!important;color:#246b63!important}",
            ".header .search-area{position:relative}",
            ".header .header-profile>a.nav-link{text-decoration:none}",
            ".header .header-profile>a.nav-link:hover{text-decoration:none}",
            ".header-right .notification_dropdown .dropdown-menu,.header-right .header-profile .dropdown-menu{background:#fff!important;border:1px solid #e9ecef!important;border-radius:14px!important;box-shadow:0 12px 30px rgba(0,0,0,.12)!important;opacity:1!important;backdrop-filter:none!important;z-index:10050!important;overflow:hidden}",
            ".header-right .notification_dropdown .dropdown-menu{width:360px!important;min-width:360px!important;padding:0!important}",
            ".header-right .notification_dropdown .widget-media{background:#fff!important;height:auto!important;max-height:340px!important;overflow:auto!important;padding:12px!important}",
            ".header-right .notification_dropdown .timeline{background:#fff!important;margin:0!important;padding:0!important}",
            ".header-right .notification_dropdown .timeline li{list-style:none!important}",
            ".header-right .notification_dropdown .timeline-panel{background:#fff!important;border-bottom:1px solid #f0f0f0!important;padding:10px 8px!important;margin:0!important;display:flex!important;align-items:flex-start!important}",
            ".header-right .notification_dropdown .timeline li:last-child .timeline-panel{border-bottom:0!important}",
            ".header-right .notification_dropdown .media-body h6{font-size:14px!important;font-weight:500!important;color:#222!important;margin:0 0 3px!important}",
            ".header-right .notification_dropdown .media-body small{font-size:12px!important;font-weight:400!important;color:#6c757d!important;line-height:1.35!important}",
            ".header-right .notification_dropdown .media{width:38px!important;height:38px!important;min-width:38px!important;border-radius:10px!important;display:flex!important;align-items:center!important;justify-content:center!important;font-size:15px!important;font-weight:500!important}",
            ".header-right .notification_dropdown .all-notification{display:block!important;background:#fff!important;border-top:1px solid #e9ecef!important;color:#6c757d!important;text-align:center!important;padding:12px 14px!important;font-size:14px!important;font-weight:400!important;text-decoration:none!important}",
            ".header-right .notification_dropdown .all-notification:hover{background:#F5F5FD!important;color:#111!important;text-decoration:none!important}",
            ".header-right .header-profile .dropdown-menu{min-width:180px!important;padding:8px!important}",
            ".header-right .header-profile .dropdown-item{border-radius:10px!important;color:#222!important;font-size:14px!important;font-weight:400!important;padding:10px 12px!important}",
            ".header-right .header-profile .dropdown-item:hover{background:#F5F5FD!important;color:#111!important}",
            ".bell-wrap{position:relative;cursor:pointer}",
            ".automation-notification-dropdown{display:none;position:absolute;right:0;top:calc(100% + 12px);width:330px;max-height:390px;overflow:auto;background:#fff;border:1px solid #e9ecef;border-radius:12px;box-shadow:0 10px 24px rgba(0,0,0,.1);z-index:9999;padding:12px}",
            ".automation-notification-dropdown.is-open{display:block}",
            ".automation-notification-dropdown ul{list-style:none;margin:0;padding:0}",
            ".automation-notification-dropdown>a{display:block;padding:10px 8px 0;color:#111;text-decoration:none;font-size:13px;font-weight:500}"
        ].join("");
        document.head.appendChild(style);
    }

    function text(value) {
        return value === null || value === undefined ? "" : String(value);
    }

    function escapeHtml(value) {
        return text(value).replace(/[&<>"']/g, function (char) {
            return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"}[char];
        });
    }

    function setText(selector, value) {
        document.querySelectorAll(selector).forEach(function (node) {
            node.textContent = text(value);
        });
    }

    function setAttr(selector, attr, value) {
        document.querySelectorAll(selector).forEach(function (node) {
            if (value) node.setAttribute(attr, value);
        });
    }

    function statusLetter(status) {
        if (status === "warning") return "!";
        if (status === "success") return "✓";
        return "N";
    }

    function renderNotifications(items) {
        document.querySelectorAll("[data-admin-notifications]").forEach(function (list) {
            if (!items || !items.length) {
                list.innerHTML = '<li class="admin-header-notification-empty">No notifications right now.</li>';
                return;
            }
            list.innerHTML = items.map(function (item) {
                var statusClass = "admin-header-status-" + escapeHtml(item.status || "info");
                return [
                    "<li>",
                    '<a class="admin-header-notification-link" href="' + escapeHtml(item.url || "#") + '">',
                    '<div class="timeline-panel">',
                    '<div class="media me-2 media-info ' + statusClass + '">' + statusLetter(item.status) + "</div>",
                    '<div class="media-body">',
                    '<h6 class="mb-1">' + escapeHtml(item.title) + "</h6>",
                    '<small class="d-block">' + escapeHtml(item.message) + "</small>",
                    '<small class="d-block text-muted">' + escapeHtml(item.time) + "</small>",
                    "</div>",
                    "</div>",
                    "</a>",
                    "</li>"
                ].join("");
            }).join("");
        });
    }

    function refreshHeader() {
        fetch(HEADER_URL, {headers: {"X-Requested-With": "XMLHttpRequest"}})
            .then(function (response) {
                if (!response.ok) throw new Error("Header refresh failed");
                return response.json();
            })
            .then(function (payload) {
                setText("[data-admin-notification-count]", payload.notifications_count || 0);
                renderNotifications(payload.notifications || []);
                if (payload.user) {
                    setText("[data-admin-user-name]", payload.user.name || "");
                    setText("[data-admin-user-role]", payload.user.role || "");
                    setAttr("[data-admin-user-avatar]", "src", payload.user.avatar || "");
                }
            })
            .catch(function () {});
    }

    function renderSearchResults(box, results, query) {
        if (!box) return;
        if (!query) {
            box.classList.remove("is-open");
            box.innerHTML = "";
            return;
        }
        if (!results || !results.length) {
            box.innerHTML = '<div class="admin-header-empty">No matching results.</div>';
            box.classList.add("is-open");
            return;
        }
        box.innerHTML = results.map(function (item) {
            return [
                '<a class="admin-header-search-item" href="' + escapeHtml(item.url || "#") + '">',
                '<span class="admin-header-search-title">' + escapeHtml(item.title) + "</span>",
                '<span class="admin-header-search-meta">' + escapeHtml(item.module) + (item.description ? " - " + escapeHtml(item.description) : "") + "</span>",
                "</a>"
            ].join("");
        }).join("");
        box.classList.add("is-open");
    }

    function setupSearch() {
        document.querySelectorAll("[data-admin-search-form]").forEach(function (form) {
            var input = form.querySelector("[data-admin-search]");
            var box = form.querySelector("[data-admin-search-results]");
            var timer = null;
            if (!input || !box) return;

            form.addEventListener("submit", function (event) {
                var q = input.value.trim();
                if (!q) {
                    event.preventDefault();
                    return;
                }
                form.setAttribute("action", SEARCH_URL);
            });

            input.addEventListener("input", function () {
                var q = input.value.trim();
                window.clearTimeout(timer);
                timer = window.setTimeout(function () {
                    if (q.length < 2) {
                        renderSearchResults(box, [], "");
                        return;
                    }
                    fetch(SUGGEST_URL + "?q=" + encodeURIComponent(q), {headers: {"X-Requested-With": "XMLHttpRequest"}})
                        .then(function (response) {
                            if (!response.ok) throw new Error("Search failed");
                            return response.json();
                        })
                        .then(function (payload) {
                            renderSearchResults(box, payload.results || [], q);
                        })
                        .catch(function () {});
                }, 220);
            });
        });

        document.addEventListener("click", function (event) {
            document.querySelectorAll("[data-admin-search-form]").forEach(function (form) {
                if (!form.contains(event.target)) {
                    var box = form.querySelector("[data-admin-search-results]");
                    if (box) box.classList.remove("is-open");
                }
            });
        });
    }

    function setupNotificationDropdowns() {
        document.querySelectorAll("[data-admin-notification-toggle]").forEach(function (toggle) {
            var dropdown = toggle.querySelector(".automation-notification-dropdown");
            if (!dropdown) return;
            toggle.addEventListener("click", function (event) {
                if (event.target.closest("a") && event.target.closest("a").getAttribute("href")) return;
                event.preventDefault();
                dropdown.classList.toggle("is-open");
            });
        });

        document.addEventListener("click", function (event) {
            document.querySelectorAll(".automation-notification-dropdown.is-open").forEach(function (dropdown) {
                if (!dropdown.parentElement.contains(event.target)) {
                    dropdown.classList.remove("is-open");
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        injectStyles();
        setupSearch();
        setupNotificationDropdowns();
        refreshHeader();
        window.setInterval(refreshHeader, 15000);
    });
})();
