from typing import Literal

from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    meme_probability: float = 0.1
    """回复表情包概率"""
    meme_save_probability: float = 0.2
    """保存表情包概率"""
    meme_similarity_method: Literal["cosine", "levenshtein", "llm"] = "levenshtein"
    """相似度计算方式"""
    max_memes: int = 500
    """最大表情包数量"""
    meme_llm_max_query: int = 50
    """当启用 LLM 查询时，最大的查询数量"""
    meme_general_max_query: int = max_memes
    """全局最大查询数量"""
    enable_security_check: bool = True
    """启用基于 LLM 的安全检查"""


config = get_plugin_config(Config)
