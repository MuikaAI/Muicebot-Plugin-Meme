import re
from random import random

from arclet.alconna import Alconna, Args
from muicebot.models import Resource
from muicebot.plugin import PluginMetadata
from nonebot import logger
from nonebot.adapters import Bot, Event
from nonebot_plugin_alconna import (
    Image,
    on_alconna,
    uniseg,
)
from nonebot_plugin_alconna.uniseg import UniMsg
from nonebot_plugin_orm import async_scoped_session

from .config import Config, config
from .utils import extract_multi_resource

__plugin_meta__ = PluginMetadata(
    name="Muicebot 表情包处理插件",
    description="自动偷图、发送表情包的小玩意",
    usage="配置好后就行",
    config=Config,
)

image_event = on_alconna(
    Alconna(re.compile(".+"), Args["img?", Image], separators=""),
    priority=1,
    block=False,
)


@image_event.handle()
async def auto_save_image(
    bot_message: UniMsg,
    event: Event,
    bot: Bot,
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
