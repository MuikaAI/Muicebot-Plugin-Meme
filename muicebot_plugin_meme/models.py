from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Meme:
    id: int = -1
    """表情包ID"""
    path: Path = field(default_factory=Path)
    """表情包路径"""
    hash: str = ""
    """表情包哈希值"""
    valid: bool = True
    """表情包是否有效"""
    description: str = ""
    """表情包描述"""
    tags: list[str] = field(default_factory=list)
    """表情包标签"""
    usage: int = 0
    """表情包使用次数"""

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)
