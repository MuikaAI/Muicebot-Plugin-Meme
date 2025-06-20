import re

from muicebot.llm import ModelCompletions, ModelRequest
from muicebot.models import Message
from muicebot.muice import Muice
from muicebot.templates import generate_prompt_from_template
from nonebot import logger

from ..config import config
from ..models import Meme

system_template = """你现在正在参与一段社交媒体对话，你的设定如下:
“{system_prompt}”
---
用户发来了以下信息:
{user_message}
---
你的回复是：
{ai_response}
---
请你根据以上信息，从给定的表情包矩阵中对你来说最贴合的表情包 id
注意：你只需要返回一段纯数字，而不需要有其他数字之外的内容。如果没有合适的表情包或者当前对话环境发送表情包不合适，请回复-1
"""


def _generate_prompt(memes: list[Meme]) -> str:
    """
    生成查询提示词
    """
    memes_info = [
        f"id: {meme.id}, tags: {meme.tags}, desc: {meme.description};" for meme in memes
    ]
    return "\n".join(memes_info)


async def llm_query(message: Message, memes: list[Meme]) -> int:
    """
    使用 LLM 进行表情包检索。
    这种查询是通过一轮对话来判断的，因此需要传入完整的消息体。

    :param message: 完整的消息体
    :param memes: 有序 Meme 列表
    """
    muice = Muice.get_instance()
    model = muice.model
    if not (model and model.is_running):
        return -1

    user_message = message.message
    ai_response = message.respond

    if muice.template:
        system_prompt = generate_prompt_from_template(
            muice.template, message.userid, message.groupid == -1
        )
    else:
        system_prompt = "无"

    system = system_template.format(
        system_prompt=system_prompt, user_message=user_message, ai_response=ai_response
    )
    prompt = _generate_prompt(
        memes[: min((config.meme_general_max_query, config.meme_llm_max_query))]
    )

    model_request = ModelRequest(prompt, system=system)
    response_usage = -1
    logger.debug(f"向 LLM 发送检索请求: {model_request}")

    response = await model.ask(model_request, stream=model.config.stream)

    if isinstance(response, ModelCompletions):
        response_text = response.text
        response_usage = response.usage
    else:
        response_chunks: list[str] = []
        async for chunk in response:
            response_chunks.append(chunk.chunk)
            response_usage = chunk.usage or response_usage
        response_text = "".join(response_chunks)
    logger.debug(f"LLM 请求已完成，用量: {response_usage}")

    try:
        target_meme_id = int(response_text)
    except ValueError:
        logger.warning(f"LLM 返回了预期之外的回复: {response_text}, 正在尝试提取数字")
        match = re.search(r"\d+", response_text)
        if match:
            target_meme_id = int(match.group())
        else:
            target_meme_id = -1

    return target_meme_id
