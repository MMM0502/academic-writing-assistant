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

function renderExportButtons(id, kind) {
  const buttons = [
    `<a class="small-button" href="/api/download/${id}?format=docx">Word</a>`,
    `<a class="small-button" href="/api/download/${id}?format=md">Markdown</a>`,
  ];
  if (kind === "format") {
    buttons.push(
      `<div class="export-dropdown">` +
      `<button class="small-button" onclick="toggleDropdown(this)">导出参考文献 ▾</button>` +
      `<div class="dropdown-menu">` +
      `<a href="/api/download/${id}?format=bibtex">BibTeX (.bib)</a>` +
      `<a href="/api/download/${id}?format=ris">RIS (.ris)</a>` +
      `<a href="/api/download/${id}?format=endnote">EndNote (.enw)</a>` +
      `<a href="/api/download/${id}?format=txt">纯文本 (.txt)</a>` +
      `</div></div>`
    );
  }
  return buttons.join("");
}

function toggleDropdown(btn) {
  const menu = btn.nextElementSibling;
  document.querySelectorAll(".dropdown-menu").forEach((m) => { if (m !== menu) m.classList.remove("show"); });
  menu.classList.toggle("show");
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".export-dropdown")) {
    document.querySelectorAll(".dropdown-menu").forEach((m) => m.classList.remove("show"));
  }
});

function renderStructure(structure) {
  if (!structure || !structure.sections) return "";
  const sections = structure.sections.map((s) => `<span class="chip chip-ok">${escapeHtml(s.label)}</span>`).join("");
  const missing = (structure.missing_sections || []).map((s) => `<span class="chip chip-warn">缺失：${escapeHtml(s)}</span>`).join("");
  return `<div class="structure-info"><p class="meta-label">文档结构</p><div class="chips">${sections}${missing}</div></div>`;
}

function renderFormat(data, target) {
  const warnings = (data.warnings || []).map((item) => `<div class="warning">${escapeHtml(item)}</div>`).join("");
  const structure = renderStructure(data.structure);
  const preserveBtn = data.preserve_available
    ? `<a class="small-button" href="/api/download/${data.id}?format=docx&mode=preserve">保留原稿 Word</a>`
    : "";
  target.innerHTML = `
    <div class="result-card">
      <div class="result-header">
        <div><h3>${escapeHtml(data.title)}</h3><p>${escapeHtml(data.style)} · ${escapeHtml(data.source_name)}</p></div>
        <div class="result-tools">${renderExportButtons(data.id, "format")}${preserveBtn}</div>
      </div>
      <div class="metrics">
        <div class="metric"><strong>${data.paragraph_count}</strong><span>段落</span></div>
        <div class="metric"><strong>${data.reference_count}</strong><span>条参考文献</span></div>
        <div class="metric"><strong>${data.character_count}</strong><span>字符</span></div>
      </div>
      ${structure}
      ${warnings}
      <div class="result-text">${escapeHtml(data.formatted_text)}</div>
    </div>`;
}

function renderCards(cards) {
  if (!cards || !cards.length) return "";
  const cardHtml = cards.map((card) => `
    <div class="literature-card">
      <div class="card-header"><span class="card-index">#${card.index}</span><strong>${escapeHtml(card.title)}</strong><span class="card-year">${escapeHtml(card.year)}</span></div>
      <div class="card-keywords">${(card.keywords || []).map((k) => `<span class="chip">${escapeHtml(k)}</span>`).join("")}</div>
      <div class="card-fields">
        ${renderCardField("研究问题", card.research_question)}
        ${renderCardField("研究方法", card.method)}
        ${renderCardField("数据集", card.dataset)}
        ${renderCardField("主要结论", card.conclusion)}
        ${renderCardField("创新点", card.innovation)}
        ${renderCardField("局限性", card.limitation)}
      </div>
    </div>`).join("");
  return `<div class="cards-section"><p class="meta-label">文献分析卡片</p>${cardHtml}</div>`;
}

