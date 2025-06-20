from random import random

from muicebot.llm import ModelCompletions
from muicebot.models import Message, Resource
from muicebot.plugin import PluginMetadata
from muicebot.plugin.hook import on_after_completion
from nonebot import logger, on_message
from nonebot.adapters import Event
from nonebot_plugin_alconna import (
    uniseg,
)
from nonebot_plugin_alconna.uniseg import UniMsg
from nonebot_plugin_orm import async_scoped_session

from .config import Config, config
from .manager import MemeManager
from .utils import extract_multi_resource

__plugin_meta__ = PluginMetadata(
    name="Muicebot 表情包处理插件",
    description="自动偷图、发送表情包的小玩意",
    usage="配置好后就行",
    config=Config,
)

meme_manager = MemeManager()


async def is_image_event(event: Event) -> bool:
    message = event.get_message()
    logger.debug(message.get_segment_class())
    return message.count("image") != 0 and not message.extract_plain_text()


image_event = on_message(rule=is_image_event)


@image_event.handle()
async def auto_save_image(
    bot_message: UniMsg,
    event: Event,
    db_session: async_scoped_session,
):
    if random() > config.meme_save_probability:
        return

    images: list[Resource] = []
    message_images = bot_message.get(uniseg.Image)
    images.extend(await extract_multi_resource(message_images, "image", event))

    if not images:
        return

    logger.debug("正在偷图...")

    await meme_manager.add_new_meme(db_session, images[0])

    logger.success("偷图成功✨")

    await db_session.commit()


@on_after_completion()
async def send_meme(message: Message, completions: ModelCompletions):
    if random() > config.meme_probability:
        return

    if meme_manager.all_valid_memes_count < config.min_memes:
        logger.warning("未达到最低表情包要求，已跳过")
        return

    target_meme = await meme_manager.query_meme(message)

    if target_meme is None:
        logger.info("未找到合适的 Meme，已跳过")
        return

    logger.success(
        f"找到了合适的 Meme! 描述: {target_meme.description} 标签: {target_meme.tags}"
    )
    completions.resources.append(
        Resource(type="image", path=target_meme.path.as_posix())
    )

    return
