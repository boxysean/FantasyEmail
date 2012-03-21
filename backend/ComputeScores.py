import re
import yaml
import sys
import sqlite3
from datetime import datetime
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-i", "--ignore", action="store_true", default=False)
(options, args) = parser.parse_args()

config = yaml.load(file("config.yaml"))

conn = sqlite3.connect(config["sqlite_db"])

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
c.execute("select id, name from interface_category where total != 1")
category_id_to_name = {}
for row in c: category_id_to_name[row[0]] = row[1]
c.execute("select id from interface_category where total == 1 limit 1")
for row in c: category_total_id = row[0]
c.close()

### fetch team transactions ###

for team in teams:
	c = conn.cursor()
	c.execute("select timestamp, emailer_id, points from interface_playertransaction where team_id = ? order by timestamp", (team["id"],))
	team["transactions"] = [{"timestamp": row[0], "emailer_id": row[1], "points": row[2]} for row in c]
	c.close()

	team["score"] = {}
	team["points"] = {}
	team["totalScore"] = 0
	team["totalPoints"] = 0
	team["tidx"] = 0
	team["roster"] = {}

### calculate points for each team ###

startDate = "2012-03-20 15:00:00"

for email in emails:
	if startDate > email["timestamp"]:
		continue

	print "[%s] %20s: %s" % (email["timestamp"], email["from"][0:20], email["subject"])

	for team in teams:
		transactions = team["transactions"]
		while team["tidx"] < len(transactions) and transactions[team["tidx"]]["timestamp"][:-7] < email["timestamp"]:
			team["roster"][transactions[team["tidx"]]["emailer_id"]] = transactions[team["tidx"]]["points"]
			team["tidx"] = team["tidx"]+1

		category = email["category"]

		if team["roster"].has_key(email["awardTo"]):
			points = team["roster"][email["awardTo"]] * email["points"]
			if team["points"].has_key(category):
				team["points"][category] = team["points"][category] + points
			else:
				team["points"][category] = points
			print "                                 + [team %20s] [emailer %20s] [category %20s]" % (team["name"][0:20], id_to_email_dict[email["awardTo"]][0:20], category_id_to_name[email["category"]][0:20])
			team["totalPoints"] = team["totalPoints"] + points

### calculate score for each team ###

for category_id in category_id_to_name.keys():
	for team in teams:
		if not team["points"].has_key(category_id):
			team["points"][category_id] = 0

	s = sorted(teams, key=lambda team: team["points"][category_id], reverse=True)
	lastScore = -1
	lastPoints = -1
	for i, team in enumerate(s):
		j = len(teams)-i
		if team["points"][category_id] == 0:
			team["score"][category_id] = 0
		elif team["points"][category_id] == lastPoints:
			team["score"][category_id] = lastScore
			team["totalScore"] = team["totalScore"] + lastScore
		else:
			team["score"][category_id] = j
			team["totalScore"] = team["totalScore"] + j
			lastPoints = team["points"][category_id]
			lastScore = j

### find the winner!!! ###

s = sorted(teams, key=lambda team: team["user"])
s = sorted(s, key=lambda team: team["totalPoints"], reverse=True)
s = sorted(s, key=lambda team: team["totalScore"], reverse=True)

print "%20s %8s %8s %8s %8s %8s %8s" % ("", category_id_to_name[2][0:8], category_id_to_name[3][0:8], category_id_to_name[4][0:8], category_id_to_name[5][0:8], category_id_to_name[6][0:8], "Total")

for ss in s:
	print "%20s %8s %8s %8s %8s %8s %8s" % (ss["name"], ss["score"][2], ss["score"][3], ss["score"][4], ss["score"][5], ss["score"][6], ss["totalScore"])

### put them in the database ###

if options.ignore:
	print "WARNING: not inserted into database"
	sys.exit(0)

c = conn.cursor()

c.execute("delete from interface_teampoints")
c.execute("delete from interface_teamscore")

for team in s:
	for category_id in category_id_to_name.keys():
		c.execute("insert into interface_teampoints (team_id, category_id, points, total) values (?, ?, ?, ?)", (team["id"], category_id, team["points"][category_id], 0))
		c.execute("insert into interface_teamscore (team_id, category_id, score, total) values (?, ?, ?, ?)", (team["id"], category_id, team["score"][category_id], 0))

	c.execute("insert into interface_teampoints (team_id, category_id, points, total) values (?, ?, ?, ?)", (team["id"], category_total_id, team["totalPoints"], 1))
	c.execute("insert into interface_teamscore (team_id, category_id, score, total) values (?, ?, ?, ?)", (team["id"], category_total_id, team["totalScore"], 1))

conn.commit()
c.close()

