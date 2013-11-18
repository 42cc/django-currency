PROJECT=test_project
PWD=$(shell pwd)
MANAGE=$(PROJECT)/manage.py
PROJECT_APP=currency


test:
	$(MANAGE) test $(PROJECT_APP)

run:
	$(MANAGE) runserver

syncdb:
	$(MANAGE) syncdb --noinput

shell:
	$(MANAGE) shell
