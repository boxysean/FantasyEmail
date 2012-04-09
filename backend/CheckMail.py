import re
import yaml
from datetime import timedelta, datetime, date
import sqlite3

#!!! apparently this is not the right way to import
from Categories import *
from Mail import *

### configs ###

config = yaml.load(file("game.yaml"))

print "Checking mail for %s" % (config["name"])

conn = sqlite3.connect(config["db"])

### functions to award email points ###

categories = [FreeFoodCategory, ThankYouCategory, GIFCategory, PraiseTheCreatorsCategory, ConversationStarterCategory]
categoriesInst = []

for category in categories:
	categoriesInst.append(category(conn))

def checkEmail(mail):
	for categoryInst in categoriesInst:
		categoryInst.check(mail)

### set up mailboxes ###

mailboxes = Mailboxes()

for mailboxDef in config["mailboxes"]:
	if mailboxDef["type"] == "UnixMailbox":
		mbFile = mailboxDef["file"]
		mbListAddress = mailboxDef["listAddress"]
		mailboxes.add(UnixMailbox(mbFile, re.compile(mbListAddress)))

### database store of points ###

c = conn.cursor()

c.execute("drop table if exists email_points")
c.execute("drop index if exists email_points_master")

c.execute("""
    create table if not exists email_points (
        id int primary key,
        timestamp datetime not null, 
        mailfrom char(128) not null,
        subject char(128) not null,
        category int not null,
        points int not null,
        awardTo int not null references "interface_emailer" ("id")
    )
""")

c.execute("create index if not exists email_points_awardTo on email_points (awardTo)")
c.execute("create unique index if not exists email_points_master on email_points (timestamp, mailfrom, subject, category)")

c.execute("drop table if exists conversation")
c.execute("drop index if exists conversation_subject")

c.execute("""
    create table if not exists conversation (
        timestamp datetime not null,
        mailfrom char(128) not null,
        subject char(128) not null
    )
""")

c.execute("create index if not exists conversation_subject on conversation (subject, timestamp)")

conn.commit()
c.close()

### read mails ###

for mail in mailboxes.getMail():
	checkEmail(mail)

conn.close()

