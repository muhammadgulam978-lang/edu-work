// =============================================================
// DEZNAV SIDEBAR — collapse/expand behaviour + active link highlight
// Add this file as: admin_panel/js/deznav-sidebar.js
// =============================================================
document.addEventListener('DOMContentLoaded', function () {
  var menu = document.getElementById('menu');
  if (!menu) return;

  // 1) Toggle submenus on click
  menu.querySelectorAll('li.has-menu > a.has-arrow').forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      var li = link.parentElement;
      var wasOpen = li.classList.contains('mm-active');

      // close sibling menus (accordion behaviour)
      menu.querySelectorAll(':scope > li.has-menu.mm-active').forEach(function (openLi) {
        if (openLi !== li) openLi.classList.remove('mm-active');
      });

      li.classList.toggle('mm-active', !wasOpen);
    });
  });

  // 2) Highlight the current page link + auto-open its parent menu
  var currentPath = window.location.pathname.replace(/\/+$/, '') || '/';
  menu.querySelectorAll('a[href]').forEach(function (link) {
    var href = link.getAttribute('href');
    if (!href || href === '#' || href === 'javascript:void(0)') return;

    var linkPath;
    try {
      linkPath = new URL(href, window.location.origin).pathname.replace(/\/+$/, '') || '/';
    } catch (error) {
      return;
    }

    var isDashboardLink = linkPath === '/admin_panel';
    var isCurrent = currentPath === linkPath || (!isDashboardLink && currentPath.indexOf(linkPath + '/') === 0);

    if (isCurrent) {
      link.classList.add('active-link');
      var parentLi = link.closest('ul')?.closest('li.has-menu');
      if (parentLi) parentLi.classList.add('mm-active');
      var topLi = link.closest('ul.metismenu') === menu ? link.closest('li') : null;
      if (topLi) topLi.querySelector(':scope > a')?.classList.add('mm-active');
    }
  });

  // 3) Mobile menu toggle button (id="mobileMenuToggle") — optional, add a button with this id anywhere in your navbar
  var toggleBtn = document.getElementById('mobileMenuToggle');
  var sidebar = document.querySelector('.deznav');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('deznav-open');
    });
  }
});
