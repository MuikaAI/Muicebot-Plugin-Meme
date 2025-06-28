from random import random
from typing import Optional

from muicebot.llm import ModelCompletions
from muicebot.models import Message, Resource
from muicebot.plugin import PluginMetadata
from muicebot.plugin.hook import on_after_completion
from nonebot import get_driver, logger, on_message
from nonebot.adapters import Event
from nonebot_plugin_alconna import (
    Alconna,
    CommandMeta,
    Image,
    Subcommand,
    UniMessage,
    on_alconna,
    uniseg,
)
from nonebot_plugin_alconna.uniseg import UniMsg
from nonebot_plugin_orm import async_scoped_session

from .config import Config, config
from .manager import MemeManager
from .utils import extract_multi_resource

COMMAND_PREFIXES = [".", "/"]

__plugin_meta__ = PluginMetadata(
    name="Muicebot 表情包处理插件",
    description="自动偷图、发送表情包的小玩意",
    usage="配置好后就行",
    config=Config,
)

driver = get_driver()
meme_manager: Optional[MemeManager] = None


@driver.on_startup
async def _():
    global meme_manager
    meme_manager = MemeManager()
    await meme_manager._load_memes()


async def is_image_event(bot_message: UniMsg) -> bool:
    return bot_message.count(Image) != 0 and not bot_message.extract_plain_text()


image_event = on_message(rule=is_image_event)

meme_cmd = on_alconna(
    Alconna(
        COMMAND_PREFIXES,
        "meme",
        Subcommand("analysis"),
        meta=CommandMeta("Muicebot Meme插件指令"),
    ),
    priority=10,
    block=True,
    skip_for_unmatch=False,
)


@meme_cmd.assign("analysis")
async def analysis():
    assert meme_manager
    await UniMessage(
        f"一共偷了{meme_manager.all_valid_memes_count}个有效表情包✨"
    ).finish()


@image_event.handle()
async def auto_save_image(
    bot_message: UniMsg,
    event: Event,
    db_session: async_scoped_session,
):
    assert meme_manager

    if random() > config.meme_save_probability:
        return

    images: list[Resource] = []
    message_images = bot_message.get(uniseg.Image)
    images.extend(await extract_multi_resource(message_images, "image", event))

    if not images:
        return

    logger.debug("正在偷图...")

    result = await meme_manager.add_new_meme(db_session, images[0])

    if result:
        logger.success("偷图成功✨")
        await db_session.commit()


@on_after_completion()
async def send_meme(message: Message, completions: ModelCompletions):
    assert meme_manager

    if random() > config.meme_probability:
        return

    if meme_manager.all_valid_memes_count < config.min_memes:
        logger.warning("未达到最低表情包要求，已跳过")
        return

    target_meme = await meme_manager.query_meme(message)

    if target_meme is None:
        return

    completions.resources.append(
        Resource(type="image", path=target_meme.path.as_posix())
    )

    return
