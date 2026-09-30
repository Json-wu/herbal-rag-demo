"""演示题的应召回原文。只给标好的问题计算召回率。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldPassage:
    filename: str
    label: str


# 键必须与示例问题原文一致。空列表表示这题没有应召回的资料。
GOLD: dict[str, tuple[GoldPassage, ...]] = {
    "黄芪的性味与归经是什么？": (GoldPassage("黄芪.md", "黄芪 · 性味归经"),),
    "资料中如何描述甘草？": (GoldPassage("甘草.md", "甘草"),),
    "什么是四气五味？": (GoldPassage("四气五味.md", "四气五味"),),
    "金银花和连翘在资料中有什么不同？": (
        GoldPassage("金银花.md", "金银花"),
        GoldPassage("连翘.md", "连翘"),
    ),
    "资料里对麻黄有哪些使用注意？": (GoldPassage("麻黄.md", "麻黄 · 使用注意"),),
    "神农本草经怎样记载甘草？": (GoldPassage("神农本草经-甘草.md", "神农本草经 · 甘草"),),
    "黄耆在本草纲目中的气味是什么？": (GoldPassage("本草纲目-黄耆.md", "本草纲目 · 黄耆"),),
    "忍冬和金银花是什么？": (GoldPassage("本草纲目-忍冬.md", "本草纲目 · 忍冬"),),
    "阿司匹林适用于哪些疾病？": (),
    "我发烧咳嗽，麻黄每天该吃多少克？": (GoldPassage("麻黄.md", "麻黄 · 使用注意"),),
}
