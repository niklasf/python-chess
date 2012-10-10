.PHONY: clean test doc

test:
	python setup.py nosetests

clean:
	python setup.py clean
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	-rm -r build/
	-rm -r dist/
	-rm -r python_chess.egg-info/
	make --directory=doc/ clean

doc:
	make --directory=doc/ html
