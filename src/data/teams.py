TEAMS = {  # abbr: (bbref full name, conf, division)
 'ATL':('Atlanta Hawks','E','Southeast'),'BOS':('Boston Celtics','E','Atlantic'),'BKN':('Brooklyn Nets','E','Atlantic'),
 'CHA':('Charlotte Hornets','E','Southeast'),'CHI':('Chicago Bulls','E','Central'),'CLE':('Cleveland Cavaliers','E','Central'),
 'DAL':('Dallas Mavericks','W','Southwest'),'DEN':('Denver Nuggets','W','Northwest'),'DET':('Detroit Pistons','E','Central'),
 'GSW':('Golden State Warriors','W','Pacific'),'HOU':('Houston Rockets','W','Southwest'),'IND':('Indiana Pacers','E','Central'),
 'LAC':('Los Angeles Clippers','W','Pacific'),'LAL':('Los Angeles Lakers','W','Pacific'),'MEM':('Memphis Grizzlies','W','Southwest'),
 'MIA':('Miami Heat','E','Southeast'),'MIL':('Milwaukee Bucks','E','Central'),'MIN':('Minnesota Timberwolves','W','Northwest'),
 'NOP':('New Orleans Pelicans','W','Southwest'),'NYK':('New York Knicks','E','Atlantic'),'OKC':('Oklahoma City Thunder','W','Northwest'),
 'ORL':('Orlando Magic','E','Southeast'),'PHI':('Philadelphia 76ers','E','Atlantic'),'PHX':('Phoenix Suns','W','Pacific'),
 'POR':('Portland Trail Blazers','W','Northwest'),'SAC':('Sacramento Kings','W','Pacific'),'SAS':('San Antonio Spurs','W','Southwest'),
 'TOR':('Toronto Raptors','E','Atlantic'),'UTA':('Utah Jazz','W','Northwest'),'WAS':('Washington Wizards','E','Southeast')}
NAME2ABBR = {v[0]: k for k, v in TEAMS.items()}
ESPN_FIX = {'GS':'GSW','NO':'NOP','NY':'NYK','SA':'SAS','UTAH':'UTA','WSH':'WAS','PHO':'PHX'}