function renderCardField(label, value) {
  if (!value || value === "未提取") return "";
  return `<div class="card-field"><span class="field-label">${escapeHtml(label)}</span><span class="field-value">${escapeHtml(value)}</span></div>`;
}

function renderComparisons(comparisons) {
  if (!comparisons || !comparisons.length) return "";
  const items = comparisons.map((cmp) => `
    <div class="comparison-item">
      <span class="cmp-source">文献 ${cmp.source_a} ↔ 文献 ${cmp.source_b}</span>
      <span class="cmp-relation">${escapeHtml(cmp.relation)}</span>
      ${cmp.shared_keywords.length ? `<span class="cmp-keywords">共同：${cmp.shared_keywords.map((k) => escapeHtml(k)).join("、")}</span>` : ""}
    </div>`).join("");
  return `<div class="comparisons-section"><p class="meta-label">观点比较与来源追踪</p>${items}</div>`;
}

function renderLlmStatus(status) {
  if (!status) return "";
  const configured = status.configured ? "已配置" : "未配置";
  const model = status.model || "无";
  const notice = status.privacy_notice ? `<div class="warning">${escapeHtml(status.privacy_notice)}</div>` : "";
  const elapsed = status.elapsed_seconds != null ? ` · 耗时 ${status.elapsed_seconds}s` : "";
  const stat = status.status ? ` · ${escapeHtml(status.status)}` : "";
  const err = status.error ? `<div class="warning">大模型调用失败：${escapeHtml(status.error)}</div>` : "";
  return `<div class="llm-status"><p class="meta-label">大模型状态</p><p>模型：${escapeHtml(model)} · ${configured}${elapsed}${stat}</p>${notice}${err}</div>`;
}

function renderReview(data, target) {
  const chips = (data.keywords || []).map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
  const skipped = (data.skipped || []).map((item) => `<div class="warning">${escapeHtml(item)}</div>`).join("");
  const cards = renderCards(data.cards);
  const comparisons = renderComparisons(data.comparisons);
  const llmStatus = renderLlmStatus(data.llm_status);
  const engineLabel = data.engine === "llm-enhanced" ? "大模型增强模式" : data.engine === "user-edited" ? "用户编辑版" : "本地规则引擎";
  const editBtn = `<button class="small-button" onclick="toggleEdit(${data.id})">编辑综述</button>`;
  target.innerHTML = `
    <div class="result-card">
      <div class="result-header">
        <div><h3>${escapeHtml(data.title)}</h3><p>${engineLabel} · ${data.item_count} 篇文献</p></div>
        <div class="result-tools">${renderExportButtons(data.id, "review")}${editBtn}</div>
      </div>
      ${llmStatus}
      <div class="chips">${chips}</div>
      ${skipped}
      ${cards}
      ${comparisons}
      <div id="review-edit-area" style="display:none;">
        <textarea id="review-edit-text" class="edit-textarea">${escapeHtml(data.markdown)}</textarea>
        <button class="small-button" onclick="saveEdit(${data.id})">保存编辑</button>
      </div>
      <div class="result-text" id="review-markdown">${escapeHtml(data.markdown)}</div>
    </div>`;
}

function toggleEdit(id) {
  const area = $("#review-edit-area");
  const markdown = $("#review-markdown");
  if (area.style.display === "none") {
    area.style.display = "block";
    markdown.style.display = "none";
  } else {
    area.style.display = "none";
    markdown.style.display = "block";
  }
}

async function saveEdit(id) {
  const text = $("#review-edit-text").value;
  if (!text.trim()) {
    showToast("内容不能为空");
    return;
  }
  const formData = new FormData();
  formData.append("job_id", id);
  formData.append("markdown", text);
  try {
    const response = await fetch("/api/review/edit", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "保存失败");
    renderReview(payload, $("#review-result"));
    showToast("编辑已保存");
  } catch (error) {
    showToast(error.message);
  }
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
        <div>${renderExportButtons(item.id, item.kind)}</div>
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
