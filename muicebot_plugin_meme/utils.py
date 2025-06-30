import math
import re
from io import BytesIO
from pathlib import Path
from typing import Literal, Union

from muicebot.models import Resource
from muicebot.utils.utils import download_file, get_file_via_adapter
from nonebot import logger
from nonebot.adapters import Event
from nonebot_plugin_alconna import UniMessage, uniseg
from PIL import Image, ImageSequence


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


def extract_and_combine_gif_frames(
    gif_path: Union[Path, bytes, BytesIO], step=2
) -> BytesIO:
    """
    提取 GIF 每一帧，并按指定间隔组合成一张图。

    :param gif_path: 输入 GIF 文件路径或字节流
    :param step: 提取帧的间隔
    """
    # 打开 GIF 动图
    if isinstance(gif_path, bytes):
        gif_path = BytesIO(gif_path)
    gif = Image.open(gif_path)

    # 提取间隔帧
    frames = [
        frame.copy().convert("RGBA")
        for i, frame in enumerate(ImageSequence.Iterator(gif))
        if i % step == 0
    ]

    if not frames:
        raise ValueError("没有提取到任何帧，请检查 step 参数是否过大。")

    # 获取帧尺寸
    frame_count = len(frames)
    width, height = frames[0].size

    cols = math.ceil(math.sqrt(frame_count))
    rows = math.ceil(frame_count / cols)

    # 按水平分布帧数
    out_width = cols * width
    out_height = rows * height

    combined_image = Image.new("RGBA", (out_width, out_height))

    for idx, frame in enumerate(frames):
        row = idx // cols
        col = idx % cols
        x = col * width
        y = row * height
        combined_image.paste(frame, (x, y))

    # 保存合成图像
    image_bytes = BytesIO()
    combined_image.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return image_bytes
