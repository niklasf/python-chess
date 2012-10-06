.PHONY: clean test

test:
	nosetests chess/

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
