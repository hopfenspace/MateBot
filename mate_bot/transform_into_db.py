#!/usr/bin/env python3

"""Script to transform the JSON files into database records

Note that this script should be run exactly once, when
the data should be moved to a productive environment.
The Telegram bot should be powered off during this
procedure. Make sure that you have the correct version
of the program installed so full support for MySQL
databases is given in advance.

This is an interactive script.
"""

from config import config
from state.dbhelper import execute


def main():
    """
    Interactively transform JSON files into database records
    """

    import os
    import json

    print(__doc__)

    print("Let's go...")

    config_path = "../config.json"
    while not os.path.exists(config_path):
        config_path = input("Path to the config JSON file: ")

    state_path = "../data/state.json"
    while not os.path.exists(state_path):
        state_path = input("Path to the state JSON file: ")

    log_path = "../data/transactions.log"
    while not os.path.exists(log_path):
        log_path = input("Path to the transactions log file: ")

    print("We need to know the current balance of the community user.")
    print("Make sure you exactly know this value. If you don't, type EXIT.")
    v = input("Enter the community balance in Cent: ")
    if "EXIT" in v.upper():
        print("Exiting.")
        exit(1)
    zwegat = int(v)

    rows, data = execute("SELECT * FROM users")

    if rows != 0 or len(data) != 0:
        print("\nWe found {} users in the database.".format(len(data)))
        print("Make sure that you start with a fresh database!")
        print("Doing otherwise leads to unknown behavior!\n")
        v = input("Press Enter to continue or type EXIT to quit: ")
        if "EXIT" in v.upper():
            print("Exiting.")
            exit(1)

    with open(state_path) as f:
        state = json.load(f)
    state = [state[k] for k in state]
    for e in state:
        e.update({"init": 0})
    print(state)
    print("\nThere are {} users in the state file:".format(len(state)))
    print(
        *["Telegram ID {id}, Balance {balance}, Name {name}, Nick {nick}".format(**e) for e in state],
        sep = "\n"
    )


if __name__ == "__main__":
    main()
else:
    raise ImportError("Do not import this script!")
