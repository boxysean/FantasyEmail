import mailbox
import email
import re
from datetime import datetime
import time

from email.header import decode_header

import os
import sys

from interface.models import Emailer, EmailAddress, Email

from django.core.exceptions import ObjectDoesNotExist

def parseTimestamp(date):
  timetuple = email.utils.parsedate_tz(date)
  timestamp = time.mktime(timetuple[0:9]) - timetuple[9]
  date = datetime.fromtimestamp(timestamp)
  return date

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

  def __init__(self, mbFile, listAddrProg, startDate=None, endDate=None):
    self.mbFile = mbFile
    mb = mailbox.UnixMailbox(file(mbFile, "r"), email.message_from_file)
    checked = set()
    count = 0
    for msg in mb:
      try:
        if not listAddrProg.search(msg["to"]):
          continue
  
        timestamp = parseTimestamp(msg["date"])
  
        if startDate > timestamp or timestamp > endDate:
          continue
  
        mail = Mail(msg)
  
        self.msgs.append(mail)

#        count = count +1
#        print "count...", count
#        if count == 50:
#          break
      except Exception as e:
        print "failed analyzing a message!" , e
  
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
  getNameProg = re.compile("^\"?([^\"]*)\"?\\s+<(\\S+@\\S+)>")

  def __init__(self, msg):
    self.msg = msg
    self.subject, self.subject_encoding = decode_header(msg["subject"])[0]

    if self.subject_encoding:
      self.subject = unicode(self.subject, self.subject_encoding)
      self.subject = self.subject.encode("ascii", "ignore") # to be nice to file systems

    # decode email address and sender

    nameRes = self.getNameProg.search(msg["from"])

    if nameRes:
      self.fromName, self.fromName_encoding = decode_header(nameRes.group(1))[0]

      if self.fromName_encoding:
        self.fromName = unicode(self.fromName, self.fromName_encoding)
        self.fromName = self.fromName.encode("ascii", "ignore")

      self.fromAddr = nameRes.group(2)
    else:
      self.fromName = None 
      self.fromAddr = self.emailProg.search(msg["from"]).group(0)

#    print "name %s addr %s" % (self.fromName, self.fromAddr)

    self.initDate()

    self.toAddr = self.emailProg.search(msg["to"]).group(0)

    self.hasGif = None
    self.lines = None

  def initDate(self):
    timetuple = email.utils.parsedate_tz(self.msg["date"])
    self.timestamp = time.mktime(timetuple[0:9]) - timetuple[9]
    date = datetime.fromtimestamp(self.timestamp)
    self.datestr = date.strftime("%Y-%m-%d %H:%M:%S")
#    print "subject %s timestamp %s date %s tz %d" % (self.subject, self.timestamp, self.msg["date"], timetuple[9])

  def getLines(self):
    if self.lines is None:
      self.lines = []
      for part in self.msg.walk():
        if part.get_content_type().lower() == "text/plain" and len(self.lines) == 0:
          payload = part.get_payload().splitlines()
          for line in payload:
            if re.search("^\\s*>", line):
              continue
            elif re.search("_______________________________________________", line):
              break
            elif re.search("^On .* wrote:$", line):
              continue
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

  def getSanitizedSubject(self):
    return self.getOriginalSubject().lower().strip()

  def isReplyFwd(self):
    return self.replyFwdProg.search(self.subject)

  def __str__(self):
    return "%30s / %30s / %20s" % (self.getFrom()[0:30], self.subject[0:30], self.datestr[0:20])

  def __hash__(self):
    res = self.subject.__hash__()
    res = int(res * 31 + self.fromAddr.__hash__())
    res = int(res * 31 + self.timestamp.__hash__())
    return res

  def __eq__(self, o):
    return self.subject == o.subject and self.fromAddr == o.fromAddr and self.timestamp == o.timestamp

  def insert(self):
    emailAddress = EmailAddress.objects.filter(emailAddress=self.fromAddr)

    try:
      emailer = emailAddress[0].emailer
      print "addEmailer: %s exists, don't worry about it" % (emailer.name)
    except ObjectDoesNotExist:
      emailer = addEmailer(self)
    except IndexError:
      emailer = addEmailer(self)

    email = Email(timestamp=self.datestr, fromAddr=self.fromAddr, emailer=emailer, subject=self.subject, sanitizedSubject=self.getSanitizedSubject())
    email.save()
    self.pk = email.pk

  def checked(self):
    email = Email.objects.filter(subject=self.subject, fromAddr=self.fromAddr, timestamp=self.datestr)

    if not email:
      return False

    return True

  def getFrom(self):
    if not self.fromName:
      return self.fromAddr

    return self.fromName

def addEmailer(mail):
  if mail.fromName:
    emailer = Emailer.objects.filter(name__exact=mail.fromName)

    if emailer.count():
      print "addEmailer: %s emailer identity exists, so we'll tie this email address to the identity..." % (mail.fromName)
      emailer = emailer[0]
      emailAddress = EmailAddress(emailer=emailer, emailAddress=mail.fromAddr)
      emailAddress.save()
      return emailer
    else:
      print "addEmailer: emailer identity %s with address %s DOES NOT exist" % (mail.fromName, mail.fromAddr)
      emailer = Emailer(name=mail.fromName, image="default.jpg")
      emailer.save()
      emailAddress = EmailAddress(emailer=emailer, emailAddress=mail.fromAddr)
      emailAddress.save()
      return emailer

  else:
    emailer = Emailer(name=mail.fromAddr, image="default.jpg")
    emailer.save()
    emailAddress = EmailAddress(emailer=emailer, emailAddress=mail.fromAddr)
    emailAddress.save()
    return emailer

