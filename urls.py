from django.conf.urls.defaults import patterns, include, url

from django.views.generic import ListView, DetailView
from django.views.generic.simple import direct_to_template

from interface.models import Team, Player, Emailer

from django.contrib import admin
admin.autodiscover()

teamDetail = DetailView.as_view(model=Team, template_name= "teamDetail.html")
emailerDetail = DetailView.as_view(model=Emailer, template_name= "emailerDetail.html")

emailerList = ListView.as_view(model=Emailer, template_name= "emailerList.html")
# teamList = ListView.as_view(model=Team, template_name= "teamList.html")

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    # Examples:
    url(r'^$', 'interface.views.home', name='home'),
    url(r'^(?P<game>[\w-]+)/team/(?P<id>[a-z\d]+)/$', "interface.views.teamDetail", name='teamDetail'),
    url(r'^(?P<game>[\w-]+)/emailers/$', 'interface.views.emailerList', name='emailerList'),
    url(r'^(?P<game>[\w-]+)/emails/$', 'interface.views.emailList', name='emailList'),
    url(r'^(?P<game>[\w-]+)/$', 'interface.views.overview', name='teamList'),
    url(r'^(?P<game>[\w-]+)/standings/$', 'interface.views.standings', name='teamList'),

    url(r'^help/$', direct_to_template, {'template': 'help.html'}),

    url(r'^(?P<game>[\w-]+)/edit/?$', 'interface.views.editTeam', name='editTeam'),
    url(r'^(?P<game>[\w-]+)/remove/?(?P<id>[a-z\d]+)/$', 'interface.views.removePlayer'),
    url(r'^(?P<game>[\w-]+)/add/?(?P<id>[a-z\d]+)/$', 'interface.views.addPlayer'),

    (r'^accounts/profile/.*', 'interface.views.home'),
    (r'^users/.*', 'interface.views.home'),
    (r'^accounts/', include('registration.urls')),

)
