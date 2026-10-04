# Wraps the commands in .github/workflows/ci.yml. Help lists them alphabetically.
.DEFAULT_GOAL := help

.PHONY: behave docs help install migrate pre-commit pytest test

behave: export DJANGO_SETTINGS_MODULE := config.settings.test
behave:
	behave features/

docs:
	mkdocs build --strict

help:
	@echo 'behave      Run the feature tests'
	@echo 'docs        Build the documentation and fail on warnings'
	@echo 'help        List these targets'
	@echo 'install     Install dependencies from requirements.txt'
	@echo 'migrate     Apply migrations with config.settings.test'
	@echo 'pre-commit  Run pre-commit on all files'
	@echo 'pytest      Run pytest'
	@echo 'test        Run migrations, pytest, behave, and pre-commit'

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

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
