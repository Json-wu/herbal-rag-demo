"""把追问补上上一句里的指代，供检索和安全判断使用。"""

_POINTING = ("它", "他", "她", "这个", "那个", "这味", "上面", "刚才")


def normalize_history(history: list[tuple[str, str]] | None) -> list[tuple[str, str]]:
    cleaned: list[tuple[str, str]] = []
    for role, content in history or []:
        if role not in {"user", "assistant"}:
            continue
        text = (content or "").strip()
        if text:
            cleaned.append((role, text[:2000]))
    return cleaned[-6:]


def needs_context(question: str) -> bool:
    text = question.strip()
    if any(mark in text for mark in _POINTING):
        return True
    return len(text) <= 12


def retrieval_query(question: str, history: list[tuple[str, str]] | None) -> str:
    text = question.strip()
    prior = _last_user(history)
    if prior and needs_context(text):
        return f"{prior} {text}"
    return text


def safety_text(question: str, history: list[tuple[str, str]] | None) -> str:
    text = question.strip()
    prior = _last_user(history)
    if prior and needs_context(text):
        return f"{prior}\n{text}"
    return text


def _last_user(history: list[tuple[str, str]] | None) -> str:
    for role, content in reversed(history or []):
        if role == "user" and content.strip():
            return content.strip()
    return ""
