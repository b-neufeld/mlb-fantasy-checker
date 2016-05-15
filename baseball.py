#!/usr/bin/python
import json, urllib, urllib2, pprint, re, datetime, time, threading, gviz_api, itertools
from threading import Thread

########################
# define league ID here
# change for YOUR league
########################
league_id = '1514'
########################
# variable to show google chart
show_chart = True
########################
# define other global variables
this_week = {}
matchup_id_array = []
# time how long it takes to execute the script
start_time = datetime.datetime.now()
timing_log = ['step 0 (start): ' + str(start_time)]
########################

def return_today():
	mydate = str(datetime.date.today()).split("-")
	y = mydate[0]
	m = mydate[1]
	d = mydate[2]
	return(y,m,d)
	
# this is a way of getting all of today's gid's (game ids) 
# returns an array of strings that look like this: 
# gid_2016_04_23_texmlb_chamlb_1
# gid_2016_04_23_slnmlb_sdnmlb_1
# etc
# these are used to grab all of the boxscore.json files that batting data can be computed from. 
def get_todays_gid_xml_blob():
	y,m,d=return_today()
	
	gid_url = "http://gdx.mlb.com/components/game/mlb/year_"+y+"/month_"+m+"/day_"+d+"/"
	data = urllib.urlopen(gid_url).read()
	
	# need a regex for pattern matching 
	# reference: http://pythex.org/?regex=variable_name%3D%22.*%5BA-Za-z%5Cs%5D%22&test_string=rbi%3D%223%22%20variable_name%3D%22Home%20Run%22%20hr%3D%220%22&ignorecase=0&multiline=0&dotall=0&verbose=0
	# gid_[0-9]{4}_[0-9]{2}_[0-9]{2}[a-z0-9_]*
	# list/set functions removes duplicate values - we expect identical values for each since we're parsing html
	# reference: http://stackoverflow.com/questions/7961363/removing-duplicates-in-lists
	gid_list = list(set(re.findall('gid_[0-9]{4}_[0-9]{2}_[0-9]{2}[a-z0-9_]*', data)))
	
	return gid_list
	
# this is a smashing together of these 2 stackoverflow posts:
# http://stackoverflow.com/questions/3472515/python-urllib2-urlopen-is-slow-need-a-better-way-to-read-several-urls
# http://stackoverflow.com/questions/1726402/in-python-how-do-i-use-urllib-to-see-if-a-website-is-404-or-200
# this function is called by the threading function to grab a bunch of boxscores simultaneously. 
def read_url(url, results, index):
	try:
		response = urllib2.urlopen(url)
	except urllib2.HTTPError as e:
		pass
	except urllib2.URLError as e:
		pass
	else:
		data = response.read()
		#debug
		#print('\nFetched %s from %s' % (len(data), url))
		data_1 = json.loads(data)
		results[index] = data_1["data"]["boxscore"]
	
# inputs: list of gid URLs 
# outputs: 
#	- A python array where every value is a dictionary of a game (JSON data).  
def build_monster_boxscore(gid_list):
	y,m,d=return_today()
	
	# define array to load boxscore.json URLs into
	urls_to_load = []
	
	# this is the monster array that all boxscore.jsons are going to be loaded into. 
	game_array = []
	
	# for every gid detected today, build a URL
	for game in gid_list:
		urls_to_load.append("http://gd2.mlb.com/components/game/mlb/year_"+y+"/month_"+m+"/day_"+d+"/"+game+"/boxscore.json")
		game_array.append(game)
	
	# define an array of empty dictionaries to store results in. 
	results = [{} for x in game_array]
	
	# define array for parallel threads
	threads = []
	
	# for every URL...
	for ii in range(len(urls_to_load)):
		# create a process variable to thread
		# pass it a URL, the results array, and the index to store it in results
		process = Thread(target=read_url, args = [urls_to_load[ii], results, ii])
		# start the process as a thread
		process.start()
		# add this process to list of threads. 
		threads.append(process)
	
	# for every process we've started... 	
	for process in threads:
		# the join command "joins" all of the started threads, ensuring the program does 
		# not move on until all of the URLs are processed. 
		process.join()
	
	return results
	
