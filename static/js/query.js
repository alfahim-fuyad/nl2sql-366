// static/js/query.js

askBtn.addEventListener("click", runQuery);

questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runQuery();
});

function runQuery() {
  const question = questionInput.value.trim();

  if (!question) {
    questionInput.focus();
    return;
  }

  askBtn.disabled = true;
  askBtn.innerHTML = '<span class="spinner"></span>Running…';
  clearResults();

  fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  })
    .then((r) => r.json())
    .then((data) => {
      askBtn.disabled = false;
      askBtn.textContent = "Ask";

      // Show generated SQL and intent
      if (data.sql) {
        sqlOutput.textContent = data.sql;
        intentLabel.textContent = "Intent: " + (data.intent || "—");
        sqlBlock.style.display = "block";
      }

      // Show error
      if (data.error) {
        showError(data.error);
        return;
      }

      /*
       * COLUMN COUNT QUERY
       *
       * Example:
       * "How many columns are there?"
       *
       * Backend should return:
       * {
       *   intent: "COLUMN_COUNT",
       *   count: 13,
       *   columns: [...]
       * }
       */
      if (
        data.intent &&
        data.intent.toUpperCase() === "COLUMN_COUNT"
      ) {
        renderColumnCount(data.columns, data.count);
        return;
      }

      /*
       * NORMAL SQL QUERY
       */
      if (data.columns && data.columns.length > 0) {
        renderTable(data.columns, data.rows || [], data.count);
      } else {
        resultsBlock.style.display = "block";

        resultsMeta.innerHTML =
          "<strong>0</strong> rows returned.";

        resultsThead.innerHTML = "";

        resultsTbody.innerHTML =
          '<tr><td colspan="99" class="no-results">No results found.</td></tr>';
      }
    })
    .catch(() => {
      askBtn.disabled = false;
      askBtn.textContent = "Ask";
      showError("Request failed. Please try again.");
    });
}


/*
 * ==========================================
 * COLUMN COUNT RESULT
 * ==========================================
 */
function renderColumnCount(columns, count) {
  resultsBlock.style.display = "block";

  const columnCount = Number(count) || (columns ? columns.length : 0);

  resultsMeta.innerHTML =
    `<strong>${columnCount.toLocaleString()}</strong> ` +
    `column${columnCount !== 1 ? "s" : ""} found.`;

  /*
   * Create a simple two-column table:
   *
   * # | Column Name
   */
  resultsThead.innerHTML = `
    <tr>
      <th>#</th>
      <th>Column Name</th>
    </tr>
  `;

  if (!columns || columns.length === 0) {
    resultsTbody.innerHTML =
      '<tr><td colspan="2" class="no-results">No columns found.</td></tr>';

    return;
  }

  resultsTbody.innerHTML = columns
    .map(
      (column, index) => `
        <tr>
          <td>${index + 1}</td>
          <td>${escHtml(String(column))}</td>
        </tr>
      `,
    )
    .join("");
}


/*
 * ==========================================
 * NORMAL QUERY RESULT TABLE
 * ==========================================
 */
function renderTable(columns, rows, count) {
  resultsBlock.style.display = "block";

  resultsMeta.innerHTML =
    `<strong>${count.toLocaleString()}</strong> ` +
    `row${count !== 1 ? "s" : ""} returned.`;

  resultsThead.innerHTML =
    "<tr>" +
    columns
      .map((c) => `<th>${escHtml(String(c))}</th>`)
      .join("") +
    "</tr>";

  if (rows.length === 0) {
    resultsTbody.innerHTML =
      `<tr><td colspan="${columns.length}" class="no-results">No results found.</td></tr>`;
  } else {
    resultsTbody.innerHTML = rows
      .map(
        (row) =>
          "<tr>" +
          row
            .map(
              (cell) =>
                `<td>${escHtml(
                  cell === null ? "NULL" : String(cell),
                )}</td>`,
            )
            .join("") +
          "</tr>",
      )
      .join("");
  }
}