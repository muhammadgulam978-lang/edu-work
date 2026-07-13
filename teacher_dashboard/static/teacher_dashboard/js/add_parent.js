// static/admin_panel/js/add_parent.js

document.addEventListener('DOMContentLoaded', function () {
    $('#students').select2({
        placeholder: "Select Students",
        allowClear: true,
        width: '100%'  // optional, makes it full width like other inputs
    });
});
