#!/usr/bin/env python3

"""Script to setup the database layout for the MateBot and migrate previous data

Note that this script should be run exactly once, when
the data should be moved to a productive environment.
The Telegram bot should be powered off during this
procedure. Make sure that you have the correct version
of the program installed, so full support for MySQL
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

    from mate_bot.config import config
    from mate_bot.state import dbhelper
    from mate_bot.state.transactions import Transaction
    from mate_bot.state.user import CommunityUser, MateBotUser

    dbhelper.BackendHelper.db_config = config["database"]
    execute = dbhelper.BackendHelper._execute

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

    def ask_yes_no(prompt) -> bool:
        answer = input(prompt)
        while answer.upper() not in ["Y", "N"] or answer == "":
            answer = input(prompt)
        return answer.upper() == "Y"

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

    def find(id_, s):
        for en in s:
            if en["id"] == id_:
                return en

    def get_first_ts_and_calc(current_state, transaction_log_path):
        first = None
        with open(transaction_log_path) as fd:
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

    def create_users_from_state(current_state, migration):
        print("\nCreating new records in the database...")
        for u in current_state:
            r, _ = insert(u, migration)
            print("User {} was created: {}".format(u["name"], r == 1))

    def check_existing_database(db_name, executor_func):
        r, v = executor_func("SHOW DATABASES")
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

    def create_community_user(current_balance: int, ts_for_insertion: datetime.datetime):
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
        print("Created community user.")

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
        database_name = dbhelper.BackendHelper.db_config["db"]
        dbhelper.BackendHelper.db_config["db"] = ""

        if check_existing_database(database_name, dbhelper.BackendHelper._execute):
            print("We found a database '{}'. Attempting to delete it...".format(database_name))
            print("\nTHE EXISTING DATABASE '{}' WILL BE DELETED AND ALL ITS DATA WILL BE ERASED!".format(database_name))
            print("\n\nAre you sure? If not, you can type EXIT to quit.")
            ask_exit()

            dbhelper.BackendHelper._execute("DROP DATABASE {}".format(database_name))
            print("Table '{}' deleted.".format(database_name))

        dbhelper.BackendHelper._execute("CREATE DATABASE {}".format(database_name))
        dbhelper.BackendHelper.db_config["db"] = database_name
        print("Table '{}' created.".format(database_name))

        print("\nCreating the database schema...\n")
        for k in dbhelper.DATABASE_SCHEMA:
            command = dbhelper.DATABASE_SCHEMA[k]._to_string(4)
            print(command)
            execute(command)
        print("\nCompleted database table setup.\n")

    def create_user_objects(current_state):
        print("\nRetrieving internal user IDs and creating User objects...")
        for u in current_state:
            s, values = execute("SELECT id FROM users WHERE tid=%s", (u["id"],))
            if s == 1:
                u["uid"] = values[0]["id"]

            u["u"] = MateBotUser(u["uid"])
            print("User {} has internal ID {} now.".format(u["name"], u["uid"]))

    def transform_user_record(record, balance = None):
        user = {
            "uid": record["id"],
            "id": record["tid"],
            "nick": record["username"],
            "name": record["name"]
        }

        if balance is None:
            user["balance"] = record["balance"]
        else:
            user["balance"] = balance
        return user

    def verify_community_user_data(community_balance, migration):
        rows, data = execute("SELECT * FROM users")
        print("\nWe found {} users in the database.".format(len(data)))

        if rows == 1 and len(data) == 1:
            if data[0]["tid"] is not None:
                print(
                    "The only user found is not the community user. By convention, "
                    "the community user has no Telegram ID (NULL)!"
                )
                ask_exit()

                community = create_community_user(community_balance, migration)

            else:

                if community_balance != data[0]["balance"]:
                    print("The balance of the community user in the database is {}.".format(data[0]["balance"]))
                    print("This seems to be wrong! Please check your config.")
                    ask_exit()

                community = transform_user_record(data[0], community_balance)

                print("Selecting the following community user:", community, sep = "\n")
                print("\nMake sure that this is ABSOLUTELY correct.\nDoing otherwise will break the data!\n")
                ask_exit()

        else:
            print("Make sure that you start with a fresh database.")
            print("Only the community user should exist!")
            print("Doing otherwise leads to unknown behavior!\n")
            ask_exit()

            community = detect_community()
            if community is not None:
                print("\nWe detected the following community user data:")
                community = transform_user_record(community)
                print(community)

            else:
                community = create_community_user(community_balance, migration)

        return community

    def make_reason_consume(r: str) -> str:
        return "consume: " + r

    def make_reason_pay(r: str) -> str:
        return r

    def make_reason_send() -> str:
        return "send: <no description>"

    def migrate_transactions(current_state, transaction_log):
        print("\nTransferring the transactions from the log file into the database...\n")
        sent = None
        failed = []
        communisms = []
        with open(transaction_log) as fd:
            for l in fd.readlines():
                tr = json.loads(l)

                t = None
                if tr["reason"] in ["drink", "ice", "water", "pizza"]:
                    t = MigratedTransaction(
                        find(tr["user"], current_state)["u"],
                        CommunityUser(),
                        -tr["diff"],
                        make_reason_consume(tr["reason"])
                    )

                elif tr["reason"].startswith("pay"):
                    t = MigratedTransaction(
                        CommunityUser(),
                        find(tr["user"], current_state)["u"],
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

        print("Completed import of old transactions.")

    def fix_init_balances(current_state, migration):
        print("\nCommitting initial transactions (using reason 'data migration')...")
        for user in current_state:
            if user["init"] > 0:
                t = MigratedTransaction(CommunityUser(), user["u"], abs(user["init"]), "data migration")
                t.commit()
                t.fix(migration)
            elif user["init"] < 0:
                t = MigratedTransaction(user["u"], CommunityUser(), abs(user["init"]), "data migration")
                t.commit()
                t.fix(migration)
        print("Completed initial balance fix.")

    def reset_community_balance(balance):
        db_balance = execute("SELECT balance FROM users WHERE id=%s", (CommunityUser().uid,))[1][0]["balance"]
        print("\nThe database stores a community's balance of {} for now.".format(db_balance))

        if db_balance != balance:
            print("We could reset this value to {} if you want.".format(balance))
            if ask_yes_no("Reset the community user's balance (Y) or let it untouched (N)? "):
                execute("UPDATE users SET balance=%s WHERE id=%s", (balance, CommunityUser().uid))

    def migrate_old_data(community_balance: int = None):
        print("\nMigrating old data...\n")
        if community_balance is None:
            community_balance = get_community_balance()

        state_path = get_path("state", "state.json", "state.json")
        log_path = get_path("transaction log", "transactions.log", "transactions.log")

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

        print("\nYou entered {} as community user balance.".format(community_balance))
        total = sum(u["balance"] for u in state)
        print("The sum of all users' balances is currently {}.".format(total))
        if total != -community_balance:
            print("Something seems to be wrong here! Please verify the data sets!")
            if ask_yes_no("Set the community user's balance to {} (Y) or not (N)? ".format(total)):
                community_balance = total
            else:
                print("This might be dangerous, but continuing with the value {}...".format(community_balance))
                ask_exit()

        print("\nCalculating the initial balance...")
        first_timestamp = get_first_ts_and_calc(state, log_path)

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

        verify_community_user_data(community_balance, migration)
        create_users_from_state(state, migration)
        create_user_objects(state)
        fix_init_balances(state, migration)
        migrate_transactions(state, log_path)
        reset_community_balance(community_balance)

        print("\nFinished data migration successfully.")
        return state, migration

    def start_new():
        migrate = ask_yes_no("Do you want to migrate your old data afterwards (Y) or not (N)? ")
        setup_freshly()

        com_user = create_community_user(
            get_community_balance(),
            datetime.datetime.now().replace(microsecond = 0)
        )
        print("You have just created the community user:", com_user, "", sep = "\n")

        if migrate:
            s, m = migrate_old_data(com_user["balance"])
            execute(
                "UPDATE users SET created=%s WHERE tid IS NULL AND id=%s",
                (m, CommunityUser().uid)
            )
        else:
            print("Finished setup.")
            exit(0)

    print(__doc__)

    print("Please make sure that your configuration was correctly set up before proceeding.\n")

    if ask_yes_no("Start with a fresh database (Y) or only migrate old data (N)? "):
        start_new()

    else:
        print(
            "\nNote: It is highly recommended to start with a fresh database.\n"
            "You can still import your old data afterwards. Do you really want\n"
            "to use an existing database (on your own risk)?\n"
        )

        if not ask_yes_no("Are you sure (Y) that you don't want to run the setup (N)? "):
            start_new()

        else:
            migrate_old_data()

    print("Exiting.")


if __name__ == "__main__":
    main()
else:
    raise ImportError("Do not import this script!")