# function to return a batter's fantasy points for the day (int) 
# inputs: player_id (int), super_boxscore (monster array) 	
def get_batter_score(player_id, super_boxscore):
	#define points
	points = 0
	
	# get total points for any number of games that a batter plays. 
	for game in super_boxscore:
		# check for empty dictionary (games that haven't started yet) and ignore. 
		if len(game) <> 0:
			# look at both home and away games in the batting dictionary
			for h_o_a in game['batting']:
				# look at every batter 
				for batter in h_o_a['batter']:
					# if the player_id exists in the game, calculate their stats
					if batter['id'] == player_id:
						# calculate points per batter from here: http://www.mlb.com/mlb/fantasy/fb/info/rules.jsp
						# boxscore.json counts doubles and everything else as hits so we have to subtract
						points += (int(batter['h']) - int(batter['d']) - int(batter['t']) - int(batter['hr'])) * 1
						points += int(batter['d']) * 2
						points += int(batter['t']) * 3
						points += int(batter['hr']) * 4
						points += int(batter['r']) * 1
						points += int(batter['rbi']) * 1
						points += int(batter['bb']) * 1
						points += int(batter['sb']) * 2
						points += int(batter['cs']) * -1

	return int(points)
	
# function to return a pitching staff's fantasy points for the day 
# inputs: player_id, super_boxscore (monster array) 
def get_pitching_score(player_id, super_boxscore):
	points = int(0)
		
	# this should total points for any number of games that a pitching staff plays. 
	for game in super_boxscore:
		
		# check for empty dictionary (games that haven't started yet) and ignore. 
		if len(game) <> 0:
			# check both home and away rosters in the pitching dictionary
			for h_o_a_pitching in game['pitching']:
				
				# zero these variables when looping through every game. 
				strikeouts = int(0)
				hits_plus_walks = int(0)
				earned_runs = int(0)
				
				# We want to calculate points in one of two situations:
				# team_flag is HOME and we're the HOME team
				# team_flag is AWAY and we're the AWAY team
				if (h_o_a_pitching['team_flag'] == 'home' and game['home_id'] == player_id) or (h_o_a_pitching['team_flag'] == 'away' and game['away_id'] == player_id):
					# strikeots
					strikeouts += int(h_o_a_pitching['so'])
					# hits plus walks
					hits_plus_walks += int(h_o_a_pitching['h']) + int(h_o_a_pitching['bb'])
					# earned runs 
					earned_runs += int(h_o_a_pitching['er'])
					
					# check for win
					# "F" appears to be FINAL
					# "O" appears to be OVER (but not final) 
					# Might be additional cases to check for with postponments, delays etc. 
					if game['status_ind'] == "F" or game['status_ind'] == "O":
						# are we the home team and did we win? 
						if h_o_a_pitching['team_flag'] == 'home' and game['home_id'] == player_id:
							# in baseball, you win if you score more runs than the other team. 
							if game['linescore']['home_team_runs'] > game['linescore']['away_team_runs']:
								points += 3
						# are we the away team and did we win? 
						if h_o_a_pitching['team_flag'] == 'away' and game['away_id'] == player_id:
							# in baseball, you win if you score more runs than the other team. 
							if game['linescore']['away_team_runs'] > game['linescore']['home_team_runs']:
								points += 3
					
					if 0 <= strikeouts <= 5:
						points += 0
					if 6 <= strikeouts <= 7:
						points += 1
					if 8 <= strikeouts <= 9:
						points += 2	
					if 10 <= strikeouts <= 12:
						points += 3
					if 13 <= strikeouts <= 15:
						points += 5
					if 16 <= strikeouts <= 19:
						points += 7
					if strikeouts >= 20:
						points += 10
					
					if earned_runs == 0:
						points += 7
					if earned_runs == 1:
						points += 5
					if earned_runs == 2:
						points += 3
					if earned_runs == 3:
						points += 2
					if earned_runs == 4:
						points += 1
					if earned_runs >= 5:
						points += 0
						
					if hits_plus_walks == 0:
						points += 20
					if hits_plus_walks == 1:
						points += 16
					if hits_plus_walks == 2:
						points += 12
					if 3 <= hits_plus_walks <= 4:
						points += 8
					if 5 <= hits_plus_walks <= 7:
						points += 4	
					if 8 <= hits_plus_walks <= 10:
						points += 2
					if 11 <= hits_plus_walks <= 12:
						points += 1
					if hits_plus_walks >= 13:
						points += 0		

	return int(points)

