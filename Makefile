.PHONY: create_environment

create_environment:
	conda env create -f environment.yml
	pre-commit install
