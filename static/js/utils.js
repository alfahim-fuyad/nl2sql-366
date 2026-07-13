// static/js/utils.js
function showGlobalError(msg) {
  const g = document.getElementById("global-error");
  g.textContent = msg;
  g.style.display = "block";
}

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.style.display = "block";
}

function clearResults() {
  sqlBlock.style.display = "none";
  errorBox.style.display = "none";
  resultsBlock.style.display = "none";
  sqlOutput.textContent = "";
  intentLabel.textContent = "";
  resultsThead.innerHTML = "";
  resultsTbody.innerHTML = "";
  resultsMeta.textContent = "";
}

function escHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
