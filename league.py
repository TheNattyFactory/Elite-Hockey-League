"""Persistent Genesis league operations. SQLite is authoritative; exhibition remains read-only."""
import json, sqlite3, hashlib
from pathlib import Path
from contextlib import contextmanager
from genesis import make_world, simulate, FRANCHISES, sign_human
import offseason
import market
import coaching
import careers
import appearance

class League:
 def __init__(self,path='ehl.db'):
  self.path=str(path)
  with self.db() as db:
   db.executescript('''
   CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY CHECK(id=1),season INTEGER NOT NULL,phase TEXT NOT NULL,sim_day INTEGER NOT NULL);
   CREATE TABLE IF NOT EXISTS teams(code TEXT PRIMARY KEY,name TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS players(id INTEGER PRIMARY KEY,team TEXT,group_name TEXT,position TEXT,name TEXT,human INTEGER NOT NULL,profile TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS games(id INTEGER PRIMARY KEY,sim_day INTEGER NOT NULL,home TEXT NOT NULL,away TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'SCHEDULED',home_score INTEGER,away_score INTEGER,shootout INTEGER DEFAULT 0,seed TEXT,UNIQUE(home,away,sim_day));
   CREATE TABLE IF NOT EXISTS events(game_id INTEGER NOT NULL,seq INTEGER NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(game_id,seq));
   CREATE TABLE IF NOT EXISTS standings(team TEXT PRIMARY KEY,gp INTEGER DEFAULT 0,w INTEGER DEFAULT 0,l INTEGER DEFAULT 0,otl INTEGER DEFAULT 0,pts INTEGER DEFAULT 0,gf INTEGER DEFAULT 0,ga INTEGER DEFAULT 0,rw INTEGER DEFAULT 0);
   CREATE TABLE IF NOT EXISTS contracts(player_id INTEGER PRIMARY KEY,team TEXT NOT NULL,xp_per_game REAL NOT NULL,season INTEGER NOT NULL);
   CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,player_id INTEGER NOT NULL,team TEXT NOT NULL,details TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS player_game_stats(game_id INTEGER,player_id INTEGER,goals INTEGER DEFAULT 0,assists INTEGER DEFAULT 0,shots INTEGER DEFAULT 0,PRIMARY KEY(game_id,player_id));
   CREATE TABLE IF NOT EXISTS xp_ledger(game_id INTEGER,player_id INTEGER,amount REAL NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(game_id,player_id,reason));
   ''')
   _install_playoff_schema(db)
   offseason.install(db)
   market.install(db)
   coaching.install(db)
   careers.install(db)
 @contextmanager
 def db(self):
  conn=sqlite3.connect(self.path,timeout=15)
  conn.row_factory=sqlite3.Row
  conn.execute('PRAGMA foreign_keys=ON')
  try:
   yield conn
   conn.commit()
  except BaseException:
   conn.rollback()
   raise
  finally:
   conn.close()
 def initialize(self,seed='GENESIS'):
  with self.db() as db:
   if db.execute('SELECT 1 FROM state').fetchone():raise ValueError('League already initialized; refusing to reset history')
   world=make_world(seed)
   db.execute("INSERT INTO state VALUES(1,1,'REGULAR',0)")
   for code,t in world.items():
    db.execute('INSERT INTO teams VALUES(?,?)',(code,t['name']))
    db.execute('INSERT INTO standings(team) VALUES(?)',(code,))
    for p in t['roster']:
     db.execute('INSERT INTO players VALUES(?,?,?,?,?,?,?)',(p['id'],code,p['group'],p['position'],p['name'],0,json.dumps(p,sort_keys=True)))
   # Every unordered pairing six times, alternating venue: 28*6=168 games.
   codes=list(world);matches=[]
   for i,a in enumerate(codes):
    for b in codes[i+1:]:
     for n in range(6):matches.append((a,b) if n%2==0 else (b,a))
   # Stable interleaving, with at most one game per team on a sim day.
   import random
   random.Random(str(seed)).shuffle(matches)
   day=1
   while matches:
    used=set();remaining=[]
    for home,away in matches:
     if home in used or away in used:remaining.append((home,away));continue
     db.execute("INSERT INTO games(sim_day,home,away) VALUES(?,?,?)",(day,home,away));used.update((home,away))
    matches=remaining;day+=1
  return self.summary()
 def world(self,db):
  teams={code:{'name':name,'roster':[]} for code,name in FRANCHISES.items()}
  for row in db.execute('SELECT profile FROM players WHERE team IS NOT NULL ORDER BY id'):
   p=json.loads(row['profile']);teams[p['team']]['roster'].append(p)
  return teams
 def summary(self):
  with self.db() as db:
   state=db.execute('SELECT * FROM state').fetchone()
   if not state:return {'initialized':False}
   games=db.execute('SELECT status,COUNT(*) n FROM games WHERE season=? GROUP BY status',(state['season'],)).fetchall()
   return {'initialized':True,'season':state['season'],'phase':state['phase'],'sim_day':state['sim_day'],'games':{r['status']:r['n'] for r in games},'players':db.execute('SELECT COUNT(*) FROM players WHERE team IS NOT NULL').fetchone()[0]}
 def schedule(self):
  with self.db() as db:return [dict(r) for r in db.execute('SELECT * FROM games WHERE season=(SELECT season FROM state WHERE id=1) ORDER BY sim_day,id')]
 def standings(self):
  with self.db() as db:return [dict(r) for r in db.execute('SELECT * FROM standings ORDER BY pts DESC,rw DESC,(gf-ga) DESC,gf DESC,team')]
 def sign(self,code,name,position='C',player_id=None,look=None):
  if code not in FRANCHISES:raise ValueError('Unknown team')
  if not isinstance(name,str) or not 2<=len(name.strip())<=48:raise ValueError('Name must be 2–48 characters')
  look=appearance.validate(look or {})
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   if not db.execute('SELECT 1 FROM state').fetchone():raise ValueError('Initialize league first')
   world=self.world(db)
   if player_id is None:player_id=db.execute('SELECT COALESCE(MAX(id),0)+1 FROM players').fetchone()[0]
   if db.execute('SELECT 1 FROM players WHERE id=?',(player_id,)).fetchone():raise ValueError('Player ID already exists')
   result=sign_human(world,code,name,position,player_id)
   old=result['displaced'];new=result['signed'];new['appearance']=look
   old['team']=None
   db.execute('UPDATE players SET team=NULL,profile=? WHERE id=?',(json.dumps(old,sort_keys=True),old['id']))
   db.execute('INSERT INTO players VALUES(?,?,?,?,?,?,?)',(new['id'],code,new['group'],new['position'],new['name'],1,json.dumps(new,sort_keys=True)))
   db.execute('INSERT INTO contracts VALUES(?,?,?,1)',(new['id'],code,.25))
   db.execute('INSERT OR REPLACE INTO contract_terms VALUES(?,1)',(new['id'],))
   db.execute('INSERT INTO transactions(kind,player_id,team,details) VALUES(?,?,?,?)',('CPU_REPLACED',old['id'],code,json.dumps({'replaced_by':new['id']})))
   db.execute('INSERT INTO transactions(kind,player_id,team,details) VALUES(?,?,?,?)',('SIGNED',new['id'],code,json.dumps({'displaced':old['id']})))
  return result
 def summary_season(self,db):
  return db.execute("SELECT season FROM state WHERE id=1").fetchone()[0]
 def next_game(self):
  with self.db() as db:
   db.execute('BEGIN IMMEDIATE')
   state=db.execute('SELECT phase FROM state WHERE id=1').fetchone()
   if not state or state['phase']!='REGULAR':raise ValueError('Regular season not active')
   game=db.execute("SELECT * FROM games WHERE season=(SELECT season FROM state WHERE id=1) AND status='SCHEDULED' ORDER BY sim_day,id LIMIT 1").fetchone()
   if not game:raise ValueError('No scheduled games remaining')
   world=self.world(db)
   seed=f'EHL-S{self.summary_season(db)}-GAME-{game["id"]}'
   result=simulate(seed=seed,home=game['home'],away=game['away'],world=world,gameplans=coaching.gameplans(db,world,[game['home'],game['away']]))
   home,away=game['home'],game['away'];hs=result['score'][home];ass=result['score'][away]
   if hs==ass:raise ValueError('Game did not resolve')
   db.execute("UPDATE games SET status='FINAL',home_score=?,away_score=?,shootout=?,seed=? WHERE id=? AND status='SCHEDULED'",(hs,ass,int(result['shootout']),seed,game['id']))
   for event in result['events']:
    db.execute('INSERT INTO events VALUES(?,?,?)',(game['id'],event['sequence'],json.dumps(event,sort_keys=True)))
   winner=home if hs>ass else away;loser=away if winner==home else home
   for team,opp,scored,allowed in ((home,away,hs,ass),(away,home,ass,hs)):
    win=team==winner;otl=not win and (result['shootout'] or any(e['period']==4 and e['event_type']=='GOAL' for e in result['events']))
    regulation_win=win and not (result['shootout'] or any(e['period']==4 and e['event_type']=='GOAL' for e in result['events']))
    db.execute('UPDATE standings SET gp=gp+1,w=w+?,l=l+?,otl=otl+?,pts=pts+?,gf=gf+?,ga=ga+?,rw=rw+? WHERE team=?',(int(win),int(not win and not otl),int(otl),2 if win else int(otl),scored,allowed,int(regulation_win),team))
   stats={}
   for e in result['events']:
    typ=e['event_type'];pid=e.get('primary_player_id')
    if typ in ('GOAL','SHOT_ATTEMPT') and pid:
     s=stats.setdefault(pid,[0,0,0]);s[0 if typ=='GOAL' else 2]+=1
    if typ=='GOAL' and e.get('secondary_player_id'):
     stats.setdefault(e['secondary_player_id'],[0,0,0])[1]+=1
   for pid,(goals,assists,shots) in stats.items():db.execute('INSERT INTO player_game_stats VALUES(?,?,?,?,?)',(game['id'],pid,goals,assists,shots))
   for team in (home,away):
    for p in world[team]['roster']:
     if not p['human']:continue
     pid=p['id'];s=stats.get(pid,[0,0,0]);contract=db.execute('SELECT xp_per_game FROM contracts WHERE player_id=?',(pid,)).fetchone()
     salary=float(contract[0]) if contract else .25
     amount=round(salary+min(.75,s[0]*.4+s[1]*.2+s[2]*.02),2)
     db.execute('INSERT INTO xp_ledger VALUES(?,?,?,?)',(game['id'],pid,amount,'GAME'))
   db.execute('UPDATE state SET sim_day=? WHERE id=1',(game['sim_day'],))
   remaining=db.execute("SELECT COUNT(*) FROM games WHERE season=(SELECT season FROM state WHERE id=1) AND status='SCHEDULED'").fetchone()[0]
   if not remaining:db.execute("UPDATE state SET phase='PLAYOFFS' WHERE id=1")
  return {'id':game['id'],'home':home,'away':away,'home_score':hs,'away_score':ass,'events':len(result['events']),'reconciled':result['reconciled']}
 def advance(self,count=1):
  if not 1<=count<=168:raise ValueError('Count must be 1..168')
  out=[]
  for _ in range(count):
   if not self.summary().get('games',{}).get('SCHEDULED'):break
   out.append(self.next_game())
  return {'simulated':len(out),'last':out[-1] if out else None,'state':self.summary()}
 def game(self,id):
  with self.db() as db:
   row=db.execute('SELECT * FROM games WHERE id=?',(id,)).fetchone()
   if not row:raise ValueError('Game not found')
   result=dict(row)
   result['events']=[json.loads(e['payload']) for e in db.execute('SELECT payload FROM events WHERE game_id=? ORDER BY seq',(id,))]
   return result

