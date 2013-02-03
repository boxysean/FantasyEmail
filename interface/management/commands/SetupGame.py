import re
import yaml
from datetime import timedelta, datetime, date
import sqlite3
import sys

from Mail import *

import os

from django.conf import settings

from django.core.management.base import BaseCommand, CommandError, make_option

from django.contrib.auth.models import User

from interface.models import *

class Command(BaseCommand):
  help = "whatever"

  def handle(self, *args, **options):
    config = yaml.load(open("game.yaml"))

    self.buildCategories(config)
    self.createPlayerAccounts(config)

  def buildCategories(self, config):
    Category.objects.all().delete()

    for categoryName in config["categories"]:
      # Use reflection in the Categories.py to dynamically load the class
      # and extract its name
      mod = __import__("interface.management.commands.Categories", fromlist=[categoryName])
      category = getattr(mod, categoryName)
      Category.objects.create(name=category.catName, description=category.catName, className=categoryName)

  def createPlayerAccounts(self, config):
    Team.objects.all().delete()
    User.objects.all().delete()

    for player in config["players"]:
      user = User.objects.create_user(player["email"], player["email"], "fantasy")
      emailer = Emailer.objects.create(name=player["name"], user=user)
      emailAddress = EmailAddress.objects.create(emailer=emailer, emailAddress=player["email"])
      team = Team.objects.create(name=player["team"], user=user, icon=player["image"])

