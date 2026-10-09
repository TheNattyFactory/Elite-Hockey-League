"""M7 coach sandbox. Explicit approvals and validated lineup assignments."""
import json
from genesis import FRANCHISES, lineup

POSITIONS=tuple(f'{p}{n}' for n in range(1,5) for p in ('LW','C','RW'))+tuple(f'{p}{n}' for n in range(1,4) for p in ('LD','RD'))+('STARTER','BACKUP')

def install(db):
 db.executescript("""
 CREATE TABLE IF NOT EXISTS coach_applications(id INTEGER PRIMARY KEY AUTOINCREMENT,team TEXT NOT NULL,applicant TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
 CREATE UNIQUE INDEX IF NOT EXISTS one_pending_coach_application ON coach_applications(team,applicant) WHERE status='PENDING';
 CREATE TABLE IF NOT EXISTS coach_assignments(team TEXT PRIMARY KEY,applicant TEXT NOT NULL,application_id INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS coach_lineups(team TEXT NOT NULL,season INTEGER NOT NULL,position TEXT NOT NULL,player_id INTEGER NOT NULL,PRIMARY KEY(team,season,position),UNIQUE(team,season,player_id));
 CREATE TABLE IF NOT EXISTS coach_tactics(team TEXT NOT NULL,season INTEGER NOT NULL,forecheck TEXT NOT NULL DEFAULT 'BALANCED',offense TEXT NOT NULL DEFAULT 'BALANCED',defense TEXT NOT NULL DEFAULT 'BALANCED',physicality TEXT NOT NULL DEFAULT 'BALANCED',goalie_usage TEXT NOT NULL DEFAULT 'STANDARD',PRIMARY KEY(team,season));
 """)

def apply(league,team,applicant):
 if team not in FRANCHISES or not applicant.strip() or len(applicant)>80:raise ValueError('Invalid application')
 with league.db() as db:
  db.execute('BEGIN IMMEDIATE')
  if not db.execute('SELECT 1 FROM state').fetchone():raise ValueError('Initialize league first')
  if db.execute('SELECT 1 FROM coach_assignments WHERE team=?',(team,)).fetchone():raise ValueError('Franchise already has coach')
  db.execute('INSERT INTO coach_applications(team,applicant) VALUES(?,?)',(team,applicant.strip()))
  return {'application_id':db.execute('SELECT last_insert_rowid()').fetchone()[0],'status':'PENDING'}

def approve(league,application_id):
 with league.db() as db:
  db.execute('BEGIN IMMEDIATE')
  row=db.execute('SELECT * FROM coach_applications WHERE id=? AND status="PENDING"',(application_id,)).fetchone()
  if not row:raise ValueError('Application not pending')
  if db.execute('SELECT 1 FROM coach_assignments WHERE team=?',(row['team'],)).fetchone():raise ValueError('Team already assigned')
  if db.execute('SELECT 1 FROM coach_assignments WHERE applicant=?',(row['applicant'],)).fetchone():raise ValueError('Applicant already coaching')
  db.execute('INSERT INTO coach_assignments VALUES(?,?,?)',(row['team'],row['applicant'],application_id))
  db.execute('UPDATE coach_applications SET status="APPROVED" WHERE id=?',(application_id,))
  db.execute('UPDATE coach_applications SET status="CLOSED" WHERE team=? AND status="PENDING"',(row['team'],))
  return {'team':row['team'],'coach':row['applicant'],'status':'APPROVED'}

def applications(league):
 with league.db() as db:return [dict(r) for r in db.execute('SELECT * FROM coach_applications ORDER BY id DESC')]

def _ensure_coach(db,team,applicant):
 row=db.execute('SELECT applicant FROM coach_assignments WHERE team=?',(team,)).fetchone()
 if not row or row['applicant']!=applicant:raise ValueError('Not assigned coach of franchise')

def default_lineup(roster):
 selected=lineup({'roster':roster});f=selected['forwards'];d=selected['defense'];g=selected['goalies']
 return {**{f'{pos}{n}':f[(n-1)*3+i]['id'] for n in range(1,5) for i,pos in enumerate(('LW','C','RW'))},**{f'{pos}{n}':d[(n-1)*2+i]['id'] for n in range(1,4) for i,pos in enumerate(('LD','RD'))},'STARTER':g[0]['id'],'BACKUP':g[1]['id']}