# Postseason operations intentionally keep the regular-season standings immutable.
def _install_playoff_schema(db):
 db.executescript('''
 CREATE TABLE IF NOT EXISTS playoff_seeds(season INTEGER NOT NULL,seed INTEGER NOT NULL,team TEXT NOT NULL,PRIMARY KEY(season,seed),UNIQUE(season,team));
 CREATE TABLE IF NOT EXISTS playoff_series(id INTEGER PRIMARY KEY AUTOINCREMENT,season INTEGER NOT NULL,round INTEGER NOT NULL,high_seed INTEGER NOT NULL,low_seed INTEGER NOT NULL,best_of INTEGER NOT NULL,high_wins INTEGER NOT NULL DEFAULT 0,low_wins INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'ACTIVE',winner TEXT);
 CREATE TABLE IF NOT EXISTS playoff_games(id INTEGER PRIMARY KEY AUTOINCREMENT,series_id INTEGER NOT NULL,game_number INTEGER NOT NULL,home TEXT NOT NULL,away TEXT NOT NULL,home_score INTEGER NOT NULL,away_score INTEGER NOT NULL,seed TEXT NOT NULL,events_json TEXT NOT NULL,UNIQUE(series_id,game_number));
 CREATE TABLE IF NOT EXISTS champions(season INTEGER PRIMARY KEY,team TEXT NOT NULL,runner_up TEXT NOT NULL,decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
 ''')

