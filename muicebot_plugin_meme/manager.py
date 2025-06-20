import json
import re
import time
from hashlib import md5
from os import remove
from pathlib import Path
from typing import Any, Literal, Optional, Union

import httpx
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound
from muicebot.llm import ModelCompletions, ModelRequest
from muicebot.models import Message, Resource
from muicebot.muice import Muice
from nonebot import logger
from nonebot_plugin_localstore import get_plugin_data_dir
from nonebot_plugin_orm import async_scoped_session, get_session
from sqlalchemy.ext.asyncio import AsyncSession

from .config import config
from .database.crud import MemeRepository
from .models import Meme

SEARCH_PATH = [Path(__file__).parent / "templates"]
MEMES_SAVE_PATH = get_plugin_data_dir() / "memes"
UNION_SESSION = Union[async_scoped_session, AsyncSession]


class MemeManager:
    def __init__(self) -> None:
        self._all_valid_memes: list[Meme] = []
        self._all_valid_memes_count: int = 0
        self._jinja2_env = Environment(loader=FileSystemLoader(SEARCH_PATH))

    @property
    def all_valid_memes_count(self) -> int:
        return self._all_valid_memes_count

    @property
    def all_valid_memes(self) -> list[Meme]:
        return self._all_valid_memes

    def _sort_memes(self):
        """
        对 memes 进行排序
        """
        self._all_valid_memes.sort(key=lambda x: x.usage)

    def _path_to_md5(self, image_path: Path | str) -> str:
        """
        将图片转换为 md5
        """
        with open(image_path, "rb") as f:
            image_data = f.read()
        if not image_data:
            raise IOError(f"读取图片文件失败: {image_path}")
        return md5(image_data).hexdigest()

    async def _save_meme(self, resource: Resource) -> Optional[Path]:
        """
        保存 Meme 到本地
        """
        logger.debug("正在保存 Meme...")
        meme_url = resource.url or resource.path
        meme_extension = (
            meme_url.split(".")[-1] if "." in meme_url.split("/")[-1] else "png"
        )
        meme_name = f"{int(time.time())}.{meme_extension}"
        meme_path = MEMES_SAVE_PATH / meme_name
        if not meme_path.parent.exists():
            meme_path.parent.mkdir(parents=True, exist_ok=True)

        if meme_url.startswith("http"):
            async with httpx.AsyncClient() as client:
                response = await client.get(meme_url)
                if response.status_code == 200:
                    with open(meme_path, "wb") as f:
                        f.write(response.content)
                else:
                    logger.error(f"下载 Meme 失败: {response.status_code}")
                    return None
        else:
            # 如果是本地路径，直接复制
            meme_path.write_bytes(Path(resource.path).read_bytes())

        return meme_path if meme_path.is_file() else None

    def _generate_prompt_from_template(self, template_name: str) -> str:
        """
        获取提示词
        （使用Jinja2模板引擎的目的是为了后续可能的扩展）
        """
        env = Environment(loader=FileSystemLoader(SEARCH_PATH))

        if not template_name.endswith((".j2", ".jinja2")):
            template_name += ".jinja2"
        try:
            template = env.get_template(template_name)
        except TemplateNotFound:
            logger.error(f"模板文件 {template_name} 未找到!")
            raise

        prompt = template.render()

        return prompt

    async def _chat_with_model(
        self,
        prompt: str,
        system: str,
        image: Resource,
        format: Literal["json", "str", "int"] = "str",
    ) -> Any:
        """
        与 llm 交互
        """
        model = Muice.get_instance().model
        if not (model and model.is_running):
            raise RuntimeError("LLM 尚未运行！")
        elif not model.config.multimodal:
            raise RuntimeError("LLM 不是多模态的！")

        model_request = ModelRequest(prompt, system=system, resources=[image])

        response = await model.ask(model_request, stream=model.config.stream)

        if isinstance(response, ModelCompletions):
            response_text = response.text
        else:
            response_chunks: list[str] = []
            async for chunk in response:
                response_chunks.append(chunk.chunk)
            response_text = "".join(response_chunks)

        if format == "int":
            try:
                response_int = int(response_text)
            except ValueError:
                logger.warning(
                    f"尝试提取模型回复时出现错误，尝试提取数字: {response_text}"
                )
                match = re.search(r"\d+", response_text)
                if match:
                    response_int = int(match.group())
                else:
                    response_int = 0
                logger.warning(f"提取结果: {response_int}")

            return response_int
        elif format == "json":
            try:
                # 防止出现代码块
                escaped_str = re.findall(
                    r"```(?:\w+)?\n(.*?)```", response_text, re.DOTALL
                )[0]
                json_text = escaped_str.replace(r"\n", "\n").replace(r"\t", "\t")
                return json.loads(json_text)
            except json.JSONDecodeError:
                logger.error(
                    f"尝试提取模型回复时出现错误，无法将其转换为JSON格式: {response_text}"
                )
                raise
        else:
            return response_text

    async def _check_memes_valid(
        self, session: UNION_SESSION, memes: list[Meme]
    ) -> list[Meme]:
        """
        [预检] 检查所有 Memes 有效性
        """
        logger.debug("检查 Memes 完整性")
        valid_memes: list[Meme] = memes.copy()
        invalid_memes: list[Meme] = []

        for index, meme in enumerate(memes):
            if not (meme.valid and meme.path.is_file()):
                invalid_memes.append(meme)
                del valid_memes[index - len(invalid_memes) + 1]

        for invalid_meme in invalid_memes:
            await self._delete_meme(session, invalid_meme, init=True)

        if invalid_memes:
            await session.commit()
            logger.info(f"已从数据库中清除了 {len(invalid_memes)} 个无效 Memes")
        else:
            logger.info("所有 Memes 检查通过，没有无效 Memes")

        return valid_memes

    async def _load_memes(self):
        """
        [初始化] 从数据库中获取所有 Meme
        """
        session = get_session()
        async with session.begin():
            memes = await MemeRepository.get_all_memes(session)
            memes = await self._check_memes_valid(session, memes)

        self._all_valid_memes = memes
        self._all_valid_memes_count = len(memes)

        logger.info(f"一共加载了 {self._all_valid_memes_count} 个有效 Memes")

    async def _delete_meme(self, session: UNION_SESSION, meme: Meme, init=False):
        """
        删除指定 Meme

        :param session: 数据库会话
        :param meme: Meme 对象
        :param init: 当前是否是在初始化过程中，即 _all_valid_memes 还未加载
        """
        if meme.path.is_file():
            remove(meme.path)

        await MemeRepository.remove_meme(session, meme.id)  # type:ignore

        if not init:
            self._all_valid_memes.remove(meme)
            self._all_valid_memes_count -= 1

    async def auto_clean_memes(self, session: async_scoped_session):
        """
        自动删除不使用的 memes
        """
        if self._all_valid_memes_count <= config.max_memes:
            return

        logger.debug("Meme 数量已达上限，正在执行自动清理...")

        self._sort_memes()
        memes_to_delete = self._all_valid_memes[config.max_memes :]
        for meme in memes_to_delete:
            await self._delete_meme(session, meme)

        logger.info(
            f"已删除 {len(memes_to_delete)} 个 Memes，当前有效 Memes 数量为 {self._all_valid_memes_count}"
        )
        await session.commit()
        logger.debug("自动清理 Memes 完成")

    async def add_new_meme(self, session: async_scoped_session, meme_image: Resource):
        """
        添加 Meme
        """
        if meme_image.type != "image":
            raise ValueError("此类型不是 image 类型！")

        new_meme_hash = self._path_to_md5(meme_image.path)

        if any(new_meme_hash == meme.hash for meme in self._all_valid_memes):
            logger.debug("检查到此 meme 已存在，停止添加")
            return

        if config.enable_security_check:
            logger.debug("正在进行安全检查...")
            check_result: int = await self._chat_with_model(
                "回复纯数字0或1",
                system=self._generate_prompt_from_template(
                    "meme_security_check.jinja2"
                ),
                image=meme_image,
                format="int",
            )
            if not check_result:
                logger.warning("此表情包未通过安全检查！已停止添加")

        logger.debug("调用LLM生成表情包描述...")
        meme_desc: dict[str, Any] = await self._chat_with_model(
            "以JSON格式生成标签和内容",
            system=self._generate_prompt_from_template("meme_description.jinja2"),
            image=meme_image,
            format="json",
        )

        meme_local_path = await self._save_meme(meme_image)
        if not meme_local_path:
            return

        new_meme = Meme(
            path=meme_local_path,
            hash=new_meme_hash,
            description=meme_desc.get("desc", ""),
            tags=meme_desc.get("tags", []),
        )

        await self.auto_clean_memes(session)
        await MemeRepository.save_meme(session, new_meme)
        self._all_valid_memes.append(new_meme)
        self._all_valid_memes_count += 1

        logger.success(
            f"已成功添加新的表情包！描述:{new_meme.description}, 标签: {new_meme.tags}"
        )

    async def query_meme(self, message: Message) -> Optional[Meme]:
        """
        查询对话中适用的 meme
        """
        # if config.similarity_method == "cosine":
        #     pass
        if config.meme_similarity_method == "levenshtein":
            from .similarity.levenshtein import query_meme

            meme_id = query_meme(message, self._all_valid_memes)
        elif config.meme_similarity_method == "llm":
            from .similarity.llm import llm_query

            meme_id = await llm_query(message, self._all_valid_memes)
        else:
            raise ValueError(
                f"未找到要求的相似度匹配算法: {config.meme_similarity_method}"
            )

        if meme_id == -1:
            logger.info("未找到合适的 Meme, 跳过")
            return None

        meme = next(
            (meme for meme in self._all_valid_memes if meme.id == meme_id), None
        )
        if not meme:
            logger.warning(f"未找到匹配的 Meme，ID: {meme_id}")
            return None

        logger.info(
            f"查询到 Meme: {meme.id}, 标签: {meme.tags}, 描述: {meme.description}"
        )
        return meme
