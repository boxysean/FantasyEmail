# Installation

Tested with python 2.7.3

    virtualenv .
    pip install -r requirements.txt
    source bin/activate
    python manage.py syncdb

Edit the `game.yaml.sample` file and save it as `game.yaml`
    
    python manage.py SetupGame

## Running from django built in server

    python manage.py runserver http://yourserver.com:8080

## apache

Copy contents of apache folder into `/etc/apache2/sites-available` and make a symlink from `/etc/apache2/sites-enabled/FantasyEmail` to `/etc/apache2/sites-available/FantasyEmail`.

    sudo chown -R www-data *
    sudo apache2ctl restart

www-data is your apache user. If www-data is not your apache user, change the apache config appropriately.

From within `python manage.py shell`, run the following command to fix [this](http://stackoverflow.com/questions/11814059/site-matching-query-does-not-exist):

    from django.contrib.sites.models import Site
    new_site = Site.objects.create(domain='foo.com', name='foo.com')
    print new_site.id

# Old...

Assuming you have django installed, start this by running
    
    python manage.py syncdb 

to set up the sqlite database for development.

Next, to start the dev server, run
    
    python manage.py runserver

and a placeholder should show up at http://127.0.0.1:8000/





