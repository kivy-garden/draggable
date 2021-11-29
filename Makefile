PYTHON = python
PYTEST = $(PYTHON) -m pytest
FLAKE8 = $(PYTHON) -m flake8

test:
	$(PYTEST) ./kivy_garden/draggable/tests

style:
	$(FLAKE8) ./kivy_garden/draggable