# grab the fantasy baseball schedule by league_id
# example URL: http://www.mlb.com/fantasylookup/json/named.fb_index_schedule.bam?league_id=1514
def get_schedule_data(league_id):
	schedule_url = "http://www.mlb.com/fantasylookup/json/named.fb_index_schedule.bam?league_id=" + league_id
	schedule_response = urllib.urlopen(schedule_url)
	schedule_data = json.loads(schedule_response.read())

	# trim out the headers and return that chunk
	return schedule_data["fb_index_schedule"]["queryResults"]["row"]	
	
# inital processing of schedule json data 
# returns: this_week dictionary 
# 	key: matchup_id
#	value: another dictionary containing K:V pairs for 
#		home_team (id)
#		home_points
#		home_name
# 		away_team (id)
#		away_points
# 		away_name
def process_schedule_data(schedule_data):
	
	# get list of team names
	team_name_list = []
	
	# max completed week - for making sure thechart data array doesn't include zeros
	max_week = 0
	
	# loop through each and every season's matchup returned from the json data
	for matchup in schedule_data:
		
		# if any geniuses use illegal characters in their names, filter them out and replace with Butt
		# reference: http://stackoverflow.com/questions/20078816/replace-non-ascii-characters-with-a-single-space?lq=1
		matchup["team_name"] = ''.join([i if ord(i) < 128 else 'Butt' for i in matchup["team_name"] ])
		
		# build list of team names
		if matchup["team_name"] not in team_name_list:
			team_name_list.append(matchup["team_name"])
		
		# get max completed week 
		if int(matchup['period_id'])-10 > max_week and matchup['is_final'] == 'y':
			max_week = int(matchup['period_id'])-10
		
		# look for matchups flagged as current - this is what we want to work with for this_week
		# for completed games, look for "is_final"==y"
		if matchup["is_current"] == "y":
			
			if matchup["matchup_set"] not in matchup_id_array:
				matchup_id_array.append(matchup["matchup_set"])
			
			# build a list of k:v pairs where k= matchup_id and v= stats about the game.
			
			# CASE #1 - the matchup ID detected is already in this_week, which means we need to add the missing home or away team stats. 
			if matchup["matchup_set"] in this_week:
				if matchup["is_home"] == "y":
					this_week[matchup["matchup_set"]]['home_team'] = matchup["team_id"]
					this_week[matchup["matchup_set"]]['home_points'] = int(matchup["team_points"])
					this_week[matchup["matchup_set"]]['home_name'] = matchup["team_name"]
				if matchup["is_home"] == "n":	
					this_week[matchup["matchup_set"]]['away_team'] = matchup["team_id"]
					this_week[matchup["matchup_set"]]['away_points'] = int(matchup["team_points"])
					this_week[matchup["matchup_set"]]['away_name'] = matchup["team_name"]
			# CASE #2 - the matchup ID detected is not yet in this_week, so we assign the home or away team the data. 
			if matchup["matchup_set"] not in this_week:
				if matchup["is_home"] == "y":
					this_week[matchup["matchup_set"]] = {'home_team' : matchup["team_id"], 'home_points' : int(matchup["team_points"]),	'home_name' : matchup["team_name"]  } 
				if matchup["is_home"] == "n":
					this_week[matchup["matchup_set"]] = {'away_team' : matchup["team_id"], 'away_points' : int(matchup["team_points"]), 'away_name' : matchup["team_name"] }  		
			# in all cases, make sure the period_id is properly assigned. This is a requirement to look up fantasy rosters. 
			this_week[matchup["matchup_set"]]['period_id'] = matchup["period_id"]
		
	# start putting together a data set for completed weeks
	# this variable has an empty list for every week (0-23)
	score_chart_data = [[0 for i in range(12)] for i in range(max_week)]
	
	#sort the list of team names alphabetically
	team_name_list.sort()
	
	for matchup in schedule_data:
		# remove fields I don't need for the chart
		# the fields we KEEP are:
		# team_name
		# period_name
		# team_points
		# period_id - subtract 10 because week 1 is period_id=11
		if matchup['is_final'] == 'y':
			period_id = int(matchup['period_id'])
			# insert team's score (when alphabeticaly sorted) into right column in score table
			score_chart_data[period_id-11][team_name_list.index(matchup['team_name'])] = int(matchup['team_points'])	
		
	# insert list of team names into score chart data array 
	score_chart_data.insert(0,team_name_list)

	return this_week, score_chart_data
	
