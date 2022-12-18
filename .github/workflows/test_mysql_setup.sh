#!/usr/bin/env bash

# This script is meant to be run in a GitHub workflow only.

mysql -e "CREATE OR REPLACE DATABASE db;" -u root -v -h 127.0.0.1 -P 3306 1>>mysql.log
sleep 0.1
