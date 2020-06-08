# python files
PY_SRC_ALL = $(wildcard statsimi/*.py) $(wildcard statsimi/*/*.py)
SETUPPY_SRC = $(wildcard setup.py) $(wildcard */setup.py)
PY_SRC = $(filter-out $(SETUPPY_SRC), $(PY_SRC_ALL))

.SECONDARY:

install:
	python3 setup.py install

test:
	python3 setup.py test

checkstyle:
	flake8 $(PY_SRC)

clean:
	@rm -rf geodata
	@rm -rf $(FIX_RES_DIR)
	@rm -rf $(EVAL_RES_DIR)
	@find . -name "*.pyc" | xargs rm -f
	@find . -name "__pycache__" | xargs rm -rf