# grab a roster json object from mlb and return it 
# needs a fantasy baseball team id and the period id. 
def get_roster_data_for_team(team_id, period_id):
	roster_url = "http://www.mlb.com/fantasylookup/json/named.fb_team_lineup.bam?&team_id=" + team_id + "&period_id=" + period_id
	roster_response = urllib.urlopen(roster_url)
	roster_data = json.loads(roster_response.read())
	
	# trim out the junk headers and return data 
	return roster_data["fb_team_lineup"]["queryResults"]["row"]
	
# h_o_a = 'home' or 'away' 	
# returns:
# this_week (modified)
# ultimately this function is helping update this_week with the total points for the live day
def get_player_points_for_today(h_o_a, roster_data, this_week, match, super_boxscore):
	
	#team_array = []
	# create a spot in the dictionary for team lineup data
	this_week[match][h_o_a+"_lineup"] = {}
	
	for player in roster_data:
		# add up all the batter scores - pitcher points don't count. Exclude bench for now. 
		if player["slot"] <> "Bn" and player["slot"] <> "P" and player["slot"] <> "DL":
			
			# get batter's points for today. 
			bat_points = get_batter_score(player["player_id"], super_boxscore)
			
			# add batter's points to today's running total. 
			this_week[match][h_o_a+"_points"] = this_week[match][h_o_a+"_points"] + bat_points
			
			# add batter's points to this_week's roster
			this_week[match][h_o_a+"_lineup"][player["player_id"]] = { 'points' : bat_points, 'name' : player["player_name"], 'position' : player["slot_val"] } 
		
		# get the pitching staff score 
		if player["slot"] <> "Bn" and player["slot"] == "P" and player["slot"] <> "DL":
			
			# get pitching staff's points 
			pitch_points = get_pitching_score(player["player_id"], super_boxscore)
			
			# add pitching staff pointst to running weekly total 
			this_week[match][h_o_a+"_points"] = this_week[match][h_o_a+"_points"] + pitch_points
			
			# build player data to append to this_week object.
			this_week[match][h_o_a+"_lineup"][player["player_id"]] = {'points' : pitch_points, 'name' : player["player_name"], 'position' : player["slot_val"] } 
			
	# attach the whole lineup dictionary to this_week
	#this_week[match][h_o_a+'_lineup'] = team_array
	
	return this_week
	
