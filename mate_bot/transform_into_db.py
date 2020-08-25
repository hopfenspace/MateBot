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


def main():
    """
    Interactively transform JSON files into database records
    """

    import os
    import json

    from config import config
    from state.dbhelper import execute
    from state.transactions import Transaction
    from state.user import MateBotUser, CommunityUser

    def askExit(text = "Press Enter to continue or type EXIT to quit: "):
        v = input(text)
        if "EXIT" in v.upper() or "QUIT" in v.upper():
            print("Exiting.")
            exit(1)
        return v

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
    zwegat = int(askExit("Enter the community balance in Cent: "))

    print("\nDetected community user ID {} in the config file.".format(config["community-id"]))
    print("Please verify that this is correct.")
    askExit()

    with open(state_path) as f:
        state = json.load(f)
    state = [state[k] for k in state]
    for e in state:
        e.update({"calc": 0})

    print("\nThere are {} users in the state file:".format(len(state)))
    print(
        *["Telegram ID {id}, Balance {balance}, Name {name}, Nick {nick}".format(**e) for e in state],
        sep = "\n"
    )

    print("\nYou entered {} as community user balance.".format(zwegat))
    total = sum(u["balance"] for u in state)
    print("The sum of all users' balances is currently {}.".format(total))
    if total != zwegat:
        print("Something seems to be wrong here! Please verify the data sets!")
        askExit()
        print("\nAre you really sure?")
        askExit()
        print("If you say so... We now use the specified community balance value.")

    rows, data = execute("SELECT * FROM users WHERE id=%s", (config["community-id"],))
    if rows == 0:
        print("\nUnable to detect community user with ID {}!".format(config["community-id"]))

    rows, data = execute("SELECT * FROM users")
    print("\nWe found {} users in the database.".format(len(data)))

    if rows == 1 and len(data) == 1:
        if zwegat != data[0]["balance"]:
            print("The balance of the community user in the database is {}.".format(data[0]["balance"]))
            print("This seems to be wrong! Please check your config.")
            askExit()

        community = {
            "balance": zwegat,
            "uid": data[0]["id"],
            "id": data[0]["tid"],
            "nick": data[0]["username"],
            "name": data[0]["name"]
        }

        print("Selecting the following community user:", community, sep = "\n")
        print("\nMake sure that this is *ABSOLUTELY* correct. Doing otherwise will break the data!\n")
        askExit()

    else:
        print("Make sure that you start with a fresh database.")
        print("Only the community user should exist!")
        print("Doing otherwise leads to unknown behavior!\n")
        askExit()

        community = {
            "balance": zwegat,
            "uid": config["community-id"],
            "id": 0,
            "nick": "",
            "name": ""
        }

        print("No community user was found. The following was generated:", community, sep = "\n")
        print("\nMake sure that this is *ABSOLUTELY* correct. Doing otherwise may break the data!\n")
        askExit()

    print("\nCalculating the initial balance...")

    def find(id_):
        for en in state:
            if en["id"] == id_:
                return en

    with open(log_path) as f:
        for line in f.readlines():
            entry = json.loads(line)
            user = find(entry["user"])
            user["calc"] += entry["diff"]

    print("Completed. Overview over the init values:")
    for u in state:
        u["init"] = u["balance"] - u["calc"]
        print("Name {name}, Balance {balance}, Calc {calc}, Init {init}".format(**u))

    print("\nPlease verify that everything is correct.")
    askExit()


if __name__ == "__main__":
    main()
else:
    raise ImportError("Do not import this script!")
