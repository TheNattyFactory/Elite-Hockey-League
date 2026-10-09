from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlsplit,parse_qs
from pathlib import Path
import json,os
from genesis import simulate,make_world
from league import League
import market
import coaching
import careers
import appearance
import branding
ROOT=Path(__file__).resolve().parent
league=League(os.environ.get('EHL_DB',str(ROOT/'ehl.db')))
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(ROOT/'static'),**kw)
 def respond(self,data,status=200):
  body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
 def route(self,write=False):
  q=urlsplit(self.path);args=parse_qs(q.query)
  if not q.path.startswith('/api/'):
   if write:self.respond({'error':'Not found'},404)
   else:super().do_GET()
   return
  try:
   if write:
    length=int(self.headers.get('Content-Length','0'))
    if length>4096:raise ValueError('Request too large')
    data=json.loads(self.rfile.read(length) or b'{}')
    if q.path=='/api/commish/initialize':result=league.initialize(str(data.get('seed','GENESIS'))[:128])
    elif q.path=='/api/commish/advance':result=league.advance(int(data.get('count',1)))
    elif q.path=='/api/commish/seed-playoffs':result=league.seed_playoffs()
    elif q.path=='/api/commish/next-playoff':result=league.next_playoff()
    elif q.path=='/api/commish/finalize-awards':result=league.finalize_awards()
    elif q.path=='/api/commish/next-season':result=league.advance_season()
    elif q.path=='/api/market/offer':result=market.offer(league,int(data['player_id']),data['team'],float(data['rate']),int(data.get('seasons',1)))
    elif q.path=='/api/market/respond':result=market.respond(league,int(data['offer_id']),bool(data['accept']))
    elif q.path=='/api/coach/apply':result=coaching.apply(league,data['team'],data['applicant'])
    elif q.path=='/api/commish/coach/approve':result=coaching.approve(league,int(data['application_id']))
    elif q.path=='/api/coach/lineup':result=coaching.save_lineup(league,data['team'],data['applicant'],data['lineup'])
    elif q.path=='/api/coach/tactics':result=coaching.save_tactics(league,data['team'],data['applicant'],data['tactics'])
    elif q.path=='/api/player/train':result=careers.train(league,int(data['player_id']),str(data['attribute']),int(data.get('points',1)))
    elif q.path=='/api/player/appearance':result=appearance.update(league,int(data['player_id']),data['appearance'])
    elif q.path=='/api/sign':result=league.sign(data['team'],data['name'],data.get('position','C'),look=data.get('appearance'))
    else:return self.respond({'error':'Unknown endpoint'},404)
   else:
    if q.path=='/api/league':result=league.summary()
    elif q.path=='/api/playoffs':result=league.playoff_summary()
    elif q.path=='/api/history':result=league.history()
    elif q.path=='/api/standings':result=league.standings()
    elif q.path=='/api/teams/branding':result={'teams':branding.teams()}
    elif q.path=='/api/team/roster':result=branding.roster(league,args.get('team',['ATL'])[0])
    elif q.path=='/api/appearance/options':result={'options':appearance.OPTIONS,'defaults':appearance.DEFAULT}
    elif q.path=='/api/player/profile':result=careers.profile(league,int(args.get('id',['0'])[0]))
    elif q.path=='/api/coach/dashboard':result=coaching.dashboard(league,args.get('team',['ATL'])[0])
    elif q.path=='/api/coach/applications':result=coaching.applications(league)
    elif q.path=='/api/schedule':result=league.schedule()
    elif q.path=='/api/playoff-games':result=league.playoff_games()
    elif q.path=='/api/playoff-game':result=league.playoff_game(int(args.get('id',['0'])[0]))
    elif q.path=='/api/saved-game':result=league.game(int(args.get('id',['0'])[0]))
    elif q.path=='/api/world':result={'teams':make_world(args.get('seed',['GENESIS'])[0][:128])}
    elif q.path=='/api/game':result=simulate(seed=args.get('seed',['EHL-FIRST-PUCK'])[0][:128],home=args.get('home',['ATL'])[0],away=args.get('away',['NSH'])[0])
    else:return self.respond({'error':'Unknown endpoint'},404)
   self.respond(result)
  except (ValueError,KeyError,AssertionError,TypeError) as ex:self.respond({'error':str(ex) or 'Invalid request'},400)
 def do_GET(self):self.route()
 def do_POST(self):
  # Local-only prototype. Do not expose commissioner endpoints to the public internet without auth/CSRF.
  self.route(True)
if __name__=='__main__':
 print('EHL Genesis M13: http://127.0.0.1:8000');ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
