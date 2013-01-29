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

class Command(BaseCommand):
  help = "whatever"

  def handle(self, *args, **options):
    ### set up mailboxes ###
  
    mailboxes = Mailboxes()
  
    config = yaml.load(file("game.yaml"))

    startDate = config.get("startDate", None)
    endDate = config.get("endDate", None)
  
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

    conn.commit()
    c.close()
  
    EmailPoint.objects.all().delete()
    Email.objects.all().delete()
  
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

    categories = [ConversationStarterCategory, FreeFoodCategory, GIFCategory, PraiseTheCreatorsCategory, ThankYouCategory]
    self.categoriesInst = []

    for category in categories:
      self.categoriesInst.append(category(conn))


