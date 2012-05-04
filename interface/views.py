
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.template import RequestContext
from models import *
from django.http import HttpResponse, HttpResponseRedirect
from datetime import datetime


from django.views.generic import ListView, DetailView
from django.core.urlresolvers import reverse

from django.shortcuts import render_to_response
from django.utils import simplejson

from datetime import datetime
import settings
from models import *

import logging

logger = logging.getLogger(__name__)



def home(request):
    if request.user.is_authenticated() and len(Team.objects.filter(user=request.user)):
        return HttpResponseRedirect('/edit')
    return render_to_response("home.html", locals() , context_instance=RequestContext(request))

def getTeam(request, id):
    team = get_object_or_404(Team, id=id)
    return render_to_response("home.html", locals() , context_instance=RequestContext(request))

def editTeam(request):
    if request.user.is_authenticated():
        team = get_object_or_404(Team, user=request.user)
        team_players = Player.objects.filter( team=team ) #this isn't being used?
        return render_to_response("editTeam.html", locals() , context_instance=RequestContext(request))
    else:
        headline= 'Error'
        return render_to_response("error.html",locals() , context_instance=RequestContext(request))
        # return HttpResponse('error yo')

def addPlayer(request, id):
    if request.user.is_authenticated():
        team = get_object_or_404(Team, user=request.user)
        emailer_to_add = get_object_or_404(Emailer, id=id)
        team_players = Player.objects.filter( team=team )
        if len(team_players) >= settings.NUMBER_OF_SLOTS_ON_TEAM:
            headline= "Too Damn Many"
            message="Sorry, you can only have eight players on your team, yo."
            return render_to_response("error.html",locals() , context_instance=RequestContext(request))
        team_emailers = []
        for p in team_players:
            team_emailers.append(p.emailer)
        if emailer_to_add in team_emailers:
            headline= "No Clones"
            message="You can't have an emailer on your team twice. That shit would be cray."
            return render_to_response("error.html",locals() , context_instance=RequestContext(request))
        print emailer_to_add.user
        print request.user
        if emailer_to_add.user == request.user:
            headline= "Not You!"
            message="You can't play for your own team. That'd be too damn easy" 
            return render_to_response("error.html",locals() , context_instance=RequestContext(request))

        new_transaction = PlayerTransaction.objects.create(timestamp= datetime.now(), team=team, emailer = emailer_to_add, add=True ) # points should be what ??! 
        new_player = Player.objects.create(team=team, emailer=emailer_to_add) # Points should be 0 when they're first added no matter what, right?
        return HttpResponseRedirect('/edit')
    else:
        headline= "Error!"
        return render_to_response("error.html",locals() , context_instance=RequestContext(request))



def removePlayer(request, id):
    if request.user.is_authenticated():
        team = get_object_or_404(Team, user=request.user)
        team_players = get_list_or_404(Player, team=team )
        player_to_remove = get_object_or_404(Player, id=id)
        new_transaction = PlayerTransaction.objects.create(timestamp= datetime.now(), team=team, emailer = player_to_remove.emailer, add=False ) # Points should be 0 here? 
        if player_to_remove in team_players:
            player_to_remove.delete()
            return HttpResponseRedirect('/edit')
        else:
            headline= "Cheater!!!"
            message="Think you're clever, trying to remove another manager's player? This has been logged"
            return render_to_response("error.html",locals() , context_instance=RequestContext(request))
    else:
        return HttpResponse('error yo')

def teamList(request):
    team_list = sorted(Team.objects.all(), key= lambda a: -a.getTotalPoints())
    categories = sorted(Category.objects.all(), key=lambda a: a.name)
    for team in team_list:
        team.teamstats_list = sorted(team.teamstats_set.all(), key=lambda a: a.category.name)
        team.teampoints_list = sorted(team.teampoints_set.all(), key=lambda a: a.category.name)

    return render_to_response("teamList.html", locals(), context_instance=RequestContext(request))

def emailList(request):
    email_list = Email.objects.all().order_by("timestamp").reverse()
    return render_to_response("emailList.html", locals(), context_instance=RequestContext(request))

