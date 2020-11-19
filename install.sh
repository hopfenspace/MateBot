pacman -S libolm python python-pip
useradd -m -s /bin/bash mate_bot
cp -r . /home/mate_bot
cp mate_bot.service /usr/lib/systemd/system/
ln -s /usr/lib/systemd/system/mate_bot.service /etc/systemd/system/multi-user.target.wants/
systemctl daemon-reload
systemctl enable mate_bot.service
chown -R mate_bot:mate_bot /home/mate_bot
python -m venv /home/mate_bot/venv
/home/mate_bot/venv/bin/python -m pip install -r requirements.txt
