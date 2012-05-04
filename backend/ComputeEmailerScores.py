import re
import yaml
from datetime import timedelta, datetime
import time
import sys
import sqlite3

config = yaml.load(file("game.yaml"))

conn = sqlite3.connect(config["db"])

### fetch emails ###

c = conn.cursor()
c.execute("select timestamp, awardTo, category, points from email_points order by timestamp")
emails = [{"timestamp": row[0], "awardTo": row[1], "category": row[2], "points": row[3]} for row in c]
c.close()

### fetch emailers ###

c = conn.cursor()
c.execute("select id, name from interface_emailer")
emailers = [{"id": row[0], "name": row[1]} for row in c]
c.close()

### construct category to id map ###

c = conn.cursor()
c.execute("select id, name from interface_category")
category_id_to_name = {}
for row in c: category_id_to_name[row[0]] = row[1]
c.close()

### calculate points for each emailer ###

for emailer in emailers:
	emailer["stats"] = {}
	for category_id in category_id_to_name.keys():
		emailer["stats"][category_id] = 0
		for email in filter(lambda email: email["awardTo"] == emailer["id"] and email["category"] == category_id, emails):
			emailer["stats"][category_id] = emailer["stats"][category_id] + email["points"]

### find the winner!!! ###

s = sorted(emailers, key=lambda emailer: emailer["name"])

### print the stats ###

sys.stdout.write("%30s " % "")

for i in category_id_to_name.keys():
	sys.stdout.write("%8s " % category_id_to_name[i][0:8])

sys.stdout.write("\n")

for ss in s:
	sys.stdout.write("%30s " % ss["name"])
	for i in category_id_to_name.keys():
		sys.stdout.write("%8d " % (ss["stats"][i] if ss["stats"].has_key(i) else 0))
	sys.stdout.write("\n")

### put them in the database ###

c = conn.cursor()

c.execute("delete from interface_emailerstats")

for emailer in s:
	for category_id in category_id_to_name.keys():
		c.execute("insert into interface_emailerstats (emailer_id, category_id, stat, total) values (?, ?, ?, ?)", (emailer["id"], category_id, emailer["stats"][category_id], 0))

conn.commit()
c.close()

