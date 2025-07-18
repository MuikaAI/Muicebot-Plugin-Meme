from typing import Literal, Optional

from nonebot import get_plugin_config
from pydantic import BaseModel, field_validator


class Config(BaseModel):
    meme_probability: float = 0.1
    """回复表情包概率"""
    meme_save_probability: float = 0.2
    """保存表情包概率"""
    meme_similarity_method: Literal["cosine", "levenshtein", "llm"] = "levenshtein"
    """相似度计算方式"""
    max_memes: int = 500
    """最大表情包数量"""
    max_meme_size: int = 1024 * 1024
    """最大表情包大小(bytes)"""
    min_memes: int = 10
    """最小表情包数量，保存的表情包达到这个数值才发送"""
    meme_llm_max_query: int = 50
    """当启用 LLM 查询时，最大的查询数量"""
    meme_general_max_query: int = max_memes
    """全局最大查询数量"""
    meme_security_check: bool = True
    """启用基于 LLM 的安全检查"""
    meme_multimodal_config: Optional[str] = None
    """生成图片描述时，使用的多模态模型配置名"""

    meme_embedding_model: str = "text-embedding-v4"
    """嵌入模型名称"""
    meme_embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    """OpenAI 兼容端口的嵌入模型 base_url"""
    meme_embedding_service_api_key: Optional[str] = None
    """访问嵌入模型所需的 API Key"""
    meme_embedding_cache_enabled: bool = True
    """启用嵌入缓存"""

    @field_validator("meme_embedding_service_api_key")
    @classmethod
    def check_api_key(cls, v: Optional[str]) -> Optional[str]:
        if cls.meme_similarity_method != "cosine" or v:
            return v

        raise ValueError(
            "启用 cosine 相似度计算时，需要配置 `meme_embedding_service_api_key` !"
        )


config = get_plugin_config(Config)
