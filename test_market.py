import tempfile, unittest
from pathlib import Path
from league import League
import market

class MarketTests(unittest.TestCase):
 def test_expiration_and_competing_offers(self):
  with tempfile.TemporaryDirectory() as d:
   l=League(Path(d)/'test.db');l.initialize()
   pid=l.sign('ATL','Contract Tester','C')['signed']['id']
   with l.db() as db:
    market.expire_for_new_season(db,2)
   self.assertEqual(market.free_agents(l)[0]['id'],pid)
   a=market.offer(l,pid,'BOS',.35,2)['offer_id']
   b=market.offer(l,pid,'DET',.4,3)['offer_id']
   with self.assertRaises(ValueError):market.offer(l,pid,'BOS',.35,1)
   result=market.respond(l,b,True)
   self.assertEqual(result['status'],'ACCEPTED')
   with l.db() as db:
    self.assertEqual(db.execute('SELECT team FROM players WHERE id=?',(pid,)).fetchone()[0],'DET')
    self.assertEqual(db.execute('SELECT end_season FROM contract_terms WHERE player_id=?',(pid,)).fetchone()[0],3)
    self.assertEqual(db.execute('SELECT status FROM contract_offers WHERE id=?',(a,)).fetchone()[0],'WITHDRAWN')
    self.assertEqual(db.execute('SELECT COUNT(*) FROM players WHERE team="DET"').fetchone()[0],23)
   with self.assertRaises(ValueError):market.respond(l,b,True)
 def test_decline(self):
  with tempfile.TemporaryDirectory() as d:
   l=League(Path(d)/'test.db');l.initialize();pid=l.sign('ATL','Tester','D')['signed']['id']
   with l.db() as db:market.expire_for_new_season(db,2)
   oid=market.offer(l,pid,'BOS',.25,1)['offer_id']
   self.assertEqual(market.respond(l,oid,False)['status'],'DECLINED')
   self.assertEqual(len(market.free_agents(l)),1)
