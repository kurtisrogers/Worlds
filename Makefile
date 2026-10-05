# CI targets wrap .github/workflows/ci.yml and run on the host.
# up, down, and logs are the local app container.
.DEFAULT_GOAL := help

.PHONY: behave check-openai-key docs down help install logs migrate pre-commit pytest test up

behave: export DJANGO_SETTINGS_MODULE := config.settings.test
behave:
	behave features/

docs:
	mkdocs build --strict

down:
	docker compose down

help:
	@echo 'behave      Run the feature tests'
	@echo 'check-openai-key  Reject a committed OpenAI-style key'
	@echo 'docs        Build the documentation and fail on warnings'
	@echo 'down        Stop the app and remove its container'
	@echo 'help        List these targets'
	@echo 'install     Install dependencies from requirements.txt'
	@echo 'logs        Follow the app container logs'
	@echo 'migrate     Apply migrations with config.settings.test'
	@echo 'pre-commit  Run pre-commit on all files'
	@echo 'pytest      Run pytest'
	@echo 'test        Run migrations, pytest, behave, pre-commit, and the key gate'
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

# Scan tracked files, then reject a temporary key-shaped fixture.
# The fixture is not committed. CI's openai-key-gate job runs this target.
check-openai-key:
	python scripts/no_openai_key.py
	python scripts/no_openai_key.py --self-test

test:
	$(MAKE) migrate
	$(MAKE) pytest
	$(MAKE) behave
	$(MAKE) pre-commit
	$(MAKE) check-openai-key

up:
	touch db.sqlite3
	docker compose up --build -d --wait
