# Gmail Calendar Sync

GmailからOpenAI APIでメール内容を解析し、航空券/カーシェア予約をGoogle Calendarに自動追加。

## Quick Start

```bash
# Setup
uv sync
uv run python get_refresh_token.py  # OAuth認証

# Development
uv run python src/main.py           # 実行
uv run pytest                       # テスト
uv run mypy src/                    # 型チェック
uv run ruff format src/             # フォーマット
```

## Required Environment Variables

@include .claude/environment.md#Required_Environment_Variables

## Development

@include .claude/workflow.md#Standard_Development_Cycle
@include .claude/workflow.md#Code_Style_Guidelines

## Architecture

@include .claude/structure.md#Directory_Structure
