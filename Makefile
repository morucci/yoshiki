test: test-type test-unit

test-type:
	@mypy --strict yoshiki

test-unit:
	@(PYTHONPATH=. python3 -m unittest -v tests/*.py)
