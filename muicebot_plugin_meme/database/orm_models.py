from nonebot_plugin_orm import Model
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class MemeORM(Model):
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="Emotion ID"
    )
    path: Mapped[str] = mapped_column(String, nullable=False, comment="表情包路径")
    hash: Mapped[str] = mapped_column(String, nullable=False, comment="表情包哈希值")
    valid: Mapped[bool] = mapped_column(
        Integer, nullable=False, default=1, comment="表情包是否有效"
    )
    description: Mapped[str] = mapped_column(
        String, nullable=False, comment="表情包描述"
    )
    tag: Mapped[str] = mapped_column(
        String, nullable=False, default="_default", comment="表情包标签"
    )
    usage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="表情包使用次数"
    )
