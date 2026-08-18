document.addEventListener('DOMContentLoaded', function () {
    const dropdown = document.querySelector('.dropdown-checkbox');
    const toggle = dropdown.querySelector('.dropdown-toggle');

    toggle.addEventListener('click', function () {
        dropdown.classList.toggle('open');
    });

    document.addEventListener('click', function (e) {
        if (!dropdown.contains(e.target)) {
            dropdown.classList.remove('open');
        }
    });
});
