"""EHL Genesis M5: auditable awards, season archive and safe rollover."""
import market
import json, random
from genesis import make_world, FRANCHISES


def install(db):
    columns={r[1] for r in db.execute('PRAGMA table_info(games)')}
    if 'season' not in columns:
        db.execute('ALTER TABLE games ADD COLUMN season INTEGER NOT NULL DEFAULT 1')
    # M4's uniqueness constraint lacked season; rebuild once to preserve all historical games.
    game_sql=db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='games'").fetchone()[0]
    if 'UNIQUE(home,away,sim_day)' in game_sql:
        db.execute('ALTER TABLE games RENAME TO games_m4_backup')
        db.execute(game_sql.replace('CREATE TABLE games','CREATE TABLE games').replace('UNIQUE(home,away,sim_day)','UNIQUE(season,home,away,sim_day)'))
        db.execute('INSERT INTO games SELECT * FROM games_m4_backup')
        db.execute('DROP TABLE games_m4_backup')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS season_archives(
      season INTEGER PRIMARY KEY, champion TEXT NOT NULL,
      standings_json TEXT NOT NULL, awards_json TEXT NOT NULL,
      archived_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS player_season_archives(
      season INTEGER NOT NULL, player_id INTEGER NOT NULL,
      games INTEGER NOT NULL, goals INTEGER NOT NULL,
      assists INTEGER NOT NULL, shots INTEGER NOT NULL,
      PRIMARY KEY(season,player_id));
    CREATE TABLE IF NOT EXISTS offseason_transactions(
      id INTEGER PRIMARY KEY AUTOINCREMENT, season INTEGER NOT NULL,
      player_id INTEGER NOT NULL, action TEXT NOT NULL,
      details TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    ''')


def awards(db,season):
    # Use only games from the season being archived, not career totals.
    rows=[dict(r) for r in db.execute('''
       SELECT p.id,p.name,p.team,COUNT(s.game_id) gp,
              SUM(s.goals) goals,SUM(s.assists) assists,SUM(s.shots) shots
       FROM player_game_stats s JOIN games g ON g.id=s.game_id
       JOIN players p ON p.id=s.player_id
       WHERE g.season=? AND g.status='FINAL'
       GROUP BY p.id ORDER BY p.id''',(season,))]
    for r in rows:
        db.execute('INSERT INTO player_season_archives VALUES(?,?,?,?,?,?)',
                   (season,r['id'],r['gp'],r['goals'],r['assists'],r['shots']))
    if not rows:return {'scoring_champion':None,'goal_leader':None,'assist_leader':None}
    def pick(key):
        p=max(rows,key=lambda r:(r[key],r['goals']+r['assists'], -r['id']))
        return {'player_id':p['id'],'name':p['name'],'team_at_archive':p['team'],
                'value':p[key]}
    return {'scoring_champion':_points_leader(rows), 'goal_leader':pick('goals'), 'assist_leader':pick('assists')}


def _points_leader(rows):
    p=max(rows,key=lambda r:(r['goals']+r['assists'],r['goals'],-r['id']))
    return {'player_id':p['id'],'name':p['name'],'team_at_archive':p['team'],
            'value':p['goals']+p['assists']}


def finalize(league):
    with league.db() as db:
        db.execute('BEGIN IMMEDIATE')
        state=db.execute('SELECT * FROM state WHERE id=1').fetchone()
        if not state or state['phase']!='AWARDS':
            raise ValueError('Championship must finish before awards')
        season=state['season']
        champion=db.execute('SELECT team FROM champions WHERE season=?',(season,)).fetchone()
        if not champion:raise ValueError('No champion recorded')
        if db.execute('SELECT 1 FROM season_archives WHERE season=?',(season,)).fetchone():
            raise ValueError('Season already archived')
        table=[dict(r) for r in db.execute('SELECT * FROM standings ORDER BY pts DESC,rw DESC,(gf-ga) DESC,gf DESC,team')]
        if len(table)!=8 or sum(t['gp'] for t in table)!=336:
            raise ValueError('Standings do not represent a completed 42-game season')
        honorees=awards(db,season)
        db.execute('INSERT INTO season_archives(season,champion,standings_json,awards_json) VALUES(?,?,?,?)',
                   (season,champion['team'],json.dumps(table),json.dumps(honorees)))
        db.execute("UPDATE state SET phase='RETIREMENT' WHERE id=1")
        return {'season':season,'champion':champion['team'],'awards':honorees,'phase':'RETIREMENT'}


def advance_season(league):
    with league.db() as db:
        db.execute('BEGIN IMMEDIATE')
        state=db.execute('SELECT * FROM state WHERE id=1').fetchone()
        if not state or state['phase']!='RETIREMENT':
            raise ValueError('Archive awards before advancing season')
        old=state['season'];new=old+1
        if not db.execute('SELECT 1 FROM season_archives WHERE season=?',(old,)).fetchone():
            raise ValueError('Missing season archive')
        # Humans are never retired or displaced automatically.
        cpu_retired=[]
        for r in db.execute('SELECT * FROM players WHERE team IS NOT NULL ORDER BY id').fetchall():
            p=json.loads(r['profile']);p['age']=int(p['age'])+1
            if not r['human'] and p['age']>=38:
                roll=random.Random(f'EHL-RETIRE-{old}-{r["id"]}').random()
                if roll<min(.8,.12+(p['age']-38)*.12):
                    cpu_retired.append(r['id'])
                    p['team']=None
                    db.execute('UPDATE players SET team=NULL,profile=? WHERE id=?',(json.dumps(p,sort_keys=True),r['id']))
                    db.execute('INSERT INTO offseason_transactions(season,player_id,action,details) VALUES(?,?,?,?)',
                               (old,r['id'],'CPU_RETIRED',json.dumps({'age':p['age']})))
                    continue
            db.execute('UPDATE players SET profile=? WHERE id=?',(json.dumps(p,sort_keys=True),r['id']))
        expired_humans=market.expire_for_new_season(db,new)
        # Fill retirement gaps using deterministic new CPU prospects.
        world=make_world(f'EHL-ROOKIES-S{new}')
        next_id=db.execute('SELECT COALESCE(MAX(id),0)+1 FROM players').fetchone()[0]
        added=[]
        for team in FRANCHISES:
            existing=[json.loads(r['profile']) for r in db.execute('SELECT profile FROM players WHERE team=?',(team,))]
            for group,target in [('F',13),('D',7),('G',3)]:
                missing=target-sum(p['group']==group for p in existing)
                if missing<0:raise ValueError('Roster overflow: '+team)
                available=[p for p in world[team]['roster'] if p['group']==group]
                for prospect in available[:missing]:
                    prospect=dict(prospect);prospect['id']=next_id;next_id+=1
                    prospect['age']=18+((prospect['id']+new)%6)
                    numbers={p['number'] for p in existing}
                    prospect['number']=next(n for n in range(1,99) if n not in numbers)
                    existing.append(prospect);added.append(prospect['id'])
                    db.execute('INSERT INTO players VALUES(?,?,?,?,?,?,?)',
                               (prospect['id'],team,group,prospect['position'],prospect['name'],0,json.dumps(prospect,sort_keys=True)))
                    db.execute('INSERT INTO offseason_transactions(season,player_id,action,details) VALUES(?,?,?,?)',
                               (old,prospect['id'],'CPU_DRAFTED',json.dumps({'team':team})))
        # Contracts renew for the Genesis sandbox; full free agency follows in M6.
        db.execute('UPDATE contracts SET season=?',(new,))
        db.execute('DELETE FROM standings')
        for team in FRANCHISES:db.execute('INSERT INTO standings(team) VALUES(?)',(team,))
        # Keep historical games/events, use new game IDs and season-specific queries.
        matches=[]
        codes=list(FRANCHISES)
        for i,a in enumerate(codes):
            for b in codes[i+1:]:
                for n in range(6):matches.append((a,b) if n%2==0 else (b,a))
        random.Random(f'EHL-SCHEDULE-S{new}').shuffle(matches)
        day=1
        while matches:
            used=set();remaining=[]
            for home,away in matches:
                if home in used or away in used:remaining.append((home,away));continue
                db.execute('INSERT INTO games(sim_day,home,away,season) VALUES(?,?,?,?)',(day,home,away,new))
                used.update((home,away))
            matches=remaining;day+=1
        db.execute("UPDATE state SET season=?,phase='REGULAR',sim_day=0 WHERE id=1",(new,))
        return {'season':new,'games_scheduled':168,'cpu_retired':len(cpu_retired),
                'cpu_drafted':len(added),'expired_human_contracts':expired_humans,'phase':'REGULAR'}


def history(league):
    with league.db() as db:
        return [{'season':r['season'],'champion':r['champion'],
                 'standings':json.loads(r['standings_json']),
                 'awards':json.loads(r['awards_json'])}
                for r in db.execute('SELECT * FROM season_archives ORDER BY season DESC')]
