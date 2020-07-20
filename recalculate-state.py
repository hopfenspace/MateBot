import json
import sys

if len(sys.argv) != 4:
	print("Usage: recalculate-state.py <start state> <transactions> <start timestamp>")
	exit(0)

with open(sys.argv[1], "r") as fd:
	state = json.load(fd)

start = float(sys.argv[3])
with open(sys.argv[2], "r") as fd:
	for line in fd.readlines():
		entry = json.loads(line)

		if entry["timestamp"] > start:

			userId = str(entry["user"])

			if userId not in state:
				state[userId] = {
					"id": int(userId),
					"nick": "",
					"name": "",
					"balance": 0,
				}

			user = state[userId]
			user["balance"] += entry["diff"]

print(json.dumps(state))
