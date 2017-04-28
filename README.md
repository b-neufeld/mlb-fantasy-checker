# mlb-fantasy-checker
Scripts for querying and displaying MLB.com's publicly-accessible data 
to display stats for your MLB.com fantasy baseball league. 

MLB Better Fantasy Stats by Brahm Neufeld

# Update 2017: I think this is now obsolete, as MLB has shut down their fantasy baseball program and redirected all users to Yahoo or other platforms. BN

I believe this project complies with MLB.com's copyright terms posted here:
http://gdx.mlb.com/components/copyright.txt
Because:
- This is, and will remain, a non-commercial project
- It is accessed by and designed for (12) individuals who have to host the script somewhere. 
- It does not scrape data in bulk, and the data it does collect is only served (not stored).

================= HOW TO USE =================

- Upload files to webserver running Python 2.7
- Change the league_id in baseball.py to YOUR league_id
- Open baseball.py in Google Chrome. Share with your league! 
	  
================= CHANGE LOG =================

2016-05-14
- Google Charts API is working - shows points_back graph
- Code cleanup

2016-05-01
- Code cleanup

2016-04-28
- Starting to work on Google Charts API

2016-04-27
- Players now print in a consistent order. 

2016-04-26
- Refactoring, code comments
- Set up a github repo https://github.com/b-neufeld/mlb-fantasy-checker

2016-04-24
- Multi-threaded most of the necessary HTTP requests to 
mlb servers, to a) reduce total number of calls to mlb and b) speed
up the script for the user. 
- Improved page load times by NOT printing a ton of hidden debug 
information on each page. 
- Because all data is reading off the boxscore.json files, any given
day should show points correctly no matter how many games are played. 

2016-04-22
- Discovered summary & detail html elements to neatly hide 
daily player totals

2016-04-21
- More cosmetics
- Refactoring and garbage cleanup
- Double headers for batting sbould be working
- Show weekly team totals and daily player totals, because why not? 

2016-04-20 
- Script-crashing bugfix 
- Was accidentally adding caught-stealings instead of subtracting
- Cosmetic improvements 

2016-04-19
- Project started, basic version up and running 
