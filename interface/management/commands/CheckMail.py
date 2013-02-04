import re
import yaml
from datetime import timedelta, datetime, date
import sqlite3
import sys

from Categories import *
from Mail import *

import os

from django.conf import settings

from django.core.management.base import BaseCommand, CommandError, make_option

from interface.models import *

import pytz as tz

class Command(BaseCommand):
  help = "whatever"

  def handle(self, *args, **options):
    ### set up mailboxes ###
  
    mailboxes = Mailboxes()
  
    config = yaml.load(open("game.yaml"))

    startDate = config.get("startDate", None)
    endDate = config.get("endDate", None)

    timezone = tz.timezone(config.get("timezone", "UTC"))

    if startDate:
      startDate = timezone.localize(startDate)
  
    if endDate:
      endDate = timezone.localize(endDate)

    for mailboxDef in config["mailboxes"]:
      if mailboxDef["type"] == "UnixMailbox":
        mbFile = mailboxDef["file"]
        mbListAddress = mailboxDef["listAddress"]
        mailboxes.add(UnixMailbox(mbFile, re.compile(mbListAddress), startDate, endDate))
  
    ### read mails ###
  
    conn = sqlite3.connect(config["db"])
  
    c = conn.cursor()
  
    c.execute("drop table if exists conversation")
    c.execute("drop index if exists conversation_subject")
  
    c.execute("""create table if not exists conversation (
        timestamp datetime not null,
        mailfrom char(128) not null,
        subject char(128) not null
    )""")

    c.execute("create index if not exists conversation_subject on conversation (subject, timestamp)")

    # delete Email objects manually because django sometimes pukes if done through orm

    c.execute("delete from interface_email;")

    conn.commit()
    c.close()

    EmailPoint.objects.all().delete()
  
    for mail in mailboxes.getMail():
      self.checkEmail(mail, conn)
  
    conn.close()

  def checkEmail(self, mail, conn):
    if mail.checked():
      return

    mail.insert()

    print "== SUBJECT:", mail.subject

    for categoryInst in self.categoriesInst:
      res = categoryInst.check(mail)
      print "%s: %s" % (categoryInst.catName, res)

  def __init__(self):
    config = yaml.load(file("game.yaml"))
    conn = sqlite3.connect(config["db"])
    
    print "Checking mail for %s" % (config["name"])
    
    ### functions to award email points ###

    self.categoriesInst = []

    for category in Category.objects.all():
      # Use reflection in the Categories.py to dynamically load the class
      # and extract its name
      mod = __import__("interface.management.commands.Categories", fromlist=[category.className])
      category = getattr(mod, category.className)
      self.categoriesInst.append(category(conn))

