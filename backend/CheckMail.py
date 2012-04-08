import mailbox
import mimetypes
import email
import re
import yaml
from datetime import timedelta, datetime
import time
import sys
import sqlite3

from Categories import *

### configs ###

config = yaml.load(file("config.yaml"))

conn = sqlite3.connect(config["sqlite_db"])

### functions to award email points ###

categories = [FreeFoodCategory, ThankYouCategory, GIFCategory, PraiseTheCreatorsCategory, ConversationStarterCategory]
categoriesInst = []

for category in categories:
	categoriesInst.append(category(conn))

def checkEmail(mail):
	for categoryInst in categoriesInst:
		categoryInst.check(mail)

### mailboxes ###

mconfig = config["mail"]
mbFiles = mconfig["mailbox_file"]

if type(mbFiles) != list:
	mbFiles = [mbFiles]

mbs = []

for mbFile in mbFiles:
	mb = mailbox.UnixMailbox(file(mbFile, "r"), email.message_from_file)
	mbs.append(mb)

### database ###

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

checked = {}

class Mail:
	replyFwdProg = re.compile("^\\s*(re|fwd)\\S*\\s*(.*)$", flags=re.IGNORECASE)
	emailProg = re.compile("[\w\-\.]+@\w[\w\-]+\.+[\w\-]+", flags=re.IGNORECASE)

	def __init__(self, msg):
		self.msg = msg
		self.subject = msg["subject"]
		self.initDate()


		self.toAddr = self.emailProg.search(msg["to"]).group(0)
		self.fromAddr = self.emailProg.search(msg["from"]).group(0)

		self.hasGif = None
		self.lines = None

	def initDate(self):
		timetuple = email.utils.parsedate_tz(self.msg["date"])
		self.timestamp = time.mktime(timetuple[0:9]) - timetuple[9]
		date = datetime.fromtimestamp(self.timestamp)
		self.datestr = date.strftime("%d/%m/%y %H:%M:%S")
#		print "subject %s timestamp %s date %s tz %d" % (self.subject, self.timestamp, self.msg["date"], timetuple[9])

	def getLines(self):
		if self.lines is None:
			self.lines = []
			for part in self.msg.walk():
				if part.get_content_type().lower() == "text/plain" and len(self.lines) == 0:
					payload = part.get_payload().splitlines()
					for line in payload:
						if re.search("^\\s*>", line):
							break
						else:
							self.lines.append(line)
		return self.lines

	def searchBody(self, p):
		return p.search(" ".join(self.getLines()))

	def hasAttachedGif(self):
		if self.hasGif is None:
			self.hasGif = False
			for part in self.msg.walk():
				if part.get_content_type().lower() == "image/gif":
					self.hasGif = True
					break

		return self.hasGif

	def getOriginalSubject(self):
		res = self.replyFwdProg.match(self.subject)
		if res:
			return res.group(2)
		else:
			return self.subject

	def isReplyFwd(self):
		return self.replyFwdProg.search(self.subject)

for mb in mbs:
	lastDay = ""

	for msg in mb:
		toMatches = re.search(mconfig["list_address"], msg["to"])

		if not toMatches:
			msg = mb.next()
			continue

		mail = Mail(msg)

		### remove duplicate messages, which happen in my mailbox :( ###

		key = (mail.subject, mail.fromAddr, mail.timestamp)

		if checked.has_key(key):
			msg = mb.next()
			del checked[key]
			continue
		else:
			checked[key] = 1

		date = datetime.fromtimestamp(mail.timestamp)
		dateDay = date.strftime("%d/%m/%Y")

		if not lastDay:
			lastDay = dateDay
		if lastDay != dateDay:
			lastDay = dateDay
			print dateDay

		print "%30s / %20s / %30s" % (mail.fromAddr[0:30], mail.subject[0:20], mail.datestr[0:30])

		checkEmail(mail)

conn.close()

