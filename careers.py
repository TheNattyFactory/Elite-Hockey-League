"""M9 player career views and atomic attribute progression; SQLite is authoritative."""
import json
from genesis import SKATER, GOALIE

MAX_ATTRIBUTE = 99

def profile(league, player_id):
    with league.db() as db:
        row=db.execute('SELECT * FROM players WHERE id=?',(int(player_id),)).fetchone()
        if not row: raise ValueError('Player not found')
        p=json.loads(row['profile'])
        season=db.execute('SELECT season FROM state WHERE id=1').fetchone()
        stats=[dict(r) for r in db.execute('''SELECT g.season, COUNT(*) games, SUM(s.goals) goals, SUM(s.assists) assists, SUM(s.shots) shots
            FROM player_game_stats s JOIN games g ON g.id=s.game_id WHERE s.player_id=? GROUP BY g.season ORDER BY g.season''',(player_id,))]
        balance=db.execute('SELECT COALESCE(SUM(amount),0) FROM xp_ledger WHERE player_id=?',(player_id,)).fetchone()[0]
        spent=db.execute('SELECT COALESCE(SUM(cost),0) FROM training_ledger WHERE player_id=?',(player_id,)).fetchone()[0]
        contract=db.execute('SELECT * FROM contracts WHERE player_id=?',(player_id,)).fetchone()
        return {'player':p,'season':season[0] if season else None,'xp_balance':round(float(p.get('xp',0))+balance-spent,2),
                'earned_xp':round(float(balance),2),'spent_xp':round(float(spent),2),
                'contract':dict(contract) if contract else None,'season_stats':stats,
                'career':{'games':sum(s['games'] for s in stats),'goals':sum(s['goals'] or 0 for s in stats),'assists':sum(s['assists'] or 0 for s in stats),'shots':sum(s['shots'] or 0 for s in stats)}}

def train(league,player_id,attribute,points=1):
    points=int(points)
    if not 1<=points<=25:raise ValueError('Train 1 to 25 points at a time')
    with league.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT profile,human FROM players WHERE id=?',(int(player_id),)).fetchone()
        if not row or not row['human']:raise ValueError('Only human players can train')
        p=json.loads(row['profile']);allowed=GOALIE if p['group']=='G' else SKATER
        if attribute not in allowed:raise ValueError('Invalid attribute for position')
        old=p['attributes'][attribute]
        if old+points>MAX_ATTRIBUTE:raise ValueError('Attribute cap is 99 in Genesis')
        # Simple transparent rising cost; total calculated before mutation.
        cost=sum(1+(old+i)//20 for i in range(points))
        earned=db.execute('SELECT COALESCE(SUM(amount),0) FROM xp_ledger WHERE player_id=?',(player_id,)).fetchone()[0]
        spent=db.execute('SELECT COALESCE(SUM(cost),0) FROM training_ledger WHERE player_id=?',(player_id,)).fetchone()[0]
        if round(float(p.get('xp',0))+earned-spent,4)<cost:raise ValueError('Insufficient XP')
        p['attributes'][attribute]=old+points
        db.execute('UPDATE players SET profile=? WHERE id=?',(json.dumps(p,sort_keys=True),player_id))
        db.execute('INSERT INTO training_ledger(player_id,attribute,old_value,new_value,cost) VALUES(?,?,?,?,?)',(player_id,attribute,old,old+points,cost))
    return profile(league,player_id)

def install(db):
    db.execute('''CREATE TABLE IF NOT EXISTS training_ledger(id INTEGER PRIMARY KEY AUTOINCREMENT,
       player_id INTEGER NOT NULL,attribute TEXT NOT NULL,old_value INTEGER NOT NULL,
       new_value INTEGER NOT NULL,cost REAL NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
