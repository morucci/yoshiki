test: test-type test-unit

test-type:
	@mypy yoshiki

test-unit:
	@(PYTHONPATH=. python3 -m unittest -v tests/*.py)
