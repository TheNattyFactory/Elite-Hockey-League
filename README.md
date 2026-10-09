# Elite Hockey League — Genesis M6: Contracts & Free Agency

Local-only sandbox. Builds on M5 (full seasons, playoffs, awards, archives) and adds **human contract expiry**, competing offers, accept/decline, salary tiers, and transaction history.

## Run

```bash
python server.py
```

Open http://127.0.0.1:8000. Tests: `python -m unittest discover -s tests -v`.

## Contract API (LOCAL ONLY, NO AUTHENTICATION)

- `GET /api/market/free-agents` — unsigned human players.
- `GET /api/market/offers?player_id=185` — offers for a player.
- `POST /api/market/offer` — `{"player_id":185,"team":"BOS","rate":0.35,"seasons":2}`.
- `POST /api/market/respond` — `{"offer_id":1,"accept":true}` (or `false`).
- Allowed salary tiers: 0.25, 0.30, 0.35, 0.40, 0.45 XP/game; term 1–4 seasons.
- One pending offer per team/player. Accepting one withdraws other pending offers. All signing changes are transactional; human roster members cannot be displaced.
- `POST /api/commish/next-season` now expires human contracts whose end season has passed and replenishes CPU roster slots. Unexpired contracts continue.
- Existing `/api/sign` remains a development shortcut, assigning a one-season 0.25 XP/game contract.

## Limitations

The prototype lacks user accounts, coach permissions, negotiation UI, salary caps, bonuses, protected offers, and dedicated free-agency phase. Offers are currently accepted during regular season for testing; player acceptance is not authenticated. Do not deploy publicly. XP ledger remains a game-level total (salary plus performance) rather than separate source entries. Full engine calibration and detailed hockey mechanics remain future work.


## M7 coach management
New `coaching.py` implements applications, commissioner approval, one coach per team, validated 20-player lineup assignment, and saved tactics. GET `/api/coach/dashboard?team=ATL`, `/api/coach/applications`; POST `/api/coach/apply`, `/api/commish/coach/approve`, `/api/coach/lineup`, `/api/coach/tactics`. These endpoints are **local sandbox only**: caller-provided coach names are NOT authentication. Do not expose publicly. The simulation still uses generated lineups; saved coach lineups/tactics are not yet consumed by the engine.


## M8 — Coach decisions affect simulation
- Coach lineups and tactics are loaded within the same SQLite transaction as the game simulation.
- Saved lineups determine the actual 12 forwards, six defensemen, starting and backup goalies in the engine.
- Forecheck, offense and defense strategies have small, bounded situational effects. Physicality and goalie usage are stored but do not yet affect the engine.
- A basic coach dashboard shows franchise lineups and saves tactics.
- If a lineup becomes invalid after roster changes, the engine falls back to a validated default lineup.
- Local prototype only: no authentication or CSRF protection.

## M9 — Player careers and progression
- `GET /api/player/profile?id=185` provides authoritative player profile, XP balance, contract, season-by-season and career scoring stats.
- `POST /api/player/train` accepts `{"player_id":185,"attribute":"SHT","points":1}`. Atomic and persisted in `training_ledger`.
- Starting 50 XP plus existing earned XP ledger minus spent XP; rising training cost is `1 + floor(current attribute / 20)` per point. Genesis prototype attribute cap 99.
- Human players only. Training uses the same player JSON used by the live game engine, so attributes immediately affect future games.
- **Security warning:** no accounts, authorization or CSRF; these endpoints must not be deployed publicly. Goalie statistics, proper played-game counts, user dashboard, and fully uncapped progression remain future milestones.

## M10 — Player Dashboard
- Open `/player.html` and enter a signed human player's ID (or use `/player.html?id=185`).
- Browser dashboard reads `/api/player/profile` and submits `/api/player/train`; SQLite remains authoritative.
- Attribute upgrade buttons display next-point XP costs and disable when unaffordable.
- Season/career scoring views and contract information are provided.
- Prototype only: no authentication or player ownership checks; **never deploy publicly**.
- Games are recorded stat appearances, not yet full dressed games. No avatar integration or goalie career analytics yet.


## Genesis M11 — Athlete creation and visual identity

- `http://127.0.0.1:8000/create.html`: create a human hockey player with franchise, position and appearance selections. Initialize the league first from the home page.
- `http://127.0.0.1:8000/player.html?id=...`: view and customize the same persisted avatar appearance.
- `static/avatar.js`: one shared SVG renderer used in creator and career profile; no duplicate implementations.
- `appearance.py`: allowlisted appearance choices stored in the canonical SQLite player profile.
- API: `GET /api/appearance/options`, `POST /api/player/appearance`, extended `POST /api/sign` with `appearance`.
- Cosmetic changes do not alter player attributes, performance or XP.
- **Prototype limitations:** there is no authentication/authorization. Any local caller can sign or change a player. Keep localhost-only. No account linkage, uniforms or team branding yet. The appearance system is EHL-specific rather than an imported EBL renderer.


## M12 — Team identity and uniforms
- `branding.py` provides a canonical stable-code palette and franchise identity.
- `GET /api/teams/branding` and `GET /api/team/roster?team=ATL` expose branding and authoritative persisted rosters.
- `/teams.html` is a responsive roster gallery. Creator/profile/roster share `/avatar.js`; portraits accept team and jersey number without duplicating saved appearance.
- Uniform colors are prototype palettes, not approved logo assets. No uploads, user-editable branding, or authenticated team management yet.


## M13 — GameCast replay

Visit `http://127.0.0.1:8000/gamecast.html`. The page discovers up to 100 completed regular-season games and 100 saved playoff games, and can generate exhibitions. It uses actual persisted event coordinates for shot attempts, tracks goals and shots on goal from the event ledger, and replays event-by-event with seek/play controls. Franchise colors and names come from `/api/teams/branding`.

New read-only APIs: `GET /api/playoff-games` and `GET /api/playoff-game?id=<id>`. The original endpoints remain intact.

**Limitations:** The engine does not yet simulate real-time shifts, penalties, special teams, or true puck trajectories. Shot markers are event-based and are not live tracking. This remains a localhost-only unauthenticated prototype.
