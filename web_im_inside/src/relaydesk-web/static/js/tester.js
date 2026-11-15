document.addEventListener("DOMContentLoaded", () => {
  const methodButtons = document.querySelectorAll(".method-btn");
  const methodInput = document.getElementById("selected-method");
  const bodyGroup = document.getElementById("body-group");
  const headersContainer = document.getElementById("headers-container");
  const addHeaderBtn = document.getElementById("btn-add-header");
  const presetJsonBtn = document.getElementById("btn-preset-json");
  const presetAuthBtn = document.getElementById("btn-preset-auth");
  const testForm = document.getElementById("tester-form");
  const responseInspector = document.getElementById("response-inspector");
  const btnCopyResponse = document.getElementById("btn-copy-response");

  // Handle HTTP method selection
  methodButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      methodButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const method = btn.getAttribute("data-method");
      methodInput.value = method;
      
      // Highlight body input when POST is selected
      if (method === "POST") {
        bodyGroup.style.display = "block";
      } else {
        bodyGroup.style.display = "block";
      }
    });
  });

  // Append a key-value header row
  function addHeaderRow(key = "", val = "") {
    const row = document.createElement("div");
    row.className = "header-row";

    const keyInput = document.createElement("input");
    keyInput.type = "text";
    keyInput.className = "form-control form-control-mono header-key";
    keyInput.placeholder = "Header-Name (e.g. Content-Type)";
    keyInput.value = key;
    keyInput.setAttribute("aria-label", "Header Name");

    const valInput = document.createElement("input");
    valInput.type = "text";
    valInput.className = "form-control form-control-mono header-val";
    valInput.placeholder = "Header-Value (e.g. application/json)";
    valInput.value = val;
    valInput.setAttribute("aria-label", "Header Value");

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn btn-danger-outline btn-sm";
    removeBtn.textContent = "Remove";
    removeBtn.setAttribute("aria-label", "Remove this header row");
    removeBtn.addEventListener("click", () => row.remove());

    row.appendChild(keyInput);
    row.appendChild(valInput);
    row.appendChild(removeBtn);
    headersContainer.appendChild(row);
  }

  if (addHeaderBtn) {
    addHeaderBtn.addEventListener("click", () => addHeaderRow());
  }

  if (presetJsonBtn) {
    presetJsonBtn.addEventListener("click", () => {
      addHeaderRow("Content-Type", "application/json");
    });
  }

  if (presetAuthBtn) {
    presetAuthBtn.addEventListener("click", () => {
      addHeaderRow("Authorization", "Bearer ");
    });
  }

  // Handle connection test execution
  if (testForm) {
    testForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const url = document.getElementById("target-url").value.trim();
      const method = methodInput.value || "GET";
      const bodyText = document.getElementById("request-body").value;

      if (!url) {
        alert("Please specify a target URL.");
        return;
      }

      // Collect user headers
      const headers = {};
      const rows = headersContainer.querySelectorAll(".header-row");
      rows.forEach((row) => {
        const k = row.querySelector(".header-key").value.trim();
        const v = row.querySelector(".header-val").value.trim();
        if (k) {
          headers[k] = v;
        }
      });

      // Render loading state (R-27)
      responseInspector.innerHTML = `
        <div class="card" aria-busy="true">
          <div class="loading-indicator">
            <div class="spinner"></div>
            <p><strong>Relaying request through internal gateway...</strong></p>
            <p class="form-hint">Contacting target endpoint and awaiting response stream.</p>
          </div>
        </div>
      `;

      try {
        const res = await fetch("/api/check", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            url: url,
            method: method,
            headers: headers,
            body: bodyText
          })
        });

        const data = await res.json();
        renderResponse(data);
      } catch (err) {
        renderError("Client transport failure: " + err.message);
      }
    });
  }

  function renderResponse(data) {
    if (!data.success && data.status === 0) {
      renderError(data.error || "Connection refused or gateway unreachable.");
      return;
    }

    let statusClass = "success";
    if (data.status >= 400 && data.status < 500) {
      statusClass = "warning";
    } else if (data.status >= 500 || data.status === 0) {
      statusClass = "error";
    }

    // Try formatting body as pretty JSON for readability
    let formattedBody = data.body || "";
    try {
      const parsed = JSON.parse(formattedBody);
      formattedBody = JSON.stringify(parsed, null, 2);
    } catch {
      // Keep plain text as-is
    }

    const headersList = Object.entries(data.headers || {})
      .map(([k, v]) => `<div><strong>${escapeHtml(k)}:</strong> ${escapeHtml(String(v))}</div>`)
      .join("");

    responseInspector.innerHTML = `
      <div class="card">
        <div class="card-header">
          <h3>Response Inspector</h3>
          <div class="response-meta">
            <span class="status-pill">
              <span class="status-dot ${statusClass}"></span>
              HTTP ${data.status}
            </span>
            <span class="status-pill">${data.elapsed_ms || 0} ms</span>
            <button id="btn-copy-body" type="button" class="btn btn-secondary btn-sm" aria-label="Copy response body">
              Copy Body
            </button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Response Headers</label>
          <div class="code-block" style="margin-top:0.25rem; font-size:0.82rem; max-height:140px;">
            ${headersList || "<span style='color:var(--color-text-muted)'>No headers returned.</span>"}
          </div>
        </div>

        <div class="form-group" style="margin-bottom:0;">
          <label class="form-label">Response Body</label>
          <pre id="response-body-pre" class="response-viewer">${escapeHtml(formattedBody)}</pre>
        </div>
      </div>
    `;

    const copyBtn = document.getElementById("btn-copy-body");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(formattedBody).then(() => {
          copyBtn.textContent = "Copied!";
          setTimeout(() => { copyBtn.textContent = "Copy Body"; }, 2000);
        });
      });
    }
  }

  function renderError(message) {
    responseInspector.innerHTML = `
      <div class="card">
        <div class="card-header">
          <h3>Inspection Error</h3>
          <span class="status-pill">
            <span class="status-dot error"></span>
            Connection Failed
          </span>
        </div>
        <div class="callout" style="border-left-color: var(--color-status-error);">
          <div class="callout-title" style="color: var(--color-status-error);">Diagnostic Report</div>
          <p>${escapeHtml(message)}</p>
        </div>
        <p class="form-hint">
          Check whether the target host exists, responds on the specified port, or adheres to the cluster private network naming rules.
        </p>
      </div>
    `;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});

