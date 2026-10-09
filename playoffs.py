"""Genesis postseason: top two division winners receive byes; six qualifiers total."""
DIVISIONS={'NORTH':('BOS','CHI','DET','MIN'),'SOUTH':('ATL','DAL','DEN','NSH')}

def seed_qualifiers(standings):
    by_team={r['team']:r for r in standings}
    if len(by_team)!=8 or any(by_team[t]['gp']!=42 for d in DIVISIONS.values() for t in d):
        raise ValueError('Regular season must be complete before seeding playoffs')
    def rank(r):return (-r['pts'],-r['rw'],-(r['gf']-r['ga']),-r['gf'],r['team'])
    winners=[sorted((by_team[t] for t in members),key=rank)[0] for members in DIVISIONS.values()]
    winners.sort(key=rank)
    other=sorted((r for r in standings if r['team'] not in {w['team'] for w in winners}),key=rank)[:4]
    return [r['team'] for r in winners+other]
