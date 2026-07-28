document.addEventListener("DOMContentLoaded", function () {
    var menuToggle = document.getElementById("menu-toggle");
    var sideMenu = document.getElementById("side-menu");
    var overlay = document.getElementById("menu-overlay");

    function closeMenu() {
        sideMenu.classList.remove("open");
        overlay.classList.remove("visible");
    }

    if (menuToggle && sideMenu && overlay) {
        menuToggle.addEventListener("click", function () {
            sideMenu.classList.toggle("open");
            overlay.classList.toggle("visible");
        });

        overlay.addEventListener("click", closeMenu);
    }

    var groupToggles = document.querySelectorAll(".side-menu__group-toggle");
    groupToggles.forEach(function (toggle) {
        toggle.addEventListener("click", function () {
            toggle.parentElement.classList.toggle("open");
        });
    });

    var deleteForms = document.querySelectorAll(".confirm-delete");
    deleteForms.forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var message = form.dataset.confirmMessage || "Are you sure you want to delete this?";
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });
});