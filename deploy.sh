#!/bin/bash
# Usage: ./deploy.sh <env_path>

# do not sudo this script (sudo pip is bad)
if [ "$EUID" -eq 0 ]; then
    echo "Do not run this script as root - sudo pip is bad!";
    exit;
fi

# check if the virtual environment path is provided
if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh <env_path>";
    exit;
fi

# check that this is run in the same dir as critic.py
if [ ! -f critic.py ]; then
    echo "This script must be run in the same directory as critic.py!";
    exit;
fi

# create the virtual environment and install packages
echo "Creating virtual environment...";
python3 -m venv $1;
source $1/bin/activate;
echo "Installing packages...";
# python3 -m pip install --upgrade pip;
pip install -r requirements.txt;
deactivate;

# run the more_deploy.sh script as root (this will ask for password)
sudo bash more_deploy.sh $1;