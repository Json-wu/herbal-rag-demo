const questionEl = document.querySelector("#question");
const askButton = document.querySelector("#ask");
const examplesEl = document.querySelector("#examples");
const answerEl = document.querySelector("#answer");
const hitsEl = document.querySelector("#hits");
const statusEl = document.querySelector("#status");
const docsEl = document.querySelector("#docs");
const formNote = document.querySelector("#form-note");
const recallBoard = document.querySelector("#recall-board");
const sessionsEl = document.querySelector("#sessions");
const resetButton = document.querySelector("#reset");
const STORAGE_KEY = "herbal-rag-sessions";
const MAX_SESSIONS = 20;
const MAX_TURNS = 12;

let state = loadState();

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

function percent(value) {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

function renderRecall(report) {
  const box = document.createElement("div");
  box.className = "metrics";
  if (!report || !report.labeled) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = "这题没有标注应召回的原文，页面不估算召回率。";
    return note;
  }
  if (!report.applicable) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = "这题没有应召回的资料，召回率和 Recall@" + report.k + " 不适用。";
    return note;
  }
  box.append(
    metricCard("召回率", percent(report.recall), `${report.recalled}/${report.relevant} 段达到相关度门槛`),
    metricCard(
      `Recall@${report.k}`,
      percent(report.recall_at_k),
      `前 ${report.k} 条含 ${report.recalled_at_k}/${report.relevant} 段`,
    ),
  );
  const wrap = document.createElement("div");
  wrap.append(box);
  if (report.missed && report.missed.length) {
    const missed = document.createElement("p");
    missed.className = "note";
    missed.textContent = `前 ${report.k} 条未包含：${report.missed.join("、")}`;
    wrap.append(missed);
  }
  return wrap;
}

function metricCard(label, value, detail) {
  const card = document.createElement("div");
  card.className = "metric";
  const number = document.createElement("strong");
  number.textContent = value;
  const name = document.createElement("span");
  name.textContent = label;
  const note = document.createElement("small");
  note.textContent = detail;
  card.append(number, name, note);
  return card;
}

function blankSession() {
  const id = window.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
  return { id, title: "新对话", updatedAt: Date.now(), turns: [] };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const data = raw ? JSON.parse(raw) : null;
    if (data && Array.isArray(data.sessions) && data.sessions.length && data.currentId) {
      return data;
    }
  } catch (_error) {
    /* 损坏的本地记录直接另起一轮。 */
  }
  const session = blankSession();
  return { currentId: session.id, sessions: [session] };
}

function currentSession() {
  return state.sessions.find((item) => item.id === state.currentId) || state.sessions[0];
}

function persist() {
  state.sessions = state.sessions.slice(0, MAX_SESSIONS);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (_error) {
    /* 浏览器拒绝写入时，当前页里的会话仍然保留。 */
  }
  renderSessions();
}

function renderSessions() {
  sessionsEl.replaceChildren();
  state.sessions.forEach((session) => {
    const row = document.createElement("div");
    row.className = session.id === state.currentId ? "session active" : "session";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "session-title";
    open.textContent = session.title;
    open.addEventListener("click", () => selectSession(session.id));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "session-delete";
    remove.textContent = "删除";
    remove.addEventListener("click", () => deleteSession(session.id));
    row.append(open, remove);
    sessionsEl.append(row);
  });
}

function selectSession(id) {
  state.currentId = id;
  persist();
  questionEl.value = "";
  renderThread();
}

function deleteSession(id) {
  state.sessions = state.sessions.filter((item) => item.id !== id);
  if (!state.sessions.length) {
    const session = blankSession();
    state.sessions = [session];
    state.currentId = session.id;
  } else if (!state.sessions.some((item) => item.id === state.currentId)) {
    state.currentId = state.sessions[0].id;
  }
  persist();
  questionEl.value = "";
  renderThread();
}

function startSession() {
  const current = currentSession();
  if (!current.turns.length) {
    questionEl.value = "";
    renderThread();
    questionEl.focus();
    return;
  }
  const session = blankSession();
  state.sessions.unshift(session);
  state.currentId = session.id;
  persist();
  questionEl.value = "";
  renderThread();
  questionEl.focus();
}

function renderThread() {
  const session = currentSession();
  answerEl.className = "panel";
  answerEl.replaceChildren();
  const title = document.createElement("h2");
  title.textContent = "对话";
  answerEl.append(title);
  if (!session.turns.length) {
    const empty = document.createElement("p");
    empty.className = "placeholder";
    empty.textContent = "选择一个示例，或输入问题。可以接着上一句追问。回答只依据这一轮检索到的原文。";
    answerEl.append(empty);
    renderHits(null);
    return;
  }
  const thread = document.createElement("div");
  thread.className = "thread";
  session.turns.forEach((turn, index) => {
    thread.append(renderTurn(turn, index, index === session.turns.length - 1));
  });
  answerEl.append(thread);
  showTurn(session.turns.length - 1);
}

