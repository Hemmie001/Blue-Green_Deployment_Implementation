#!/bin/bash
# Description: Toggles the active Blue/Green pool via the .env file and reloads Nginx.

# Check for required argument
NEW_POOL=$1
if [ "$NEW_POOL" != "blue" ] && [ "$NEW_POOL" != "green" ]; then
    echo "ERROR: Invalid pool specified."
    echo "Usage: $0 [blue|green]"
    exit 1
fi

echo "--- Blue/Green Manual Pool Switcher ---"
echo "Targeting new ACTIVE_POOL: ${NEW_POOL}"
echo "--------------------------------------"

# 1. Update the .env file
# This command handles both quoted and unquoted values reliably
if [ -f .env ]; then
    echo "1. Updating .env file..."
    
    # Use sed to replace the ACTIVE_POOL line, handling potential quotes
    sed -i.bak -E "s/^(ACTIVE_POOL=).*/\1\"${NEW_POOL}\"/" .env
    
    # Check if the update was successful
    if grep -q "ACTIVE_POOL=\"${NEW_POOL}\"" .env || grep -q "ACTIVE_POOL=${NEW_POOL}" .env; then
        echo "   -> .env updated successfully to ACTIVE_POOL=\"${NEW_POOL}\"."
        rm .env.bak # Clean up the backup file
    else
        echo "   -> ERROR: Failed to update ACTIVE_POOL in .env. Exiting."
        exit 1
    fi
else
    echo "ERROR: .env file not found. Please create it from .env.example."
    exit 1
fi

# 2. Restart ONLY the Nginx service to re-read the updated ACTIVE_POOL environment variable
echo "2. Restarting Nginx container to apply new routing..."
# The 'docker-compose up -d nginx' command forces a recreation/restart of the nginx service.
# This triggers the 'command' defined in the docker-compose.yml to run 'envsubst' again.
docker-compose up -d nginx

echo "--------------------------------------"
echo "SUCCESS: Routing now directs traffic to the ${NEW_POOL} pool."
echo "Verify status: curl -s http://localhost:8080/version | grep X-App-Pool"
