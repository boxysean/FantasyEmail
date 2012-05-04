import re
import yaml
import sys
import sqlite3
from datetime import datetime
from optparse import OptionParser
import time

parser = OptionParser()
parser.add_option("-i", "--ignore", action="store_true", default=False)
parser.add_option("-f", "--follow", type="string", dest="follow_team_name", default=None)
(options, args) = parser.parse_args()

config = yaml.load(file("game.yaml"))

conn = sqlite3.connect(config["db"])

### fetch teams ###

c = conn.cursor()
c.execute("select t.id, t.name, u.username from interface_team t inner join auth_user u on (t.user_id = u.id)")
teams = [{"id": row[0], "name": row[1], "user": row[2]} for row in c]
c.close()

### fetch emails ###

c = conn.cursor()
c.execute("select timestamp, awardTo, category, points, subject, mailfrom from email_points order by timestamp")
emails = [{"timestamp": row[0], "awardTo": row[1], "category": row[2], "points": row[3], "subject": row[4], "from": row[5]} for row in c]
c.close()

### construct email to emailer_id map ###

c = conn.cursor()
c.execute("select emailAddress, emailer_id from interface_emailaddress")
email_to_id_dict = {}
id_to_email_dict = {}
for row in c:
	email_to_id_dict[row[0]] = row[1]
	id_to_email_dict[row[1]] = row[0]
c.close()

### construct category to id map ###

c = conn.cursor()
c.execute("select id, name from interface_category")
category_id_to_name = {}
for row in c: category_id_to_name[row[0]] = row[1]
c.close()

### fetch team transactions ###

for team in teams:
	c = conn.cursor()
	c.execute("select timestamp, emailer_id, `add` from interface_playertransaction where team_id = ? order by timestamp", (team["id"],))
	team["transactions"] = [{"timestamp": row[0], "emailer_id": row[1], "add": row[2]} for row in c]
	c.close()

	team["stats"] = {}
	team["points"] = {}
	team["totalPoints"] = 0
	team["tidx"] = 0
	team["roster"] = {}
	team["rank"] = {}
	team["done"] = {}

### calculate points for each team ###

startDate = time.mktime(config["startDate"].timetuple())
endDate = time.mktime(config["endDate"].timetuple())

for email in emails:
	if startDate > email["timestamp"] or email["timestamp"] > endDate:
		continue

	print "[%s] %20s: %s" % (email["timestamp"], email["from"][0:20], email["subject"])

	for team in teams:
		transactions = team["transactions"]
		if team["tidx"] < len(transactions):
			transaction_dt = datetime.strptime(transactions[team["tidx"]]["timestamp"], "%Y-%m-%d %H:%M:%S")
			transaction_time = time.mktime(transaction_dt.timetuple())
			while team["tidx"] < len(transactions) and transaction_time < email["timestamp"]:
				if team["name"] == options.follow_team_name:
					print "                                TT [team %20s] [emailer %20s] [add %s]" % (team["name"][0:20], id_to_email_dict[transactions[team["tidx"]]["emailer_id"]][0:20], transactions[team["tidx"]]["add"])
				team["roster"][transactions[team["tidx"]]["emailer_id"]] = transactions[team["tidx"]]["add"]
				team["tidx"] = team["tidx"]+1

		category = email["category"]

		if team["roster"].has_key(email["awardTo"]) and team["roster"][email["awardTo"]]:
			points = email["points"]
			if team["stats"].has_key(category):
				team["stats"][category] = team["stats"][category] + points
			else:
				team["stats"][category] = points
			if team["name"] == options.follow_team_name and points > 0:
				print "                                 + [team %20s] [emailer %20s] [category %20s]" % (team["name"][0:20], id_to_email_dict[email["awardTo"]][0:20], category_id_to_name[email["category"]][0:20])

### calculate points for each team ###

for category_id in category_id_to_name.keys():
	for team in teams:
		if not team["points"].has_key(category_id):
			team["points"][category_id] = 0
		if not team["stats"].has_key(category_id):
			team["stats"][category_id] = 0

	s = sorted(teams, key=lambda team: team["stats"][category_id], reverse=False)

	for i, team in reversed(list(enumerate(s))):
		team["rank"][category_id] = i+1

	### O(n^2) is easiest! ###

	for i in range(len(s)):
		if s[i]["done"].has_key(category_id):
			continue

		avg = s[i]["rank"][category_id]
		count = 1.0

		for j in range(i+1, len(s)):
			if s[i]["stats"][category_id] == s[j]["stats"][category_id]:
				avg = avg + s[j]["rank"][category_id]
				count = count + 1

		for j in range(i, len(s)):
			if s[i]["stats"][category_id] == s[j]["stats"][category_id]:
				s[j]["points"][category_id] = avg / count
				s[j]["done"][category_id] = True

for team in teams:
	team["totalPoints"] = sum(team["points"][x] for x in team["points"].keys())
	
### find the winner!!! ###

s = sorted(teams, key=lambda team: team["user"])
s = sorted(s, key=lambda team: team["totalPoints"], reverse=True)

### print the stats ###

sys.stdout.write("%20s " % "")

for i in category_id_to_name.keys():
	sys.stdout.write("%8s " % category_id_to_name[i][0:8])

sys.stdout.write("\n")

for ss in s:
	sys.stdout.write("%20s " % ss["name"])
	for i in category_id_to_name.keys():
		sys.stdout.write("%8d " % (ss["stats"][i] if ss["stats"].has_key(i) else 0))
	sys.stdout.write("\n")

### print the points ###

sys.stdout.write("%20s " % "")

for i in category_id_to_name.keys():
	sys.stdout.write("%8s " % category_id_to_name[i][0:8])

sys.stdout.write("%8s\n" % "Total")

for ss in s:
	sys.stdout.write("%20s " % ss["name"])
	for i in category_id_to_name.keys():
		sys.stdout.write("%8.1f " % (ss["points"][i] if ss["points"].has_key(i) else 0))
	sys.stdout.write("%8.1f \n" % (ss["totalPoints"]))

### put them in the database ###

if options.ignore:
	print "WARNING: not inserted into database"
	sys.exit(0)

c = conn.cursor()

c.execute("delete from interface_teampoints")
c.execute("delete from interface_teamstats")

for team in s:
	for category_id in category_id_to_name.keys():
		c.execute("insert into interface_teampoints (team_id, category_id, points, total) values (?, ?, ?, ?)", (team["id"], category_id, team["points"][category_id], 0))
		c.execute("insert into interface_teamstats (team_id, category_id, stat, total) values (?, ?, ?, ?)", (team["id"], category_id, team["stats"][category_id], 0))

conn.commit()
c.close()

