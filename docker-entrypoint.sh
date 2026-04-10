#!/bin/sh
set -e
CFG="/vpn-webapp/config.ini"
EX="/vpn-webapp/config.example.ini"

if [ -d "$CFG" ]; then
  echo "Ошибка: $CFG — каталог, а нужен файл." >&2
  echo "На сервере в каталоге с docker-compose выполните: rm -rf ./config.ini && nano config.ini" >&2
  echo "(если файла не было, Docker мог создать пустую папку вместо файла)" >&2
  exit 1
fi

if [ ! -f "$CFG" ] && [ -f "$EX" ]; then
  echo "config.ini не найден — копирую из config.example.ini (заполните секреты и перезапустите контейнер)."
  cp "$EX" "$CFG"
fi

exec "$@"
