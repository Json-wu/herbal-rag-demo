const questionEl = document.querySelector("#question");
const askButton = document.querySelector("#ask");
const examplesEl = document.querySelector("#examples");
const answerEl = document.querySelector("#answer");
const hitsEl = document.querySelector("#hits");
const statusEl = document.querySelector("#status");
const docsEl = document.querySelector("#docs");
const formNote = document.querySelector("#form-note");

const kindLabel = {
  answer: "",
  refuse: "拒答",
  safety: "安全边界",
};

function appendText(parent, text) {
  const lines = text.split("\n");
  lines.forEach((line, index) => {
    parent.append(document.createTextNode(line));
    if (index < lines.length - 1) {
      parent.append(document.createElement("br"));
    }
  });
}

function focusHit(marker) {
  const card = document.getElementById(`hit-${marker}`);
  if (!card) return;
  document.querySelectorAll(".hit").forEach((item) => item.classList.remove("active"));
  card.classList.add("active");
  card.scrollIntoView({ behavior: "smooth", block: "center" });
}

function renderAnswer(payload) {
  answerEl.className = "panel";
  if (payload.refusal_reason) answerEl.classList.add(payload.refusal_reason);
  answerEl.replaceChildren();
  const title = document.createElement("h2");
  title.textContent = "回答";
  const body = document.createElement("div");
  body.className = "answer-text";
  payload.answer.split(/(\[\d+\])/g).forEach((part) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (!match) {
      appendText(body, part);
      return;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "cite";
    button.textContent = part;
    button.addEventListener("click", () => focusHit(match[1]));
    body.append(button);
  });
  answerEl.append(title, body);
  if (!payload.citations.length) return;
  const list = document.createElement("ul");
  list.className = "cite-list";
  payload.citations.forEach((cite) => {
    const hit = payload.hits[cite.marker - 1];
    if (!hit) return;
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "text-button";
    button.textContent = `[${cite.marker}] ${hit.title} · ${hit.section} · ${hit.filename}`;
    button.addEventListener("click", () => focusHit(String(cite.marker)));
    item.append(button);
    list.append(item);
  });
  answerEl.append(list);
}

function renderHits(payload) {
  hitsEl.className = "panel";
  hitsEl.replaceChildren();
  const title = document.createElement("h2");
  title.textContent = "检索片段";
  hitsEl.append(title);
  const note = document.createElement("p");
  note.className = "note";
  if (payload.refusal_reason === "medical_boundary") {
    note.textContent = "下列片段只供核对，没有被用作诊断、处方或剂量建议。";
    hitsEl.append(note);
  } else if (payload.refusal_reason === "insufficient_evidence") {
    note.textContent = payload.hits.length
      ? "检索到的片段不足以支持回答，因此没有引用。"
      : "没有检索到达到相关度要求的片段。";
    hitsEl.append(note);
  }
  payload.hits.forEach((hit, index) => {
    const marker = index + 1;
    const card = document.createElement("article");
    card.className = "hit";
    card.id = `hit-${marker}`;
    const head = document.createElement("div");
    head.className = "hit-head";
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = payload.refused ? `片段 ${marker}` : `[${marker}]`;
    const score = document.createElement("span");
    score.textContent = `相关度 ${Number(hit.score).toFixed(2)}`;
    head.append(badge, score);
    const heading = document.createElement("h3");
    heading.textContent = hit.title;
    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `${hit.section} · ${hit.filename}`;
    const source = document.createElement("p");
    source.className = "meta";
    source.textContent = `来源：${hit.source}`;
    const quote = document.createElement("p");
    quote.className = "quote";
    quote.textContent = hit.text;
    card.append(head, heading, meta, source, quote);
    hitsEl.append(card);
  });
}

async function ask(question) {
  questionEl.value = question;
  askButton.disabled = true;
  askButton.textContent = "检索中…";
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!response.ok) throw new Error(String(response.status));
    const payload = await response.json();
    renderAnswer(payload);
    renderHits(payload);
    if (window.matchMedia("(max-width: 860px)").matches) {
      answerEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (_error) {
    answerEl.className = "panel";
    answerEl.replaceChildren();
    const title = document.createElement("h2");
    title.textContent = "回答";
    const note = document.createElement("p");
    note.textContent = "请求失败，请确认服务仍在运行。";
    answerEl.append(title, note);
  } finally {
    askButton.disabled = false;
    askButton.textContent = "检索并回答";
  }
}

async function refreshMeta() {
  const health = await fetch("/api/health").then((response) => response.json());
  const mode = health.llm_ready ? "在线模型" : "摘录模式（不调用大模型）";
  statusEl.textContent = `${mode} · ${health.documents} 篇资料`;
  const docs = await fetch("/api/documents").then((response) => response.json());
  docsEl.replaceChildren();
  docs.forEach((doc) => {
    const item = document.createElement("li");
    item.textContent = `${doc.title} · ${doc.source} · ${doc.filename} · ${doc.chunks} 个片段`;
    docsEl.append(item);
  });
}

async function init() {
  const examples = await fetch("/api/examples").then((response) => response.json());
  examples.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "example";
    const label = document.createElement("span");
    label.textContent = item.question;
    button.append(label);
    if (kindLabel[item.kind]) {
      const tag = document.createElement("small");
      tag.textContent = kindLabel[item.kind];
      button.append(tag);
    }
    button.addEventListener("click", () => ask(item.question));
    examplesEl.append(button);
  });
  await refreshMeta();
}

askButton.addEventListener("click", () => {
  const question = questionEl.value.trim();
  if (question) ask(question);
});

questionEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    askButton.click();
  }
});

document.querySelector("#file").addEventListener("change", async (event) => {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  const data = new FormData();
  data.append("file", file);
  formNote.textContent = "正在导入…";
  const response = await fetch("/api/ingest", { method: "POST", body: data });
  const payload = await response.json();
  if (!response.ok) {
    formNote.textContent = typeof payload.detail === "string" ? payload.detail : "导入失败";
    return;
  }
  formNote.textContent = payload.skipped
    ? `${payload.filename} 内容未变化，已跳过`
    : `已导入 ${payload.title}（${payload.filename}），${payload.chunks} 个片段`;
  event.target.value = "";
  refreshMeta();
});

init();
