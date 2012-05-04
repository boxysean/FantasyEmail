import re
import yaml
from datetime import timedelta, datetime, date
import sqlite3

#!!! apparently this is not the right way to import
from Categories import *
from Mail import *

### configs ###

class AwardPoints:
	def checkEmail(self, mail, conn):
		mail.insert(conn, "emails")
		for categoryInst in self.categoriesInst:
			res = categoryInst.check(mail)
#			print "%s: %s" % (categoryInst.catName, res)

	def __init__(self, conn):
		self.conn = conn

		config = yaml.load(file("game.yaml"))
		
		print "Checking mail for %s" % (config["name"])
		
		### functions to award email points ###

		categories = [ConversationStarterCategory, LateNightCategory, LastReplyCategory, OneWordCategory]
		self.categoriesInst = []

		for category in categories:
			self.categoriesInst.append(category(conn))

		### database store of points ###

		c = conn.cursor()

		c.execute("""create table if not exists email_points (
        id int primary key,
        timestamp datetime not null, 
        mailfrom char(128) not null,
        subject char(128) not null,
        sanitizedSubject char(128) not null,
        category int not null,
        points int not null,
        awardTo int not null references "interface_emailer" ("id")
    )""")

		c.execute("create index if not exists email_points_awardTo on email_points (awardTo)")
		c.execute("create unique index if not exists email_points_master on email_points (timestamp, mailfrom, subject, category)")

		c.execute("""create table if not exists conversation (
        timestamp datetime not null,
        mailfrom char(128) not null,
        subject char(128) not null
    )""")

		c.execute("create index if not exists conversation_subject on conversation (subject, timestamp)")

		c.execute("""create table if not exists emails (
        timestamp datetime not null,
        mailfrom char(128) not null,
        subject char(128) not null,
        sanitizedSubject char(128) not null
    )""")

		c.execute("create index if not exists emails_timestamp on emails (timestamp)")

		conn.commit()
		c.close()

if __name__ == "__main__":
	### set up mailboxes ###

	mailboxes = Mailboxes()

	config = yaml.load(file("game.yaml"))

	for mailboxDef in config["mailboxes"]:
		if mailboxDef["type"] == "UnixMailbox":
			mbFile = mailboxDef["file"]
			mbListAddress = mailboxDef["listAddress"]
			mailboxes.add(UnixMailbox(mbFile, re.compile(mbListAddress)))

	### read mails ###

	conn = sqlite3.connect(config["db"])

	c = conn.cursor()

	c.execute("drop table if exists email_points")
	c.execute("drop index if exists email_points_master")

	c.execute("drop table if exists conversation")
	c.execute("drop index if exists conversation_subject")

	c.execute("drop table if exists emails")
	c.execute("drop index if exists emails_timestamp")

	conn.commit()
	c.close()

	ap = AwardPoints(conn)

	for mail in mailboxes.getMail():
#		print mail.subject
		ap.checkEmail(mail, conn)

	conn.close()

