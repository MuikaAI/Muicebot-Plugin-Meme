import json
from hashlib import md5, sha256
from pathlib import Path
from time import perf_counter
from typing import Optional

import numpy as np
import openai
from async_lru import alru_cache
from muicebot.models import Message
from nonebot import logger
from nonebot_plugin_localstore import get_plugin_data_dir
from numpy import ndarray

from ..config import config
from ..models import Meme

client = openai.AsyncOpenAI(
    base_url=config.meme_embedding_base_url,
    api_key=config.meme_embedding_service_api_key,
)

# 初始化嵌入缓存目录
if config.meme_embedding_cache_enabled:
    cache_dir = get_plugin_data_dir() / "embedding"
    cache_dir.mkdir(parents=True, exist_ok=True)
else:
    cache_dir = None


def _get_embedding_cache_path(text: str) -> Optional[Path]:
    """
    获取嵌入缓存文件路径

    :param text: 查询文本
    """
    if not cache_dir:
        return None

    # 根据文本和模型名称生成缓存键
    content = f"{config.meme_embedding_model}:{text}"
    cache_key = md5(content.encode("utf-8")).hexdigest()

    return cache_dir / cache_key


def _load_embedding_from_cache(text: str) -> Optional[ndarray]:
    """
    从缓存文件中加载嵌入向量

    :param text: 查询文本
    """
    if not config.meme_embedding_cache_enabled:
        return None

    try:
        cache_path = _get_embedding_cache_path(text)
        if not cache_path:
            return None

        meta_path = cache_path.with_suffix(".json")
        npy_path = cache_path.with_suffix(".npy")

        if not (meta_path.exists() and npy_path.exists()):
            return None

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        if (
            isinstance(meta, dict)
            and "model" in meta
            and meta["model"] == config.meme_embedding_model
            and "text_hash" in meta
            and meta["text_hash"] == sha256(text.encode("utf-8")).hexdigest()
        ):
            embedding = np.load(npy_path)
            logger.debug(f"从缓存加载嵌入向量: {text[:50]}...")
            return embedding
        return None

    except Exception as e:
        logger.warning(f"加载缓存失败: {e}")
        return None


def _save_to_cache(text: str, embedding: ndarray) -> None:
    """
    将嵌入向量保存到缓存文件
    """
    import json

    if not config.meme_embedding_cache_enabled or not cache_dir:
        return

    try:
        cache_path = _get_embedding_cache_path(text)
        if not cache_path:
            return

        meta_path = cache_path.with_suffix(".json")
        npy_path = cache_path.with_suffix(".npy")

        meta_data = {
            "model": config.meme_embedding_model,
            "text_hash": sha256(text.encode("utf-8")).hexdigest(),
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f)
        np.save(npy_path, embedding)

        logger.debug(f"嵌入向量已缓存: {text[:50]}...")
    except Exception as e:
        logger.warning(f"保存缓存失败: {e}")


@alru_cache(maxsize=1024)
async def _get_embedding(text: str) -> ndarray:
    """
    调用 OpenAI API 兼容端口获取字符串的嵌入向量，支持离线缓存

    :param text: 要查询的字符串
    """
    logger.debug(f"正在查询文本嵌入向量: {text[:50]}...")

    # 首先尝试从磁盘缓存加载
    cached_embedding = _load_embedding_from_cache(text)
    if cached_embedding is not None:
        return cached_embedding

    # 缓存未命中，调用 API
    start_time = perf_counter()
    try:
        response = await client.embeddings.create(
            model=config.meme_embedding_model, input=[text]
        )
        embedding = np.array(response.data[0].embedding)

        # 保存到磁盘缓存
        _save_to_cache(text, embedding)

        end_time = perf_counter()
        logger.debug(f"已完成查询，用时: {end_time - start_time}s")
        return embedding

    except Exception as e:
        logger.error(f"获取嵌入向量失败: {e}")
        raise


def _cosine_similarity(vec1: ndarray, vec2: ndarray) -> float:
    """
    计算两个变量间的余弦相似度
    """
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


async def cosine_query(message: Message, memes: list[Meme]) -> int:
    """
    使用余弦相似度查询 Meme
    """
    memes = memes[: config.meme_general_max_query]
    vec1 = await _get_embedding(message.respond)
    most_similar_meme_index = 0
    most_similar_meme_cosine = 0.0

    start_time = perf_counter()
    for index, meme in enumerate(memes):
        vec2 = await _get_embedding(meme.description)
        cos_sim = _cosine_similarity(vec1, vec2)
        if cos_sim > most_similar_meme_cosine:
            most_similar_meme_index = index
            most_similar_meme_cosine = cos_sim
    end_time = perf_counter()

    logger.info(f"余弦相似度查询耗时: {end_time - start_time}s")

    return most_similar_meme_index
