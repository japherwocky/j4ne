

`j4ne.py --help`

~~~
(env) D:\j4ne>python j4ne.py --help
Usage: j4ne.py [OPTIONS]
~~~

J4NE is built on top of tornado, and comes with a number of handy logging options,
which makes it pretty easy to install in arbitrary environments.

D:\j4ne\env\lib\site-packages\tornado\log.py options:

  --log-file-max-size              max size of log files before rollover       
                                   (default 100000000)
  --log-file-num-backups           number of log files to keep (default 10)    
  --log-file-prefix=PATH           Path prefix for log files. Note that if you 
                                   are running multiple tornado processes,     
                                   log_file_prefix must be different for each  
                                   of them (e.g. include the port number)      
  --log-rotate-interval            The interval value of timed rotating        
                                   (default 1)
  --log-rotate-mode                The mode of rotating files(time or size)    
                                   (default size)
  --log-rotate-when                specify the type of TimedRotatingFileHandler
                                   interval other options:('S', 'M', 'H', 'D', 
                                   'W0'-'W6') (default midnight)
  --log-to-stderr                  Send log output to stderr (colorized if     
                                   possible). By default use stderr if
                                   --log_file_prefix is not set and no other   
                                   logging is configured.

Note that logging is set to info by default.  Try using --logging=debug to see
more detailed information about what's going on. 

~~~
  --logging=debug|info|warning|error|none
                                   Set the Python log level. If 'none', tornado
                                   won't touch the logging configuration.      
                                   (default info)
~~~


~~~
D:\j4ne\j4ne.py options:
~~~

Run this first to create a local database.  
~~~
  --mktables                       bootstrap a new sqlite database (default    
                                   False)
~~~

Then do something like `j4ne.py --addFeed=http://wsjm.com` to try to respectfully
spider a site and create a full sitemap in the local database.

If you don't want (or can't handle) every single page on a site, it's safe to
interrupt this prcoess at an arbitrary spot.

~~~
  --addFeed                        attempt to create a feed from an address    
  --debug                          run server in debug mode (default False)    
  --migration                      run a named database migration

  --port                           serve web requests from the given port      
                                   (default 8888)
  --runtests                       Run tests (default False)
  --serve                          serve web requests on --port (default True)
~~~

