import re
import yaml
import sys
import sqlite3
from datetime import datetime, timedelta
from optparse import OptionParser
import time
import os
from copy import deepcopy

from django.conf import settings

from interface.models import *

from django.core.management.base import BaseCommand, CommandError, make_option

from django.core.exceptions import ObjectDoesNotExist

def moduloDay(t):
  return t - timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond)

class Command(BaseCommand):

  option_list = BaseCommand.option_list + (
      make_option("-i", "--ignore",
        action="store_true",
        dest="ignore",
        default=False,
        help="Don't actually add these to the database"),
      
      make_option("-f", "--follow",
        type="string",
        dest="follow_team_name",
        default=None,
        help="Follow a particular team and give information about it")
      )

  def calculatePoints(self, categories, teams):
    for category in categories:
      for team in teams:
        if not team.points.has_key(category):
          team.points[category] = 0
        if not team.stats.has_key(category):
          team.stats[category] = 0
        team.done.clear()
    
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
 
  def handle(self, *args, **options):
    config = yaml.load(file("game.yaml"))
    
    ### fetch team transactions ###
    
    teams = list(Team.objects.all())
    categories = list(Category.objects.all())

    for team in teams:
      team.stats = {}
      team.points = {}
      team.totalPoints = 0
      team.tidx = 0
      team.roster = {}
      team.rank = {}
      team.done = {}
      team.transactions = list(team.playertransaction_set.all())
      team.statsHistory = {}
      team.pointsHistory = {}
      for category in categories:
        team.statsHistory[category] = {}
        team.pointsHistory[category] = {}
      try:
        x = len(team.transactions)
      except ObjectDoesNotExist:
        team.transactions = []
      except IndexError:
        team.transactions = []

    ### calculate stats for each team ###
    
    startDate = config["startDate"]
    endDate = config["endDate"]

    historyDate = moduloDay(config["startDate"])
    latestDate = moduloDay(EmailPoint.objects.all().order_by("-email__timestamp")[0].email.timestamp)

    for emailPoint in EmailPoint.objects.all():
      email = emailPoint.email

      if startDate > email.timestamp or email.timestamp > endDate:
        continue

      # make a historical note of each team
      t = moduloDay(email.timestamp)

      if historyDate < t:
        self.calculatePoints(categories, teams)

      while historyDate < t:
        for team in teams:
          for category in categories:
            team.pointsHistory[category][historyDate] = team.points.get(category, 0)
            team.statsHistory[category][historyDate] = team.stats.get(category, 0)
        historyDate += timedelta(days=1)
   
#      print "[%s] %20s: %s" % (email.timestamp, email.emailer, email.subject)
    
      for team in teams:
#        print "TEAM %s" % team.name
        while team.tidx < len(team.transactions) and team.transactions[team.tidx].timestamp < email.timestamp:
          transaction = team.transactions[team.tidx]
          if team.name == options["follow_team_name"]:
            print "                                TT [team %20s] [emailer %20s] [add %s]" % (team.name[0:20], transaction.emailer.name[0:20], transaction.add)

          team.roster[transaction.emailer] = transaction.add
          team.tidx = team.tidx+1
    
        category = emailPoint.category
    
        if team.roster.has_key(emailPoint.awardTo) and team.roster[emailPoint.awardTo]:
          points = emailPoint.points
          team.stats[category] = team.stats.get(category, 0) + points
          if team.name == options["follow_team_name"] and points > 0:
            print "                                 + [team %20s] [emailer %20s] [category %20s]" % (team.name[0:20], emailPoint.awardTo.name[0:20], emailPoint.category.name[0:20])

    ### calculate points for each team ###
    
    self.calculatePoints(categories, teams)

    while historyDate <= latestDate:
      for team in teams:
        for category in categories:
          team.pointsHistory[category][historyDate] = team.points.get(category, 0)
          team.statsHistory[category][historyDate] = team.stats.get(category, 0)
      historyDate += timedelta(days=1)
    
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
    
    if options["ignore"]:
      print "WARNING: not inserted into database"
      sys.exit(0)
  
    TeamPoints.objects.all().delete()
    TeamPointsHistory.objects.all().delete()
    TeamStats.objects.all().delete()
    TeamStatsHistory.objects.all().delete()

    date = moduloDay(config["startDate"])
    gameDates = []

    while date <= latestDate:
      gameDates.append(deepcopy(date))
      date = date + timedelta(days=1)
    
    for team in s:
      for category in categories:
        TeamPoints(team=team, category=category, points=team.points[category]).save()
        TeamStats(team=team, category=category, stat=team.stats[category]).save()
        for date in gameDates:
          TeamPointsHistory(team=team, category=category, points=team.pointsHistory[category][date], timestamp=date).save()
          TeamStatsHistory(team=team, category=category, stat=team.statsHistory[category][date], timestamp=date).save()

