import random
from time import time_ns

from muicebot.models import Message
from nonebot import logger

from ..models import Meme


def _levenshtein_distance(s1: str, s2: str) -> int:
    """
    计算两个字符串的编辑距离
    """
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _extract_keywords(text: str) -> list[str]:
    """
    从文本中提取关键词，假设关键词被括号包围
    """
    import re

    # 使用正则表达式提取括号中的内容
    keywords = re.findall(r"\((.*?)\)", text)
    return [keyword.strip() for keyword in keywords if keyword.strip()]


def query_meme(message: Message, memes: list[Meme]) -> int:
    """
    通过编辑距离来查询 Meme, 这种方式需要假定消息体回复中带有括号包括住的情绪关键词
    由于此方式可能造成重复率过高，因此采取抽签
    """
    keywords = _extract_keywords(message.respond)
    if not keywords:
        return -1

    logger.debug(f"提取到的关键词: {keywords}")
    meme_scores: list[tuple[Meme, int]] = []

    t1 = time_ns()
    for meme in memes:
        for tag in meme.tag:
            for keyword in keywords:
                distance = _levenshtein_distance(tag, keyword)
                meme_scores.append((meme, distance))
    t2 = time_ns()
    logger.debug(f"编辑距离查询耗时: {(t2 - t1) / 1_000_000} ms")

    # 按照编辑距离排序
    meme_scores.sort(key=lambda x: x[1])

    # 随机从编辑距离最小的 Meme 中抽取一个
    min_distance = meme_scores[0][1]
    candidates = [meme for meme, distance in meme_scores if distance == min_distance]
    selected_meme = random.choice(candidates) if candidates else None

    return selected_meme.id if selected_meme else -1
