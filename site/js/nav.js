// Mobile nav toggle. No Bootstrap JS/jQuery is loaded anywhere on the site - just bootstrap.min.css
// - so the .collapse/.show classes it already styles are wired up by hand here instead of relying
// on bootstrap.bundle.js's data-toggle behaviour.
const navbarToggle = document.getElementById("navbarToggle");
const navbarLinks = document.getElementById("navbarLinks");
if (navbarToggle && navbarLinks) {
    navbarToggle.addEventListener("click", () => {
        const open = navbarLinks.classList.toggle("show");
        navbarToggle.setAttribute("aria-expanded", String(open));
    });
}
