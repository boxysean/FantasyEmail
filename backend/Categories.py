import re
import sqlite3

class Category:
	idMap = {}

	def __init__(self, dbc):
		self.dbc = dbc
		self.catId = Category.getId(self.catName, dbc)
	
	@staticmethod
	def getId(desc, dbc):
		if not len(Category.idMap):
			c = dbc.cursor()
			c.execute("select id, name from interface_category where total != 1")
			for row in c:
				Category.idMap[row[1].__str__()] = row[0]
			c.close()

		return Category.idMap[desc]

	def award(self, mail, category, points, awardTo=""):
		if not len(awardTo):
			awardTo = mail.fromAddr
		c = self.dbc.cursor()
		c.execute("select emailer_id from interface_emailaddress where realEmail = ?", (awardTo,))
		awardToId = -1
		for res in c:
			awardToId = res[0]

		if awardToId >= 0:
			c.execute("insert into email_points (timestamp, mailfrom, subject, category, points, awardto) values (?, ?, ?, ?, ?, ?)", (mail.timestamp, mail.fromAddr, mail.subject, category.catId, points, awardToId))
			self.dbc.commit()
		else:
			print "### WARNING: Could not find entry for email address %s ###" % awardTo
		c.close()
	

class ThankYouCategory(Category):
	catName = "Thank You"
	thankYouProg = re.compile("(thanks|thank\\s*you)", flags=re.IGNORECASE)
	
	def check(self, mail):
		if self.thankYouProg.search(mail.subject) and not mail.isReplyFwd():
			self.award(mail, self, 1)

class FreeFoodCategory(Category):
	catName = "Free Food!"
	freeFoodProg = re.compile("free\\s*food", flags=re.IGNORECASE)

	def check(self, mail):
		yes = False
		if self.freeFoodProg.search(mail.subject) and not mail.isReplyFwd():
			yes = True
		elif mail.searchBody(self.freeFoodProg):
			yes = True
	
		if yes:
			self.award(mail, self, 1)

class GIFCategory(Category):
	catName = "GIFs"
	gifProg = re.compile("(http|www|com|net|org|ca|co|)\\S*\\.gif", flags=re.IGNORECASE)

	def check(self, mail):
		if mail.hasAttachedGif() or mail.searchBody(self.gifProg):
			self.award(mail, self, 1)

class ConversationStarterCategory(Category):
	catName = "Conversation Starter"

	def check(self, mail):
		if mail.isReplyFwd():
			origSubject = mail.getOriginalSubject().lower().strip()
			c = self.dbc.cursor()
			c.execute("select mailfrom from conversation where subject = ? order by timestamp desc limit 1", (origSubject,))
			awardTo = None
			for row in c:
				awardTo = row[0]
				break
			c.close()
			if awardTo and mail.fromAddr != awardTo:
#				print "CONVERSATION STARTER award to", awardTo
				self.award(mail, self, 1, awardTo)
		else:
			sanitizedSubject = mail.subject.__str__().lower().strip()
			c = self.dbc.cursor()
			res = c.execute("insert into conversation (timestamp, mailfrom, subject) values (?, ?, ?)", (mail.timestamp, mail.fromAddr, sanitizedSubject))
			self.dbc.commit()
			c.close()

class PraiseTheCreatorsCategory(Category):
	catName = "Praise The Creators"
	praiseCreatorProg = re.compile("you\\s+are\\s+the\\s+best[ ,.]+(sean|zach|sheiva|naliaka|tiffany)", flags=re.IGNORECASE)

	def check(self, mail):
		if self.praiseCreatorProg.search(mail.subject) and not mail.isReplyFwd():
			self.award(mail, self, 1)

