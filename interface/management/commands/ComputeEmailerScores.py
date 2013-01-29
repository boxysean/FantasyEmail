import re
import yaml
from datetime import timedelta, datetime
import time
import sys
import sqlite3
import os

from django.core.management.base import BaseCommand, CommandError, make_option

from interface.models import *

class Command(BaseCommand):
  help = "whatever"

  def handle(self, *args, **options):
    config = yaml.load(file("game.yaml"))
    
    ### calculate points for each emailer ###
    
    emailers = list(Emailer.objects.all())
    
    for emailer in emailers:
      emailer.stats = {}
      for category in Category.objects.all():
        emailer.stats[category] = 0
        for email in EmailPoint.objects.filter(awardTo=emailer, category=category):
          emailer.stats[category] = emailer.stats[category] + email.points
    
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
    
    for emailer in s:
      for category in Category.objects.all():
        EmailerStats(emailer=emailer, category=category, stat=emailer.stats[category], total=0).save()
