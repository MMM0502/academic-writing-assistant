const $ = (selector) => document.querySelector(selector);

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2800);
}

function setupDropzone(zoneSelector, inputSelector, labelSelector) {
  const zone = $(zoneSelector);
  const input = $(inputSelector);
  const label = $(labelSelector);
  ["dragenter", "dragover"].forEach((eventName) => zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach((eventName) => zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.remove("dragging");
  }));
  zone.addEventListener("drop", (event) => {
    input.files = event.dataTransfer.files;
    updateFileLabel(input, label);
  });
  input.addEventListener("change", () => updateFileLabel(input, label));
}

function updateFileLabel(input, label) {
  const files = [...input.files];
  label.textContent = files.length ? files.map((file) => file.name).join("、") : "尚未选择文件";
}

function activateTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      $(`#panel-${tab.dataset.tab}`).classList.add("active");
      if (tab.dataset.tab === "history") loadHistory();
    });
  });
}

async function submitForm(form, endpoint, resultSelector) {
  const files = form.querySelector('input[type="file"]').files;
  if (!files.length) {
    showToast("请先选择文件");
    return;
  }
  const result = $(resultSelector);
  result.innerHTML = '<div class="empty-state">正在分析文稿，请稍候...</div>';
  const data = new FormData(form);
  try {
    const response = await fetch(endpoint, { method: "POST", body: data });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "处理失败");
    endpoint.includes("format") ? renderFormat(payload, result) : renderReview(payload, result);
    showToast("处理完成，结果已保存到本地记录");
  } catch (error) {
    result.innerHTML = `<div class="warning">${escapeHtml(error.message)}</div>`;
    showToast(error.message);
  }
}

function renderFormat(data, target) {
  const warnings = (data.warnings || []).map((item) => `<div class="warning">${escapeHtml(item)}</div>`).join("");
  target.innerHTML = `
    <div class="result-card">
      <div class="result-header">
        <div><h3>${escapeHtml(data.title)}</h3><p>${escapeHtml(data.style)} · ${escapeHtml(data.source_name)}</p></div>
        <div class="result-tools"><a class="small-button" href="/api/download/${data.id}?format=docx">下载整理后的 Word</a><a class="small-button" href="/api/download/${data.id}?format=md">下载 Markdown</a></div>
      </div>
      <div class="metrics">
        <div class="metric"><strong>${data.paragraph_count}</strong><span>段落</span></div>
        <div class="metric"><strong>${data.reference_count}</strong><span>条参考文献</span></div>
        <div class="metric"><strong>${data.character_count}</strong><span>字符</span></div>
      </div>
      ${warnings}
      <div class="result-text">${escapeHtml(data.formatted_text)}</div>
    </div>`;
}

function renderReview(data, target) {
  const chips = (data.keywords || []).map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
  const skipped = (data.skipped || []).map((item) => `<div class="warning">${escapeHtml(item)}</div>`).join("");
  target.innerHTML = `
    <div class="result-card">
      <div class="result-header">
        <div><h3>${escapeHtml(data.title)}</h3><p>${data.engine === "llm-enhanced" ? "大模型增强模式" : "本地规则引擎"} · ${data.item_count} 篇文献</p></div>
        <div class="result-tools"><a class="small-button" href="/api/download/${data.id}?format=docx">下载整理后的 Word</a><a class="small-button" href="/api/download/${data.id}?format=md">下载 Markdown</a></div>
      </div>
      <div class="chips">${chips}</div>
      ${skipped}
      <div class="result-text">${escapeHtml(data.markdown)}</div>
    </div>`;
}

async function loadHistory() {
  const target = $("#history-list");
  try {
    const response = await fetch("/api/history");
    const data = await response.json();
    if (!data.items.length) {
      target.innerHTML = '<div class="empty-state">还没有处理记录。完成一次文稿规整或综述生成后，结果会出现在这里。</div>';
      return;
    }
    target.innerHTML = data.items.map((item) => `
      <div class="history-item">
        <div><span class="history-type">${item.kind === "format" ? "文稿规整" : "综述生成"}</span><h3>${escapeHtml(item.title)}</h3><p>${new Date(item.created_at).toLocaleString("zh-CN")}</p></div>
        <div><a class="small-button" href="/api/download/${item.id}?format=docx">Word</a><a class="small-button" href="/api/download/${item.id}?format=md">Markdown</a></div>
      </div>`).join("");
  } catch {
    target.innerHTML = '<div class="warning">历史记录读取失败，请检查服务是否仍在运行。</div>';
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[char]));
}

activateTabs();
setupDropzone("#format-dropzone", '#format-form input[type="file"]', "#format-file-name");
setupDropzone("#review-dropzone", '#review-form input[type="file"]', "#review-file-name");
$("#format-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/api/format", "#format-result");
});
$("#review-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitForm(event.currentTarget, "/api/review", "#review-result");
});
$("#refresh-history").addEventListener("click", loadHistory);
loadHistory();
