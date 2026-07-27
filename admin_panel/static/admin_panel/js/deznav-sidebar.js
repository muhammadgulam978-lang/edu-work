(function () {
  'use strict';

  function cleanPath(pathname) {
    var value = pathname || '/';
    return value.length > 1 ? value.replace(/\/+$/, '') : value;
  }

  function initSidebar(sidebar) {
    if (!sidebar || sidebar.dataset.eduSidebarReady === 'true') return;
    sidebar.dataset.eduSidebarReady = 'true';

    var menu = sidebar.querySelector('[data-edu-sidebar-menu]');
    var overlay = document.querySelector('[data-edu-sidebar-overlay]');
    if (!menu) return;

    var parents = Array.prototype.slice.call(menu.querySelectorAll(':scope > li.has-menu'));
    var toggles = Array.prototype.slice.call(document.querySelectorAll('[data-edu-sidebar-toggle], #mobileMenuToggle, .nav-control'))
      .filter(function (item, index, list) { return list.indexOf(item) === index; });

    function setParentOpen(parent, open) {
      if (!parent) return;
      var trigger = parent.querySelector(':scope > a.has-arrow');
      var submenu = parent.querySelector(':scope > ul');
      parent.classList.toggle('mm-active', open);
      if (trigger) {
        trigger.classList.toggle('mm-active', open);
        trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
      }
      if (submenu) submenu.setAttribute('aria-hidden', open ? 'false' : 'true');
    }

    function closeSiblingParents(current) {
      parents.forEach(function (parent) {
        if (parent !== current) setParentOpen(parent, false);
      });
    }

    parents.forEach(function (parent) {
      var trigger = parent.querySelector(':scope > a.has-arrow');
      if (!trigger) return;

      trigger.setAttribute('role', 'button');
      trigger.setAttribute('aria-expanded', parent.classList.contains('mm-active') ? 'true' : 'false');

      trigger.addEventListener('click', function (event) {
        event.preventDefault();
        var shouldOpen = !parent.classList.contains('mm-active');
        closeSiblingParents(parent);
        setParentOpen(parent, shouldOpen);
      });

      trigger.addEventListener('keydown', function (event) {
        if (event.key === ' ') {
          event.preventDefault();
          trigger.click();
        }
      });
    });

    var currentPath = cleanPath(window.location.pathname);
    var currentSearch = window.location.search || '';
    var currentHash = window.location.hash || '';
    var candidates = [];

    menu.querySelectorAll('a[href]').forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href || href === '#' || href.indexOf('javascript:') === 0 || link.classList.contains('has-arrow')) return;

      var url;
      try {
        url = new URL(href, window.location.origin);
      } catch (error) {
        return;
      }
      if (url.origin !== window.location.origin) return;

      var linkPath = cleanPath(url.pathname);
      var score = -1;
      if (linkPath === currentPath) {
        score = 10000 + linkPath.length;
        if (url.search === currentSearch) score += 1000;
        if (url.hash && url.hash === currentHash) score += 500;
      } else if (linkPath !== '/' && currentPath.indexOf(linkPath + '/') === 0) {
        score = linkPath.length;
      }
      if (score >= 0) candidates.push({ link: link, score: score });
    });

    candidates.sort(function (a, b) { return b.score - a.score; });
    if (candidates.length) {
      var activeLink = candidates[0].link;
      activeLink.classList.add('active-link');
      activeLink.setAttribute('aria-current', 'page');
      var activeParent = activeLink.closest('li.has-menu');
      if (activeParent) {
        closeSiblingParents(activeParent);
        setParentOpen(activeParent, true);
      }
    }

    function isMobile() {
      return window.matchMedia('(max-width: 991px)').matches;
    }

    function setMobileOpen(open) {
      sidebar.classList.toggle('deznav-open', open);
      document.body.classList.toggle('edu-sidebar-open', open);
      if (overlay) {
        overlay.classList.toggle('is-active', open);
        overlay.setAttribute('aria-hidden', open ? 'false' : 'true');
      }
      toggles.forEach(function (toggle) {
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }

    toggles.forEach(function (toggle) {
      toggle.setAttribute('aria-controls', sidebar.id || 'eduSidebar');
      if (!toggle.hasAttribute('aria-expanded')) toggle.setAttribute('aria-expanded', 'false');

      toggle.addEventListener('click', function () {
        if (isMobile()) {
          setMobileOpen(!sidebar.classList.contains('deznav-open'));
        } else if (toggle.hasAttribute('data-edu-sidebar-toggle')) {
          sidebar.classList.toggle('collapsed');
          toggle.setAttribute('aria-expanded', sidebar.classList.contains('collapsed') ? 'false' : 'true');
        }
      });
    });

    if (overlay) {
      overlay.addEventListener('click', function () {
        setMobileOpen(false);
      });
    }

    document.addEventListener('click', function (event) {
      if (!isMobile() || !sidebar.classList.contains('deznav-open')) return;
      if (sidebar.contains(event.target)) return;
      if (toggles.some(function (toggle) { return toggle.contains(event.target); })) return;
      setMobileOpen(false);
    });

    menu.addEventListener('click', function (event) {
      var link = event.target.closest('a[href]');
      if (link && !link.classList.contains('has-arrow') && isMobile()) setMobileOpen(false);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape') return;
      if (sidebar.classList.contains('deznav-open')) {
        setMobileOpen(false);
        if (toggles[0]) toggles[0].focus();
        return;
      }

      var openParent = menu.querySelector(':scope > li.has-menu.mm-active');
      if (openParent) {
        setParentOpen(openParent, false);
        var trigger = openParent.querySelector(':scope > a.has-arrow');
        if (trigger) trigger.focus();
      }
    });

    window.addEventListener('resize', function () {
      if (!isMobile()) setMobileOpen(false);
    });
  }

  function initAllSidebars() {
    document.querySelectorAll('[data-edu-sidebar]').forEach(initSidebar);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllSidebars);
  } else {
    initAllSidebars();
  }
})();
