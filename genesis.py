"""Deterministic Original Eight rosters and player-driven possession exhibitions."""
from dataclasses import dataclass, asdict
import random, hashlib

FRANCHISES = {
 'ATL':'Atlanta Firebirds','BOS':'Boston Admirals','CHI':'Chicago Railers',
 'DAL':'Dallas Stampede','DEN':'Denver Summit','DET':'Detroit Forge',
 'MIN':'Minneapolis Frost','NSH':'Nashville Copperheads'}
SKATER = ('SHT','PWR','PAS','HND','OIQ','SPD','ACC','AGI','DIQ','CHK','STK','BLK','STR','STA','CMP','FO')
GOALIE = ('REF','POS','GLV','BLK','REC','LOW','HGH','LAT','PCK','VIS','CMP','STA')
FIRST = ('Evan','Miles','Connor','Liam','Nolan','Jack','Owen','Caleb','Ryan','Mason','Logan','Tyler','Adam','Cole','Dylan','Noah','Alex','Grant','Wyatt','Leo','Ben','Aiden','Parker','Luke','Finn','Carter','Julian','Reid','Brady','Blake')
LAST = ('Mercer','Bennett','Fletcher','Hayes','Coleman','Brooks','Stone','Frost','Miller','Reed','Turner','Sullivan','Carter','Hughes','Ward','Parker','Bishop','Hunter','Morgan','Collins','Price','Wells','Cooper','Dawson','Knight','Walker','Harris','Murray','Lane','Barker')

