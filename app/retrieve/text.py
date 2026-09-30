"""中文提问的关键词与二字索引串。"""

import re

_STOP_PHRASES = tuple(
    sorted(
        (
            "有什么不同",
            "每天该吃",
            "有哪些",
            "哪些",
            "什么是",
            "是什么",
            "有什么",
            "如何",
            "怎么",
            "怎样",
            "是否",
            "适用于",
            "多少克",
            "适用",
            "资料中",
            "资料里",
            "资料",
            "描述",
            "介绍",
            "说明",
            "记载",
            "疾病",
            "不同",
            "区别",
            "请问",
            "一下",
            "关于",
            "什么",
            "每天",
        ),
        key=len,
        reverse=True,
    )
)
_PARTICLES = set("的了在和与及或对是吗呢啊吧把被而就都很也我")
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]{2,}")


def extract_entities(question: str) -> list[str]:
    text = question.strip()
    for phrase in _STOP_PHRASES:
        text = text.replace(phrase, " ")
    text = "".join(" " if char in _PARTICLES else char for char in text)
    entities: list[str] = []
    seen: set[str] = set()
    for run in _CJK_RUN.findall(text):
        if len(run) > 2 and run.endswith("中"):
            run = run[:-1]
        if run not in seen:
            seen.add(run)
            entities.append(run)
    return entities


def bigrams(text: str) -> list[str]:
    grams: list[str] = []
    for run in _CJK_RUN.findall(text):
        if len(run) == 2:
            grams.append(run)
        else:
            grams.extend(run[index : index + 2] for index in range(len(run) - 1))
    return grams


def index_tokens(*parts: str) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        for gram in bigrams(part):
            if gram not in seen:
                seen.add(gram)
                ordered.append(gram)
    return " ".join(ordered)


def fts_query(entities: list[str]) -> str:
    seen: set[str] = set()
    grams: list[str] = []
    for entity in entities:
        for gram in bigrams(entity):
            if gram not in seen:
                seen.add(gram)
                grams.append(gram)
    return " OR ".join(f'"{gram}"' for gram in grams)
