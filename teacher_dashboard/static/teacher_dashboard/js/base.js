 function toggleDropdown(menuName, event) {
    // Yeh zaroori hai taake click event document tak na jaye aur dropdown turant close na ho jaye
    event.stopPropagation();

    // Sab dropdown menus ko close kar do except clicked wala
    var allMenus = document.querySelectorAll('.dropdown-menu');
    allMenus.forEach(function(menu) {
        if (menu.id !== 'dropdownMenu' + menuName) {
            menu.style.display = 'none';
        }
    });

    // Clicked wala toggle karo
    var menu = document.getElementById('dropdownMenu' + menuName);
    if (menu.style.display === 'block') {
        menu.style.display = 'none';
    } else {
        menu.style.display = 'block';
    }
}

// Page pe click hone par dropdowns close karne ke liye:
document.addEventListener('click', function(e) {
    var admissionsToggle = document.getElementById('dropdownToggleAdmissions');
    var admissionsMenu = document.getElementById('dropdownMenuAdmissions');
    var academicToggle = document.getElementById('dropdownToggleAcademicYear');
    var academicMenu = document.getElementById('dropdownMenuAcademicYear');

    if (
        !admissionsToggle.contains(e.target) &&
        !admissionsMenu.contains(e.target)
    ) {
        admissionsMenu.style.display = 'none';
    }

    if (
        !academicToggle.contains(e.target) &&
        !academicMenu.contains(e.target)
    ) {
        academicMenu.style.display = 'none';
    }
});


