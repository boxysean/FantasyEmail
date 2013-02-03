import re
import sqlite3
from datetime import datetime

import os
import sys

import curses
from curses.ascii import isdigit
import nltk
from nltk.corpus import cmudict

from django.conf import settings

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

    print "++++ AWARD ++++ category %s dbCategory %s" % (category.catName, dbCategory.name)

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

class ManicCategory(Category):
  catName = "Manic"

  def check(self, mail):
    lines = mail.getLines()
    for line in lines:
      if re.search(r"(!!|\?\?)", line):
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

class NightOwlCategory(Category):
  catName = "Night Owl"

  def check(self, mail):
    date = datetime.fromtimestamp(mail.timestamp)
    hour = (int(date.strftime("%H"))-4)%24 # omg so bad

    if 0 <= hour <= 7:
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

class PassingGradeCategory(Category):
  catName = "Passing Grade"
  dict = cmudict.dict()
  punctuation = re.compile("[.,!?()\[\]<>\"]+")
  runningFk = 0
  calcs = 0
  threshold = 4.0
  

  def nsyl(self, word):
    try:
      return max([len(list(y for y in x if isdigit(y[-1]))) for x in self.dict[word.lower()]])
    except:
      return 0

  def check(self, mail):
    lines = mail.getLines()
    nWords = 0
    nSyl = 0
    nSentences = 0
    for line in lines:
#      print line
      nWords = nWords + len(line.split())
      nSentences += line.count('.') + line.count('!') + line.count('?')
      for word in line.split():
        word = self.punctuation.sub("", word)
        nSyl = nSyl + self.nsyl(word)

    nSentences = max(nSentences, 1)

    fk = 0.39 * (float(nWords) / nSentences) + 11.8 * (float(nSyl) / nWords) - 15.59
    self.runningFk += fk
    self.calcs += 1

    #print mail.subject, "words", nWords, "syls", nSyl, "sentences", nSentences, "fk", fk, "running fk", self.runningFk / self.calcs, "\n"

    if fk >= self.threshold:
      self.award(mail, self, 1)
      return True

    return False

class HotAirCategory(Category):
  catName = "Hot Air"

  def check(self, mail):
    self.award(mail, self, 1)
    return True

class PottyMouthCategory(Category):
  catName = "Potty Mouth"
  banned_words = set(["ahole","ass","assface","asshat","asshole","assholes","asswipe","azzhole","bastard","bastards","bastardz","basterds","basterdz","biatch","bitch","bitches","butthole","buttwipe","cnts","cntz","cock","cocks","cocksucker","cum","cunt","cunts","cuntz","dick","dildo","dildos","dyke","fag","faggot","fags","fagz","fuck","fucker","fuckin","fucking","fucks","goddamned","goddamn","jizz","motherfucker","motherfuckers","motherfucking","nigger","pussy","retard","retarded","skank","scum","scumbag","fck","cnt""schlong","shit","shits","shitty","whore","asses","clusterfuck", "fucked"])

  def __init__(self, dbc):
    Category.__init__(self, dbc)

    new_banned_words = []

    for word in self.banned_words:
      new_banned_words.append(word.lower())

    self.banned_words = new_banned_words

  def check(self, mail):
    lines = mail.getLines()
    for line in lines:
      line = line.lower()
      for word in re.split("\W+", line):
        if word in self.banned_words:
          self.award(mail, self, 1)
          return True
    return False

class ProfessionalCategory(Category):
  catName = "Professional"
  dict = cmudict.dict()
  punctuation = re.compile("[.,!?()\[\]<>\"]+")
  alphaNumeric = re.compile("^[\W_]+$")
  numeric = re.compile("^[0-9.+-]+$")
  banned_words = set(["ahole","ass","assface","asshat","asshole","assholes","asswipe","azzhole","bastard","bastards","bastardz","basterds","basterdz","biatch","bitch","bitches","butthole","buttwipe","cnts","cntz","cock","cocks","cocksucker","cum","cunt","cunts","cuntz","dick","dildo","dildos","dyke","fag","faggot","fags","fagz","fuck","fucker","fuckin","fucking","fucks","goddamned","goddamn","jizz","motherfucker","motherfuckers","motherfucking","nigger","pussy","retard","retarded","skank","scum","scumbag","fck","cnt""schlong","shit","shits","shitty","whore","asses","clusterfuck", "fucked"])

  rok = 0
  rcount = 0

  threshold = 0.95

  def check(self, mail):
    lines = mail.getLines()
    okCount = 0
    count = 0
    okay = True
    for line in lines:
      for word in line.split():
        word = self.punctuation.sub("", word).lower()
        if self.alphaNumeric.match(word):
          continue
        count += 1
        if word in self.banned_words:
          okay = False
        elif word in self.dict:
          okCount += 1
        elif self.numeric.match(word):
          okCount += 1
        else:
  #        print "nope", word
          pass

    self.rok += okCount
    self.rcount += count
  #  print count, okCount, float(self.rok) / self.rcount

    if okay and float(okCount) / count >= self.threshold:
  #    print mail.subject, mail.fromAddr, "professh!", okCount, count, float(okCount) / count
      self.award(mail, self, 1)
      return True

    return False
    
