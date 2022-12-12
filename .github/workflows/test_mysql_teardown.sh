#!/usr/bin/env bash

# This script is meant to be run in a GitHub workflow only.

mysql -e "DROP DATABASE IF EXISTS db;" -u root -v -h 127.0.0.1 -P 3306
