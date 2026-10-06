# CI targets wrap .github/workflows/ci.yml and run on the host.
# up, down, and logs are the local app container.
.DEFAULT_GOAL := help

.PHONY: behave docs down help install logs migrate pre-commit pytest test test-review-e2e up

behave: export DJANGO_SETTINGS_MODULE := config.settings.test
behave:
	behave --no-skipped --tags="not @pending-review-panel and not @pending-review-api" features/

docs:
	mkdocs build --strict

down:
	docker compose down

help:
	@echo 'behave      Run the feature tests'
	@echo 'docs        Build the documentation and fail on warnings'
	@echo 'down        Stop the app and remove its container'
	@echo 'help        List these targets'
	@echo 'install     Install dependencies from requirements.txt'
	@echo 'logs        Follow the app container logs'
	@echo 'migrate     Apply migrations with config.settings.test'
	@echo 'pre-commit  Run pre-commit on all files'
	@echo 'pytest      Run pytest'
	@echo 'test        Run migrations, pytest, behave, and pre-commit'
	@echo 'test-review-e2e  Run chapter-review features, including pending scenarios'
	@echo 'up          Build the app image, migrate, and serve it'

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

logs:
	docker compose logs -f

migrate: export DJANGO_SETTINGS_MODULE := config.settings.test
migrate:
	python manage.py migrate --settings=config.settings.test

pre-commit:
	pre-commit run --all-files

pytest: export DJANGO_SETTINGS_MODULE := config.settings.test
pytest:
	pytest

test:
	$(MAKE) migrate
	$(MAKE) pytest
	$(MAKE) behave
	$(MAKE) pre-commit

# Host-only. Includes pending panel and API scenarios. Panel scenarios
# fail closed until the review panel (#5) exists. State and anchor
# scenarios fail closed until PR #28 is on main.
test-review-e2e: export DJANGO_SETTINGS_MODULE := config.settings.test
test-review-e2e:
	behave --tags="not @pending-excluded-from-this-run" features/chapter_review.feature

up:
	touch db.sqlite3
	docker compose up --build -d --wait
