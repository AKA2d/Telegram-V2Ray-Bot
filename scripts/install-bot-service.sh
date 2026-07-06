#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="telegram-v2ray-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
VENV_DIR="${REPO_DIR}/.venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
RUN_USER="${SUDO_USER:-$(logname 2>/dev/null || whoami)}"
RUN_GROUP="$(id -gn "${RUN_USER}")"

if [[ ${EUID} -ne 0 ]]; then
  echo "This installer needs root privileges. Re-running with sudo..."
  exec sudo "${BASH_SOURCE[0]}" "$@"
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Installing python3 and venv support..."
  apt-get update
  apt-get install -y python3 python3-venv python3-pip
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "${VENV_DIR}"
fi

"${PYTHON_BIN}" -m pip install --upgrade pip
"${PYTHON_BIN}" -m pip install -r "${REPO_DIR}/requirements.txt"

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Telegram V2Ray Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=${REPO_DIR}/telegram-bot
EnvironmentFile=${REPO_DIR}/telegram-bot/bot/.env
Environment=PYTHONUNBUFFERED=1
User=${RUN_USER}
Group=${RUN_GROUP}
ExecStart=${PYTHON_BIN} ${REPO_DIR}/telegram-bot/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"

sleep 2
systemctl status "${SERVICE_NAME}" --no-pager || true

echo
printf 'Service installed at %s\n' "${SERVICE_FILE}"
echo "Useful commands:"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
