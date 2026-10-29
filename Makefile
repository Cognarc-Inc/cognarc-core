# 常用指令。所有路徑相對於 repo 根目錄。
SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help lint test test-db pg-up pg-down export check-tiers

help:
	@echo "make lint | test | test-db | pg-up | pg-down | export | check-tiers"

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run pyright

# 不需要資料庫的測試。
test:
	uv run pytest -m "not db" tests

# 需要 Postgres：CORE_TEST_ADMIN_URL 未設時先 make pg-up（臨時實例，資料放 .pgdata/）。
test-db:
	CORE_TEST_ADMIN_URL=$${CORE_TEST_ADMIN_URL:-postgresql+psycopg://$$USER@127.0.0.1:55434/postgres} uv run pytest tests

pg-up:
	scripts/dev_pg.sh up

pg-down:
	scripts/dev_pg.sh down

# 只有 internal 來源 repo 有 tools/ 與 tiers.toml。
check-tiers:
	uv run python tools/export_tier.py --check

export: check-tiers
	uv run python tools/export_tier.py --tier oss --out dist/oss --force --git-init
	uv run python tools/export_tier.py --tier enterprise --out dist/enterprise --force --git-init
	uv run python tools/export_tier.py --tier internal --out dist/internal --force --git-init
