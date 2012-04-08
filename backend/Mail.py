import mailbox
import email
import re
from datetime import datetime
import time

### mailboxes ###

class Mailboxes:
	mailboxes = []
	
	def add(self, mailbox):
		self.mailboxes.append(mailbox)

	def getMail(self, since=None):
		res = []
		for mailbox in self.mailboxes:
			print "adding mailbox %s" % mailbox
			res = res + mailbox.getMail(since)

		res = sorted(set(res), key=lambda mail: mail.timestamp)
		return res

class Mailbox:
	msgs = []

	def getMail(self, since=None):
		if since:
			return filter(lambda m: m.timestamp >= since)
		else:
			return self.msgs

class UnixMailbox(Mailbox):
	mbFile = ""

	def __init__(self, mbFile, listAddrProg):
		self.mbFile = mbFile
		mb = mailbox.UnixMailbox(file(mbFile, "r"), email.message_from_file)
		checked = set()
		for msg in mb:
			if not listAddrProg.search(msg["to"]):
				continue

			mail = Mail(msg)

			### my mailing list sends me duplicate messages :( ###

			key = (mail.subject, mail.fromAddr, mail.timestamp)

			if key in checked:
				checked.remove(key)
			else:
				checked.add(key)
				self.msgs.append(mail)

	def __repr__(self):
		return "Unix Mailbox (%s)" % (self.mbFile)

class GmailMailbox(Mailbox):
	pass

class ImapMailbox(Mailbox):
	pass

### Mail ###

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

	def __str__(self):
		return "%30s / %30s / %20s" % (self.fromAddr[0:30], self.subject[0:30], self.datestr[0:20])

	def __hash__(self):
		res = self.subject.__hash__()
		res = int(res * 31 + self.fromAddr.__hash__())
		res = int(res * 31 + self.timestamp.__hash__())
		return res

	def __eq__(self, o):
		return self.subject == o.subject and self.fromAddr == o.fromAddr and self.timestamp == o.timestamp

