"""Validated cosmetic appearance, stored inside the canonical player profile."""
import json
OPTIONS = {'skin': ['fair','light','medium','tan','deep'], 'hair': ['buzz','short','sidepart','curly','long','bald'], 'hair_color': ['black','brown','blond','red','gray'], 'eyes': ['round','narrow','wide'], 'eye_color': ['brown','blue','green','gray'], 'face': ['oval','square','round'], 'facial_hair': ['none','stubble','mustache','beard'], 'helmet': ['on','off']}
DEFAULT = {'skin':'light','hair':'short','hair_color':'brown','eyes':'round','eye_color':'brown','face':'oval','facial_hair':'none','helmet':'on'}
def validate(values):
 if not isinstance(values,dict):raise ValueError('Appearance must be an object')
 if set(values)-set(OPTIONS):raise ValueError('Unknown appearance option')
 result=DEFAULT.copy()
 for key,value in values.items():
  if not isinstance(value,str) or value not in OPTIONS[key]:raise ValueError('Invalid '+key)
  result[key]=value
 return result
def update(league,player_id,values):
 with league.db() as db:
  db.execute('BEGIN IMMEDIATE')
  row=db.execute('SELECT profile,human FROM players WHERE id=?',(int(player_id),)).fetchone()
  if not row or not row['human']:raise ValueError('Only human athletes can customize appearance')
  p=json.loads(row['profile']);p['appearance']=validate(values)
  db.execute('UPDATE players SET profile=? WHERE id=?',(json.dumps(p,sort_keys=True),player_id))
 return {'player_id':int(player_id),'appearance':p['appearance']}
