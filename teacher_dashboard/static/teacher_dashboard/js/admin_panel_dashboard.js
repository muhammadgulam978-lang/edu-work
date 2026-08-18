//changing end
var data = {
    labels: ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"],
    datasets: [{
        backgroundColor: "rgba(0,0,0,0)",
        borderColor: "rgba(248, 149, 31, 1)",
        borderWidth: 4.5,
        data: [10.2, 10, 13, 12, 15, 13, 14.5, 11, 13.5, 13, 11],
    }]
};

var options = {
    maintainAspectRatio: false,
    legend: {
        display: false
    },
    scales: {
        yAxes: [{
            stacked: true,
            gridLines: {
                display: true,
                color: "rgba(91,37,245, 0.03)"
            },
            ticks: {
                maxTicksLimit: 5,
                min: 9,
                max: 16
            }
        }],
        xAxes: [{
            gridLines: {
                display: false
            }
        }]
    },
    elements: {
        point: {
            radius: 0
        }
    }
};


var ctx = document.getElementById('exchangeRates').getContext('2d');
var myLineChart = new Chart(ctx, {
    type: 'line',
    data: data,
    options: options
});

/*LAST COSTS*/
var data = {
    labels: ["Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"],
    datasets: [{
        label: 'Spending',
        backgroundColor: "rgba(91,37,245, 0.2)",
        data: [500, 300, 800, 150, 200, 150, 800, 200, 800, 100],
    }, {
        label: 'Arrival',
        backgroundColor: "rgba(248, 149, 31, 1)",
        data: [1000, 800, 1800, 1100, 1000, 800, 1800, 1600, 1800, 1200],
    }, ]
};

var options = {
    cornerRadius: 0,
    maintainAspectRatio: false,
    legend: {
        position: 'bottom',
        labels: {
            fontColor: "rgba(0,0,0, 0.5)",
            boxWidth: 20,
            padding: 10
        }
    },
    scales: {
        yAxes: [{
            gridLines: {
                display: true,
                color: "rgba(91,37,245, 0.03)"
            },
            ticks: {
                maxTicksLimit: 5,
            }
        }],
        xAxes: [{}]
    }
};


var ctx = document.getElementById('last_costs').getContext('2d');
var myLineChart = new Chart(ctx, {
    type: 'bar',
    data: data,
    options: options
});

/*EFFICIENCY CHART*/

var data = {
    labels: ["Spend", "Earned"],
    datasets: [{
        label: "Population (millions)",
        backgroundColor: ["rgba(248, 149, 31, 1)", "#dad7e9"],
        data: [65, 35]
    }]
};

var options = {
    maintainAspectRatio: false,
    legend: {
        position: 'bottom',
        labels: {
            fontColor: "rgba(0,0,0, 0.5)",
            boxWidth: 20,
            padding: 10
        }
    },
};


var ctx = document.getElementById('efficiency').getContext('2d');
var myLineChart = new Chart(ctx, {
    type: 'doughnut',
    data: data,
    options: options
});


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


