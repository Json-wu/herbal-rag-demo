"""页面与 README 共用的演示问题。"""

from app.schemas import ExampleQuestion

EXAMPLES: list[ExampleQuestion] = [
    ExampleQuestion(id="huangqi", question="黄芪的性味与归经是什么？", kind="answer"),
    ExampleQuestion(id="gancao", question="资料中如何描述甘草？", kind="answer"),
    ExampleQuestion(id="siqi", question="什么是四气五味？", kind="answer"),
    ExampleQuestion(id="compare", question="金银花和连翘在资料中有什么不同？", kind="answer"),
    ExampleQuestion(id="mahuang", question="资料里对麻黄有哪些使用注意？", kind="answer"),
    ExampleQuestion(id="refuse", question="阿司匹林适用于哪些疾病？", kind="refuse"),
    ExampleQuestion(
        id="safety",
        question="我发烧咳嗽，麻黄每天该吃多少克？",
        kind="safety",
    ),
]
