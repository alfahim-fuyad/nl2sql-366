// static/js/navbar.js
document
  .getElementById("logo-btn")
  .addEventListener("click", () => window.location.reload());

const navbar = document.getElementById("navbar");
const hamburger = document.getElementById("nav-hamburger");

function closeNav() {
  navbar.classList.remove("nav-open");
  hamburger.setAttribute("aria-expanded", "false");
}

hamburger.addEventListener("click", (e) => {
  e.stopPropagation();
  const isOpen = navbar.classList.toggle("nav-open");
  hamburger.setAttribute("aria-expanded", String(isOpen));
});

document
  .getElementById("nav-links")
  .querySelectorAll("button")
  .forEach((btn) => {
    btn.addEventListener("click", () => {
      if (window.innerWidth <= 640) closeNav();
    });
  });

document.addEventListener("click", (e) => {
  if (!navbar.contains(e.target)) closeNav();
});
