import json
import re
from base64 import b64encode
from os import remove
from pathlib import Path
from typing import Any, Literal, Optional

from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound
from muicebot.llm import ModelCompletions, ModelRequest
from muicebot.models import Message, Resource
from muicebot.muice import Muice
from nonebot import logger
from nonebot_plugin_orm import async_scoped_session

from .config import config
from .database.crud import MemeRepository
from .models import Meme

SEARCH_PATH = [Path(__file__).parent / "templates"]


class MemeManager:
    def __init__(self) -> None:
        self.all_valid_meme: list[Meme] = []
        self.all_valid_meme_count: int = 0
        self._jinja2_env = Environment(loader=FileSystemLoader(SEARCH_PATH))

    def _sort_memes(self):
        """
        对 memes 进行排序
        """
        self.all_valid_meme.sort(key=lambda x: x.usage)

    def _path_to_base64(self, image_path: Path | str) -> str:
        """
        将图片转换为 base64
        """
        with open(image_path, "rb") as f:
            image_data = f.read()
        if not image_data:
            raise IOError(f"读取图片文件失败: {image_path}")
        return b64encode(image_data).decode("utf-8")

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
                return json.loads(response_text)
            except json.JSONDecodeError:
                logger.error(
                    f"尝试提取模型回复时出现错误，无法将其转换为JSON格式: {response_text}"
                )
                raise
        else:
            return response_text

    async def check_memes_valid(
        self, session: async_scoped_session, memes: list[Meme]
    ) -> list[Meme]:
        """
        [预检] 检查所有 Memes 有效性
        """
        logger.debug("检查 Memes 完整性")
        valid_memes: list[Meme] = memes.copy()
        invalid_memes: list[Meme] = []

        for index, meme in enumerate(memes):
            if meme.valid and meme.path.is_file():
                invalid_memes.append(meme)
            elif meme.valid:
                del valid_memes[index - len(invalid_memes) + 1]

        for invalid_meme in invalid_memes:
            await self.delete_meme(session, invalid_meme)

        if invalid_memes:
            await session.commit()
            logger.info(f"已从数据库中清除了 {len(invalid_memes)} 个无效 Memes")
        else:
            logger.info("所有 Memes 检查通过，没有无效 Memes")

        return valid_memes

    async def load_all_memes(self, session: async_scoped_session):
        """
        [初始化] 从数据库中获取所有 Meme
        """
        memes = await MemeRepository.get_all_memes(session)
        memes = await self.check_memes_valid(session, memes)
        self.all_valid_meme = memes
        self.all_valid_meme_count = len(memes)

        logger.info(f"一共加载了 {self.all_valid_meme_count} 个有效 Memes")

    async def delete_meme(self, session: async_scoped_session, meme: Meme):
        """
        删除指定 Meme
        """
        if meme.path.is_file():
            remove(meme.path)

        await MemeRepository.remove_meme(session, meme.id)  # type:ignore

        self.all_valid_meme.remove(meme)
        self.all_valid_meme_count -= 1

    async def auto_clean_memes(self, session: async_scoped_session):
        """
        自动删除不使用的 memes
        """
        if self.all_valid_meme_count <= config.max_memes:
            return

        logger.debug("Meme 数量已达上限，正在执行自动清理...")

        self._sort_memes()
        memes_to_delete = self.all_valid_meme[config.max_memes :]
        for meme in memes_to_delete:
            await self.delete_meme(session, meme)

        logger.info(
            f"已删除 {len(memes_to_delete)} 个 Memes，当前有效 Memes 数量为 {self.all_valid_meme_count}"
        )
        await session.commit()
        logger.debug("自动清理 Memes 完成")

    async def add_new_meme(self, session: async_scoped_session, meme_image: Resource):
        """
        添加 Meme
        """
        if meme_image.type != "image":
            raise ValueError("此类型不是 image 类型！")

        new_meme_hash = self._path_to_base64(meme_image.path)

        if any([new_meme_hash == meme.hash for meme in self.all_valid_meme]):
            logger.debug("检查到此 meme 已存在，停止添加")
            return

        if config.enable_security_check:
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

        meme_desc: dict[str, Any] = await self._chat_with_model(
            "以JSON格式生成标签和内容",
            system=self._generate_prompt_from_template("meme_description.jinja2"),
            image=meme_image,
        )

        new_meme = Meme(
            path=Path(meme_image.path),
            hash=new_meme_hash,
            description=meme_desc.get("desc", ""),
            tag=meme_desc.get("tags", []),
        )

        await self.auto_clean_memes(session)
        await MemeRepository.save_meme(session, new_meme)
        self.all_valid_meme.append(new_meme)
        self.all_valid_meme_count += 1

        logger.success(
            f"已成功添加新的表情包！描述:{new_meme.description}, 标签: {new_meme.tag}"
        )

    async def query_meme(self, message: Message) -> Optional[Meme]:
        # if config.similarity_method == "cosine":
        #     pass
        if config.meme_similarity_method == "levenshtein":
            from .similarity.levenshtein import query_meme

            meme_id = query_meme(message, self.all_valid_meme)
        elif config.meme_similarity_method == "llm":
            from .similarity.llm import llm_query

            meme_id = await llm_query(message, self.all_valid_meme)
        else:
            raise ValueError(
                f"未找到要求的相似度匹配算法: {config.meme_similarity_method}"
            )

        meme = next((meme for meme in self.all_valid_meme if meme.id == meme_id), None)
        if not meme:
            logger.warning(f"未找到匹配的 Meme，ID: {meme_id}")
            return None

        logger.info(
            f"查询到 Meme: {meme.id}, 标签: {meme.tag}, 描述: {meme.description}"
        )
        return meme
