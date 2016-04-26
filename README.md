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

PASSWORDS
=========

j4ne connects to Discord, Twitter, and Twitch.  She looks for passwords in 'keys.py',
which you'll need to fill in with your own credentials.


GO TIME
=======

`env/bin/python j4ne.py`