def _league_seed_playoffs(self):
 from playoffs import seed_qualifiers
 with self.db() as db:
  db.execute('BEGIN IMMEDIATE')
  state=db.execute('SELECT * FROM state WHERE id=1').fetchone()
  if not state or state['phase']!='PLAYOFFS':raise ValueError('Finish the regular season first')
  if db.execute('SELECT 1 FROM playoff_seeds WHERE season=? LIMIT 1',(state['season'],)).fetchone():raise ValueError('Playoffs already seeded')
  seeds=seed_qualifiers([dict(r) for r in db.execute('SELECT * FROM standings')])
  for n,team in enumerate(seeds,1):db.execute('INSERT INTO playoff_seeds VALUES(?,?,?)',(state['season'],n,team))
  for a,b in ((3,6),(4,5)):
   db.execute('INSERT INTO playoff_series(season,round,high_seed,low_seed,best_of) VALUES(?,?,?,?,5)',(state['season'],1,a,b))
 return self.playoff_summary()

def _league_playoff_summary(self):
 with self.db() as db:
  return {'seeds':[dict(r) for r in db.execute('SELECT * FROM playoff_seeds WHERE season=(SELECT season FROM state WHERE id=1) ORDER BY seed')],
          'series':[dict(r) for r in db.execute('SELECT * FROM playoff_series WHERE season=(SELECT season FROM state WHERE id=1) ORDER BY round,id')],
          'champions':[dict(r) for r in db.execute('SELECT * FROM champions ORDER BY season DESC')]}

