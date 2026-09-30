#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null; then
  echo "没找到 python3，先执行："
  echo "sudo apt update && sudo apt install -y python3 python3-venv python3-pip git"
  exit 1
fi

python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "已生成 .env，请编辑填写 BOT_TOKEN、OWNER_ID、OPENAI_API_KEY"
  echo "nano .env"
  exit 0
fi

echo "依赖已装好。启动： ./start.sh"
echo "后台常驻： ./install-service.sh"
