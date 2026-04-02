# Compatibility Guide

[English](../en/compatibility.md) | 简体中文

这份指南说明 Traceloom public beta 当前的支持边界。

## Supported client story

- canonical product surface：Traceloom MCP
- 第一官方推荐客户端：Cherry Studio
- 次级路径：其他 MCP-capable IDE 和本地 AI 工具，复用同一条只读 server 命令

## Supported baseline

- companion executable 是当前首条不需要 Python 的首次体验路径
- Python `3.10+` 只在源码 checkout fallback 下才需要
- 从本地 checkout 仓库执行 `python -m pip install .`
- 已安装的 `traceloom` CLI 是 public-beta 评估时的主要 outsider 路径
- `python -m traceloom` 仅作为 fallback，留给受限 shell 或 contributor workflow
- 面向符合 Traceloom artifact model 的仓库，进行本地只读 MCP 使用
- 通过本地 CLI 使用当前这批 governed write helpers：draft creation、draft revision、artifact supersession、review decision、validation record、status promotion

## Known limits

- 暂无公开 write-side MCP 操作
- 没有 hosted SaaS 或托管同步服务
- public-beta 指南目前最强的是内置 examples、starter template 和 Cherry Studio 路径

## 当前足够稳定、值得评估的部分

- feature triage
- release triage
- impact analysis
- version-aware 的 read/query 行为
- 当前 Track A 窄范围切片的本地 governed write helpers，包括 draft/version lifecycle 写操作

## 仍在演进、需要保守看待的部分

- Cherry Studio 之外更广泛的客户端专用接入指南
- 超出本地 CLI helpers 之外的 write-side workflow automation
- 超出当前 companion executable 支持路径之外的 packaging 和 install 体验
