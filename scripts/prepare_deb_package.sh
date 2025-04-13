#!/bin/bash
releaseVersion="0.6.0"

rootPath="/home/ericl/HomeTemp"
appName="Homie"
debFileName="${appName}_${releaseVersion}"
releaseAppFolder="/home/ericl/HomeTemp/data/release/$debFileName"

usrLocal="$releaseAppFolder/usr/local/$appName"
debFolder="$releaseAppFolder/DEBIAN"
systemFolder="$releaseAppFolder/etc/systemd/system"

echo "| ----------------------------------------------------------------------------------"
echo "| App name: $appName"
echo "| Target version: $releaseVersion"
echo "| Source root: $rootPath"
echo "| ----------------------------------------------------------------------------------"

echo "| Start preparing $debFileName in $releaseAppFolder"
echo "| >> Preparing package build folder structure"
mkdir $releaseAppFolder
mkdir -p $usrLocal
mkdir -p $debFolder
mkdir -p $systemFolder

##### prepare usr/local/Homie
cp -rf "$rootPath/core" "$usrLocal/"
cp -rf "$rootPath/endpoint" "$usrLocal/"
cp -rf "$rootPath/monitoring" "$usrLocal/"
cp -f "$rootPath/default_config.ini" "$usrLocal/config.ini"
cp -f "$rootPath/start.py" "$usrLocal/"
cp -f "$rootPath/start.sh" "$usrLocal/"
cp -f "$rootPath/requirements.txt" "$usrLocal/"
cp -f "$rootPath/readme.md" "$usrLocal/"
cp -f "$rootPath/changelog.md" "$usrLocal/"
cp -f "$rootPath/LICENSE" "$usrLocal/"
#create start_wrapper.sh
cat > "$usrLocal/start_wrapper.sh" <<EOF
#!/bin/bash
INI_FILE="config.ini"
# Read the 'instance' value from the [core] section
instanceName=\$(awk -F '=' '/\[core\]/ {found=1} found && \$1 ~ /instance/ {gsub(/ /, "", \$2); print \$2; exit}' "\$INI_FILE")
./start.sh \$instanceName
EOF

###### prepare DEBIAN
# Create packakge metadata
cat > "$debFolder/control" <<EOF
Package: $appName
Version: $releaseVersion
Section: base
Priority: optional
Architecture: armhf
Maintainer: Wurstbroteater <you@example.com>
Depends: docker-compose, docker.io, python3, python3-pip, ufw, screen, libpq-dev, xvfb, chromium-chromedriver
Description: $appName v$releaseVersion - Application to measure temperature and humdity of a room, 
  retrieve online weather data, visualize it, analyse it. Connect a camera to take pictures, too!
EOF
# Create post-install script
cat > "$debFolder/postinst" <<EOF
#!/bin/bash
set -e
apt-get update
apt-get install -y screen libpq-dev xvfb chromium-chromedriver
# Fix permissions for chromedriver
if [ -d /usr/lib/chromium-browser ]; then
    chmod -R 755 /usr/lib/chromium-browser
elif [ -f /usr/bin/chromedriver ]; then
    chmod -R 755 /usr/bin/chromedriver
fi
# Allow port 3000 in the firewall
if command -v ufw >/dev/null 2>&1; then
    ufw allow 3000/tcp
    ufw reload
fi
# Prepare docker
CURRENT_USER=\$(logname)
usermod -aG docker "\$CURRENT_USER"
systemctl restart docker
sleep 2
# Prepare python
python -m venv --system-site-packages /usr/local/$appName/.venv
source /usr/local/$appName/.venv/bin/activate
pip install -r /usr/local/$appName/requirements.txt
# Prepare file permissions
chmod +x /usr/local/$appName/start.sh
chmod +x /usr/local/$appName/start_wrapper.sh
# Enable systemd service (start at boot)
systemctl enable $appName

echo "*************************************************************"
echo "INSTALLATION COMPLETE."
echo ">>> Please alter the config.ini and reboot your system before"
echo ">>> startint the app! Otherwise, it may not work."
echo "*************************************************************"
exit 0

EOF
# Create pre-remove sciprt
cat > "$debFolder/prerm" <<EOF
#!/bin/bash
set -e
# Stop and disable systemd service
systemctl stop $appName || true
systemctl disable $appName || true
if command -v ufw >/dev/null 2>&1; then
    ufw delete allow 3000/tcp || true
    ufw reload
fi
exit 0
EOF

echo "| >> Setting file permissions"
chmod -R 755 "$debFolder"

###### prepare systemd service file
cat > "$systemFolder/$appName.service" <<EOF
[Unit]
Description=$appName Service
After=network.target docker.service
Requires=docker.service

[Service]
WorkingDirectory=/usr/local/$appName
ExecStart=/usr/local/$appName/start_wrapper.sh
ExecStop=/usr/bin/docker compose down
Restart=always
User=root
Environment="COMPOSE_PROJECT_NAME=$appName"

[Install]
WantedBy=multi-user.target
EOF

echo "| Done!"
echo "| Start building $debFileName in $releaseAppFolder"
dpkg-deb --build $releaseAppFolder
echo "| >> Removing build folder structure"
rm -rf $releaseAppFolder
echo "| ----------------------------------------------------------------------------------"
echo "| Building $debFileName was successful!"