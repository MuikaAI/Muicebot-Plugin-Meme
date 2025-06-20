import json
from pathlib import Path
from typing import Optional, Union

from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Meme
from .orm_models import MemeORM


class MemeRepository:
    @staticmethod
    def _convert(meme_orm: MemeORM) -> Meme:
        return Meme(
            id=meme_orm.id,
            path=Path(meme_orm.path),
            hash=meme_orm.hash,
            valid=meme_orm.valid,
            description=meme_orm.description,
            tags=list(meme_orm.tag),
            usage=meme_orm.usage,
        )

    @staticmethod
    async def get_all_memes(
        session: Union[async_scoped_session, AsyncSession], limit: Optional[int] = None
    ) -> list[Meme]:
        """
        获得全部有效 memes
        """
        stmt = select(MemeORM).where(MemeORM.valid == True).limit(limit)  # noqa:E712
        result = await session.execute(stmt)
        memes = result.scalars().all()
        return [MemeRepository._convert(meme) for meme in memes]

    @staticmethod
    async def get_meme_by_id(
        session: async_scoped_session, memeid: int
    ) -> Optional[Meme]:
        stmt = select(MemeORM).where(MemeORM.id == id)
        result = await session.execute(stmt)
        meme = result.scalar_one_or_none()
        return MemeRepository._convert(meme) if meme else None

    @staticmethod
    async def save_meme(session: async_scoped_session, meme: Meme):
        """
        存储 meme
        """
        session.add(
            MemeORM(
                path=meme.path.as_posix(),
                hash=meme.hash,
                valid=meme.valid,
                description=meme.description,
                tag=json.dumps(meme.tags, ensure_ascii=False),
                usage=meme.usage,
            )
        )

    @staticmethod
    async def remove_meme(
        session: Union[async_scoped_session, AsyncSession], meme_id: int
    ):
        """
        删除 meme

        这不会真正从表中删除，而是将 meme 标记为 invalid
        """
        stmt = update(MemeORM).where(MemeORM.id == meme_id).values(valid=False)
        await session.execute(stmt)

    @staticmethod
    async def get_meme_count(session: async_scoped_session) -> int:
        """
        获取有效的 Memes 数量
        """
        count = await session.execute(
            select(func.count()).where(MemeORM.valid == True)  # noqa:E712
        )
        return count.scalar() or 0
