from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import dispatcher

class Emailer(models.Model):
  name = models.CharField(max_length=200)
  image = models.CharField(max_length=200)
  user = models.ForeignKey(User, null=True, blank=True)
  def __str__(self):
    return self.name
  class Meta:
    ordering= ["name"]

class EmailAddress(models.Model):
  emailer = models.ForeignKey(Emailer)
  emailAddress = models.CharField(max_length=200)
  def __str__(self):
    return "%s: %s" % (self.emailer.name, self.emailAddress)
 
class Team(models.Model):
  name = models.CharField(max_length=200)
  user = models.ForeignKey(User)
  icon = models.CharField(max_length=200)
        # slug = AutoSlugField(populate_from='name')
  def __str__(self):
    return "%s: %s" % (self.user, self.name)

  def getTotalPoints(self):
    res = 0
    for points in  self.teampoints_set.all():
      res = res + points.points
    return res

class Player(models.Model):
  team = models.ForeignKey(Team)
  emailer = models.ForeignKey(Emailer)
  def __str__(self): return "%s" % self.team
  def name(self):
    return self.emailer.name

class PlayerTransaction(models.Model):
  timestamp = models.DateTimeField()
  team = models.ForeignKey(Team)
  emailer = models.ForeignKey(Emailer)
  add = models.BooleanField()
  def __str__(self): return "%s set %s to %s at %s" % (self.team.name, self.emailer.name, self.add, self.timestamp)
  def name(self):
    return self.emailer.name

class Category(models.Model):
  name = models.CharField(max_length=200)
  description = models.TextField()
  className = models.CharField(max_length=200)
  def __str__(self): return self.name

class EmailerStats(models.Model):
  emailer = models.ForeignKey(Emailer)
  category = models.ForeignKey(Category)
  stat = models.IntegerField()
  total = models.BooleanField()
  def __str__(self): return "[%s] %s: %s" % (self.category, self.emailer, self.stat)

class TeamPoints(models.Model):
  team = models.ForeignKey(Team)
  category = models.ForeignKey(Category)
  points = models.DecimalField(max_digits=5, decimal_places=2)
  total = models.BooleanField()
  def __str__(self): return "[%s] %s: %s" % (self.category, self.team, self.points)

class TeamStats(models.Model):
  team = models.ForeignKey(Team)
  category = models.ForeignKey(Category)
  stat = models.IntegerField()
  total = models.BooleanField()
  def __str__(self): return "[%s] %s: %s" % (self.category, self.team, self.stat)

class Email(models.Model):
  timestamp = models.DateTimeField()
  fromAddr = models.CharField(max_length=200)
  emailer = models.ForeignKey(Emailer)
  subject = models.CharField(max_length=256)
  sanitizedSubject = models.CharField(max_length=256)
  def __str__(self): return "[%s] %s: %s" % (self.timestamp, self.emailer, self.subject)

class EmailPoint(models.Model):
  email = models.ForeignKey(Email)
  category = models.ForeignKey(Category)
  awardTo = models.ForeignKey(Emailer)
  points = models.IntegerField()

def createNewTeam(sender, created, instance=None, **kwargs):
    if instance is None:
        return
    if created == True:
        name = instance.username + "'s Team"
        new_team, was_created= Team.objects.get_or_create(name =name, user=instance)
        if was_created: # silly, but there seems to be a bug in the created var coming from the signal
            print instance.email
            # doh regex needs to applied on EmailAdress model, not our user instance
            matching_email_address= EmailAddress.objects.filter(emailAddress=instance.email)
            if len(matching_email_address):
                print 'email matched'
                emailer= matching_email_address[0].emailer
                emailer.user = instance
                emailer.save()



#post_save.connect(createNewTeam, sender=User)

