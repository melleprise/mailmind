#!/bin/sh
set -e

# Set environment variables
export NODE_OPTIONS="--max-old-space-size=4096 --no-experimental-fetch"
export DISABLE_ROLLUP_NATIVE=true
export ROLLUP_NATIVE=false
export VITE_DISABLE_NATIVE=true
export PATH="/app/node_modules/.bin:${PATH}"

# Function to check if node_modules exist and reflect package.json
# Basic check: Does node_modules exist? Is vite there (as a proxy)?
check_dependencies() {
  if [ ! -d "node_modules" ] || [ ! -f "node_modules/.bin/vite" ]; then
    # Also check if package.json has changed since last install (if marker exists)
    if [ -f "node_modules/.package-hash" ] && 
       [ "$(md5sum package.json | cut -d' ' -f1)" = "$(cat node_modules/.package-hash)" ]; then
      # node_modules seem to exist but vite binary missing, likely broken install
      echo "node_modules exist but vite binary missing. Forcing reinstall."
      return 1 
    else
      # node_modules potentially missing or package.json changed
      return 1
    fi
  fi
  return 0
}

# Store hash of package.json after successful install
store_package_hash() {
  md5sum package.json | cut -d' ' -f1 > node_modules/.package-hash
}

# Navigate to app directory (redundant if WORKDIR is /app, but safe)
cd /app

echo "Entrypoint: Running npm install (will update dependencies)..."
# Remove potentially broken node_modules before reinstalling
# rm -rf node_modules
npm install --verbose --unsafe-perm=true
if [ $? -ne 0 ]; then
  echo "Entrypoint: npm install failed!"
  exit 1
fi
echo "Entrypoint: npm install successful."

echo "Entrypoint: Starting application..."
# Use exec to replace the shell process with the node process
exec npm run dev 
# tail -f /dev/null # Auskommentiert 