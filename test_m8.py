import unittest, tempfile, os
from genesis import make_world,simulate
from league import League
import coaching
class TestM8(unittest.TestCase):
 def test_lineup_and_tactics_affect_engine(self):
  w=make_world();baseline=simulate(seed='coach-seed',world=w)
  roster=w['ATL']['roster'];a=coaching.default_lineup(roster);a['STARTER'],a['BACKUP']=a['BACKUP'],a['STARTER']
  plan={'ATL':{'lineup':a,'tactics':{'offense':'SHOOT_FIRST','forecheck':'AGGRESSIVE','defense':'PROTECT_NET'}},'NSH':{}}
  changed=simulate(seed='coach-seed',world=w,gameplans=plan)
  self.assertEqual(changed['rosters']['ATL']['goalies'][0]['id'],a['STARTER'])
  self.assertNotEqual(baseline['events'],changed['events'])
  self.assertEqual(changed,simulate(seed='coach-seed',world=w,gameplans=plan))
  self.assertTrue(changed['reconciled'])
 def test_gameplan_database_read(self):
  with tempfile.TemporaryDirectory() as t:
   league=League(os.path.join(t,'ehl.db'));league.initialize('GENESIS')
   with league.db() as db:
    plans=coaching.gameplans(db,league.world(db),['ATL','NSH'])
   self.assertIn('ATL',plans)
   self.assertEqual(plans['ATL']['lineup'],{})
if __name__=='__main__':unittest.main()
