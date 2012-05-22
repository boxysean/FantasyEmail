import re
import yaml
import sys
import sqlite3
from datetime import datetime
from optparse import OptionParser
import time
import os

sys.path = sys.path + ["/Users/boxysean/Documents/workspace/riskyListy"]

from django.conf import settings
try:
	settings.configure(
	    DATABASE_ENGINE = 'django.db.backends.sqlite3',
	    DATABASE_NAME = os.path.join("..", 'db'),
	    DATABASE_USER = '',
	    DATABASE_PASSWORD = '',
	    DATABASE_HOST = '',
	    DATABASE_PORT = '',
	    TIME_ZONE = 'America/New_York',
	)
except:
	pass


from interface.models import *

def main():
	parser = OptionParser()
	parser.add_option("-i", "--ignore", action="store_true", default=False)
	parser.add_option("-f", "--follow", type="string", dest="follow_team_name", default=None)
	(options, args) = parser.parse_args()
	
	config = yaml.load(file("game.yaml"))
	
	conn = sqlite3.connect(config["db"])
	
	### fetch team transactions ###
	
	teams = list(Team.objects.all())
	
	for team in teams:
		team.stats = {}
		team.points = {}
		team.totalPoints = 0
		team.tidx = 0
		team.roster = {}
		team.rank = {}
		team.done = {}
		team.transactions = list(team.playertransaction_set.all())
	
	### calculate points for each team ###
	
	startDate = config["startDate"]
	endDate = config["endDate"]
	
	for emailPoint in EmailPoint.objects.all():
		email = emailPoint.email
	
		if startDate > email.timestamp or email.timestamp > endDate:
			continue
	
		print "[%s] %20s: %s" % (email.timestamp, email.emailer, email.subject)
	
		for team in teams:
			while team.tidx < len(team.transactions) and team.transactions[team.tidx].timestamp < email.timestamp:
				transaction = team.transactions[team.tidx]
				if team.name == options.follow_team_name:
					print "                                TT [team %20s] [emailer %20s] [add %s]" % (team.name[0:20], transaction.emailer.name[0:20], transaction.add)
				team.roster[transaction.emailer] = transaction.add
				team.tidx = team.tidx+1
	
			category = emailPoint.category
	
			if team.roster.has_key(emailPoint.awardTo) and team.roster[emailPoint.awardTo]:
				points = emailPoint.points
				if team.stats.has_key(category):
					team.stats[category] = team.stats[category] + points
				else:
					team.stats[category] = points
				if team.name == options.follow_team_name and points > 0:
					print "                                 + [team %20s] [emailer %20s] [category %20s]" % (team.name[0:20], emailPoint.awardTo.name[0:20], emailPoint.category.name[0:20])
	
	### calculate points for each team ###
	
	for category in Category.objects.all():
		for team in teams:
			if not team.points.has_key(category):
				team.points[category] = 0
			if not team.stats.has_key(category):
				team.stats[category] = 0
	
		s = sorted(teams, key=lambda team: team.stats[category], reverse=False)
	
		for i, team in reversed(list(enumerate(s))):
			team.rank[category] = i+1
	
		### O(n^2) is easiest! ###
	
		for i in range(len(s)):
			if s[i].done.has_key(category):
				continue
	
			avg = s[i].rank[category]
			count = 1.0
	
			for j in range(i+1, len(s)):
				if s[i].stats[category] == s[j].stats[category]:
					avg = avg + s[j].rank[category]
					count = count + 1
	
			for j in range(i, len(s)):
				if s[i].stats[category] == s[j].stats[category]:
					s[j].points[category] = avg / count
					s[j].done[category] = True
	
	for team in teams:
		team.totalPoints = sum(team.points[x] for x in team.points.keys())
		
	### find the winner!!! ###
	
	s = sorted(teams, key=lambda team: team.name)
	s = sorted(s, key=lambda team: team.totalPoints, reverse=True)
	
	### print the stats ###
	
	sys.stdout.write("%20s " % "")
	
	for category in Category.objects.all():
		sys.stdout.write("%8s " % category.name[0:8])
	
	sys.stdout.write("\n")
	
	for ss in s:
		sys.stdout.write("%20s " % ss.name)
		for category in Category.objects.all():
			sys.stdout.write("%8d " % (ss.stats[category] if ss.stats.has_key(category) else 0))
		sys.stdout.write("\n")
	
	### print the points ###
	
	sys.stdout.write("%20s " % "")
	
	for category in Category.objects.all():
		sys.stdout.write("%8s " % category.name[0:8])
	
	sys.stdout.write("%8s\n" % "Total")
	
	for ss in s:
		sys.stdout.write("%20s " % ss.name)
		for category in Category.objects.all():
			sys.stdout.write("%8.1f " % (ss.points[category] if ss.points.has_key(category) else 0))
		sys.stdout.write("%8.1f \n" % (ss.totalPoints))
	
	### put them in the database ###
	
	if options.ignore:
		print "WARNING: not inserted into database"
		sys.exit(0)
	
	c = conn.cursor()
	
	c.execute("delete from interface_teampoints")
	c.execute("delete from interface_teamstats")
	
	conn.commit()
	c.close()
	
	for team in s:
		for category in Category.objects.all():
			TeamPoints(team=team, category=category, points=team.points[category], total=0).save()
			TeamStats(team=team, category=category, stat=team.stats[category], total=0).save()
	

if __name__ == "__main__":
	main()

