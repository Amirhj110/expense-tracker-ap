#!/bin/bash
python manage.py migrate --noinput
python manage.py createsuperuser --noinput --username admin --email admin@example.com || true
python manage.py create_categories || true
gunicorn expensetracker.wsgi:application
