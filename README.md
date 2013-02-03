# Installation

    virtualenv .
    pip install -r requirements.txt

## apache

Copy contents of apache folder into `/etc/apache2/sites-available` and make a symlink from `/etc/apache2/sites-enabled/FantasyEmail` to `/etc/apache2/sites-available/FantasyEmail`.

# Old...

Assuming you have django installed, start this by running
    
    python manage.py syncdb 

to set up the sqlite database for development.

Next, to start the dev server, run
    
    python manage.py runserver

and a placeholder should show up at http://127.0.0.1:8000/





