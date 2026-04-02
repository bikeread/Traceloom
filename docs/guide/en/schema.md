# Schema Guide

English | [简体中文](../zh-CN/schema.md)

The implementation source of truth is currently [04_schema_v1.yaml](../../04_schema_v1.yaml).

## v1 artifact types

Traceloom v1 models six first-class artifact families:

1. Brief
2. PRD / Story Pack
3. Solution Design
4. Execution Plan
5. Test & Acceptance
6. Release / Review

## Primary trace chain

`GOAL -> REQ -> DEC -> TASK -> TC -> REL -> REV`

## Current runtime note

The schema still lives at the repository root during active development.
A later change may package it under `traceloom/schemas/`, but this reorganization does not move it yet.
