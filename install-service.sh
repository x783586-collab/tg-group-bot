#!/bin/bash
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"
USER_NAME="$(whoami)"

if [ ! -f .env ]; then
  echo "先填写 .env 再装服务"
  exit 1
fi

if [ ! -d .venv ]; then
  bash install.sh
fi

SERVICE=/etc/systemd/system/tg-bot.service
sudo tee "$SERVICE" >/dev/null <<EOF
[Unit]
Description=Telegram group bot
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$DIR
Environment=PATH=$DIR/.venv/bin
ExecStart=$DIR/.venv/bin/python $DIR/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now tg-bot
sudo systemctl status tg-bot --no-pager
echo
echo "看日志： journalctl -u tg-bot -f"
echo "重启：   sudo systemctl restart tg-bot"
echo "停止：   sudo systemctl stop tg-bot"
