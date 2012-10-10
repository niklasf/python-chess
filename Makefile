.PHONY: clean test

test:
	python setup.py nosetests

clean:
	python setup.py clean
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
