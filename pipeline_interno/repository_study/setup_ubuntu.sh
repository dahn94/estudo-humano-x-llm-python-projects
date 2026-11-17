#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip pipx openjdk-21-jre-headless unzip curl docker.io docker-compose-v2
pipx ensurepath
pipx install semgrep
sudo usermod -aG docker "$USER"
sudo service docker start

echo "Semgrep instalado:"
"$HOME/.local/bin/semgrep" --version
echo "Java instalado:"
java -version
echo "Docker instalado:"
sudo docker --version
echo "Ambiente Linux pronto. Feche e abra o Ubuntu para aplicar o grupo docker."
