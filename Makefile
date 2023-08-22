PYTHON = python
PYTEST = $(PYTHON) -m pytest
FLAKE8 = $(PYTHON) -m flake8

test:
	$(PYTEST) ./tests

style:
	$(FLAKE8) ./src/kivy_garden/draggable