function renderTurn(turn, index, latest) {
  const block = document.createElement("article");
  block.className = latest ? "turn active" : "turn";
  if (turn.refusal_reason) block.classList.add(turn.refusal_reason);
  const question = document.createElement("p");
  question.className = "turn-q";
  const jump = document.createElement("button");
  jump.type = "button";
  jump.textContent = turn.question;
  jump.addEventListener("click", () => showTurn(index));
  question.append(jump);
  block.append(question, renderRecall(turn.recall));
  const body = document.createElement("div");
  body.className = "answer-text";
  fillAnswer(body, turn, index);
  block.append(body);
  if (turn.citations && turn.citations.length) {
    const list = document.createElement("ul");
    list.className = "cite-list";
    turn.citations.forEach((cite) => {
      const hit = turn.hits[cite.marker - 1];
      if (!hit) return;
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "text-button";
      button.textContent = `[${cite.marker}] ${hit.title} · ${hit.section} · ${hit.filename}`;
      button.addEventListener("click", () => {
        showTurn(index);
        focusHit(String(cite.marker));
      });
      item.append(button);
      list.append(item);
    });
    block.append(list);
  }
  return block;
}

function fillAnswer(body, turn, index) {
  turn.answer.split(/(\[\d+\])/g).forEach((part) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (!match) {
      appendText(body, part);
      return;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "cite";
    button.textContent = part;
    button.addEventListener("click", () => {
      showTurn(index);
      focusHit(match[1]);
    });
    body.append(button);
  });
}

function showTurn(index) {
  const session = currentSession();
  const turn = session.turns[index];
  document.querySelectorAll(".turn").forEach((item, itemIndex) => {
    item.classList.toggle("active", itemIndex === index);
  });
  renderHits(turn || null);
}

function renderHits(payload) {
  hitsEl.className = "panel";
  hitsEl.replaceChildren();
  const title = document.createElement("h2");
  title.textContent = "检索片段";
  hitsEl.append(title);
  if (!payload) {
    const empty = document.createElement("p");
    empty.className = "placeholder";
    empty.textContent = "相关原文、来源、章节、文件名和相关度会显示在这里。";
    hitsEl.append(empty);
    return;
  }
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

async function ask(question, options = {}) {
  const text = question.trim();
  if (!text) return;
  if (options.fresh) startSession();
  const session = currentSession();
  const history = session.turns.slice(-4).flatMap((turn) => [
    { role: "user", content: turn.question.slice(0, 2000) },
    { role: "assistant", content: turn.answer.slice(0, 2000) },
  ]);
  questionEl.value = text;
  askButton.disabled = true;
  askButton.textContent = "检索中…";
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text, history }),
    });
    if (!response.ok) throw new Error(String(response.status));
    const payload = await response.json();
    session.turns.push({
      question: text,
      answer: payload.answer,
      refusal_reason: payload.refusal_reason,
      hits: payload.hits,
      citations: payload.citations,
      recall: payload.recall,
    });
    session.turns = session.turns.slice(-MAX_TURNS);
    if (session.title === "新对话") session.title = text.slice(0, 18);
    session.updatedAt = Date.now();
    state.sessions.sort((left, right) => right.updatedAt - left.updatedAt);
    persist();
    formNote.textContent = "";
    questionEl.value = "";
    renderThread();
    if (window.matchMedia("(max-width: 860px)").matches) {
      answerEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (_error) {
    formNote.textContent = "请求失败，请确认服务仍在运行。";
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

async function loadRecall() {
  const response = await fetch("/api/recall");
  if (!response.ok) return;
  const board = await response.json();
  recallBoard.replaceChildren();
  const title = document.createElement("h2");
  title.textContent = "标注题指标";
  const line = document.createElement("p");
  line.textContent = `${board.questions} 道可计算的题，平均召回率 ${percent(board.recall)}，平均 Recall@${board.k} ${percent(board.recall_at_k)}。`;
  const list = document.createElement("ul");
  list.className = "recall-list";
  board.items.forEach((item) => {
    const row = document.createElement("li");
    if (!item.applicable) {
      row.textContent = `${item.question} · 不适用`;
    } else {
      row.textContent = `${item.question} · 召回率 ${percent(item.recall)} · Recall@${board.k} ${percent(item.recall_at_k)}`;
    }
    list.append(row);
  });
  recallBoard.append(title, line, list);
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
    button.addEventListener("click", () => ask(item.question, { fresh: true }));
    examplesEl.append(button);
  });
  renderSessions();
  renderThread();
  try {
    await refreshMeta();
  } catch (_error) {
    statusEl.textContent = "暂时读不到索引状态";
  }
  try {
    await loadRecall();
  } catch (_error) {
    /* 指标接口失败时仍保留会话。 */
  }
}

resetButton.addEventListener("click", startSession);

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
