#!/bin/bash

echo "=== Detak Agent Deployment Preparation ==="

# Step 1: Install required Python modules
echo "Installing required Python modules..."
sudo pip3 install pika python-dotenv pymongo
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python modules."
    exit 1
fi
echo "Python modules installed successfully."

# Step 2: Create 'detak' user with /opt/detak as home directory
echo "Creating 'detak' user..."
if id "detak" &>/dev/null; then
    echo "User 'detak' already exists."
else
    sudo useradd -m -d /opt/detak -s /bin/bash detak
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create 'detak' user."
        exit 1
    fi
    echo "User 'detak' created successfully."
fi

# Step 3: Create /opt/detak/detak_agent directory
echo "Setting up /opt/detak/detak_agent directory..."
DETAK_DIR="/opt/detak/detak_agent"
if [ ! -d "$DETAK_DIR" ]; then
    sudo mkdir -p "$DETAK_DIR"
    sudo chown -R detak:detak /opt/detak
    echo "Directory $DETAK_DIR created and ownership set to 'detak'."
else
    echo "Directory $DETAK_DIR already exists."
fi

# Step 4: Call detak_deploy.py
echo "Running detak_deploy.py..."
python3 detak_deploy.py
if [ $? -ne 0 ]; then
    echo "Error: detak_deploy.py failed."
    exit 1
fi

echo "=== Deployment Complete ==="