# Adoption Guide

[English](../en/adoption.md) | 简体中文

这份指南帮助你判断 Traceloom 是否适合现有团队流程，以及如何在不过度投入的前提下完成评估。

## 推荐评估路径

1. 先用仓库内置的 golden-path example。
2. 把 Cherry Studio 或其他 MCP 客户端连接到本地 Traceloom server。
3. 运行三条 canonical question flows。
4. 对照团队当前回答同类问题的方式，比较结果是否更清晰。
5. 如果评估结果积极，再复制 starter template 试一个小范围真实 feature。

## 适配信号

- 团队已经把关键交付上下文保存在 Git 和 Markdown 中
- 你更看重跨 artifact traceability，而不是富文档编辑体验
- 你希望本地 AI 工具读取交付 lineage，而不是先上 hosted service

## 不太适合的信号

- 你首先需要的是 hosted collaboration 产品
- 真实 source of truth 不在 Git 中，而且无法干净镜像
- 在 read-side 评估完成前，你就必须依赖公开 write-side automation

## 第一步真实采用动作

把 `templates/starter-repo` 复制到一个沙箱仓库里，再把占位内容替换成一个小范围 feature。
第一次切片要尽量小，最好能让一个团队在一个 release cycle 内完整评审整条 artifact 链。

## 扩大采用前需要验证的点

- 团队能否持续保持 artifact scope 和 IDs 一致
- 三条 canonical question flows 在真实项目数据上是否仍然有价值
- 额外的评审成本是否在团队可接受范围内