def validate(roster,assignments):
 if set(assignments)!=set(POSITIONS):raise ValueError('Exactly 20 positions required')
 ids=list(assignments.values())
 if len(set(ids))!=20:raise ValueError('Duplicate player in lineup')
 players={p['id']:p for p in roster}
 for slot,pid in assignments.items():
  p=players.get(pid)
  if not p:raise ValueError('Player not on franchise roster')
  if slot.startswith(('LW','RW','C')) and p['group']!='F':raise ValueError('Forward slot requires forward')
  if slot.startswith(('LD','RD')) and p['group']!='D':raise ValueError('Defense slot requires defense')
  if slot in ('STARTER','BACKUP') and p['group']!='G':raise ValueError('Goalie slot requires goalie')
 return True

def save_lineup(league,team,applicant,assignments):
 if team not in FRANCHISES:raise ValueError('Unknown franchise')
 with league.db() as db:
  db.execute('BEGIN IMMEDIATE');_ensure_coach(db,team,applicant)
  season=db.execute('SELECT season FROM state').fetchone()[0]
  roster=league.world(db)[team]['roster'];assignments={str(k):int(v) for k,v in assignments.items()}
  validate(roster,assignments)
  db.execute('DELETE FROM coach_lineups WHERE team=? AND season=?',(team,season))
  db.executemany('INSERT INTO coach_lineups VALUES(?,?,?,?)',[(team,season,k,v) for k,v in assignments.items()])
  return {'team':team,'season':season,'lineup':assignments}

def save_tactics(league,team,applicant,tactics):
 allowed={'forecheck':('CONSERVATIVE','BALANCED','AGGRESSIVE'),'offense':('POSSESSION','BALANCED','RUSH','SHOOT_FIRST'),'defense':('PROTECT_NET','BALANCED','PRESSURE_PUCK'),'physicality':('LOW','BALANCED','AGGRESSIVE'),'goalie_usage':('WORKHORSE','STANDARD','TANDEM')}
 if set(tactics)!=set(allowed) or any(tactics[k] not in values for k,values in allowed.items()):raise ValueError('Invalid tactics')
 with league.db() as db:
  db.execute('BEGIN IMMEDIATE');_ensure_coach(db,team,applicant)
  season=db.execute('SELECT season FROM state').fetchone()[0]
  db.execute('INSERT OR REPLACE INTO coach_tactics VALUES(?,?,?,?,?,?,?)',(team,season,*[tactics[k] for k in allowed]))
  return {'team':team,'season':season,'tactics':tactics}

def dashboard(league,team):
 if team not in FRANCHISES:raise ValueError('Unknown franchise')
 with league.db() as db:
  state=db.execute('SELECT season FROM state').fetchone()
  if not state:raise ValueError('Initialize league first')
  season=state['season'];roster=league.world(db)[team]['roster']
  coach=db.execute('SELECT applicant FROM coach_assignments WHERE team=?',(team,)).fetchone()
  rows=db.execute('SELECT position,player_id FROM coach_lineups WHERE team=? AND season=?',(team,season)).fetchall()
  chosen={r['position']:r['player_id'] for r in rows}
  tactics=db.execute('SELECT * FROM coach_tactics WHERE team=? AND season=?',(team,season)).fetchone()
  return {'team':team,'season':season,'coach':coach['applicant'] if coach else None,'roster':roster,'lineup':chosen or default_lineup(roster),'tactics':dict(tactics) if tactics else None}


def gameplans(db,world,teams):
 """Load and validate current season coaching choices inside the simulation transaction."""
 state=db.execute('SELECT season FROM state WHERE id=1').fetchone()
 if not state:return {}
 season=state['season'];out={}
 for team in teams:
  saved=db.execute('SELECT position,player_id FROM coach_lineups WHERE team=? AND season=?',(team,season)).fetchall()
  assignments={r['position']:r['player_id'] for r in saved}
  if assignments:
   try:validate(world[team]['roster'],assignments)
   except ValueError:assignments={}  # Fall back safely after trades/retirement
  row=db.execute('SELECT * FROM coach_tactics WHERE team=? AND season=?',(team,season)).fetchone()
  tactics={k:row[k] for k in ('forecheck','offense','defense','physicality','goalie_usage')} if row else {}
  out[team]={'lineup':assignments,'tactics':tactics}
 return out
