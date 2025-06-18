<div align=center>
  <img width=200 src="https://bot.snowy.moe/logo.png"  alt="image"/>
  <h1 align="center">MuiceBot-Plugin-Memes</h1>
  <p align="center">Muicebot 自动偷图、自动发送表情包插件✨</p>
</div>
<div align=center>
  <a href="https://nonebot.dev/"><img src="https://img.shields.io/badge/nonebot-2-red" alt="nonebot2"></a>
  <img src="https://img.shields.io/badge/Code%20Style-Black-121110.svg" alt="codestyle">
  <a href='https://qm.qq.com/q/lhUBw6Gcdq'><img src="https://img.shields.io/badge/QQ群-MuiceHouse-blue" alt="QQ群组"></a>
</div>

## 目前支持的表情包匹配算法

- `levenshtein` 编辑距离查询（使用表情包标签和模型回复中的情绪标签进行查询）

- `llm` 直接问 LLM 哪个更加合适

## 配置

### meme_probability

- 说明: 发送表情包概率

- 类型: float

- 默认值: 0.1

### meme_save_probability

- 说明: 保存表情包概率

- 类型: float

- 默认值: 0.2

### meme_similarity_method

- 说明: 相似度计算方式

- 类型: Literal["levenshtein", "llm"]

- 默认值: levenshtein

### max_memes

- 说明: 最大表情包数量

- 类型: int

- 默认值: 500

### meme_general_max_query

- 说明: 全局最大查询数量

- 类型: int

- 默认值: 等同于 max_memes

### meme_llm_max_query

- 说明: 当启用 LLM 查询时，最大的查询数量

- 类型: int

- 默认值: 50