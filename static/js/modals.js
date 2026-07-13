// static/js/modals.js

function openModal(id) {
  document.getElementById(id).classList.add("open");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}

document
  .getElementById("about-btn")
  .addEventListener("click", () => openModal("about-modal"));
document
  .getElementById("help-btn")
  .addEventListener("click", () => openModal("help-modal"));

document.querySelectorAll(".modal-close").forEach((btn) => {
  btn.addEventListener("click", () => closeModal(btn.dataset.close));
});

document.querySelectorAll(".modal-overlay").forEach((overlay) => {
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal(overlay.id);
  });
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    closeNav();
    document
      .querySelectorAll(".modal-overlay.open")
      .forEach((o) => closeModal(o.id));
  }
});
