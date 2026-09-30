"""个人症状、诊断、处方、剂量与急症的本地规则。不记录问题原文。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyMatch:
    kind: str


_EMERGENCY = ("胸痛", "昏迷", "大出血", "呼吸困难", "喘不上气", "自杀", "心跳停止", "中毒", "抽搐", "晕倒")
_DOSAGE = ("多少克", "几克", "剂量", "用量", "每天吃", "吃多少", "怎么吃", "如何服用", "服用多少", "克数")
_PRESCRIPTION = ("开方", "处方", "该吃什么药", "吃什么药", "用什么药", "怎么配", "替我配", "给我开")
_DIAGNOSIS = ("是不是得了", "帮我诊断", "我得了什么", "给我诊断", "是什么病", "帮我看看")
_SYMPTOMS = ("发烧", "咳嗽", "腹泻", "失眠", "头晕", "不舒服", "疼", "痛")
_PRONOUNS = ("我", "家人", "孩子", "宝宝", "老人", "爸爸", "妈妈")
_SEEKING = ("该怎么办", "怎么办", "吃什么", "用什么", "怎么治", "如何治疗", "该吃", "能不能吃")


def classify(question: str) -> SafetyMatch | None:
    text = question.strip()
    if not text:
        return None
    if any(term in text for term in _EMERGENCY):
        return SafetyMatch("emergency")
    if any(term in text for term in _DOSAGE):
        return SafetyMatch("dosage")
    if any(term in text for term in _PRESCRIPTION):
        return SafetyMatch("prescription")
    if any(term in text for term in _DIAGNOSIS):
        return SafetyMatch("diagnosis")
    has_person = any(term in text for term in _PRONOUNS)
    has_symptom = any(term in text for term in _SYMPTOMS)
    has_seek = any(term in text for term in _SEEKING)
    if has_person and has_symptom and has_seek:
        return SafetyMatch("symptom")
    return None
