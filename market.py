"""M6 human contract offers and offseason free agency. Local sandbox, no authentication."""
import json
RATES=(0.25,0.30,0.35,0.40,0.45)

def install(db):
 db.executescript('''
 CREATE TABLE IF NOT EXISTS contract_offers(id INTEGER PRIMARY KEY AUTOINCREMENT,player_id INTEGER NOT NULL,team TEXT NOT NULL,rate REAL NOT NULL,seasons INTEGER NOT NULL,season INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
 CREATE UNIQUE INDEX IF NOT EXISTS offer_pending_unique ON contract_offers(player_id,team) WHERE status='PENDING';
 CREATE TABLE IF NOT EXISTS contract_terms(player_id INTEGER PRIMARY KEY,end_season INTEGER NOT NULL);
 ''')
 for r in db.execute('SELECT player_id,season FROM contracts').fetchall():
  db.execute('INSERT OR IGNORE INTO contract_terms VALUES(?,?)',(r['player_id'],r['season']))

def free_agents(league):
 with league.db() as db:
  return [dict(r) for r in db.execute('SELECT id,name,position FROM players WHERE human=1 AND team IS NULL ORDER BY id')]

def offers(league,player_id=None):
 with league.db() as db:
  q='SELECT * FROM contract_offers';params=()
  if player_id is not None:q+=' WHERE player_id=?';params=(player_id,)
  return [dict(r) for r in db.execute(q+' ORDER BY id DESC',params)]

def offer(league,player_id,team,rate,seasons):
 from genesis import FRANCHISES
 if team not in FRANCHISES:raise ValueError('Unknown team')
 if rate not in RATES:raise ValueError('Unsupported salary tier')
 if not 1<=seasons<=4:raise ValueError('Contract term must be 1-4 seasons')
 with league.db() as db:
  db.execute('BEGIN IMMEDIATE')
  st=db.execute('SELECT * FROM state').fetchone()
  if not st or st['phase'] not in ('FREE_AGENCY','REGULAR'):raise ValueError('Offers unavailable in this phase')
  p=db.execute('SELECT * FROM players WHERE id=? AND human=1',(player_id,)).fetchone()
  if not p:raise ValueError('Human player not found')
  if p['team'] is not None:raise ValueError('Player is already signed')
  if db.execute("SELECT 1 FROM contract_offers WHERE player_id=? AND team=? AND status='PENDING'",(player_id,team)).fetchone():raise ValueError('Pending offer already exists')
  db.execute('INSERT INTO contract_offers(player_id,team,rate,seasons,season) VALUES(?,?,?,?,?)',(player_id,team,rate,seasons,st['season']))
  return {'offer_id':db.execute('SELECT last_insert_rowid()').fetchone()[0],'status':'PENDING'}

def respond(league,offer_id,accept):
 from genesis import sign_human
 with league.db() as db:
  db.execute('BEGIN IMMEDIATE')
  row=db.execute('SELECT * FROM contract_offers WHERE id=?',(offer_id,)).fetchone()
  if not row or row['status']!='PENDING':raise ValueError('Offer not pending')
  player=db.execute('SELECT * FROM players WHERE id=? AND human=1',(row['player_id'],)).fetchone()
  if not player or player['team'] is not None:raise ValueError('Player not free agent')
  if not accept:
   db.execute("UPDATE contract_offers SET status='DECLINED' WHERE id=?",(offer_id,))
   return {'offer_id':offer_id,'status':'DECLINED'}
  world=league.world(db)
  # Reuse deterministic CPU displacement; do not displace humans.
  signed=sign_human(world,row['team'],player['name'],player['position'],player['id'])
  old=signed['displaced'];new=signed['signed'];old['team']=None
  db.execute('UPDATE players SET team=NULL,profile=? WHERE id=?',(json.dumps(old,sort_keys=True),old['id']))
  new['human']=True
  db.execute('UPDATE players SET team=?,group_name=?,profile=? WHERE id=?',(row['team'],new['group'],json.dumps(new,sort_keys=True),player['id']))
  season=db.execute('SELECT season FROM state').fetchone()[0]
  db.execute('INSERT INTO contracts(player_id,team,xp_per_game,season) VALUES(?,?,?,?)',(player['id'],row['team'],row['rate'],season))
  db.execute('INSERT OR REPLACE INTO contract_terms VALUES(?,?)',(player['id'],season+row['seasons']-1))
  db.execute("UPDATE contract_offers SET status='ACCEPTED' WHERE id=?",(offer_id,))
  db.execute("UPDATE contract_offers SET status='WITHDRAWN' WHERE player_id=? AND status='PENDING'",(player['id'],))
  db.execute('INSERT INTO transactions(kind,player_id,team,details) VALUES(?,?,?,?)',('CPU_REPLACED',old['id'],row['team'],json.dumps({'replaced_by':player['id']})))
  db.execute('INSERT INTO transactions(kind,player_id,team,details) VALUES(?,?,?,?)',('SIGNED',player['id'],row['team'],json.dumps({'offer_id':offer_id,'rate':row['rate'],'end_season':season+row['seasons']-1})))
  return {'offer_id':offer_id,'status':'ACCEPTED','team':row['team'],'player_id':player['id'],'displaced_cpu_id':old['id']}

def expire_for_new_season(db,new):
 expired=[]
 for r in db.execute('SELECT c.player_id,c.team,t.end_season,p.profile FROM contracts c JOIN players p ON p.id=c.player_id LEFT JOIN contract_terms t ON t.player_id=c.player_id WHERE p.human=1').fetchall():
  if r['end_season'] is not None and r['end_season']>=new:continue
  p=json.loads(r['profile']);p['team']=None
  db.execute('UPDATE players SET team=NULL,profile=? WHERE id=?',(json.dumps(p,sort_keys=True),r['player_id']))
  db.execute('DELETE FROM contracts WHERE player_id=?',(r['player_id'],))
  db.execute('DELETE FROM contract_terms WHERE player_id=?',(r['player_id'],))
  db.execute('INSERT INTO transactions(kind,player_id,team,details) VALUES(?,?,?,?)',('EXPIRED',r['player_id'],r['team'],json.dumps({'new_season':new})))
  expired.append(r['player_id'])
 return expired