def make_world(seed='GENESIS'):
 rng=random.Random(str(seed)); teams={}; ident=0
 for code,name in FRANCHISES.items():
  roster=[]; numbers=set()
  for group,count in [('F',13),('D',7),('G',3)]:
   for index in range(count):
    ident+=1
    pos=('C','LW','RW')[index%3] if group=='F' else group
    tier=rng.choices(['ELITE','TOP','REGULAR','DEPTH','FRINGE'],[3,12,50,30,5])[0]
    midpoint={'ELITE':86,'TOP':76,'REGULAR':65,'DEPTH':54,'FRINGE':44}[tier]
    attrs={a:max(10,min(99,round(rng.gauss(midpoint,9)))) for a in (GOALIE if group=='G' else SKATER)}
    if group=='F': attrs['FO']=max(10,min(99,attrs['FO']+(8 if pos=='C' else -12)))
    number=rng.choice([n for n in range(1,99) if n not in numbers]);numbers.add(number)
    roster.append({'id':ident,'name':f'{rng.choice(FIRST)} {rng.choice(LAST)}','team':code,'group':group,'position':pos,'age':rng.triangular(18,36,24)//1,'number':number,'hand':rng.choice(('L','R')),'tier':tier,'attributes':attrs,'human':False})
  teams[code]={'name':name,'roster':roster}
 return teams

def check_world(world):
 assert len(world)==8
 ids=[]
 for code,team in world.items():
  roster=team['roster']; assert len(roster)==23
  assert {g:sum(p['group']==g for p in roster) for g in ('F','D','G')}=={'F':13,'D':7,'G':3}
  assert len({p['number'] for p in roster})==23
  ids.extend(p['id'] for p in roster)
 assert len(set(ids))==184
 return True

def lineup(team):
 r=team['roster']; forwards=[p for p in r if p['group']=='F']; defense=[p for p in r if p['group']=='D']; goalies=[p for p in r if p['group']=='G']
 forwards.sort(key=lambda p:sum(p['attributes'][k] for k in ('OIQ','PAS','SHT','SPD')),reverse=True)
 defense.sort(key=lambda p:sum(p['attributes'][k] for k in ('DIQ','STK','BLK','PAS')),reverse=True)
 goalies.sort(key=lambda p:sum(p['attributes'][k] for k in ('REF','POS','REC','LAT')),reverse=True)
 return {'forwards':forwards[:12],'defense':defense[:6],'goalies':goalies[:2],'scratches':forwards[12:]+defense[6:]+goalies[2:]}

def sign_human(world,code,name,position='C',player_id=100000):
 assert code in world and position in ('C','LW','RW','D','G')
 group='F' if position in ('C','LW','RW') else position
 team=world[code]; eligible=[p for p in team['roster'] if p['group']==group and not p['human']]
 if not eligible: raise ValueError('No CPU slot available; human players are protected')
 dressed_ids={p['id'] for g in ('forwards','defense','goalies') for p in lineup(team)[g]}
 eligible.sort(key=lambda p:(p['id'] in dressed_ids,sum(p['attributes'].values()),-p['age'],p['id']))
 old=eligible[0];number=old['number'];team['roster'].remove(old)
 human={'id':player_id,'name':name,'team':code,'group':group,'position':position,'age':18,'number':number,'hand':'R','tier':'HUMAN','attributes':{a:10 for a in (GOALIE if group=='G' else SKATER)},'human':True,'xp':50.0}
 team['roster'].append(human)
 return {'signed':human,'displaced':old}

def skill(player,*keys):return sum(player['attributes'][k] for k in keys)/len(keys)

def simulate(seed='EHL-FIRST-PUCK',home='ATL',away='NSH',world=None,playoff=False,gameplans=None):
 assert home!=away
 world=world or make_world('GENESIS');check_world(world)
 rng=random.Random(str(seed)); gameplans=gameplans or {}
 def chosen(code):
  plan=gameplans.get(code) or {}; assignments=plan.get('lineup') or {}
  if not assignments:return lineup(world[code])
  roster={p['id']:p for p in world[code]['roster']}
  ids=[assignments[f'{pos}{n}'] for n in range(1,5) for pos in ('LW','C','RW')]
  ds=[assignments[f'{pos}{n}'] for n in range(1,4) for pos in ('LD','RD')]
  gs=[assignments[k] for k in ('STARTER','BACKUP')]
  return {'forwards':[roster[i] for i in ids],'defense':[roster[i] for i in ds],'goalies':[roster[i] for i in gs], 'scratches':[p for p in roster.values() if p['id'] not in ids+ds+gs]}
 home_line=chosen(home);away_line=chosen(away);lines={home:home_line,away:away_line}
 score={home:0,away:0};shots={home:0,away:0};saves={home:0,away:0};events=[];touches=[];seq=0
 def emit(period,clock,kind,team=None,**data):
  nonlocal seq
  seq+=1;events.append({'sequence':seq,'period':period,'clock_seconds':clock,'event_type':kind,'team_id':team,'score_home':score[home],'score_away':score[away],**data})
 def contest(a,b,ak,bk,adv=0):
  delta=(skill(a,*ak)-skill(b,*bk))/55+adv
  return rng.random()<max(.12,min(.88,.5+delta))
 def attack(team,period,clock):
  other=away if team==home else home; offense=lines[team];defense=lines[other]
  attacker=rng.choice(offense['forwards']); defender=rng.choice(defense['defense']); goalie=defense['goalies'][0]
  emit(period,clock,'POSSESSION',team,primary_player_id=attacker['id'])
  offense_tactics=(gameplans.get(team) or {}).get('tactics') or {}
  defense_tactics=(gameplans.get(other) or {}).get('tactics') or {}
  entry_adv={'CONSERVATIVE':-.035,'BALANCED':0,'AGGRESSIVE':.035}.get(defense_tactics.get('forecheck','BALANCED'),0)
  if not contest(attacker,defender,('SPD','HND','OIQ'),('DIQ','STK','AGI'),adv=-entry_adv):
   emit(period,clock,'TURNOVER',other,primary_player_id=defender['id']);return
  receiver=rng.choice([p for p in offense['forwards'] if p['id']!=attacker['id']]);touches.clear()
  if contest(attacker,defender,('PAS','OIQ','HND'),('STK','DIQ'),adv={'POSSESSION':.06,'BALANCED':0,'RUSH':-.025,'SHOOT_FIRST':-.05}.get(offense_tactics.get('offense','BALANCED'),0)):
   emit(period,clock,'PASS',team,primary_player_id=attacker['id'],secondary_player_id=receiver['id']);touches.append(attacker['id']);attacker=receiver
  x=round(rng.uniform(68,96),1);y=round(rng.uniform(12,73),1)
  emit(period,clock,'SHOT_ATTEMPT',team,primary_player_id=attacker['id'],x=x,y=y)
  if contest(defender,attacker,('BLK','DIQ'),('SHT','HND'),adv=-.24+{'PROTECT_NET':.055,'BALANCED':0,'PRESSURE_PUCK':-.035}.get(defense_tactics.get('defense','BALANCED'),0)):
   emit(period,clock,'BLOCK',other,primary_player_id=defender['id'],secondary_player_id=attacker['id'],x=x,y=y);return
  if rng.random()<max(.07,.26-(skill(attacker,'SHT','HND')-60)/300):
   emit(period,clock,'MISS',team,primary_player_id=attacker['id'],x=x,y=y);return
  shots[team]+=1
  quality=(x-68)/28
  chance=max(.015,min(.23,.075+quality*.045+(skill(attacker,'SHT','PWR','OIQ')-skill(goalie,'REF','POS','VIS'))/500+{'SHOOT_FIRST':.008,'RUSH':.012,'POSSESSION':.005,'BALANCED':0}.get(offense_tactics.get('offense','BALANCED'),0)))
  if rng.random()<chance:
   score[team]+=1;emit(period,clock,'GOAL',team,primary_player_id=attacker['id'],secondary_player_id=touches[-1] if touches else None,x=x,y=y,goalie_id=goalie['id'])
  else:
   saves[other]+=1;emit(period,clock,'SAVE',other,primary_player_id=goalie['id'],secondary_player_id=attacker['id'],x=x,y=y)
 emit(1,1200,'GAME_START')
 for period in (1,2,3):
  emit(period,1200,'PERIOD_START');clock=1200
  while clock>0:
   clock=max(0,clock-rng.randint(13,30))
   if clock:attack(rng.choice((home,away)),period,clock)
  emit(period,0,'PERIOD_END')
 shootout=False
 if score[home]==score[away]:
  if playoff:
   period=4
   while score[home]==score[away]:
    emit(period,1200,'PERIOD_START',subtype='PLAYOFF_OVERTIME');clock=1200
    while clock>0 and score[home]==score[away]:
     clock=max(0,clock-rng.randint(8,22))
     if clock:attack(rng.choice((home,away)),period,clock)
    emit(period,clock,'PERIOD_END');period+=1
  else:
   emit(4,300,'PERIOD_START',subtype='OVERTIME');clock=300
   while clock>0 and score[home]==score[away]:
    clock=max(0,clock-rng.randint(8,22))
    if clock:attack(rng.choice((home,away)),4,clock)
   emit(4,clock,'PERIOD_END')
  if score[home]==score[away] and not playoff:
   shootout=True;winner=rng.choice((home,away));emit(5,0,'SHOOTOUT_WINNER',winner);score[winner]+=1;emit(5,0,'SHOOTOUT_DECISION',winner)
 emit(events[-1]['period'],0,'GAME_END')
 goals={t:sum(e['event_type']=='GOAL' and e['team_id']==t for e in events) for t in (home,away)}
 for t,other in ((home,away),(away,home)):
  assert shots[t]==goals[t]+saves[other]
  assert score[t]==goals[t]+int(shootout and any(e['event_type']=='SHOOTOUT_DECISION' and e['team_id']==t for e in events))
 return {'engine_version':'0.2.0','seed':str(seed),'home':home,'away':away,'teams':{t:world[t]['name'] for t in (home,away)},'score':score,'goals':goals,'shots':shots,'saves':saves,'shootout':shootout,'events':events,'reconciled':True,'rosters':{t:lines[t] for t in (home,away)},'gameplans':gameplans}
