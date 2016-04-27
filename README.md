# mlb-fantasy-checker
Scripts for querying and displaying MLB.com's publicly-accessible data to display stats for your MLB.com fantasy baseball league. 

MLB Better Fantasy Stats by Brahm Neufeld

I believe this project complies with MLB.com's copyright terms posted here:
http://gdx.mlb.com/components/copyright.txt
Because:
	- This is, and will remain, a non-commercial project
	- It is accessed by and designed for (12) individuals (in our league)
	- It does not scrape data in bulk, and the data it does collect is 
	  only served (not stored).
	  
================= CHANGE LOG =================

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
	
================= TODO LIST =================

- Make source code downloadable in a .zip, url to be shared in this txt

- Charts or graphs using Google chart API? Probably works great on mobile! 
Can get all required data from schedule.json

- Indicate completed games.