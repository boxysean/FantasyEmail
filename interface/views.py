
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.template import RequestContext
from models import *
from django.http import HttpResponse, HttpResponseRedirect
from datetime import datetime, timedelta
from django.db.models import Sum

from django.views.generic import ListView, DetailView
from django.core.urlresolvers import reverse

from django.shortcuts import render_to_response
from django.utils import simplejson

from datetime import datetime, timedelta
import settings

import time

from django.core.exceptions import ObjectDoesNotExist


import logging
import yaml

logger = logging.getLogger(__name__)


config = yaml.load(open("game.yaml"))


def moduloDay(t):
  return t - timedelta(hours=t.hour, minutes=t.minute, seconds=t.second, microseconds=t.microsecond)


def home(request):
    return render_to_response("home.html", locals() , context_instance=RequestContext(request))

def getTeam(request, game, id):
    if request.user.is_authenticated():
        team = get_object_or_404(Team, id=id)
        return render_to_response("home.html", locals() , context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/accounts/login/')

def editTeam(request, game):
    if request.user.is_authenticated():
        team = get_object_or_404(Team, user=request.user)
        categories = sorted(Category.objects.all(), key=lambda a: a.name)
        teamemailers = team.player_set.all()
        for emailer in teamemailers:
            emailer.stats_list = sorted(emailer.emailer.emailerstats_set.all(), key=lambda a: a.category.name) 
            if not emailer.stats_list:
                emailer.stats_list = [{"stat": 0}] * len(categories)
        teamstats = sorted(team.teamstats_set.all(), key=lambda a: a.category.name)
        teampoints = sorted(team.teampoints_set.all(), key=lambda a: a.category.name)

        return render_to_response("editTeam.html", locals() , context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/accounts/login/')

def addPlayer(request, game, id):
    if request.user.is_authenticated():
        team = get_object_or_404(Team, user=request.user)
        emailer_to_add = get_object_or_404(Emailer, id=id)
        team_players = Player.objects.filter( team=team )
        if len(team_players) >= settings.NUMBER_OF_SLOTS_ON_TEAM:
            headline= "Too Damn Many"
            message="Sorry, you can only have two players on your team, yo."
            return render_to_response("error.html",locals() , context_instance=RequestContext(request))
        team_emailers = []
        for p in team_players:
            team_emailers.append(p.emailer)
        if emailer_to_add in team_emailers:
            headline= "No Clones"
            message="You can't have an emailer on your team twice. That shit would be cray."
            return render_to_response("error.html",locals() , context_instance=RequestContext(request))
        try:
            if emailer_to_add.user == request.user:
                headline= "Not You!"
                message="You can't play for your own team. That'd be too damn easy" 
                return render_to_response("error.html",locals() , context_instance=RequestContext(request))
        except ObjectDoesNotExist:
            pass

        new_transaction = PlayerTransaction.objects.create(timestamp= datetime.now(), team=team, emailer = emailer_to_add, add=True ) # points should be what ??! 
        new_player = Player.objects.create(team=team, emailer=emailer_to_add) # Points should be 0 when they're first added no matter what, right?
        return HttpResponseRedirect('/%s/edit' % (game))
    else:
        return HttpResponseRedirect('/accounts/login/')

def removePlayer(request, game, id):
    if request.user.is_authenticated():
        team = get_object_or_404(Team, user=request.user)
        team_players = get_list_or_404(Player, team=team )
        player_to_remove = get_object_or_404(Player, id=id)
        new_transaction = PlayerTransaction.objects.create(timestamp= datetime.now(), team=team, emailer = player_to_remove.emailer, add=False ) # Points should be 0 here? 
        if player_to_remove in team_players:
            player_to_remove.delete()
            return HttpResponseRedirect('/%s/edit' % (game))
        else:
            headline= "Cheater!!!"
            message="Think you're clever, trying to remove another manager's player? This has been logged"
            return render_to_response("error.html",locals() , context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/accounts/login/')

def overview(request, game):
    if request.user.is_authenticated():
        team_list = sorted(Team.objects.all(), key= lambda a: -a.getTotalPoints())
        categories = sorted(Category.objects.all(), key=lambda a: a.name)
        for team in team_list:
            team.teamstats_list = sorted(team.teamstats_set.all(), key=lambda a: a.category.name)
            team.teampoints_list = sorted(team.teampoints_set.all(), key=lambda a: a.category.name)

        return render_to_response("overview.html", locals(), context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/accounts/login/')

def overviewGraph(request, game):
  if request.user.is_authenticated():
    res = {
        "startTimestamp": int(time.mktime(config["startDate"].timetuple())),
        "endTimestamp": int(time.mktime(config["endDate"].timetuple())),
        "teams": []
    }

    for team in Team.objects.all():
      values = []
      res["teams"].append({ "key": team.name, "values": values })
      total = 0
      for point in team.teampointshistory_set.values("timestamp").order_by("timestamp").annotate(total=Sum("points")):
        values.append({ "x" : int(time.mktime(point["timestamp"].timetuple()))*1000, "y" : float(point["total"]) })

      print values

    return HttpResponse(simplejson.dumps(res), mimetype="application/json")
  else:
    return HttpResponseForbidden()

def standings(request, game):
    if request.user.is_authenticated():
        team_list = sorted(Team.objects.all(), key= lambda a: -a.getTotalPoints())
        categories = sorted(Category.objects.all(), key=lambda a: a.name)
        for team in team_list:
            team.teampoints_list = sorted(team.teampoints_set.all(), key=lambda a: a.category.name)
            if not team.teampoints_list:
                team.teampoints_list = [{"points": 0}] * len(categories)

            team.teamstats_list = sorted(team.teamstats_set.all(), key=lambda a: a.category.name)
            if not team.teamstats_list:
                team.teamstats_list = [{"stat": 0}] * len(categories)

        stats_no_sorter = len(categories) + 2

        return render_to_response("standings.html", locals(), context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/accounts/login/')

def emailerList(request, game):
    if request.user.is_authenticated():
        categories = sorted(Category.objects.all(), key=lambda a: a.name)
        emailers = Emailer.objects.all().order_by("name")
        try:
          user_team = Team.objects.filter(user=request.user)
        except:
          user_team = None
        for emailer in emailers:
            emailer.stats_list = map(lambda x : x.stat, sorted(emailer.emailerstats_set.all(), key=lambda a: a.category.name))

            if not emailer.stats_list:
                emailer.stats_list = [0] * len(categories)

            period = request.GET.get("period", 0)

            try:
                period = int(period)
            except:
                period = 0

            if period > 0:
                # find out how the emailer has done over time
                yesterday = moduloDay(datetime.now() - timedelta(days=period))
                yesterdays_stats = map(lambda x : x.stat, sorted(emailer.emailerstatshistory_set.filter(timestamp=yesterday), key=lambda a: a.category.name))

                if not yesterdays_stats:
                    yesterdays_stats = [0] * len(categories)

                emailer.stats_list = map(lambda x : x[0] - x[1], zip(emailer.stats_list, yesterdays_stats))

            emailer.stats_total = sum(emailer.stats_list)

            player_set = emailer.player_set.all()

            if len(player_set) == 1:
                player = player_set[0]
                emailer.owned_by = player.team.name
                emailer.owned_by_icon = player.team.icon
                emailer.owns_player = user_team != None and len(user_team) > 0 and player.team.name == user_team[0].name
                emailer.player_id = player.id
            else:
                emailer.owned_by = "Free Agent"

        rank = 0
        lastTotal = -1

        for idx, emailer in enumerate(sorted(emailers, key=lambda x: x.stats_total, reverse=True)):
            if emailer.stats_total != lastTotal:
                rank = idx
                lastTotal = emailer.stats_total
            emailer.rank = rank+1

        return render_to_response("emailerList.html", locals(), context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/accounts/login/')

def teamDetail(request, game, id):
    if request.user.is_authenticated():
        team = get_object_or_404(Team, id=id)
        categories = sorted(Category.objects.all(), key=lambda a: a.name)
        teamemailers = team.player_set.all()
        for emailer in teamemailers:
            emailer.stats_list = sorted(emailer.emailer.emailerstats_set.all(), key=lambda a: a.category.name) 
            if not emailer.stats_list:
                emailer.stats_list = [{"stat": 0}] * len(categories)
        teamstats = sorted(team.teamstats_set.all(), key=lambda a: a.category.name)
        if not teamstats:
            teamstats = [{"stat": 0}] * len(categories)
        return render_to_response("teamDetail.html", locals(), context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/accounts/login/')

def emailList(request, game):
    if request.user.is_authenticated():
        email_list = Email.objects.all().order_by("timestamp").reverse()
        for email in email_list:
            email.isoformat = (email.timestamp).isoformat()
        return render_to_response("emailList.html", locals(), context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/accounts/login/')

def transactionList(request, game):
  if request.user.is_authenticated():
    transactions = PlayerTransaction.objects.all().order_by("timestamp").reverse()
    for transaction in transactions:
      transaction.isoformat = (transaction.timestamp).isoformat()
    return render_to_response("transactionList.html", locals(), context_instance=RequestContext(request))
  else:
    return HttpResponseRedirect('/accounts/login/')
