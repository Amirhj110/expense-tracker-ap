#!/bin/bash

# Wait for database to be ready
sleep 5

# Run migrations
python manage.py migrate --noinput

# Create superuser (skip if exists)
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell

# Create categories
python manage.py create_categories

# Start the server
gunicorn expensetracker.wsgi:application