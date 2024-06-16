.DEFAULT_GOAL := run
.PHONY: create_environment run


create_environment:
	conda env create -f environment.yml
	pip install --no-build-isolation -e .
	pre-commit install

run:
	python -m ifonly