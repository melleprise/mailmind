#!/bin/bash
set -e

# Function to wait for PostgreSQL
wait_for_postgres() {
# ... existing code ...
}

# Wait for PostgreSQL to be ready
wait_for_postgres

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput
 
# Load initial data (fixtures)
echo "Loading initial data fixtures..."
python manage.py loaddata mailmind/core/fixtures/*.json mailmind/prompt_templates/fixtures/*.json || echo "Warning: Fixture loading failed or partially failed."

# Start the main process (e.g., Django development server)
echo "Starting Django development server..."
exec python manage.py runserver 0.0.0.0:8000 