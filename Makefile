.PHONY: test reports rtl
test:
	python -m pytest -q
reports:
	python -m tools.accounting
rtl:
	python -m tools.rtl_check
