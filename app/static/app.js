const $ = (selector) => document.querySelector(selector);

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2800);
}

async function loadAiStatus() {
  const label = $("#ai-status");
  const dot = $("#status-dot");
  try {
    const response = await fetch("/api/ai-status");
    const data = await response.json();
    if (data.configured) {
      label.textContent = `AI 已配置 · ${data.model}`;
      dot.classList.add("online");
      dot.title = "AI 已配置，综述会尝试调用大模型";
    } else {
      label.textContent = "本地规则引擎 · AI 未配置";
      dot.classList.add("offline");
      dot.title = "未配置 API Key，当前使用本地规则引擎";
    }
  } catch {
    label.textContent = "AI 状态未知";
    dot.classList.add("offline");
  }
}

function setupDropzone(zoneSelector, inputSelector, labelSelector, appendFiles = false) {
  const zone = $(zoneSelector);
  const input = $(inputSelector);
  const label = $(labelSelector);
  let selectedFiles = [];
  const syncFiles = (files) => {
    selectedFiles = appendFiles ? [...selectedFiles, ...files] : [...files];
    const unique = new Map(selectedFiles.map((file) => [`${file.name}:${file.size}:${file.lastModified}`, file]));
    selectedFiles = [...unique.values()];
    const transfer = new DataTransfer();
    selectedFiles.forEach((file) => transfer.items.add(file));
    input.files = transfer.files;
    updateFileLabel(input, label);
  };
  ["dragenter", "dragover"].forEach((eventName) => zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach((eventName) => zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.remove("dragging");
  }));
  zone.addEventListener("drop", (event) => {
    syncFiles([...event.dataTransfer.files]);
  });
  input.addEventListener("change", () => syncFiles([...input.files]));
}

function updateFileLabel(input, label) {
  const files = [...input.files];
  label.textContent = files.length ? files.map((file) => file.name).join(", ") : "尚未选择文件";
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

function renderMarkdown(markdown) {
  const lines = String(markdown || "").replace(/\r\n?/g, "\n").split("\n");
  const output = [];
  let listType = "";
  const closeList = () => {
    if (listType) output.push(`</${listType}>`);
    listType = "";
  };

  lines.forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      closeList();
      return;
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = Math.min(6, heading[1].length);
      output.push(`<h${level}>${escapeHtml(heading[2])}</h${level}>`);
      return;
    }
    const ordered = line.match(/^\d+[.、)]\s+(.+)$/);
    if (ordered) {
      if (listType !== "ol") {
        closeList();
        output.push("<ol>");
        listType = "ol";
      }
      output.push(`<li>${escapeHtml(ordered[1])}</li>`);
      return;
    }
    const unordered = line.match(/^[-*]\s+(.+)$/);
    if (unordered) {
      if (listType !== "ul") {
        closeList();
        output.push("<ul>");
        listType = "ul";
      }
      output.push(`<li>${escapeHtml(unordered[1])}</li>`);
      return;
    }
    closeList();
    output.push(`<p>${escapeHtml(line)}</p>`);
  });
  closeList();
  return output.join("");
}

function renderReview(data, target) {
  const chips = (data.keywords || []).map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
  const skipped = (data.skipped || []).map((item) => `<div class="warning">${escapeHtml(item)}</div>`).join("");
  const aiWarning = data.ai && data.ai.configured && data.ai.last_error
    ? `<div class="warning">AI 调用失败，已回退到本地规则引擎：${escapeHtml(data.ai.last_error)}</div>`
    : "";
  const summaries = (data.document_summaries || []).map((item, index) => `
    <article class="source-summary">
      <h4>${index + 1}. ${escapeHtml(item.title || item.filename)} <span class="evidence-engine">${item.evidence_engine === "ai-assisted" ? "AI辅助提取" : "本地提取"}</span></h4>
      <p><strong>研究问题/摘要：</strong>${escapeHtml(item.abstract || "未识别")}</p>
      <p><strong>研究方法：</strong>${escapeHtml(item.methods || "未识别")}</p>
      <p><strong>核心发现：</strong>${escapeHtml(item.findings || "未识别")}</p>
      <p><strong>局限或展望：</strong>${escapeHtml(item.limitations || "未识别")}</p>
    </article>`).join("");
  target.innerHTML = `
    <div class="result-card">
      <div class="result-header">
        <div><h3>${escapeHtml(data.title)}</h3><p>${data.engine === "llm-enhanced" ? "大模型增强模式" : "本地规则引擎"} · ${data.item_count} 篇文献</p></div>
        <div class="result-tools"><a class="small-button" href="/api/download/${data.id}?format=docx">下载整理后的 Word</a><a class="small-button" href="/api/download/${data.id}?format=md">下载 Markdown</a></div>
      </div>
      <div class="keyword-label">抽取关键词（仅作线索，不代表系统判断的研究主题）</div>
      <div class="chips">${chips}</div>
      ${aiWarning}
      ${skipped}
      <div class="result-text markdown-body">${renderMarkdown(data.markdown)}</div>
      <h3 class="subsection-title">逐篇原文证据摘录（用于核对）</h3>
      <p class="evidence-note">仅展示从上传文本中提取到的完整句子；无法确认完整句或字段时会标为“未识别”，不会补写。扫描件或 PDF 的文字抽取质量也会影响结果。</p>
      <div class="source-summaries">${summaries}</div>
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
setupDropzone("#review-dropzone", '#review-form input[type="file"]', "#review-file-name", true);
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
loadAiStatus();
