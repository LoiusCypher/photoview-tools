#!/bin/bash
if [[ -z "${HOSTNAME}" ]];         then echo "No HOSTNAME available!" ; exit 1 ; fi
if [ ! -f ./.env ];                then echo "Please provide .env file with MARIADB_USER= and MARIADB_PASSWORD= setting!" ; exit 1 ; fi
source ./.env
if [[ -z "${MARIADB_USER}" ]];     then echo "Please provide .env file with MARIADB_USER= and MARIADB_PASSWORD= setting!" ; exit 1 ; fi
if [[ -z "${MARIADB_PASSWORD}" ]]; then echo "Please provide .env file with MARIADB_USER= and MARIADB_PASSWORD= setting!" ; exit 1 ; fi
if [ ! -f ./docker-compose-filescanner.yml ]; then
    wget https://raw.githubusercontent.com/LoiusCypher/photoview-tools/refs/heads/main/docker-compose-filescanner.yml
fi
export HOSTNAME && sudo docker compose -f docker-compose-filescanner.yml down --remove-orphans
sudo docker pull ghcr.io/loiuscypher/photoview-tools:main
#export HOSTNAME && sudo docker compose -f docker-compose-filescanner.yml --profile dev up --remove-orphans filescanner_dev
export HOSTNAME && sudo docker compose -f docker-compose-filescanner.yml up --remove-orphans filescanner