def _league_next_playoff(self):
 with self.db() as db:
  db.execute('BEGIN IMMEDIATE')
  state=db.execute('SELECT * FROM state WHERE id=1').fetchone()
  if not state or state['phase']!='PLAYOFFS':raise ValueError('Playoffs not active')
  seeds={r['seed']:r['team'] for r in db.execute('SELECT * FROM playoff_seeds WHERE season=?',(state['season'],))}
  if len(seeds)!=6:raise ValueError('Seed playoffs first')
  series=db.execute("SELECT * FROM playoff_series WHERE season=? AND status='ACTIVE' ORDER BY round,id LIMIT 1",(state['season'],)).fetchone()
  if series is None:
   last=db.execute('SELECT MAX(round) FROM playoff_series WHERE season=?',(state['season'],)).fetchone()[0]
   if last==1:
    finished=list(db.execute('SELECT * FROM playoff_series WHERE round=1 AND status="COMPLETE"'))
    if len(finished)!=2:raise ValueError('First round incomplete')
    survivors=[1,2]+[next(k for k,v in seeds.items() if v==r['winner']) for r in finished]
    survivors.sort()
    for a,b in ((survivors[0],survivors[3]),(survivors[1],survivors[2])):
     db.execute('INSERT INTO playoff_series(season,round,high_seed,low_seed,best_of) VALUES(?,?,?,?,7)',(state['season'],2,a,b))
   elif last==2:
    finished=list(db.execute('SELECT * FROM playoff_series WHERE round=2 AND status="COMPLETE"'))
    if len(finished)!=2:raise ValueError('Semifinals incomplete')
    finalists=sorted(next(k for k,v in seeds.items() if v==r['winner']) for r in finished)
    db.execute('INSERT INTO playoff_series(season,round,high_seed,low_seed,best_of) VALUES(?,?,?,?,7)',(state['season'],3,*finalists))
   elif last==3:
    final=db.execute('SELECT * FROM playoff_series WHERE round=3 AND status="COMPLETE"').fetchone()
    if not final:raise ValueError('Final incomplete')
    loser=seeds[final['low_seed']] if final['winner']==seeds[final['high_seed']] else seeds[final['high_seed']]
    db.execute('INSERT INTO champions(season,team,runner_up) VALUES(?,?,?)',(state['season'],final['winner'],loser))
    db.execute("UPDATE state SET phase='AWARDS' WHERE id=1")
    return {'complete':True,'champion':final['winner'],'runner_up':loser}
   else:raise ValueError('No active playoff series')
   series=db.execute("SELECT * FROM playoff_series WHERE season=? AND status='ACTIVE' ORDER BY round,id LIMIT 1",(state['season'],)).fetchone()
  high,low=seeds[series['high_seed']],seeds[series['low_seed']]
  n=series['high_wins']+series['low_wins']+1
  # Higher seed receives games 1,2,5,7; lower seed games 3,4,6.
  high_home=n in (1,2,5,7)
  home,away=(high,low) if high_home else (low,high)
  seed=f'EHL-PLAYOFF-S{state["season"]}-SERIES{series["id"]}-G{n}'
  world=self.world(db)
  result=simulate(seed=seed,home=home,away=away,world=world,playoff=True,gameplans=coaching.gameplans(db,world,[home,away]))
  hs,ass=result['score'][home],result['score'][away]
  # Genesis engine has shootouts; postseason cannot. Resolve tied regulation
  # using seeded 20-minute overtime periods with the existing event model.
  # Existing simulate() always resolves games; reject SO until playoff-specific engine exists.
  if result['shootout']:
   raise ValueError('Playoff engine requires sudden-death overtime; shootout result rejected')
  db.execute('INSERT INTO playoff_games(series_id,game_number,home,away,home_score,away_score,seed,events_json) VALUES(?,?,?,?,?,?,?,?)',
             (series['id'],n,home,away,hs,ass,seed,json.dumps(result['events'])))
  high_win=(home if hs>ass else away)==high
  column='high_wins' if high_win else 'low_wins'
  db.execute(f'UPDATE playoff_series SET {column}={column}+1 WHERE id=?',(series['id'],))
  updated=db.execute('SELECT * FROM playoff_series WHERE id=?',(series['id'],)).fetchone()
  needed=series['best_of']//2+1
  if updated['high_wins']>=needed or updated['low_wins']>=needed:
   winner=high if updated['high_wins']>=needed else low
   db.execute("UPDATE playoff_series SET status='COMPLETE',winner=? WHERE id=?",(winner,series['id']))
  return {'series_id':series['id'],'round':series['round'],'game_number':n,'home':home,'away':away,'home_score':hs,'away_score':ass,'winner':home if hs>ass else away}

League.seed_playoffs=_league_seed_playoffs
League.playoff_summary=_league_playoff_summary
League.next_playoff=_league_next_playoff
League.finalize_awards=lambda self:offseason.finalize(self)
League.advance_season=lambda self:offseason.advance_season(self)
League.history=lambda self:offseason.history(self)


def _league_playoff_game(self, game_id):
 with self.db() as db:
  row=db.execute("SELECT pg.*,ps.round,ps.season FROM playoff_games pg JOIN playoff_series ps ON ps.id=pg.series_id WHERE pg.id=?",(game_id,)).fetchone()
  if not row:raise ValueError('Playoff game not found')
  result=dict(row);result['events']=json.loads(result.pop('events_json'));return result

def _league_playoff_games(self):
 with self.db() as db:
  return [dict(r) for r in db.execute("SELECT pg.id,pg.series_id,pg.game_number,pg.home,pg.away,pg.home_score,pg.away_score,ps.round,ps.season FROM playoff_games pg JOIN playoff_series ps ON ps.id=pg.series_id ORDER BY pg.id DESC LIMIT 100")]

League.playoff_game=_league_playoff_game
League.playoff_games=_league_playoff_games
