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
    from state.user import CommunityUser

    def askExit(text = "Press Enter to continue or type EXIT to quit: "):
        v = input(text)
        if "EXIT" in v.upper() or "QUIT" in v.upper():
            print("Exiting.")
            exit(1)
        return v

    def insertUser(userdata: dict):
        return execute(
            "INSERT INTO users (tid, username, name) VALUES (%s, %s, %s)",
            (userdata["id"], userdata["nick"], userdata["name"])
        )

    def makeConsumeReason(r: str) -> str:
        return "consume: " + r

    def makePayReason(r: str) -> str:
        return r

    def makeSendReason(r: str) -> str:
        return "send: <no description>"

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
            "nick": None,
            "name": None
        }

        print("No community user was found. The following was generated:", community, sep = "\n")
        print("\nMake sure that this is *ABSOLUTELY* correct. Doing otherwise may break the data!\n")
        askExit()

        print("\nAdding community user to the database...")
        insertUser(community)
        community["uid"] = execute("SELECT id FROM users WHERE tid=%s", (community["id"]))[1][0]["id"]

    print("\nCalculating the initial balance...")

    def find(id_):
        for en in state:
            if en["id"] == id_:
                return en

    with open(log_path) as f:
        for line in f.readlines():
            entry = json.loads(line)
            user = find(entry["user"])
            if not entry["reason"].startswith("communism"):
                user["calc"] += entry["diff"]

    print("Completed. Overview over the init values:")
    for u in state:
        u["init"] = u["balance"] - u["calc"]
        print("Name {name}, Balance {balance}, Calc {calc}, Init {init}".format(**u))

    print("\nPlease verify that everything is correct.")
    askExit()

    print("\nCreating new records in the database...")
    for user in state:
        s, _ = insertUser(user)
        print("User {} was created: {}".format(user["name"], s == 1))

    print("\nRetrieving internal user IDs and creating User objects...")
    community["u"] = CommunityUser(community["uid"])
    users = [community["u"]]
    for user in state:
        s, values = execute("SELECT id FROM users WHERE tid=%s", (user["id"],))
        if s == 1:
            user["uid"] = values[0]["id"]
        # CommunityUser objects don't need Telegram User objects, therefore no MateBotUser
        user["u"] = CommunityUser(user["uid"])
        users.append(user["u"])
        print("User {} has internal ID {} now.".format(user["name"], user["uid"]))

    print("\nCommitting initial transactions (using reason 'data migration')...")
    for user in state:
        if user["init"] > 0:
            Transaction(community["u"], user["u"], abs(user["init"]), "data migration").commit()
        elif user["init"] < 0:
            Transaction(user["u"], community["u"], abs(user["init"]), "data migration").commit()

    print("\nTransferring the transactions from the log file into the database...")
    sent = None
    failed = []
    communisms = []
    with open(log_path) as f:
        for line in f.readlines():
            entry = json.loads(line)
            user = find(entry["user"])

            if entry["reason"] in ["drink", "ice", "water", "pizza"]:
                Transaction(
                    user["u"],
                    community["u"],
                    -entry["diff"],
                    makeConsumeReason(entry["reason"])
                ).commit()

            elif entry["reason"].startswith("pay"):
                Transaction(
                    community["u"],
                    user["u"],
                    entry["diff"],
                    makePayReason(entry["reason"])
                ).commit()

            elif entry["reason"].startswith("sent"):
                if sent is not None:
                    print("Warning! The previous sending transaction was incomplete!")
                    print(sent)
                    print(entry)
                    askExit()
                sent = entry

            elif entry["reason"].startswith("received"):
                if sent is None:
                    print("\nError! There is no known sending transaction!")
                    print(entry)
                    askExit()

                if sent["user"] == entry["user"]:
                    print("Warning! Skipping transaction with same sender and receiver:")
                    print(sent)
                    print(entry)
                    sent = None
                    continue

                if sent["diff"] != -entry["diff"]:
                    print("\nError! The value of the sending and receiving transactions differ!")
                    print(sent)
                    print(entry)
                    askExit()

                Transaction(
                    find(sent["user"])["u"],
                    find(entry["user"])["u"],
                    abs(entry["diff"]),
                    makeSendReason(entry["reason"])
                ).commit()

                sent = None

            elif entry["reason"].startswith("communism"):
                communisms.append(entry)

            else:
                failed.append(entry)
                print(
                    "\nError (not loaded into database):",
                    json.dumps(entry, indent = 4, sort_keys = True),
                    sep = "\n"
                )
                askExit()

    if len(failed) > 0:
        print("\nThere were {} entries that could not be loaded in the database automatically.".format(len(failed)))

    if len(communisms) > 0:
        print("\nThere are {} entries regarding communisms. We ignore them.".format(len(communisms)))


if __name__ == "__main__":
    main()
else:
    raise ImportError("Do not import this script!")
