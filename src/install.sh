#!/bin/bash
git clone https://github.com/simonjisu/autoupdate.git
python autoupdate/src/main.py \
    --opt "new_init" \
    -bp "." \
    -dp "/usr/bin" \
    -ms 1000 \
    -sv \
    -em $1 \
    -pw $2

export FLASK_APP=superset
export FLASK_ENV=development

flask fab create-admin \
    --username $3 \
    --firstname $4 \
    --lastname $5 \
    --email $6 \
    --password $7

superset db upgrade
superset init