# more processing on this_week variable. grab per-player points for today and previous days 
# return a modified this_week dictionary packed with sweet juicy information
def get_player_points_this_week(this_week, super_boxscore):
	
	# loop through every unique fantasy match this week and start to grab points for each player
	for match in this_week:
		#home_team_array = []
		#away_team_array = []
				
		# home team ======================================
		roster_data = get_roster_data_for_team(this_week[match]['home_team'], this_week[match]['period_id'])
		# get today's player points
		this_week = get_player_points_for_today('home', roster_data, this_week, match, super_boxscore)
		#===================================================
		
		# away team ======================================
		roster_data = get_roster_data_for_team(this_week[match]['away_team'], this_week[match]['period_id'])
		# get today's player points
		this_week = get_player_points_for_today('away', roster_data, this_week, match, super_boxscore)
		#===================================================
	
	return this_week

# this function prints the lineup for the home or away team.
# h_o_a = 'home' or 'away', affects what order things are printed
def print_lineup(lineup, h_o_a):
	
	# print lineup positions in this order. 
	print_order = ['C','1B','2B','3B','SS','OF','OF','OF','Util','PS']
	# track printed players so we don't double print the outfielders
	printed_players = []
	
	print '<details>Today\'s Lineup & Scores<br>'
	
	for i in range(len(print_order)):
		for player in lineup:
			if print_order[i] == lineup[player]['position'] and lineup[player]['name'] not in printed_players:	
				print '<span class="player">'
				
				if h_o_a == 'away':
					print str(lineup[player]['name']) 
				if h_o_a == 'home':
					print str(lineup[player]['points'])
				
				print ' - '
				print str(lineup[player]['position']) 
				print ' - '
				
				if h_o_a == 'away':
					print str(lineup[player]['points']) 
				if h_o_a == 'home':
					print str(lineup[player]['name'])
				
				print '</span><br>'
				# this is how we don't double-print any outfielders 
				printed_players.append(lineup[player]['name'])
	print '</details></td>'

def print_headers(jscode):
	# show some HTML while the rest of the script loads data - that's why this is up here. 
	print "Content-type: text/html\n\n";
	print "<html><head>";
	
	print """
	<script src="https://www.google.com/jsapi" type="text/javascript"></script>
	<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
	  <script type="text/javascript">
	    google.charts.load('current', {'packages':['corechart']});
      	google.charts.setOnLoadCallback(drawChart);
	    
	    function drawChart() {
	      %(jscode)s
	      
	      var chart = new google.visualization.LineChart(document.getElementById('table_div_jscode'));
	      
	      var options = {
	          title: 'Fantasy Baseball Points Back (Lower = Better)',
	          curveType: 'function',
	          legend: { position: 'none' },
	          chartArea: {left:40,top:40,width:'95%%',height:'90%%'},
	          hAxis: { viewWindowMode: 'maximized',
	          			minValue: '1', 
	          			viewWindow: {min:'1'}},
	          vAxis: { viewWindowMode: 'maximized'},
	          
       		 };
        
	      chart.draw(jscode_data, options);
	      
	    }
	  </script>
	""" % vars()
	
	print "<link rel='stylesheet' type='text/css' href='style.css'>";
	print "<title>MLB.com Fantasy Is Garbage On Mobile</title>";
	print '<meta charset="utf-8" />'
	print '<meta name="viewport" content="initial-scale=1.0; maximum-scale=1.0; width=device-width;">';
	print "</head><body>";
	print '<div class="table-title"> <h3>A-R.I.M.P.J CURRENT SCORES <br> Team Points are WEEKLY<br>Player Points are TODAY</h3> </div>'

# from here: http://stackoverflow.com/questions/5655708/python-most-elegant-way-to-intersperse-a-list-with-an-element
def intersperse(seq, value):
    res = [value] * (2 * len(seq))
    res[::2] = seq
    return res

