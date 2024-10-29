#!/bin/bash
# do not run this script directly - run deploy.sh instead 

# copy the config file, slack_notifier.py, critic.py, and subscriber.py into the virtual environment
echo "Copying files...";
mkdir $1/src;

# write the systemd service files
echo "Writing systemd service files...";
cat << EOF > critic.service
[Unit]
Description=Critic Maestro crash report service

[Service]
Type=simple
Restart=on-failure
ExecStart=$1/bin/python3 $(pwd)/critic.py

[Install]
WantedBy=multi-user.target
EOF

cat << EOF > critic_slack.service
[Unit]
Description=Critic Slack notifier service
After=critic.service

[Service]
Type=simple
Restart=on-failure
ExecStart=$1/bin/python3 $(pwd)/slack_notifier.py

[Install]
WantedBy=multi-user.target
EOF

# symlink the service files to the systemd directory
echo "Symlinking service files...";
ln -s $(pwd)/critic.service /etc/systemd/system/critic.service;
ln -s $(pwd)/critic_slack.service /etc/systemd/system/critic_slack.service;

# enable the services
echo "Enabling services...";
systemctl daemon-reload;
systemctl enable critic.service;
systemctl enable critic_slack.service;
echo "Starting services...";
systemctl start critic.service;
systemctl start critic_slack.service;
echo "Done!";