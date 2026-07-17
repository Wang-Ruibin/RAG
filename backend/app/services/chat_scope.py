from __future__ import annotations

import hashlib
import re

OUT_OF_SCOPE_REFUSALS = (
    "抱歉，我主要回答与河海大学有关的问题，这个问题超出了我的服务范围。你可以换一个河海大学相关的问题，我很乐意继续帮你。",
    "不好意思，我是河海大学校园知识助手，暂时无法回答这个校外话题。欢迎问我有关学校、院系、招生或校园生活的问题。",
    "这个问题似乎与河海大学无关，抱歉我暂时不能为你解答。如果你想了解河海大学，我会尽力提供有依据的信息。",
    "感谢你的提问，不过我的知识范围主要围绕河海大学，暂时无法回答这一问题。你可以试试询问校史、专业、招生或校园服务。",
)
NO_EVIDENCE_REFUSALS = (
    "抱歉，我暂时没有找到足以回答这个河海大学相关问题的可靠资料。你可以补充更具体的信息，我再帮你查找。",
    "目前校园知识库和可用的联网来源都没有提供足够依据，我暂时无法准确回答。建议补充时间、学院或事项名称后再试。",
    "很抱歉，我还没有检索到能够可靠回答这一问题的资料。为了避免给出不准确的信息，请换一种更具体的问法。",
)
SOCIAL_GREETINGS = (
    "你好！我是河海智答，主要帮助你了解河海大学。有什么校史、院系、招生或校园生活方面的问题，都可以问我。",
    "很高兴见到你，我是河海大学校园知识助手“河海智答”。请告诉我你想了解什么。",
    "你好呀！我是河海智答，可以帮你查询河海大学相关信息。今天想从哪里开始了解呢？",
)
HOHAI_MARKERS = (
    "河海大学",
    "河海",
    "hohai university",
    "hhu",
    "西康路校区",
    "江宁校区",
    "常州校区",
    "河海里尔",
)
CAMPUS_INTENT_MARKERS = (
    "学校",
    "校园",
    "校训",
    "校史",
    "建校",
    "校庆",
    "学院",
    "院系",
    "专业",
    "招生",
    "录取",
    "报考",
    "分数线",
    "学费",
    "宿舍",
    "食堂",
    "图书馆",
    "校历",
    "开学",
    "放假",
    "课程",
    "选课",
    "考试",
    "成绩",
    "奖学金",
    "助学金",
    "毕业",
    "就业",
    "招聘",
    "教师",
    "教授",
    "导师",
    "研究生",
    "本科",
    "博士",
    "硕士",
    "学生",
    "校区",
    "校园卡",
    "教务",
    "科研",
    "实验室",
    "社团",
    "讲座",
    "通知",
    "官网",
    "地址",
    "交通",
    "办事",
    "档案",
    "排名",
)
OTHER_UNIVERSITY_PATTERN = re.compile(
    r"[\u4e00-\u9fff]{2,10}大学|[a-z]{2,30}\s+university", re.IGNORECASE
)


def _pick_variant(seed: str, variants: tuple[str, ...]) -> str:
    digest = hashlib.sha256(seed.strip().lower().encode("utf-8")).digest()
    return variants[digest[0] % len(variants)]


def social_response(question: str) -> str | None:
    normalized = re.sub(r"[\s，。！？!?、,.]+", "", question).lower()
    if normalized in {"你好", "您好", "嗨", "哈喽", "hello", "hi", "你是谁", "你能做什么"}:
        return _pick_variant(question, SOCIAL_GREETINGS)
    if normalized in {"谢谢", "谢谢你", "感谢", "多谢"}:
        return "不客气！如果还有关于河海大学的问题，随时告诉我。"
    if normalized in {"再见", "拜拜", "bye", "goodbye"}:
        return "再见！欢迎下次继续来了解河海大学。"
    return None


def is_hohai_related(question: str) -> bool:
    normalized = re.sub(
        r"^(请问|想问一下|我想知道|麻烦问下|麻烦问一下)", "", question.strip().lower()
    )
    if any(marker in normalized for marker in HOHAI_MARKERS):
        return True
    if OTHER_UNIVERSITY_PATTERN.search(normalized):
        return False
    return any(marker in normalized for marker in CAMPUS_INTENT_MARKERS)


def refusal_for(question: str, *, out_of_scope: bool) -> str:
    variants = OUT_OF_SCOPE_REFUSALS if out_of_scope else NO_EVIDENCE_REFUSALS
    return _pick_variant(question, variants)
