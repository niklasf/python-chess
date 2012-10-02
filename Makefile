.PHONY: clean test

test:
	nosetests libchess/

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