def print_google_chart(score_chart_data):

	# grab team names out of this array			
	team_names = score_chart_data[0]

	# remove first row because it's a list of strings (team names)
	del score_chart_data[0]

	# build data table legend info. 
	description = [(team_names[x],"number",team_names[x]) for x in range(len(team_names))]

	description =  intersperse(description, '')
	#print description
	# promising troubleshooting http://stackoverflow.com/questions/27944921/how-to-use-custom-properties-with-python-google-charts-aviz-api-py
	for item in description: 
		#print 'item', item, 'description', description.index(item)
		# detect empty strings http://stackoverflow.com/questions/9573244/most-elegant-way-to-check-if-the-string-is-empty-in-python
		if not item:
			#print 'hello', description.index(item), description[description.index(item)-1]
			description[description.index(item)] = (description[description.index(item)-1][0] + str('-anno'),"string","",dict({'type':'string', 'role':'annotation'}))
			#description[description.index(item)] = "{type:'string', role:'annotation'}"
			#description.insert(0, ("annotation","string","annotation"))
	
	#print description

	all_zeros = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
	completed_weeks = []
	
	for week in score_chart_data:
		if week is not all_zeros:
			#print sizeof(week)
			#print week, score_chart_data.index(week)
			# add in the spacers for Google Charts annotations	
			#print week
			completed_weeks.append(week)
	
	#print completed_weeks
	
	formatted_weeks = []

	# calculate running points totals - doesn't include week in progress. 
	for week in completed_weeks:
		num_weeks = len(completed_weeks)-1
		
		index = completed_weeks.index(week)
		#print index
		
		week = intersperse(week, '')
		
		#print week
		
		completed_weeks[index] = week
		
		if index > 0:
			for team_score in week:
				#if isinstance(team_score, int):
				if team_score <> '':
					#print team_score, week.index(team_score), completed_weeks[index][week.index(team_score)]
					#if week.index(team_score) > 0:
					# add this week's points to last week's points if week > 0
					completed_weeks[index][week.index(team_score)] = team_score + completed_weeks[index-1][week.index(team_score)]
				#if team_score == '' and index == num_weeks:
				#	print week
	
	# moved from preceeding for loop
	#week.insert(0,"Week " + str(completed_weeks.index(week)+1))
			
	#print completed_weeks		
				
	# now calculate points back. Doesn't include the week in progress. 
	points_back = completed_weeks	
	for week in points_back: 
		
		#max_week = max(filter(bool,week[1:]))
		max_week = max(filter(bool,week))
		
		#print week, max_week
		
		# since every week is a running total, subtracting this week's team_points
		# from max_week gives us points_back for every team. 
		for team_points in week:
			if team_points <> '':
			#if not team_points:
				points_back[points_back.index(week)][week.index(team_points)] = max_week - team_points
			if team_points == '' and points_back.index(week) == len(points_back)-1:
				#print week.index(team_points)
				points_back[points_back.index(week)][week.index(team_points)] = team_names[(week.index(team_points)-1)/2]
		week.insert(0,"Week " + str(points_back.index(week)+1))
	
	#print points_back
	#print team_names
	
	
	# insert a row for the Week
	description.insert(0, ("Week","string","Week"))
	# set up Google Charts gviz_api chart info. 
	data_table = gviz_api.DataTable(description)
	#print points_back
	data_table.LoadData(points_back)
	#print data_table.ToJSCode("jscode_data", columns_order=(team_names ), )
	
	#print description
	
	# Create a JavaScript code string.
	team_names = list(itertools.chain.from_iterable(zip(team_names,[s + '-anno' for s in team_names])))
	team_names.insert(0,'Week')
	#print team_names
	# this is what I need to buid.... I think. 
	# YES, YES, YES  --> TODO TODO TODO WORK ON BUILDING THIS PROPER TEAM NAMES STRING. 
	#team_names = ['Week', u'2 n da Posey,1 n da Pujol', '2 n da Posey,1 n da Pujol-anno', u"Can't Cutch This", 'anno2', u'Cruz Missiles', 'anno3', u'Lick My Pujols', 'anno4', u'Majestic Beavers', 'anno5', u"Melvin doesn't like a BJ", 'anno6', u'Puig Destroyer', 'anno7', u'SMELL THE GLOVE', 'anno8', u'The Bonairs 2000', 'anno9', u'TrouserTrout', 'anno10', u'Tulogit to Quit', 'anno11', u'Votto649', 'anno12']
	
	#print points_back
	# create the Java code to hide in the HTML headers to call the chart. 
	jscode = data_table.ToJSCode("jscode_data", columns_order=(team_names ), )
	
	# now print HTML headers; these are formatted with Google Charts API stuff. 
	print_headers(jscode)


