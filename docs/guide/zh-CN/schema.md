# Schema Guide

[English](../en/schema.md) | 简体中文

当前实现层面的 source of truth 是 [04_schema_v1.yaml](../../../04_schema_v1.yaml)。

## v1 artifact types

Traceloom v1 建模了六类一等 artifact families：

1. Brief
2. PRD / Story Pack
3. Solution Design
4. Execution Plan
5. Test & Acceptance
6. Release / Review

## Primary trace chain

`GOAL -> REQ -> DEC -> TASK -> TC -> REL -> REV`

## Current runtime note

在当前开发阶段，schema 仍然位于仓库根目录。
后续可能会把它打包到 `traceloom/schemas/` 下，但这次仓库整理不会移动它。
