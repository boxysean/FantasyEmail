import re
import yaml
from datetime import timedelta, datetime, date
import sqlite3

#!!! apparently this is not the right way to import
from Categories import *
from Mail import *

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

### configs ###

class AwardPoints:
	def checkEmail(self, mail, conn):
		mail.insert()
		for categoryInst in self.categoriesInst:
			res = categoryInst.check(mail)
#			print "%s: %s" % (categoryInst.catName, res)

	def __init__(self, conn):
		self.conn = conn

		config = yaml.load(file("game.yaml"))
		
		print "Checking mail for %s" % (config["name"])
		
		### functions to award email points ###

#		categories = [ConversationStarterCategory, LateNightCategory, LastReplyCategory, OneWordCategory]
		categories = [ProfessionalCategory, LateNightCategory, PassingGradeCategory, OneWordCategory]
		self.categoriesInst = []

		for category in categories:
			self.categoriesInst.append(category(conn))

		### database store of points ###

		c = conn.cursor()

		c.execute("""create table if not exists conversation (
        timestamp datetime not null,
        mailfrom char(128) not null,
        subject char(128) not null
    )""")

		c.execute("create index if not exists conversation_subject on conversation (subject, timestamp)")

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

	c.execute("drop table if exists conversation")
	c.execute("drop index if exists conversation_subject")

	c.execute("delete from interface_emailpoint")
	c.execute("delete from interface_email")

	conn.commit()
	c.close()

	ap = AwardPoints(conn)

	for mail in mailboxes.getMail():
#		print mail.subject
		ap.checkEmail(mail, conn)

	conn.close()

