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

## 介绍✨

`MuiceBot-Plugin-Memes` 是一个基于 `Muicebot` 的表情包插件，支持自动偷图、生成表情包描述，并自动在对话中插入表情包

## 目前支持的表情包匹配算法

- `levenshtein` 编辑距离查询（使用表情包标签和模型回复中的情绪标签进行查询，容易无结果，一般准确）

- `llm` 直接问 LLM 哪个更加合适（大约需要 1k ~ 3k token，非常准确）

## 先决条件

- `muicebot` 版本号大于等于 `1.0.2`

- 当前需要启用多模态的模型（已确认这是一个框架缺陷）

## 安装

向机器人对话：

```
.store install meme
```

（可能会）报错，关闭机器人

在命令行窗口中执行数据库迁移：

```shell
nb orm upgrade
```

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

### min_memes

- 说明: 最小表情包数量，保存的表情包达到这个数值才发送

- 类型: int

- 默认值: 10

### meme_general_max_query

- 说明: 全局最大查询数量

- 类型: int

- 默认值: 等同于 max_memes

### meme_llm_max_query

- 说明: 当启用 LLM 查询时，最大的查询数量

- 类型: int

- 默认值: 50

### meme_security_check

- 说明: 添加表情时，启用基于 LLM 的安全检查

- 类型: bool

- 默认值: True

### meme_multimodal_config

- 说明: 生成图片描述时，使用的多模态模型配置名

- 类型: Optional[str]

- 默认值: None

## 下一步工作

- [ ] 通过计算余弦相似度匹配 Meme 描述和模型文本内容

- [ ] 通过 [Muice-Chatbot中的OFA图像识别功能](https://github.com/Moemu/Muice-Chatbot/blob/main/docs/other_func.md#ofa-%E5%9B%BE%E5%83%8F%E8%AF%86%E5%88%AB%E8%AF%86%E5%88%AB--%E5%8F%91%E9%80%81%E8%A1%A8%E6%83%85%E5%8C%85) 生成图片描述

- [X] 检查对 gif 表情包的适用性
