.PHONY: install test replay report check
install:
	python3 -m pip install -e ../Hard-Decisions -e '.[dev,jev]'
test:
	python3 -m pytest -q
replay:      ## rescore every committed record, offline
	da replay
report:
	da report
check: test replay report
