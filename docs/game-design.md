# Game design draft v0.1 (2026-11-02)

Working title: **Gatebound** (placeholder). A Roblox action RPG: the RPGs we played on Roblox as kids, done properly.
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
| 1 | **Ashen Vale** | The style test: pine meadows, ruined watchtowers, old roads, a quiet village of millers | slimes, boars, bandits, moss golems | **Mossback Warden**, a golem grown into the Gate |
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

Ten Lands is the long-term target. **Launch with 3** (1-3), each finished properly, and add a Land per update. Each new
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

- Each Land has its own weapon and armour **looks** and its own legendaries (Ashen Vale's moss-stone greatsword, Rimefell's
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
- **Twin Fang** (fight with two weapons at once): hidden in Ashen Vale; you need a hidden mastery requirement on two weapon
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

1. **Look**: match the reference (the matching passes), then build Ashen Vale's terrain from what we learn.
2. **Combat core**: movement, camera, one weapon type (Sword & Shield), one enemy (slime), damage numbers, hit feel.
3. **Loot core**: drops, rarities, inventory, equip, the drop moment.
4. **Ashen Vale vertical slice**: village, 3 zones, its enemies, a dungeon, the Mossback Warden, first quests.
5. Pets, armour sets, a hidden skill, then Lands 2 and 3.

## 13. Open questions for the user

- Name, and does the Gates idea work for you?
- Camera: over-the-shoulder like the reference, or the classic free Roblox camera?
- Which weapon types matter most to you at launch?
- Should the player's avatar be their own Roblox avatar wearing our armour, or a fixed hero look?
- How much story: light (a thread through Guardians) or real characters and cutscenes?
- Monetisation stance: cosmetics and convenience only (my recommendation) or more?
