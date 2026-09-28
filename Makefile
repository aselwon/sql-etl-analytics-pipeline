.PHONY: up build ingest transform test-data pipeline dashboard test demo-bad down
up:
	docker compose up -d db
build:
	docker compose build
ingest: up
	docker compose run --rm pipeline python -m shoppulse ingest
transform: up
	docker compose run --rm pipeline python -m shoppulse transform
test-data: up
	docker compose run --rm pipeline python -m shoppulse test-data
pipeline: up
	docker compose run --rm pipeline python -m shoppulse run
dashboard:
	docker compose up -d dashboard
test: up
	docker compose run --rm pipeline pytest -q
demo-bad: up
	docker compose run --rm pipeline python -m shoppulse ingest --data-dir data/bad
down:
	docker compose down
