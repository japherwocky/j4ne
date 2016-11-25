SYSTEM REQUIREMENTS 
===================

_As root, or with sudo:_

Python 3.5
----------

```
add-apt-repository ppa:fkrull/deadsnakes
apt-get update
apt-get install python3.5 python3.5-dev python3-pip python-virtualenv
```

Compiler dependencies
---------------------

```
apt-get install build-essential git
```

Audio tools
-----------

```
add-apt-repository ppa:mc3man/trusty-media
apt-get update
apt-get install ffmpeg libopus-dev libffi-dev
```


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

Discord Credentials
-------------------

First you will need to add your Discord application to the \`keys.py\` file. If you do not yet have those, you can create an application here: [Discord Applications](https://discordapp.com/developers/applications/)

``` python
# proj-dir/keys.py

discord_token = 'your-secret-token'
discord_app_id = 'your-discord-client/application-ID'
```

Optional Credentials
--------------------

-TODO

Running the server for the first time
-------------------------------------

The following options should be passed to 'j4ne.py' if you are running the bot for the first time.

`newbot`  
    This option will generate a link at the command line so you can add j4ne to your Discord server

`mktables`  
    Generates a new sqlite database

`twitch` & `twitchapi`  
    These options should be set to \`False\` if you will not be using these features and not added the credentials to \`keys.py\`

Examble:

``` bash
env/bin/python j4ne.py -newbot=True -mktables=True -twitch=False -twitchapi=False
```
