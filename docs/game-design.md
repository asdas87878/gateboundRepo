# Game design draft v0.1 (2026-11-02)

Working title: **Gatebound** (placeholder, kept). A Roblox action RPG: the RPGs we played on Roblox as kids, done properly.
It draws on anime adventure (Sword Art Online's climb through bosses, the pastoral knights-and-taverns warmth of The
Seven Deadly Sins) and classic loot RPGs. Everything here is a proposal to argue over, not a decision.

## 1. The one rule: fun first

Every system answers one question: **does this make the next five minutes more fun?** A grind is good when:
- **You always see progress.** Some bar is always close to full: XP, weapon mastery, a set piece, a pet's level. Something
  ticks up on every kill.
- **Rewards are unpredictable but fair.** Drops are random (that's the thrill), but bad-luck protection guarantees the big
  ones eventually (section 5). Nobody grinds 10 hours for nothing.
- **There are three goals at once.** The next minute (kill this pack), tonight (finish the set, beat the guardian), this week
  (the mythic, the hidden skill). Each one is visible on screen or one click away.
- **Combat feels good on its own.** Hit-stop, sounds, damage numbers, enemies that react, quick respawns. If hitting a slime
  is fun, farming slimes is fun.
- **Repetition is "just tedious enough".** Farming spots have a rhythm (a clear in 30-90 s, then respawn), and every repeat
  pays something. When a spot stops paying (your level outgrows it), the game points you onward instead of letting it rot.
- **Roblox players aren't confused.** One main currency, few menus, big obvious icons, a tutorial that's just playing, and
  every new system introduced alone when it unlocks. If a 10-year-old can't explain a system in one sentence, cut it.
- **Death is cheap, time is respected.** A short respawn, no lost items, a fast walk back. Sessions work at 10 minutes and at
  3 hours.

## 2. The world: the Gates

The realm is a chain of **Lands** (biomes), linked by ancient stone **Gates**: the arch from the style test. Long ago the
Gates were sealed, and each is held by a **Guardian**. You're a **Wayfarer**, one of the few who can wake a Gate. Beat a
Land's Guardian and its Gate opens to the next Land. That's the main thread, like climbing floors, but across a world
instead of up a tower. Party clears of Guardians are the big moments.

Each Land has:
- a **village** (safe hub: NPCs, blacksmith, tavern, pet keeper, quest board, its own music),
- **3-4 field zones** that get harder the further you go, with their own enemies and a wandering **field boss**,
- a **dungeon** (instanced, party of 1-4, a short run with a dungeon boss, the best farming in the Land),
- the **Gate Guardian** (a big, multi-phase fight that unlocks the next Land),
- **secrets** (hidden paths, puzzle ruins, a hidden-skill shrine, rare spawns).

### Lands (draft list, in order)

| # | Land | Mood | Enemies | Guardian |
|---|---|---|---|---|
| 1 | **Verdant Vale** (was Verdant Vale; full layout in `docs/lands/land1-verdant-vale.md`) | Lush anime meadows, mossy boulders, ruined watchtowers, a glowing forest; hub Brightwater, a castle town on a river island | slimes, hornhares, boars, moss golems, thornwolves, wisps, bandits | **Mossback Warden**, a golem grown into the Gate |
| 2 | **Hollowmere** | Misty marsh, willows, stilt-house village, lanterns at dusk | frog-knights, will-o'-wisps, bog hounds | **The Mire Matron** |
| 3 | **Brightwheat Downs** | 7DS-style rolling farmland, windmills, a tavern town on a hill, a castle in the distance | scarecrows, giant crows, rogue knights | **The Black Knight of the Mill** |
| 4 | **Fae Hollow** | Giant mushrooms, glowing flowers, a fairy-king forest | sprites, thorn beasts, mushroom folk | **The Thorn Queen** |
| 5 | **Rimefell** | Snowy highlands, pine-and-stone mountain hold | ice wolves, yetis, frost wraiths | **The Rime Drake** |
| 6 | **Sunscar Expanse** | Desert ruins, half-buried statues, oasis bazaar | scorpions, sand wraiths, glass serpents | **The Sleeping Colossus** |
| 7 | **Emberdeep** | Volcanic caldera, dwarf forge-city | magma imps, forge constructs | **Cinderhart** |
| 8 | **Drowned Crown** | A sunken kingdom, coral halls, tide caves | merfolk raiders, crab knights, eels | **The Tide Leviathan** |
| 9 | **Skyreach** | Floating islands, griffon roosts, wind bridges | harpies, storm elementals, griffons | **The Storm Roc** |
| 10 | **Duskhold** | A cursed kingdom at eternal sunset, a haunted castle | revenants, cursed knights, shadow beasts | **The Hollow King** |
| ... | **The Last Gate** | Endgame: a celestial ruin, repeatable scaling floors | everything, remixed | rotating |

### Guardian arenas: the Gate is the anchor, never the whole idea

A stone arch with a boss in front of it would get old by Land 3. So the Gate is always there, but each Guardian fight has
its **own place, its own movement, and one twist** that changes the arena during the fight. Rules:
- **No flat circle twice.** Every arena has height, hazards or a shape that matters.
- **The arena changes mid-fight** (a phase 2 that breaks, floods, lifts or moves the ground). That change is the moment
  players remember and clip.
- **The Gate takes part**: it's the boss's body, a weapon, a shield, a timer, or the way out that slams shut.
- **The walk-up builds it up**: a shrinking path, a view of the arena from above, a mural in the village showing the boss.

| Land | Arena | Twist |
|---|---|---|
| Verdant Vale | A ring of ruined watchtowers on a hill; the Gate is half-swallowed by the Mossback Warden's body | Phase 2: the Warden tears the Gate out of the ground and uses it as a club; towers fall and become cover/ramps |
| Hollowmere | A sunken temple roof in the marsh, lily pads and stone islands | The water rises each phase; islands sink, and the Matron hides beneath you |
| Brightwheat Downs | A burning windmill on a hilltop at dusk | The mill's sails sweep the arena like clock hands; jump the sails, fight on the mill's roof in phase 2 |
| Fae Hollow | A giant flower; the Gate is woven from thorns | The arena shrinks as thorns close in; cut flowers to open space |
| Rimefell | A frozen lake under a cliff | The ice cracks where big attacks land; the Drake drags the fight to the cliff face in phase 2 |
| Sunscar | On the back of the Sleeping Colossus as it wakes and walks | The arena moves; the Gate is carved in its chest, the final weak point |
| Emberdeep | A forge-bridge over lava | Bridge segments drop; forge hammers slam on a rhythm you can use against the boss |
| Drowned Crown | A throne room in an air bubble | The bubble shrinks; swim phases between air pockets |
| Skyreach | Floating platforms around the Gate in a storm | The Roc's wind shoves platforms around; ride griffons between them in phase 2 |
| Duskhold | The Hollow King's castle, room to room | The fight moves through the castle; the last phase is in the throne room as the sun finally sets |

### Beyond the world (the long road)

The Gates chain doesn't end at Land 10. **The Last Gate opens upward**: the Gates were never only between Lands, they're
between **worlds**. Later chapters, as big updates:
- **The Moon Reach**: low gravity, silver ruins, the old Gate-builders' outpost (higher jumps, slow falls: movement changes).
- **Other realms and planets**: a crystal world, a giant-beast world, a dead star's forge, each a new set of Lands with the
  same village/zones/dungeon/Guardian frame.
- **A ship or sky-vessel** hub between worlds once space opens up: your own base to decorate, show off pets and trophies.
- Each new world keeps the old-world fantasy heart (knights, taverns, relics) but in a stranger setting, so it feels like the
  same game going somewhere bigger, not a new game.

Ten Lands is the long-term target for the first world. **Launch with 3** (1-3), each finished properly, and add a Land per update. Each new
Land is the update's headline.

## 3. Combat

Third person, melee first, readable on a phone.
- **Click (M1)**: a 3-4 hit combo per weapon type. **Q**: dodge roll (i-frames, short cooldown). **1-3**: weapon skills.
  **4**: potion. **R**: ultimate (charges from hits). That's the whole input set.
- **Weapon types** (start with 4, add later): Sword & Shield, Greatsword, Dual Blades, Spear. Later: Bow, Staff, Scythe.
  Each type plays differently (speed, reach, skills).
- **Weapon skills** come from the weapon type's **Mastery**: use a weapon type and its mastery levels up, unlocking new
  skills to slot (anime "sword skills"). Swapping weapon types is a fresh grind with a fresh feeling.
- **Enemies telegraph** attacks (a wind-up, a ground marker for big hits). Bosses have phases and one "learn this" mechanic
  each: skill beats stats, but stats help.
- **Juice**: hit-stop on heavy hits, screen shake on crits, big rarity-coloured crit numbers, enemies flinch and stagger,
  satisfying kill pops with XP orbs flying to you.

## 4. Progression (what goes up)

| Thing | How it rises | What it gives |
|---|---|---|
| **Level** (1-100, 10 per Land) | XP from everything | stats, access to the next zones |
| **Weapon mastery** (per weapon type) | hits and kills with that type | skills, skill upgrades, a mastery title |
| **Gear** | drops, crafting, upgrading | most of your power |
| **Pets** | feeding, levelling, evolving | passive buffs, help in fights |
| **Village reputation** (per village) | quests, bounties | shop items, recipes, cosmetics |
| **Collection log** | discovering items, enemies, secrets | titles, small permanent stat bonuses |

Only **Level** and **Gear** gate content. Everything else is power and pride, so a player who ignores pets is never stuck.

## 5. Loot

### Rarities

| Rarity | Colour | Feel |
|---|---|---|
| Common | grey | filler, salvage it |
| Uncommon | green | an early upgrade |
| Rare | blue | a solid upgrade with one bonus stat |
| Epic | purple | two bonus stats, set pieces start here |
| **Legendary** | gold | a unique **effect** (e.g. "every 5th hit releases a wind slash"); named, with a hand-made model |
| **Mythic** | red/rainbow | the chase item: a unique effect, a unique model with glowing VFX, an **awakening** quest that upgrades it again. Announced to the whole server when it drops |

- Each Land has its own weapon and armour **looks** and its own legendaries (Verdant Vale's moss-stone greatsword, Rimefell's
  frost spear). The look tells you where something came from.
- **Drops are personal.** Everyone in a party gets their own roll. No loot stealing, ever. This makes co-op purely good.
- **The drop moment** matters most: a beam of light in the rarity's colour, a rising sound, a pause before the reveal for
  Legendary and up.
- **Bad-luck protection**: every boss kill without a Legendary raises your next chance (hidden pity). After N kills the
  Legendary is guaranteed. Mythics have a long but finite pity too.
- **Salvage and craft**: unwanted gear becomes materials; the blacksmith turns materials into upgrades or a chosen item from a
  Land's pool. A bad drop is still progress.
- **Upgrading** (+1 to +10): costs materials and gold, **never fails or breaks the item** (failure that destroys hours of
  grind feels awful, especially for kids).

### Armour
Four slots: **Helm, Chest, Legs, Charm**. Each Land has 1-2 **sets** with **2-piece and 4-piece bonuses** ("4-piece: dodging
leaves a damaging frost trail"). Collecting a full set is a great medium-term goal. Armour is shown on your character, so
good gear looks good, and an optional **cosmetic overlay** lets players keep a favourite look.

## 6. Pets

- Pets hatch from **eggs** dropped by bosses and found in secrets (also bought with in-game gold, never only with Robux).
- A pet follows you, **picks up drops**, and gives **one passive buff** (more gold, faster regen, a bit of damage). Later
  pets also attack or cast small spells.
- Pets **level up** by being out with you and **evolve** at set levels into a bigger, cooler form. The evolution is a visible
  goal.
- One pet out at a time to start (more slots unlock later), so it stays simple.

## 7. Hidden skills (the hard ones)

**Unique Skills**: rare, powerful abilities that aren't tied to a weapon type and are unlocked by secrets, not by grinding
alone. Examples:
- **Twin Fang** (fight with two weapons at once): hidden in Verdant Vale; you need a hidden mastery requirement on two weapon
  types plus finding a ruined shrine.
- **Blink Step** (a short teleport instead of a roll): beat the Storm Roc without taking a lightning hit.
- **Sunbreaker** (a huge charged strike): collect 7 scattered sun-shards across three Lands.

Rules: hints come from NPCs, tavern rumours and old tablets. The first player on a server to unlock one gets a server-wide
announcement. Each is rare but **achievable by any dedicated player**, never random-only. These are what players will make
YouTube videos about.

## 8. Villages and NPCs

- Each village: **blacksmith** (craft, upgrade, salvage), **merchant** (potions, basics), **tavern** (rumours/hints, daily
  bounties, the social spot with music), **pet keeper**, **quest board**, a few named characters with short storylines.
- **Quests**: a main story quest per Land (leads you through its zones to the Guardian), short side quests (each with a
  real reward), **daily bounties** (3 a day: "kill 30 bog hounds") for a daily reason to log in.
- NPCs speak in **short lines**. Nobody reads walls of text on Roblox.

## 9. Co-op and social

- **Parties of up to 4**, joined from the menu or by walking up to a friend. Enemies scale a little with party size.
- **World bosses**: a timed event per Land (a horn sounds, everyone on the server races there). Great for meeting people.
- **Guilds** later. **Trading** later and carefully (scams and duping are real risks; start with no trading, maybe add it
  with protections).

## 10. Session shapes

- **First 10 minutes**: you wake by the first Gate, a short fight, the village, your first Rare drop by minute 5 (scripted),
  level 3-4, your first weapon skill. The hook is "I'm already strong and there's a giant golem in that Gate".
- **A normal 30-minute session**: a daily bounty, a dungeon run or two, an upgrade at the blacksmith, a pet level.
- **A long session**: push a zone, try the Guardian with friends, hunt a secret.

## 11. Fun checklist for every new feature

1. Can a kid explain it in one sentence?
2. Does it give a reward on the first try?
3. Is there a visible bar or goal?
4. Does it feel good to do the 50th time (sound, animation, payout)?
5. Does it make playing with friends better, never worse?
6. Does it point to the next thing when it's done?

## 12. Build order (proposed)

1. **Look**: match the reference (the matching passes), then build Verdant Vale's terrain from what we learn.
2. **Combat core**: movement, camera, one weapon type (Sword & Shield), one enemy (slime), damage numbers, hit feel.
3. **Loot core**: drops, rarities, inventory, equip, the drop moment.
4. **Verdant Vale vertical slice**: village, 3 zones, its enemies, a dungeon, the Mossback Warden, first quests.
5. Pets, armour sets, a hidden skill, then Lands 2 and 3.

## 13. Decisions (user, 2026-11-02)

- **Name**: Gatebound stays as the placeholder.
- **Gates**: yes, but the Guardian fights must not feel one-note (section 2, "Guardian arenas"). Far along, travel goes
  beyond this world: other realms, space, other planets (section 2, "Beyond the world").
- **Camera**: over the shoulder.
- **Avatars**: the player's own Roblox avatar, wearing our armour.
- **Launch weapons**: Sword & Shield, Greatsword, Dual Blades, Spear.
- **Story**: a light thread through the Guardians, told mostly through NPC dialogue. No long cutscenes.
- **Money**: cosmetics and convenience only, never power.

## 14. Direction: an RPG's goals with a simulator's rhythm (agreed with the user 2026-11-06)

This replaces section 2's world structure and section 8's villages where they differ. Nothing here has been playtested. Earlier the same day this section described a village with a Gate Court inside the Lands; the user's take since then is what's below.

**The loop:**
1. **Fight.** Kills pay at once, loot flies to you, your pack fills.
2. **Champion.** Each farming area has a kill bar. A full bar spawns a mini-boss and a chest.
3. **Haul home.** Full pack, waystone home, pour it into your storehouse. This is the simulator's "sell" moment.
4. **Spend.** Build, upgrade, forge, give rescued NPCs a house, Terraria-style.
5. **Feel it.** Your weapon is visibly bigger; old enemies die in one hit.
6. **Boss.** Craft its summoning item from what you farmed. It drops signature gear and the key to the next Land.

**The world:** the Haven (see `docs/lands/haven.md`) is a shared floating island with a plot per player around it, like a tycoon game, so you see other players' bases. **30 Lands in six themes of five** (`docs/lands/lands-list.md`, the user's call): a theme shares a look, and each Land changes something and has its own boss, for steadier progression. They float in the sky, stacked above and below each other: the sky is the map, locked ones are far and dim, and beating a boss lights the next and draws it closer. You leave through your theme's arch and come home by waystone. Inside a Land, travel is part of the fun: launchers, ziplines, gliding, one signature way of moving per Land.

**Building a Land:** smaller Lands, a few enemy types and a boss, curated part by part. Each theme's first Land has 5-6 composed sets and the rest 2-3 plus a boss arena (Proposed: the list has the sums), each designed from its entry view. Necks (a gorge, a hollow tree, a tunnel) block sight and then reveal the next set; light and music change at the necks. Edges fall away with tapering rock, waterfalls and other islands in view. One locked camera per set is matched to concept art. Top-down generated layouts only made good views by luck, so layout now starts from the player's camera. The fence, props, bridge, cottage and trees carry over; only the layout changes.

**Hooks, best first (none agreed one by one yet):**
- **The forge reveal:** a timing minigame, recipes you discover.
- **Home keeps working:** garden plots and mutated harvests while you're out.
- **The Climb:** the endless tower, pick-one boons between floors, a weekly leaderboard.
- **Pets from eggs:** simple pets only.
- **Rare variants:** a 1-in-5,000 golden enemy, announced to the server.
- **Decor as loot:** props drop as decorations for your base.
- **Harder tiers of a Land.**
- **Bigger enemy packs:** after a performance test.

**Keep:** quests, weapon skills, proper bosses, dungeons, gear, hidden skills, rescued NPCs, a collection log, drop odds shown. **Money:** Robux buys cosmetics and convenience only.

**Cut (the user's call):** monsters joining or fighting beside you, Land remixes, event gates everyone rushes into. It must all be playable solo. Hordes and Ascension resets were cut on my recommendation, so they can come back.

**Release (Proposed):** launch with the first two themes, then a theme per update.

**Order:** the user makes concept art while a rough fun test gets built in a plain room (one enemy, pack, kill bar, haul home, one building, forge). Then the Haven and one Land set are built to match the art. Judge those, then expand.

**Open:** set plots vs free building; memory at a full server of plots.

## 15. The user's principles (2026-11-08, from a voice brief; overrides section 14 where they differ)

**The foundation is the simulator loop.** Kill enemies in a Land, gain resources, take them home, turn them into better tools, farm
stronger things faster. The replayability is always hanging a sweeter fruit just out of reach, so the player needs the next tool to
get it.
- **The twist on a normal simulator:** better tools need **specific ingredients in combinations**, not just a bigger number.
- **The crafting UI** is a little hard to work out, but it can be worked out.

**Four ways to get stronger:**
- **Weapons:** crafted with ingredients.
- **Abilities:** levelled with XP; flashy VFX moves such as a fireball.
- **Stats:** levelled with XP, slower, such as movement speed.
- **Charms:** equipped like pets, each a specific bonus (for example +20 armour and lifesteal on hits). About 3 slots to start, more
  later, and the coolest charms come from hard content.

**Drops:** XP (levels skills), gold, gems and specific ingredients (for crafting). What gold and gems buy is undecided.

**The base:** craft, upgrade, personalise, and chill.
- **The base is upgradable, and some tools need a higher-level base.** A forge station (craft, smelt, exchange, create) has tiers,
  and a tier can need a quest ingredient, for example a mithril anvil.
- **A town hall** whose role is undecided. It must not be only a limiter: it needs real rewards of its own. Forge or town hall
  first is an open choice.
- **NPC vendor hubs, like Terraria:** NPCs rescued in the Lands come to live at the base.
- **Extra scenery.** What else a base can have, and what to take from tycoons, is open.

**No main quest line.** Where to go should be self-explanatory: no hand-holding. There are challenges instead (kill 20 of an enemy,
beat the second boss), and they bring NPCs home.

**The Lands:** 30 or more.
- **Shape:** farming stations of basic enemies, then a layer of tougher enemies on the way to a boss. Size and details are open.
  The farming must not get over-complicated.
- **You can always walk into a Land too strong for you and be killed.** That's from the RPG the user loved as a kid: defeat gives
  you something to strive for. The challenge must suit a beginner's skill.

**The feel:** bright, full of VFX, clear progression, fast travel, satisfying rewards. Gold visibly flies into your inventory with
good sounds, and depositing gives instant, satisfying feedback.

**Travel:** easy to get home and to the Lands, from the UI and from a physical landmark, but not so easy that it breaks the balance.
Worry: going all the way home to cash in may take too long and put players off.

**The start:** no long cutscene. A friend who's told to hop on must be playing at once. How the game works must be clear but still
intriguing and a little mysterious.

**Rebirth eventually:** after the 30 Lands, like Borderlands' True Vault Hunter Mode or Mayhem, with big long-term rewards for
rebirthers.

**Showing what you're missing:** the player starts with a basic sword and basic enemies, and should clearly see the cool weapons
they don't have yet (how is open).

**Section 14 questions this raises:**
- Charms vs section 14's pets from eggs.
- Open-but-deadly Lands vs section 14's locked, dim ones.
- What gold and gems are for.

Claude's suggestions for the gaps were made in the chat on 2026-11-08; the ones the user agrees to go in here.
