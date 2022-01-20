SYSTEM REQUIREMENTS 
===================

System dependencies are built into the Vagrant file, with ansible scripts in `/sys/`.  

`vagrant up local` will bootstrap a local VM with the app (and python virtualenv) installed in `/opt/j4ne`


PYTHON REQUIREMENTS
===================

_As the user your bot should run as_:

Create a virtualenv and install python dependencies
---------------------------------------------------

```
virtualenv -p python3.5 env
env/bin/pip install -r requirements.txt
```



Getting j4ne up and running
===========================


J4ne needs a bunch of credentials, which are stored in the `keys.py` files.  Sorry, it will probably crash if you don't have a full set.

You can turn some networks off by passing `--< network >=False`, eg, `--twitter=False` to not load twitter.

This is awkward and bad UX, sorry.


Discord Credentials
-------------------

You can create a Discord application here: [Discord Applications](https://discordapp.com/developers/applications/)

``` python
# proj-dir/keys.py

discord_token = 'your-secret-token'
discord_app_id = 'your-discord-client/application-ID'
```

Afterwards use the `--newbot` option to generate an invitation link to your server:

    ./env/bin/python j4ne.py --newbot


Running the server for the first time
-------------------------------------

The following options should be passed to `j4ne.py` if you are running the bot for the first time.

* `newbot` : This option will generate a link at the command line so you can add j4ne to your Discord server

* `mktables` : Generates a new sqlite database


Updating or migrating a database
--------------------------------

Migrations can be run by name, see `db.py` for notes
