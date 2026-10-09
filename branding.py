"""Canonical franchise identity, keyed by stable team code."""
from genesis import FRANCHISES
COLORS={
 'ATL':('#b52832','#f7b547'),'BOS':('#123b60','#c6d4e1'),'CHI':('#bb3333','#e7e7e7'),
 'DAL':('#245d4b','#f0b748'),'DEN':('#3969a8','#e8f0fa'),'DET':('#b74432','#b6b7bc'),
 'MIN':('#3584a5','#ecf3f8'),'NSH':('#b57a27','#193b5a')}

def teams():
 return {code:{'code':code,'name':name,'primary':COLORS[code][0],
                'secondary':COLORS[code][1],'jersey':{'home':'dark','away':'light'},
                'mark':code} for code,name in FRANCHISES.items()}

def roster(league,code):
 if code not in COLORS:raise ValueError('Unknown franchise')
 with league.db() as db:
  import json
  rows=db.execute('SELECT id,profile FROM players WHERE team=? ORDER BY group_name,position,name,id',(code,)).fetchall()
  players=[dict(json.loads(r['profile']),id=r['id']) for r in rows]
 return {'team':teams()[code],'players':players}
