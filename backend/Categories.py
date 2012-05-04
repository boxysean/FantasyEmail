import re
import sqlite3
from datetime import datetime

import os
import sys

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
#	    TIME_ZONE = 'America/New_York',
	)
except RuntimeError:
	pass



from interface.models import Category as CategoryModel, EmailAddress, EmailPoint, Email


class Category:
	idMap = {}

	def __init__(self, dbc):
		self.dbc = dbc
		self.catId = Category.getId(self.catName, dbc)
	
	@staticmethod
	def getId(desc, dbc):
		if not len(Category.idMap):
			c = dbc.cursor()
			c.execute("select id, name from interface_category")
			for row in c:
				Category.idMap[row[1].__str__()] = row[0]
			c.close()

		return Category.idMap[desc]

	def award(self, mail, category, points, awardTo=""):
		if not len(awardTo):
			awardTo = mail.fromAddr

		email = Email.objects.filter(pk=mail.pk)[0]
		dbCategory = CategoryModel.objects.filter(name=category.catName)[0]
		emailAddress = EmailAddress.objects.filter(emailAddress=awardTo)[0]

		emailPoint = EmailPoint(email=email, category=dbCategory, awardTo=emailAddress.emailer, points=points)
		emailPoint.save()

class ThankYouCategory(Category):
	catName = "Thank You"
	thankYouProg = re.compile("(thanks|thank\\s*you)", flags=re.IGNORECASE)
	
	def check(self, mail):
		if self.thankYouProg.search(mail.subject) and not mail.isReplyFwd():
			self.award(mail, self, 1)
			return True
		return False

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

		return yes

class GIFCategory(Category):
	catName = "GIFs"
	gifProg = re.compile("(http|www|com|net|org|ca|co|)\\S*\\.gif", flags=re.IGNORECASE)

	def check(self, mail):
		if mail.hasAttachedGif() or mail.searchBody(self.gifProg):
			self.award(mail, self, 1)
			return True
		return False

class ConversationStarterCategory(Category):
	catName = "Conversation Starter"

	def check(self, mail):
		if mail.isReplyFwd():
			origSubject = mail.getSanitizedSubject()
			c = self.dbc.cursor()
			c.execute("select mailfrom from conversation where subject = ? order by timestamp desc limit 1", (origSubject,))
			awardTo = None
			for row in c:
				awardTo = row[0]
				break
			c.close()
			if awardTo and mail.fromAddr != awardTo:
				self.award(mail, self, 1, awardTo)
				return True
		else:
			sanitizedSubject = mail.getSanitizedSubject()
			c = self.dbc.cursor()
			res = c.execute("insert into conversation (timestamp, mailfrom, subject) values (?, ?, ?)", (mail.timestamp, mail.fromAddr, sanitizedSubject))
			self.dbc.commit()
			c.close()
		return False

class OneWordCategory(Category):
	catName = "One Word"

	def check(self, mail):
		lines = filter(lambda x: len(x.strip()) != 0, mail.getLines())
		if len(lines) == 1 and len(lines[0].split()) == 1:
			self.award(mail, self, 1)
			return True

		return False

class LastReplyCategory(Category):
	catName = "Last Reply"

	def check(self, mail):
		if mail.isReplyFwd():
			sanitizedSubject = mail.getSanitizedSubject()

			# remove existing points awarded for last word in this thread
			dbCategory = CategoryModel.objects.filter(name=self.catName)[0]
			emails = Email.objects.filter(sanitizedSubject=sanitizedSubject)
			for email in emails:
				emailPoint = EmailPoint.objects.filter(email=email, category=dbCategory)
				emailPoint.delete()

			# award this email for the last word
			self.award(mail, self, 1)
			return True

		return False

class LateNightCategory(Category):
	catName = "Late Night"

	def check(self, mail):
		date = datetime.fromtimestamp(mail.timestamp)
		hour = (int(date.strftime("%H"))-4)%24 # omg so bad

		if 20 <= hour <= 24 or 0 <= hour <= 3:
			self.award(mail, self, 1)
			return True

		return False

class PraiseTheCreatorsCategory(Category):
	catName = "Praise The Creators"
	praiseCreatorProg = re.compile("you\\s+are\\s+the\\s+best[ ,.]+(sean|zach|sheiva|naliaka|tiffany)", flags=re.IGNORECASE)

	def check(self, mail):
		if self.praiseCreatorProg.search(mail.subject) and not mail.isReplyFwd():
			self.award(mail, self, 1)
			return True
		return False

