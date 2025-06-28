import re
from typing import Literal

from muicebot.models import Resource
from muicebot.utils.utils import download_file, get_file_via_adapter
from nonebot import logger
from nonebot.adapters import Event
from nonebot_plugin_alconna import UniMessage, uniseg


async def extract_multi_resource(
    message: UniMessage, type: Literal["audio", "image", "video", "file"], event: Event
) -> list[Resource]:
    """
    提取单个多模态文件
    """
    resources = []

    for resource in message:
        assert isinstance(
            resource, uniseg.segment.Media
        )  # 正常情况下应该都是 Media 的子类

        try:
            if resource.path is not None:
                path = str(resource.path)
            elif resource.url is not None:
                path = await download_file(
                    resource.url, file_name=resource.name, cache=True
                )
            elif resource.origin is not None:
                logger.warning("无法通过通用方式获取文件URL，回退至适配器自有方式...")
                path = await get_file_via_adapter(resource.origin, event)  # type:ignore
            else:
                continue

            if path:
                resources.append(Resource(type, path=path))
        except Exception as e:
            logger.error(f"处理文件失败: {e}")

    return resources


def process_message(message: str) -> str:
    """
    提取思考结果
    """
    if not message.startswith("<think>"):
        return message

    thoughts_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
    result = thoughts_pattern.sub("", message).strip()

    return result
