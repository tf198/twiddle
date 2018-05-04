
test:
	python -m unittest discover

coverage:
	coverage run --source=twiddle -m unittest discover
	coverage html