###################################################
# START OF THE MEAT'N'POTATOES PART OF THE SCRIPT #
###################################################

# get fantasy baseball league schedule data from MLB 
schedule_data = get_schedule_data(league_id)
timing_log.append(['step 1 (after schedule data grab): ' + str(datetime.datetime.now() - start_time)])

# populate this_week with some initial data from the schedule
# also, get data to print a fancy chart. 
this_week, score_chart_data = process_schedule_data(schedule_data)
timing_log.append(['step 2 (after process schedule data): ' + str(datetime.datetime.now() - start_time)])

# print google chart 
if show_chart:
	print_google_chart(score_chart_data)


# get list of real (non-fantasy) games being played today
gid_list = get_todays_gid_xml_blob()

# get the super boxscore that contains everything happening TODAY
super_boxscore = build_monster_boxscore(gid_list)
timing_log.append(['step 2.5 (after get super boxscore): ' + str(datetime.datetime.now() - start_time)])

# now fill up this_week with per-player point scoring information
this_week = get_player_points_this_week(this_week, super_boxscore)
timing_log.append(['step 3 (after get player points this week): ' + str(datetime.datetime.now() - start_time)])

# debug data in hidden html comment
# NOTE - DO NOT PRINT in live script - big drag on page load time. 
'''
pp = pprint.PrettyPrinter(indent=1)
print '<!-- debugging info: '
pp.pprint(super_boxscore)
print '-->'
'''

# quickly turn on or off all the output for debugging
if 1==1:
	#===========PUT CONTENT BELOW THIS POINT
	print '<table class="table-fill"> <thead> <tr> <th class="text-right" width="300px">Away</th> <th class="text-left" width="300px">Home</th> </tr> </thead>'
	
	for matchup in this_week:
		# row header
		print '<tbody class="table-hover"> <tr>'
		
		# away team data
		print '<td class="text-right" width="300px">'
		print '<summary><a href="http://www.mlb.com/mlb/fantasy/fb/team/index.jsp?team_id=' + str(this_week[matchup]['away_team']) + '">'
		print this_week[matchup]['away_name']
		print '</a>'
		print ' - <b>' + str(this_week[matchup]['away_points']) + '</b></summary>'
		print_lineup(this_week[matchup]['away_lineup'], 'away')
		
		# home team data
		print '<td class="text-left" width="300px">'
		print '<summary><b>' + str(this_week[matchup]['home_points']) + ' - </b>'
		print '<a href="http://www.mlb.com/mlb/fantasy/fb/team/index.jsp?team_id=' + str(this_week[matchup]['home_team']) + '">'
		print this_week[matchup]['home_name']
		print '</a></summary>'
		print_lineup(this_week[matchup]['home_lineup'], 'home')	
		print '</td>'
		
		# row closer
		print '</tr>'
	
	print '</tbody> </table>';
	
	print '<div> <h4>REFRESH PAGE TO RELOAD SCORES</h4> </div>'
	
	print '<div> <h4><a class="footer" href="https://github.com/b-neufeld/mlb-fantasy-checker">about & source</a></h4> </div>'
	
	timing_log.append(['step 4 (end of script): ' + str(datetime.datetime.now() - start_time)])
	
	print '<!--'
	pp = pprint.PrettyPrinter(indent=1)
	pp.pprint(timing_log)
	print '-->'
	
	print '<div> <h4> Loaded in ' + str(datetime.datetime.now() - start_time) + '</h4></div>'
	
	# This div is where the Google Chart is served to. 
	if show_chart:
		print """
		
		    <div id="table_div_jscode" style="width: 100%; height: 600px" ></div>
		 """
	
	#===========PUT CONTENT ABOVE THIS POINT
	print "</body></html>";
