import re
import yaml
from datetime import timedelta, datetime
import time
import sys
import sqlite3
import os

from copy import deepcopy

from django.core.management.base import BaseCommand, CommandError, make_option

from interface.models import *

def moduloDay(t):
  return t - timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond)

class Command(BaseCommand):
  help = "whatever"

  def handle(self, *args, **options):
    config = yaml.load(file("game.yaml"))

    ### calculate points for each emailer ###
    
    emailers = list(Emailer.objects.all())

    latestDate = moduloDay(EmailPoint.objects.all().order_by("-email__timestamp")[0].email.timestamp)

    for emailer in emailers:
      emailer.stats = {}
      emailer.history = {}
      for category in Category.objects.all():
        emailer.stats[category] = 0
        emailer.history[category] = {}
        historyDate = moduloDay(config["startDate"])
        historyEndDate = moduloDay(config["endDate"])
        lastStat = 0

        for email in EmailPoint.objects.filter(awardTo=emailer, category=category).order_by("email__timestamp"):
          # get the day of the email
          t = moduloDay(email.email.timestamp)
          while historyDate < t:
            emailer.history[category][historyDate] = emailer.stats[category]
            historyDate += timedelta(days=1)
          emailer.stats[category] = emailer.stats[category] + email.points
          lastStat = emailer.stats[category]

        while historyDate <= latestDate:
          emailer.history[category][historyDate] = lastStat
          historyDate += timedelta(days=1)

        # save the stats in a database
        EmailerStats(emailer=emailer, category=category, stat=emailer.stats[category]).save()

        # fill in the days that are missing
    
    s = sorted(emailers, key=lambda emailer: emailer.name)
    
    ### print the stats ###
    
    sys.stdout.write("%30s " % "")
    
    for category in Category.objects.all():
      sys.stdout.write("%8s " % category.name[0:8])
    
    sys.stdout.write("\n")
    
    for ss in s:
      sys.stdout.write("%30s " % ss.name)
      for category in Category.objects.all():
        sys.stdout.write("%8d " % (ss.stats[category] if ss.stats.has_key(category) else 0))
      sys.stdout.write("\n")
    
    ### put them in the database ###
    
    EmailerStats.objects.all().delete()
    EmailerStatsHistory.objects.all().delete()

    date = moduloDay(config["startDate"])
    gameDates = []

    while date <= latestDate:
      gameDates.append(deepcopy(date))
      date = date + timedelta(days=1)
    
    for emailer in s:
      for category in Category.objects.all():
        EmailerStats(emailer=emailer, category=category, stat=emailer.stats[category]).save()
        for date in gameDates:
          EmailerStatsHistory(emailer=emailer, category=category, stat=emailer.history[category][date], timestamp=date).save()
