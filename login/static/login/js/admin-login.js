document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.querySelector(".password-toggle");
    const password = document.getElementById("password");

    if (!toggle || !password) {
        return;
    }

    toggle.addEventListener("click", function () {
        const shouldShow = password.type === "password";
        password.type = shouldShow ? "text" : "password";
        toggle.setAttribute("aria-label", shouldShow ? "Hide password" : "Show password");
        toggle.setAttribute("aria-pressed", String(shouldShow));
        toggle.innerHTML = shouldShow
            ? '<i class="fa-regular fa-eye-slash" aria-hidden="true"></i>'
            : '<i class="fa-regular fa-eye" aria-hidden="true"></i>';
    });
});
