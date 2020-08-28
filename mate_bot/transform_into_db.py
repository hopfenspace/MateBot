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
    import datetime

    from state.dbhelper import execute
    from state.transactions import Transaction
    from state.user import CommunityUser, MateBotUser

    class MigratedTransaction(Transaction):
        def fix(self, timestamp: datetime.datetime):
            if self._committed and self._id is not None:
                execute(
                    "UPDATE transactions SET registered=%s WHERE id=%s",
                    (timestamp, self._id,)
                )

    def get_path(file_description, file_name = "", default_path = ""):
        while not os.path.exists(default_path):
            if file_name != "":
                default_path = input("Path to the {} file (named {}): ".format(file_description, file_name))
            else:
                default_path = input("Path to the {} file: ".format(file_description))
        return default_path

    def ask_exit(text = "Press Enter to continue or type EXIT to quit: "):
        v = input(text)
        if "EXIT" in v.upper() or "QUIT" in v.upper():
            print("Exiting.")
            exit(1)
        return v

    def insert(user_data: dict, ts_migration: datetime.datetime):
        return execute(
            "INSERT INTO users (tid, username, name, created) VALUES (%s, %s, %s, %s)",
            (user_data["id"], user_data["nick"], user_data["name"], ts_migration)
        )

    def check_existing_database(db_name, mod):
        r, v = mod.execute("SHOW DATABASES")
        if r == 0:
            return False
        return any(db_name in v[c].values() for c in range(len(v)))

    def setup_database(setup_tables_script):
        print("\nCreating the tables based on the setup script...")
        with open(setup_tables_script) as fd:
            c = fd.read()
        r = []

        for i in c.split("\n"):
            if i == "" or i.strip().startswith("--"):
                continue
            r.append(i.strip())

        for c in " ".join(r).split(";"):
            if c != "":
                print("\nExecuting:", c)
                execute(c)

        print("\nCompleted table setup.\n")

    def create_community_user(current_balance: int, ts_for_insertion):
        print("\nAttempting to create a new community user...")

        print("What's the username of your community user?")
        username = input("Username (press Enter to skip): ")
        while username != "" and len(username) < 4:
            print("The username is too short.")
            username = input("Username (press Enter to skip): ")
        if username == "":
            username = None

        print("What's the full name of your community user?")
        name = input("Full name: ")
        while len(name) < 5:
            print("The name is too short.")
            name = input("Full name: ")

        community_user = {
            "balance": current_balance,
            "uid": None,
            "id": None,
            "nick": username,
            "name": name
        }

        print(
            "The following was generated:",
            community_user,
            "\nMake sure that this is ABSOLUTELY correct!",
            sep = "\n"
        )
        ask_exit()

        print("\nAdding community user to the database...")
        insert(community_user, ts_for_insertion)
        community_user["uid"] = execute(
            "SELECT id FROM users WHERE tid IS NULL",
            (community_user["id"])
        )[1][0]["id"]

        return community_user

    def get_community_balance():
        print(
            "What is the current balance of the community? This "
            "value\nwill be used as starting value for the community "
            "user.\nMake sure that this is correct, as the community user\n"
            "is the only user that may start with a non-zero balance.\n"
            "Note: The amount is measured in Cent.\n"
        )

        b = input("Current balance: ")
        while not b.isdecimal():
            b = input("Current balance: ")
        return int(b)

    def setup_freshly():
        import state.dbhelper
        database_name = state.dbhelper._config["database"]["db"]
        state.dbhelper._config["database"]["db"] = ""

        if check_existing_database(database_name, state.dbhelper):
            print("We found a database '{}'. Attempting to delete it...".format(database_name))
            print("\nTHE EXISTING DATABASE '{}' WILL BE DELETED AND ALL ITS DATA WILL BE ERASED!".format(database_name))
            print("\n\nAre you sure? If not, you can type EXIT to quit.")
            ask_exit()

            state.dbhelper.execute("DROP DATABASE {}".format(database_name))
            print("Table '{}' deleted.".format(database_name))

        state.dbhelper.execute("CREATE DATABASE {}".format(database_name))
        state.dbhelper._config["database"]["db"] = database_name
        print("Table '{}' created.".format(database_name))

        setup_database(get_path("database table setup", "create_tables.sql", "create_tables.sql"))

        create_community_user(get_community_balance(), datetime.datetime.now().replace(microsecond = 0))

    def make_reason_consume(r: str) -> str:
        return "consume: " + r

    def make_reason_pay(r: str) -> str:
        return r

    def make_reason_send() -> str:
        return "send: <no description>"

    print(__doc__)

    answer = input("\nStart with a fresh database (Y) or migrate old data (N)? ")
    while answer.upper() not in ["Y", "N"] or answer == "":
        answer = input("\nStart with a fresh database (Y) or migrate old data (N)? ")

    if answer.upper() == "Y":
        setup_freshly()
        exit(0)

    elif answer.upper() == "N":
        print("Okay, going on ...")

    config_path = get_path("config", "config.json", "config.json")

    state_path = get_path("state", "state.json", "state.json")

    log_path = get_path("transaction log", "transactions.log", "transactions.log")

    print("We need to know the current balance of the community user.")
    print("Make sure you exactly know this value. If you don't, type EXIT.")
    zwegat = int(ask_exit("Enter the community balance in Cent: "))

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
        ask_exit()
        print("\nAre you really sure?")
        ask_exit()
        print("If you say so... We now use the specified community balance value.")

    def find(id_, s):
        for en in s:
            if en["id"] == id_:
                return en

    def get_first_ts_and_calc(current_state):
        first = None
        with open(log_path) as fd:
            for line in fd.readlines():
                entry = json.loads(line)
                user = find(entry["user"], current_state)

                if not entry["reason"].startswith("communism"):
                    user["calc"] += entry["diff"]
                if first is None:
                    first = entry["timestamp"]
                elif entry["timestamp"] < first:
                    first = entry["timestamp"]

        return first

    print("\nCalculating the initial balance...")

    first_timestamp = get_first_ts_and_calc(state)

    def show_state_overview(current_state):
        for u in current_state:
            u["init"] = u["balance"] - u["calc"]
            print("Name {name}, Balance {balance}, Calc {calc}, Init {init}".format(**u))

    print("Completed. Overview over the init values:")
    show_state_overview(state)
    print("\nPlease verify that everything is correct.")
    ask_exit()

    first_ts = datetime.datetime.fromtimestamp(int(first_timestamp))
    migration = first_ts.replace(hour = 0, minute = 0, second = 0)
    print("\nFirst timestamp: '{}'\nWe use '{}' as data migration timestamp now.".format(first_ts, migration))

    rows, data = execute("SELECT * FROM users")
    print("\nWe found {} users in the database.".format(len(data)))

    def detect_community():
        print("\nDetecting community user automatically...")
        r, v = execute("SELECT * FROM users WHERE tid IS NULL")
        if r == 0:
            print("No community user found by convention.")
            return None
        elif r > 0:
            print(
                "More than one community user found.\nERROR: Critical! There must never be more than "
                "one virtual user!\nPlease delete all virtual users and start with a fresh database."
            )
            exit(1)
        return v[0]

    if rows == 1 and len(data) == 1:
        if data[0]["tid"] is not None:
            print(
                "The only user found is not the community user. By convention, "
                "the community user has no Telegram ID (NULL)!"
            )
            ask_exit()

            community = create_community_user(zwegat, migration)

        else:

            if zwegat != data[0]["balance"]:
                print("The balance of the community user in the database is {}.".format(data[0]["balance"]))
                print("This seems to be wrong! Please check your config.")
                ask_exit()

            community = {
                "balance": zwegat,
                "uid": data[0]["id"],
                "id": data[0]["tid"],
                "nick": data[0]["username"],
                "name": data[0]["name"]
            }

            print("Selecting the following community user:", community, sep = "\n")
            print("\nMake sure that this is *ABSOLUTELY* correct. Doing otherwise will break the data!\n")
            ask_exit()

    else:
        print("Make sure that you start with a fresh database.")
        print("Only the community user should exist!")
        print("Doing otherwise leads to unknown behavior!\n")
        ask_exit()

        community = detect_community()
        if community is not None:
            print("\nWe detected the following community user data:")
            print(community)
        else:
            community = create_community_user(zwegat, migration)

    def create_users_from_state(current_state):
        print("\nCreating new records in the database...")
        for u in current_state:
            r, _ = insert(u, migration)
            print("User {} was created: {}".format(u["name"], r == 1))

    create_users_from_state(state)

    def create_user_objects(current_state):
        print("\nRetrieving internal user IDs and creating User objects...")
        community["u"] = CommunityUser()
        for u in current_state:
            s, values = execute("SELECT id FROM users WHERE tid=%s", (u["id"],))
            if s == 1:
                u["uid"] = values[0]["id"]

            u["u"] = MateBotUser(u["uid"])
            print("User {} has internal ID {} now.".format(u["name"], u["uid"]))

    create_user_objects(state)

    def fix_init_balances():
        print("\nCommitting initial transactions (using reason 'data migration')...")
        for user in state:
            if user["init"] > 0:
                t = MigratedTransaction(community["u"], user["u"], abs(user["init"]), "data migration")
                t.commit()
                t.fix(migration)
            elif user["init"] < 0:
                t = MigratedTransaction(user["u"], community["u"], abs(user["init"]), "data migration")
                t.commit()
                t.fix(migration)

    fix_init_balances()

    def migrate_transactions(current_state):
        print("\nTransferring the transactions from the log file into the database...")
        sent = None
        failed = []
        communisms = []
        with open(log_path) as fd:
            for l in fd.readlines():
                tr = json.loads(l)

                t = None
                if tr["reason"] in ["drink", "ice", "water", "pizza"]:
                    t = MigratedTransaction(
                        find(tr["user"], current_state),
                        community["u"],
                        -tr["diff"],
                        make_reason_consume(tr["reason"])
                    )

                elif tr["reason"].startswith("pay"):
                    t = MigratedTransaction(
                        community["u"],
                        find(tr["user"], current_state),
                        tr["diff"],
                        make_reason_pay(tr["reason"])
                    )

                elif tr["reason"].startswith("sent"):
                    if sent is not None:
                        print("Warning! The previous sending transaction was incomplete!")
                        print(sent)
                        print(tr)
                        ask_exit()
                    sent = tr

                elif tr["reason"].startswith("received"):
                    if sent is None:
                        print("\nError! There is no known sending transaction!")
                        print(tr)
                        ask_exit()

                    if sent["user"] == tr["user"]:
                        print("Warning! Skipping transaction with same sender and receiver:")
                        print(sent)
                        print(tr)
                        sent = None
                        continue

                    if sent["diff"] != -tr["diff"]:
                        print("\nError! The value of the sending and receiving transactions differ!")
                        print(sent)
                        print(tr)
                        ask_exit()

                    t = MigratedTransaction(
                        find(sent["user"], current_state)["u"],
                        find(tr["user"], current_state)["u"],
                        abs(tr["diff"]),
                        make_reason_send()
                    )

                    sent = None

                elif tr["reason"].startswith("communism"):
                    communisms.append(tr)

                else:
                    failed.append(tr)
                    print(
                        "\nError (not loaded into database):",
                        json.dumps(tr, indent = 4, sort_keys = True),
                        sep = "\n"
                    )
                    ask_exit()

                if t is not None:
                    t.commit()
                    t.fix(datetime.datetime.fromtimestamp(int(tr["timestamp"])))

        if len(failed) > 0:
            print("\nThere were {} entries that could not be loaded in the database automatically.".format(len(failed)))

        if len(communisms) > 0:
            print("\nThere are {} entries regarding communisms. We ignore them.".format(len(communisms)))

    migrate_transactions(state)


    if len(failed) > 0:
        print("\nThere were {} entries that could not be loaded in the database automatically.".format(len(failed)))

    if len(communisms) > 0:
        print("\nThere are {} entries regarding communisms. We ignore them.".format(len(communisms)))


if __name__ == "__main__":
    main()
else:
    raise ImportError("Do not import this script!")
