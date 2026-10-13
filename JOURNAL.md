# Play journal

A running log of how the city is played, why each decision was made, and what the
game actually did. Newest entries at the bottom. Numbers marked "save facts" come
from parsing the native `.SC2` save (`agent/sc2.py`), not from reading the screen -
the screen is easy to misread and the agent has hallucinated progress before.

## The goal

Reach **10,000 population without going broke**, on an Easy start ($20,000), playing
in `LLM_PROVIDER=external` mode: Devin looks at each screenshot and sends the move,
the agent executes it with xdotool. Everything is recorded (`runs/screen-*.mp4`) and
visible live over noVNC.

## Strategy, and why

1. **Trust the save file, not the screen.** Borrowed from Claude/Gemini Plays Pokemon,
   which feed the model facts read out of game memory because screen reading is
   unreliable. After every periodic save the parsed date / funds / population is
   appended to the history, and the prompt says to trust it over the screen.
2. **Pause while deciding.** From VideoGameBench: real-time play while the model thinks
   wrecks performance. Each turn the game sits paused; the city is un-paused in
   deliberate `speed.cheetah` + `wait` bursts to let years pass.
3. **Bigger moves instead of pixel guessing.** From the "vibe gaming SimCity" write-up
   (which gave up on pixels and moved to a Micropolis HTTP API with a "build a block"
   command) and from Cradle/Voyager's reusable skills. Hence the composite `block`
   action: one move lays a road ring, fills it with a zone, and runs a power line
   through the middle that sticks out one tile each side so the next block chains onto
   it. This collapses what used to be ~8 fiddly moves into 1.
4. **Lessons the hard way, now encoded in the prompt.** A power line only carries power
   if it touches an *edge* of the plant (a corner does nothing); roads do not conduct
   power; a zone tile more than ~3 tiles from a road never develops; freshly zoned land
   is nearly invisible on screen, so check the funds drop instead.

## Log

### Run 1 (1900-1935, `AGENT006.SC2`) - learning run
Built a coal plant, roads, power lines and zones by hand. Nothing grew for ~20 years:
the power line missed the plant edge and most zones were too far from a road. After
fixing both (c. 1914 and 1920) factories and houses appeared. Ended ~750 people, no
money trouble. Conclusion: hand-placing is too slow and too error-prone to reach
10,000 - build bigger moves first.

### Run 2 (1900-1919, `AGENT007.SC2`) - aborted
Same manual approach with the new save-fact feedback. Reached only ~234 people by 1919
at $13.4k; growth cost several look-and-click rounds per fix, and a periodic save fired
in the middle of a batch and swallowed a tool selection (fixed in `01b6ad9`: saves now
wait for a batch to finish). Newspaper reported unemployment, i.e. too few jobs.
Stopped the run and built the `block` action instead.

### Run 3 (1900-) - the 10,000 attempt
Easy map, paused on the first turn, `options.auto_budget` on so the year-end budget
window never blocks a move. Centred and zoomed one step in (16px tiles) onto the flat
plateau south of the river, because `block` assumes 16px tiles and flat ground - the
game silently refuses to build on slopes, which is what made the earlier AI run fail.
First `block` test at (100,170) placed the zone and the power line correctly but left
the road ring ragged, so a 0.4s pause was added between the four ring drags (DOSBox
drops input when drags are issued back to back).

Looking closer at the first block: 3 of the 4 ring roads were laid; the north-east
edge was missing (the drag issued right after the previous one was dropped). The
running container still has the old code, so I re-drew that edge by hand rather than
restart the city. Funds went $20,000 -> $19,513 for the block, confirming it built.

**Power plant choice:** coal ($4,000) rather than oil/gas/hydro - it is the cheapest
plant with enough output (~200 MW) for the first several thousand people, and on Easy
the pollution only matters near homes. Placed on the flat ground just south of block 1
and wired to the block's power stub with a short line that ends on the plant's edge
(not its corner - the lesson from run 1).

Both plant placements failed: the tool showed "Coal Power $4,000" but funds did not
drop, so the game refused the spot. This map is a maze of terraces and cliffs; a 4x4
plant needs level ground and the 8x8 blocks need even more of it. Rather than pay to
terraform, I **re-rolled the map**: still January 1900 with only ~$500 spent, so
nothing of value is lost, and restarting the container also loads the fixed `block`
code (pauses between ring drags). New rule for myself: before building, look for one
big level area (uniform diamond lattice, no brown cliff bands) and test-place the
plant there first; build blocks only after the plant's $4,000 shows up in the funds.

**Re-rolled map:** gentler, with one level patch in the north-east of the starting
view. Test-placed the coal plant there first: funds $20,000 -> $16,000, so it is
really built. The first residential block goes just south-west of it, with one short
power line from the plant's bottom edge across the ring road into the zone (zones
pass power to each other, so one connection powers the whole block).
Plan for the next blocks: residential first because homes are where the population
number comes from, then one industrial block (jobs; the 1919 newspaper in run 2
complained about unemployment), then commercial once there are enough people for
shops - aiming at roughly 2 R : 1 C : 1 I.

**Feb 1904, save facts: population 0, funds $15,380.** Four years passed with no
houses at all. The block's middle power line still shows the lightning "no power"
marks, so the short connector from the plant missed: it ended on the ring road rather
than in the zone. This is the same failure as runs 1 and 2 - the plant-to-city link is
the single most fragile step - so I redrew it as one straight line along a tile axis,
starting on the tile beside the plant's side edge and ending on the block's middle
line, so it can't stop short.

**Apr 1907:** the lightning marks are gone from block 1's middle line, so the
redrawn connector works and the whole block is powered. Letting the game run at full
speed now; houses should start appearing within a year or two of game time.

**Jul 1914 - the real reason nothing grows.** Still zero houses after 14 years on a
powered, road-ringed block. A National Guard notice and an earthquake newspaper
interrupted, and while closing them a stray click with the centring tool scrolled the
view away. Then I looked at the **RCI demand meter** in the toolbar: the green (R) and
blue (C) bars hang *below* the line (negative demand) and only yellow (I) points up.
In SimCity 2000 people won't move into a town with no jobs, so an all-residential
start stalls forever. Run 2's "unemployment" headline was the same signal.
**New strategy:** read the RCI meter before every zoning decision and zone whatever
bar is highest. Right now that means an **industrial block next to the residential
one** (sharing the ring road and power line), then residential again once the green
bar turns positive. Added this rule to the agent prompt too.

**Jul 1914, recovering the view:** opened the map window, clicked the city on the
minimap to scroll back, closed it. Same zoom, but everything moved by about (-76,+40)
pixels, so all coordinates are re-measured from a fresh screenshot before building.
**Industrial block:** placed directly south-east of block 1 so it shares block 1's
ring road and its middle power line continues straight into it - no extra wiring,
no new connection to get wrong. Industry next to homes adds some pollution, but
early on jobs within a short commute matter more than clean air.

**May 1916 - it works.** Two game years after the industrial block went in: factories
on block 2 and houses on block 1, the first real growth of any run. All three RCI bars
now point up. Funds $14,796. This confirms the jobs-first diagnosis.
**Next: commercial block** chained south-east of the industrial block (shares its road
and power line). Picked that spot because the other neighbours of the existing blocks
are the power plant (north-east) or cliff bands (south-west), and `block` needs level
ground. Commercial now because the blue C bar is up and shops also add jobs.

**Jul 1922:** funds $14,418, money roughly flat - the city now pays its own way.
Blocks 1 (homes) and 2 (factories) are nearly full. The commercial block only half
built: its ring ran into a slope, so only the south-east end got zoned and some
shops appeared there. RCI now says **R strongly up, C slightly down, I slightly
down** - factories and shops are waiting for workers and customers, so the next
blocks are residential.

Checked the zoom: one `zoom_in` doubled everything (plant ~100px wide), so the blocks
had been built at the intended 16px-tile scale. Zoomed back out. Every zoom or scroll
nudges the view, so I re-measure ring corners on a 4x crop before each new block.

**Where to put more homes:** south-west of the blocks is a strip only ~4 tiles deep
before a terrace; north-east is a cliff. The only big level patch is north-west of
block 1, and it has a small pond in it. Built the next residential block there
anyway: losing a few water tiles is cheaper than terraforming, it shares block 1's
north-west road, and its middle power line lands exactly on block 1's line, so it is
powered with no extra wiring.

**May 1925, save facts: population 3,392, funds $14,152.** A third of the way there,
and money is steady. The pond block filled with houses within three years. The RCI
meter has flipped again: **I strongly up, R and C down** - the new residents need
jobs. So the next block is industrial, on the flat forest west of the pond block
(chained power again). This R -> I -> R see-saw is the core loop: zone whatever
the meter asks for, one 8x8 block at a time, and let ~3 game years pass between moves.

**Feb 1928 (screen: $14,387).** The industrial block west of the pond block never
appeared: funds did not drop and the forest is untouched. A newspaper popped up during
the run (approval 51%, a "Pollution Blows!" headline) and most likely swallowed the
drags. Lesson: check funds right after every block, *before* un-pausing, and redo it
if nothing was spent. Retrying the same block now. RCI still says I high, R slightly
up, C slightly down.

Retry worked: funds dropped $14,387 -> $13,891 (~$500 for ring + zone + line) and the
yellow industrial ring is visible west of the pond block, chained to its power line.
Running ~3 game years before the next move.

**Oct 1930 (screen: $14,083).** Another newspaper (approval up to 59%, closed). The
second industrial block filled with factories in ~2 years. RCI now: **R high, I
medium, C below the line**, so the next block is residential again, south-west of the
new factories (their power line chains into it). Newspapers keep interrupting the
runs; I close them first and check funds after each block, because a missed block
costs a whole run of ~3 game years.

Residential block south-west of the factories: funds dropped $14,083 -> $13,629, so it
was built, but its west corner sits right at the edge of the map view and the
south-west road came out incomplete. Yellow "no power" bolts are showing on the new
zone. Running ~2 years to see whether power and growth arrive before I patch it.

**Nov 1934, save facts: population 4,053, funds $14,160.** Up from 3,392 in 1925.
The new south-west residential block is still unpowered after ~4 years (yellow bolts,
no houses). Cause: I chained it in the wrong direction. A block's middle power line
runs down-right on screen (from west corner toward south corner), so only blocks
chained at `(x + 8*size, y + 4*size)` (down-right) share it. That is what the README
says; I misremembered it. The pond -> factories chain was down-right by luck and
worked. This one was down-*left*, so its line runs parallel to the factory line and
never touches it. Fix: one short power line straight up-right across the shared road,
from the middle of the new line to the middle of the factory line.

**Jan 1941 (screen: $15,172).** The short power link worked: it cost $10, the bolts
disappeared, and the south-west residential block is filling with houses. Funds are
*rising* - taxes now cover upkeep. For the first time the RCI meter shows **R, C and I
all high**, so the city can absorb every zone type. Commercial goes first, because the
only shop block so far is the half-built one and the factories and homes need shops.
New block: down-right of the south-west homes (the correct chaining direction this
time), so its line starts on the homes' powered line.

Commercial block built: funds $15,172 -> $14,875 ($297 - cheaper than earlier blocks
because part of the ring runs down a slope and some road pieces were refused). The
blue commercial dots cover the block, trees and all. Running ~3 years.

**Feb 1947 (screen: $15,827).** Shops are going up in the new commercial block, and
funds keep climbing (+$950 in 6 years). RCI: **R and I high, C now below the line**;
the shops have caught up. Next moves are another residential block and another
industrial block. The level land next to the current blocks is used up, so I'm
looking further out (or scrolling the view) for flat patches.

**Running out of level land (Feb 1947).** The city sits on a terrace: cliffs to the
north-east, slopes to the south-west, and the plant blocks the north. Placing more
8x8 blocks would mean scrolling to new land and running long power lines. Before
that, a cheaper idea: **densify what already works.** I'm rezoning the pond block's
interior from light to dense residential with the same two zone-fill drags the block
action uses. If the game accepts it (funds drop), each existing residential block can
hold several times more people on the same roads and power.

Result: **refused.** Funds stayed at $15,827 and the pond block looks unchanged; the
game won't rezone tiles that already have buildings on them. So densifying means
bulldozing first (losing people for a while), which is a bad trade right now. Back to
finding new land: next I'm checking whether the arrow keys scroll the city view.

Arrow keys do scroll the city view (one `Right` press moved everything ~40px left).
That makes new land reachable without changing zoom, but every scroll changes all
coordinates, so I re-measure corners before building after each scroll. Looking
north first: the forest above the factories looked flat.

**Feb 1947, save facts: population 4,660, funds $15,827.** Growth is slowing: +600
in 13 years, versus +3,400 in the decade before. Why I think it's slowing:
1. **No more ready land.** Every block so far sat on the one level terrace; what's
   left is slopes, cliffs and forest.
2. **No water and no services.** In SC2000 zones without water stay low-density, and
   with no police, fire or schools land value stays low.

Plan: (a) keep adding blocks on the flattest land north of the factories (scrolled
into view); (b) then add a water pump and pipes, plus a police and fire station,
which money now allows ($15.8k and rising). Bigger houses on the land we already
have are the main way to reach 10,000.

**North block (Feb 1947).** After scrolling, the flat strip north of the factories is
only ~6 tiles deep before the next terrace, so this one is a 6x6 residential block
sharing the factories' north-east road. It is chained *up-right* (the only direction
with room), so its middle power line doesn't land on a powered line. Fix in the same
move: extend the line 2 tiles down-right, then 3 tiles down-left onto the pond
block's north-east road, right next to its powered houses (a power line crossing a
road conducts into the neighbouring zone).

Result: built (funds $15,827 -> $15,477), but my scroll-offset estimate was one tile
off. The new block sits one row of trees above the factories instead of sharing
their road, so my link line probably stops short of anything powered. Zooming in on
the link end to patch it. Lesson: after a scroll, measure an existing corner on a
zoomed crop instead of computing it from the scroll distance.

Zoomed crop: the link ended one tile above the factories' north-east road, with the
powered houses just across it. Extending it 2 tiles down-left across the road should
complete the connection (~$15).

The 2-tile extension cost only $4 and bent the wrong way: the zoomed crop shows it
went up-left instead of down-left across the road, so the north block may still be
unpowered. Another newspaper (a city-dump headline) interrupted the run. Next: close
it and check the north block for "no power" bolts.

**Aug 1948 (screen: $15,631).** The north block is powered and already full of houses
within ~18 months. The power reached it after all, either through the bent link or
through a corner touching the factories. RCI: **R and I high, C slightly below the
line.** Next: an industrial block, wherever I can find level land.

**Next industrial block (Aug 1948).** The full view shows terraces almost everywhere.
The one clean flat patch left is between the north block and the coal plant, so a 6x6
industrial block goes there, with factories next to the plant and away from most
homes. Its corner only touches the north block, so it can't borrow power. Instead I
extend its middle line straight into the plant in the same move.

Result: **partial failure, $838 spent** ($15,631 -> $14,793). The "flat" patch had
a terrace at its north edge. The road ring climbed it in a wavy line, and most of
the inside was refused for zoning; only a few yellow industrial patches stuck. The
line into the plant did connect. Lesson: on the 2x full view, terraces under
grassland are hard to see; the 4x crop shows them as darker brown bands. Check a 4x
crop of the whole block footprint before building. Running ~2 years to see what the
patches yield.

**Aug 1948, save facts: population 4,434 (down from 4,660), funds $14,793.** The
first drop, despite a new residential block filling in. Another newspaper since then:
approval 69%, but the headlines are about pollution and dumping. My read: the city
is all factories, a coal plant and homes packed side by side, with no services, so
some residents are leaving. Adding more zones alone has stopped working. Next moves
target *quality*, not quantity: a police and a fire station first, then water.

**Services (May 1949, screen: $14,964).** First service building: a **police
station** ($500) on the flat wooded patch just south-east of the coal plant. Why
police first: crime rises with density and drags down land value and residential
desirability, and this spot touches the plant and the blocks below it, so it is
powered with no extra line. A fire station follows if this one is accepted.

Police station accepted (funds $14,964 -> $14,464) but it shows the yellow "no power"
bolt. It sits about one tile away from the end of the plant's outgoing line, not
touching it. Bridging the gap with a 1-2 tile power line.

**May 1950 (screen: $14,587).** The bridge line worked: the police station's bolt is
gone and it's powered. Funds are steady (taxes roughly cover the new $100/yr-ish
upkeep). RCI is unchanged: **R and I high, C slightly below the line.** Demand isn't
the problem; land is. Next I'm checking whether the landscape tools can level one
more block's worth of ground; at ~$15k in the bank, buying flat land is affordable.

**Trying to buy flat land (May 1950).** Instead of hunting for a new site, I'm
levelling the inside of the half-failed plant-side industrial ring, whose roads
already exist and whose line already reaches the plant. The level tool flattens the
dragged area to the height of the tile where the drag starts, so I start on the low
west side. If funds drop and the terrace disappears, I re-zone the inside with the
block action's two zone-fill drags.

**May 1950, save facts: population 4,642, funds $14,587.** Back up from the 1948 dip
(4,434), so the police station and north block helped a little.

Levelling **did nothing**: funds unchanged, terrain unchanged. Either the drag needs
a different gesture for that tool, or the terrace is too tall to level in one pass.

### Where the run stands (plateau)

| Save | Date | Population | Funds |
|---|---|---|---|
| AGENT011 | May 1925 | 3,392 | $14,152 |
| AGENT012 | Nov 1934 | 4,053 | $14,160 |
| AGENT013 | Feb 1947 | 4,660 | $15,827 |
| (1948) | Aug 1948 | 4,434 | $14,793 |
| (1950) | May 1950 | 4,642 | $14,587 |

Growth has been flat at ~4,500 for 15 game years, with plenty of money. What worked:
industry-first zoning, reading the RCI meter, and 8x8 composite blocks on level
ground (each ~$500, ~600-900 people). What's blocking 10,000: the starting terrace is
full and the rest of the visible map is terraced; blocks built on slopes come out
partial; there's no water system, and SC2000 keeps unwatered zones low-density.
Getting past this means scrolling to new flat land with long power lines, building
pumps and pipes, or re-rolling to a flat map and replaying the proven opening on it.

## Phase 3: restarting growth without leaving the screen (from May 1950)

David's rule: **no scrolling off to new land; play fairly like a human.** So the
fix has to come from using the land I already have better. Plan, in order:

1. **Water.** SC2000 caps zones without water at small buildings. Pumps (need power;
   better next to fresh water) by the pond, plus pipes laid under the developed
   blocks in the underground view.
2. **Redevelop instead of expanding.** Rezoning built-up light zones was refused, so
   bulldoze the weakest small-house tiles first, then zone them dense.
3. **Land value.** Parks as buffers between homes and factories/plant; school and
   hospital once funds allow.
4. **Hand terraforming.** The level drag did nothing; try raise/lower clicks on
   single tiles to flatten the hilly patches the way a human would.

**Water, step 1 (May 1950).** Pump placed on the flat strip just east of the police
station (funds $14,587 -> $14,487). There's no free tile beside the pond, so it's a
land pump with lower output. I'm connecting it with a short power line to the
station and a pipe trunk south-west into the developed blocks.

### Thinking like the mayor (David's push)

Up to now I've been acting as a builder: find flat land, drop a block. With 15 years of
flat population, the right move is to **diagnose before building**, using the
game's own reports: city maps (pollution, crime, land value, traffic), the
population/RCI graphs, the budget and tax rates, and the newspaper and opinion poll.
Then fix the biggest problem first. Below I record what each report shows and
the decision it leads to.

Pump connected: power line plus a pipe trunk from the pump south-west to the
developed blocks (funds $14,487 -> $14,359; underground view shows the blue pipe).

**Diagnosis 1: the budget (May 1950).**

| Line | 1950 year-end estimate |
|---|---|
| Property tax (7%) | +$216 |
| Police | -$100 |
| Transit (roads) | -$18 |
| Fire, health, education, ordinances, bonds | $0 (none built or enacted) |
| **Net for the year** | **+$99** |

Mayor's read: the city earns almost nothing, but has **$14,359 sitting idle** in the
bank. That money is doing nothing for growth. Fifty years of "don't go broke" made
me hoard cash. A real mayor would turn the reserve into things that raise land
value and lift growth caps (water, parks, a school, a fire station), and could cut the
tax rate to pull in residents and businesses, since tax income is too small to matter
next to the reserve.

**Diagnosis 2: the save file's own city statistics.** These fields come from the
OpenCity2k file spec (RCI demand is -2000..+2000):

| Save | Date | Pop | R demand | C demand | I demand | Pollution | Crime | Work force % | EQ |
|---|---|---|---|---|---|---|---|---|---|
| AGENT011 | May 1925 | 3,392 | -974 | -1104 | +2000 | 4,474 | 853 | 68 | 83 |
| AGENT012 | Nov 1934 | 4,053 | +2000 | -530 | -981 | 5,428 | 1,226 | 64 | 81 |
| AGENT013 | Feb 1947 | 4,660 | +2000 | -1432 | +2000 | 5,927 | 1,481 | 60 | 74 |
| AGENT014 | Aug 1948 | 4,434 | +1977 | -640 | +2000 | 5,843 | 1,601 | 60 | 74 |
| AGENT015 | May 1950 | 4,642 | +2000 | -321 | +1961 | 6,333 | 1,278 | 59 | 74 |

Mayor's read:
- **Residential demand has been maxed at +2000 since 1934.** People want to live here;
  the city isn't giving them homes. This is a supply problem, not a demand problem.
  Each home tile stays small: no water, a cheap coal plant and factories next to homes
  (pollution has risen every save), and no parks, so land value is low.
- **Industrial demand is also maxed.** Jobs are wanted too; work force % is falling (68 -> 59).
- **Commercial demand is negative** and there are **0 neighbour-connection tiles**, so
  shops have no outside trade. That's acceptable for now since R and I lead.
- **Education (EQ) is falling** (83 -> 74) with no school. Smarter residents bring cleaner
  industry, which lets homes sit near jobs.
- Crime dropped after the police station (1,601 -> 1,278): that intervention worked.

Decision: increase housing supply and housing quality on land I already have:
water everywhere, high-density homes on any free tile away from smoke, parks as
pollution buffers, then a school.

**Diagnosis 3: the city maps (Map window, May 1950).**
- *Pollution:* a solid white cloud covers the whole developed area. The coal plant
  sits in the middle of town with factories around it and homes right next to both.
- *Water supply:* almost every developed tile shows red (no water). The new pump
  was placed while paused, so I'm running the sim briefly and re-checking.
- *Whole map:* the city fills only a small patch near the centre of a large map.
  There's a river in the south and a lake to the north-east, both off-screen and
  out of bounds under David's rule.

This confirms the save-file read: homes are capped at small sizes by **no water** and
held down by **pollution**. Water is the cheapest fix with the biggest effect.

**Diagnosis 4: the newspaper (Jan 1951).** The headline story is "Fire Station Needed":
residents demand fire protection, and the status bar reads "Fire Protection Demanded".
The editorial is "Pollution Blows!" Mayor approval is 70%. So residents name the same
two problems the data shows: **pollution** and **missing services**. A fire station
($500) goes on the list right after water.

### Crisis: the power plant is gone (Feb 1951)

After closing the newspaper the status bar reads **"Power Plant Needed"**, and where the
coal plant stood there's only rubble. SC2000 plants wear out after about 50 years;
this one went up in 1901. **The whole city is now without power**, and the water pump
needs power too. This is likely part of the 1948-1951 stall. Rebuilding now is the
first priority.

Mayor's choice: **oil instead of coal.** Pollution is the residents' top complaint
("Pollution Blows!") and the plant sits in the middle of town. Oil costs more
(~$6,600 vs ~$4,000) but makes more power with less smoke, and the city has
$14,458 idle. Rebuilt on the old site, which is known to be level and already has
the power lines attached.

Mar 1951 paper: **"Williams Labs Creates Gas Power"**, so gas plants are now
available, and **approval has dropped 70% -> 61%** in two months without power.
Clearing the rubble (bulldozer) and opening the plant chooser on the old site; I'll
pick from what the chooser actually offers.

**Plant chooser (Jul 1951, $14,443):** Coal 200 MW/$4,000 · Hydro 20 MW/$400 (needs a
waterfall) · Oil 220 MW/$6,600 · **Gas 50 MW/$2,000 (new)**. Gas is too small for
~4,600 people plus growth. **Chose oil:** the most power, and less smoke than coal
right next to homes. That leaves about $7,800 for water and services.

**Oil plant built (Jul 1951): funds $14,443 -> $7,843.** It sits on the old coal
site, so the existing lines and the police-station/pump link should pick it up.
Lesson recorded in the AI prompt too: choosing a plant takes three clicks (plant
tool -> click the site to open the chooser -> pick a card -> click the site again);
my first try switched tools before the last click and built nothing.
Plants expire after ~50 years. The next one is due around 2001.

**The blackout in numbers (save facts):**

| Date | Population | Funds | Note |
|---|---|---|---|
| May 1950 | 4,642 | $14,587 | coal plant still running |
| Jul 1951 | **1,054** | $14,452 | plant expired; city dark |
| Sep 1953 | 4,449 | $8,023 | two years after the oil plant |

The blackout wiped out three-quarters of the city in about a year, and rebuilding
power brought nearly all of it back within two years. So the 1948-1950 "plateau"
was partly the old plant failing, not only a land shortage. Mayor's lesson: watch
infrastructure age, not just zoning, and never let the treasury sink below the cost
of replacing the plant.

**Sep 1953 save:** population 4,449, funds $8,023, R demand +2000, C -28, I +693,
pollution 5,099 (down from 6,333 with coal; the oil plant is cleaner, as hoped).
The water map is **still red across the whole city**: the single land pump plus one
pipe trunk isn't watering anything. Inspecting the underground view next.

Underground check: the pipe exists, but the short power line feeding the pump shows
the yellow "unpowered" marks. The pump and police station were linked to the *old*
coal plant's outgoing line, which died with the plant. An unpowered pump pumps
nothing, so the whole city stayed dry. Fix: a direct line from the oil plant's east
edge to the pump.

Jun 1955 ($8,166): my plant-to-pump line **missed**. It still shows unpowered marks
because it doesn't touch the plant, and a zoomed view shows the pump is actually at
about (406,295), south-east of the police station, not where I clicked. Re-drawing
along one tile axis, from the tile against the plant's south-east edge to the pump.
Lesson: zoom in on the building I'm wiring *before* drawing the line.

Oct 1956 ($8,259): after the re-drawn line, the wires around the pump and police
station no longer show any "unpowered" marks, so the pump should finally be running.

**Oct 1956 save (AGENT019):** population **4,783 (new high)**, funds $8,259, R demand
+2000, C +188, I -332, pollution 5,293, crime 1,137. Residents still want homes. Jobs
are now satisfied (I below the line), so the next zoning should be residential and
commercial, not factories.

Even with the pump powered, the Water Supply map stayed red. The underground view
explains it: the only pipe is a short stub running from the pump to the edge of
town. It never goes under the neighbourhoods. Pipes are cheap ($3 a tile), so I'm
laying a trunk under the city's main diagonal plus three cross pipes through the
residential blocks, then checking the map again.

Underground zoom: the long pipe drag only laid about 8 tiles before stopping, so the
three cross pipes were **islands** that didn't touch the pump's network. Water, like
power, only flows through connected pipe. I'm re-laying the trunk in two shorter drags
that end exactly where each cross pipe starts. Lesson: keep each pipe or line drag
short (about 8 tiles or fewer) and check the joins in the underground view.

Both re-lay drags were silently refused (nothing appeared, funds unchanged), the
same spot where the first long trunk stopped, so something at that tile blocks
pipes. New route: chain the cross pipes end-to-end along the other axis (the far
end of the north pipe -> the end of the middle pipe -> the end of the south pipe).
The south pipe already joins the pump's line.

Apr 1960 ($8,374): the reroute worked partly. The middle cross pipe now joins the
south pipe, which joins the pump, so two neighbourhoods are on the pump's network.
The north-west pipe is still an island; I'll join it once I see water flowing.

**Apr 1960 save (AGENT020):** population 4,791, funds $8,426, R demand +2000, C -350,
I -679, pollution 5,243. Population is flat but money is steady. Residents still want
homes, while shops and factories have enough. So the land for homes is the
constraint, which is why water (to let houses grow taller) is still the priority.

Jan 1962 ($8,566): with the middle and south pipes joined to the pump, the Water
Supply map is still red. The pipes now look fine, so I'm checking the pump itself
with the query tool (is it powered, how much is it pumping) before spending more.

**Root cause found (Jan 1962):** the query tool on the water pump says
**Powered: No, Watered: 0 gallons per month.** My earlier power-line fixes looked right
on screen but never touched the pump. That's why no pipe network could ever carry
water. Lesson: use the query tool on a building to check it's powered; don't infer it
from line colours.

Zoomed surface view: the wires around the pump form a tangle that stops one tile
short of the oil plant. Buildings pass power to touching buildings, and the police
station touches the plant, so I'm running a 2-tile line from the pump's south-west
neighbour into the police station, then querying the pump again.

The new 2-tile line cost $2, but the pump still said "Powered: No". The game was
paused, though, and power is only recalculated while the simulation runs. Running
it for a few seconds before querying again.

**Jan 1962 save (AGENT021):** population 4,826, funds $8,564, R +2000, C -118, I -659,
pollution 5,148, crime 1,018. By Feb 1963 the pump still says **Powered: No**, so the
2-tile line doesn't connect either. Zooming in to the individual tiles before
trying again.

8x zoom: every wire segment around the old pump, and the pump itself, carries the
red "unpowered" zigzag. The whole tangle is an island that ends about one tile short
of the police station. Instead of adding more wire, I'm placing a **new $100 pump on
the tile touching the police station.** Touching buildings share power, and that tile
sits over the pipe trunk, so the new pump gets both power and pipes.

The new pump was **refused**: the query shows the tile is sloped "Clear terrain" and
funds didn't drop. Next idea: drag a power line along one tile axis that *starts
inside* the oil plant and ends next to the old pump. The game skips tiles it can't
build on, so the first wire tile it lays will be the one touching the plant. That
closes the one-tile gap without me having to pinpoint the plant's edge.

**Jun 1965 save (AGENT022):** population 4,891 (a slow new high), funds $8,842,
R +2000, C +3, I -703, pollution **6,743, rising again**. Money is steady and growth
is a trickle. Residents still want homes; the city can't house them.

**Water is finally on (Jun 1965).** After the line that starts inside the oil plant,
the pump query reads **Powered: Yes, Watered: 33,120 gallons per month**, and the red
"unpowered" marks are gone from the wires. The trick that worked: drag the line from
inside the source building, so the game itself lays the first tile against the
plant's edge. Next: let water spread through the joined pipes and watch whether homes
start growing taller.

**Feb 1966 newspaper:** the opinion column says "Pollution Blows!" and **mayor
approval is down to 47%** (61% in 1951). Pollution in the save rose from 5,148 (1962)
to 6,743 (1965). Residents' biggest complaint is clearly pollution, so after water,
the next priority is pollution relief: parks and trees between the factories and the
homes, and moving to a cleaner power mix when the oil plant can be replaced.

**Apr 1966 newspaper:** "Flood Squishes New City", plus a front-page story,
**"Fire Station Wanted"**: hot, windy weather makes a big fire likely, and the city
has no fire department. Approval is 58%. The status bar says "Fire Protection
Demanded". A fire in a city with no fire station could undo decades of growth, the
way the blackout did, so a fire station is now the top build after confirming water.

**Accident (Dec 1966):** while I was dismissing the stacked newspaper pages, a click
picked the Centering tool and scrolled the main view onto empty river land. I'm
**not** building there. That's the off-screen expansion I've ruled out. I'm
re-centring on the city right away, then re-checking the landmarks before any more
building, since all my coordinates depend on the view.

While I was clearing the newspaper pages and re-centring, the game was **unpaused**
(probably by the Escape key or a menu click) and ran from Dec 1966 to Jan 1972 with
nobody steering. The view is still off-centre, with the city at the left edge. I'm
pausing now, then re-centring on the city before doing anything else.

**Jul 1971 save (AGENT023):** population 4,814, funds $9,417, R +2000, C -206, I -756,
**pollution 10,251** (up 50% from 6,743 in 1965), EQ 72. Even with water on, the
population hasn't moved. Pollution is now the dominant problem, and it's what the
residents keep complaining about.

**Jan 1976 newspaper:** "Barton Labs Perfects The Wind Turbine" (wind power is now
invented, a clean option for when the oil plant wears out), "Beautiful Smog", and
"Pollution Blows!" again. Mayor approval is 51%. The game was still running when the
paper appeared, because my pause click had landed while a paper was on screen.
Rule: close every paper *first*, then pause, then check that the status bar says
*PAUSED*.

**Getting back to the city view (May 1976, paused):** the pump that used to be at
screen (407,296) is now at about (135,225), so the view has moved by roughly
(-272,-71) pixels. The Centering tool puts whatever point I click at the middle of the
view, so two clicks at (184,220) should each shift it back about (+136,+35). Then I'll
re-measure the pump to confirm the old coordinates hold. I also added a prompt rule:
close every newspaper page before pausing, and never leave the Centering tool selected.

View restored (May 1976): the city is fully back on screen. The Centering tool snaps
to tiles, so the view now sits two tiles from the original: the pump is at (424,304)
instead of (407,296), so every old coordinate is **+16, +8**. I'm keeping this view
and using the new offsets rather than nudging it again.

**Budget review (May 1976):** property tax 7%. The year-end estimate is only about
$212 in tax income, $100 for police and $18 for transit. The city spends nothing on
fire, health or education, and has **no city ordinances**. The treasury ($9,893) is
mostly old savings, not ongoing profit, so anything with yearly upkeep has to be
chosen carefully. Checking the ordinance list for pollution measures.

Also noticed: the yellow-dotted terraces at the top-left of the view are land zoned
decades ago that never developed. That's existing, on-screen land the city could
grow into once whatever's blocking it is fixed (likely power, water or road access).

**Mayor's policy package (May 1976): city ordinances instead of more construction.**
Each one targets a problem the city's own reports flagged:

| Ordinance | Why |
|---|---|
| Pollution Controls | Pollution is at 10,251, residents' top complaint ("Pollution Blows!"), approval at 51% |
| Volunteer Fire Dept | "Fire Station Wanted" / "Fire Protection Demanded", with no fire department at all |
| Pro-Reading Campaign | Education quotient has slid from 83 to 72 since 1925 |
| City Beautification | Raises land value, which attracts denser and better housing |

Ordinances act city-wide, need no land (the visible land is the constraint), and can
be switched off. Checking the estimated annual cost against the ~$212 yearly tax
income before confirming.

All four ordinances are active, and they cost very little: Pollution Controls $12/yr,
Volunteer Fire Dept $4/yr, City Beautification $3/yr, Pro-Reading $2/yr, **$21/yr in
total** against about $212/yr of tax income. A city-wide policy fix for about a tenth
of the budget. Running the city again to see whether pollution and approval respond.

Jul 1979: funds have risen to $10,111 with the ordinances active, so they cost almost
nothing. No fires visible. Letting the city run a few more years before reading the
next save, to see whether pollution drops.

**May 1984 newspaper: the ordinances are working.** Mayor approval is **64%**, up from
about 51% in 1976. Fred's Opinion column now complains "Traffic Bites!" where it used
to say "Pollution Blows!", so pollution is no longer residents' main complaint.
The status bar still reads "Fire Protection Demanded"; the volunteer fire ordinance
isn't enough, and the city needs a real fire station. Solar power has been invented.
Next: close the paper, read the next save, then site a fire station and look at traffic.

Closing the 1984 paper let the game run again (to Oct 1984, $10,456), the same trap the
prompt warns about: the newspaper's pause doesn't last. I'm pausing straight away before
building the fire station.

**Fire station attempt 1 failed (Nov 1988).** Funds stayed at $10,732 (no $500 drop):
the spot next to the V road is sloped. My Pause click also seems to have *unpaused* a
game that was already paused (the newspaper had paused it), so the city drifted another
four years, Oct 1984 to Nov 1988. Lesson: read the status bar first and only press
Pause when it doesn't say *PAUSED*. Looking for a truly flat 3×3 spot next.

**Fire station attempt 2 failed too.** I tried the flat plateau just east of the water
pump (455,292), but funds stayed at $10,732. The terrain there looks flat, so the
problem may be the input (a quick click not counting as a build), not the land.
Trying a press-and-move on the same spot to tell the two apart.

Attempt 3 (press-and-move) showed the fire station's 3×3 footprint outline on screen,
so the input reaches the game. The station still wasn't built (funds unchanged): the
footprint's west corner overlapped the slope edge, and the game needs all nine tiles
flat. Moving the station two tiles east, onto the middle of the plateau.

**Fire station built (Nov 1988).** On the 4th attempt it went in on the flat plateau
east of the water pump, and funds fell $10,732 → $10,232, which proves the build.
Lesson: civic buildings need all nine 3×3 tiles flat. Pressing and moving shows the
footprint first, so you can see when one corner is on a slope. Next: wire it to the
powered pump and confirm with the Query tool.

Wiring the station from the pump cost $6 (funds $10,232 → $10,226). Query on the
station: **31 firefighters, 4 fire engines, response time 0 minutes, annual cost $0.**
The $0 is suspicious: the 1976 budget showed nothing spent on fire, so the fire
department may be funded at 0%. Checking the Budget window.

Budget, Nov 1988: the fire department is funded at 100% (the $0 was just the first
partial year; the year-end estimate is −$8). Ordinances cost −$23/yr. The city still
ends the year **+$61**, so services are affordable. Next question: why have the
yellow-dotted zoned terraces at the top-left stayed empty for decades? Querying one.

**Native save AGENT025 (Nov 1988): the ordinances worked.**

| | May 1976 (AGENT024) | Nov 1988 (AGENT025) |
|---|---:|---:|
| Population | 4,794 | 4,578 |
| Funds | $9,893 | $10,232 |
| Pollution | 10,351 | **3,280** (−68%) |
| Crime | 1,101 | 955 |
| R / C / I demand | +2000 / −356 / −700 | +2000 / **+604** / −921 |

Pollution Controls cut pollution by two-thirds for $12/yr, and commercial demand has
turned positive. Population still hasn't moved, so pollution wasn't the only cap.

**New diagnosis: zoned land doesn't match demand.** The yellow-dotted terraces at the
top-left are *light industrial* zones on clear, flat land with $13,000/acre value and
no pollution. They've sat empty for decades because industrial demand is negative
(−921) and has been since the 1950s. Meanwhile residential demand is maxed. The fix a
mayor would make: **re-zone that empty industrial land as residential** (plus some
commercial, now that C demand is +604). It's on screen, already flat, and needs no
demolition of buildings, only de-zoning empty tiles.

Re-zoning, step 1: the dotted strips sit on stepped terraces. Only the strip right
beside the north neighbourhood is within the 3-tile road reach that zones need, so I'm
re-zoning that one first (light residential over the empty industrial tiles). The
higher strips would also need a road before they could grow.

Re-zone step 1 **worked**: the empty industrial strip turned green (light residential)
for $95 (funds $10,226 → $10,131), with no bulldozing needed. SimCity lets you zone
straight over *empty* zoned tiles; developed buildings are left untouched. Step 2:
the next strip up the terrace becomes residential too, and the empty strip beside the
V road becomes light **commercial**, because commercial demand is now +604.

Re-zone step 2: funds $10,131 → $10,081 ($50). The second terrace strip is now
residential (green), and the strip beside the V road is commercial (blue). The two
highest strips stay industrial for now; they're too far from any road, so they need a
road up the terrace before re-zoning would help. Running the city ~30 s to see if the
new homes and shops fill in.

**Jul 1992 check: re-zoning alone hasn't worked yet, and water is now the limit.**
- Save AGENT026 (Jan 1992): population **4,413** (down from 4,578), funds $10,048,
  pollution steady at 3,282, R/C/I demand +2000 / +188 / −804.
- The status bar now reads **"Water Shortage Reported"**. The single pump (33,120
  gallons/month) can't supply the whole city.
- The re-zoned green and blue strips are still just dots after ~3.5 years. Meanwhile
  part of the north factory block has turned into houses (red roofs), so the city is
  shifting from factories to homes on its own.
- Diagnosis: homes want to grow (R demand maxed), but without enough water they stay
  small, and new zones are slow to fill. Next: add pumps. They make the most water
  next to a lake or river, so I'm looking at the pond in the middle of the city.

Another drift: the game was running (my last Pause press had toggled it back on), so
it reached **Jan 1996** before a newspaper stopped it. Mayor approval 55%, and
Fred's Opinion still says "Traffic Bites!". A closer look shows the blue "pond" in
the middle of the city is the pool of a big park, not a lake, so a pump beside it
would get no bonus. Plan: add more pumps on the flat plateau by the existing pump
and fire station (both powered), then join them to the pipe network.

Pump siting: the strip of flat tiles between the existing pump (424,304) and the
fire station, just south of the power line that now links them, is flat and empty.
New pumps there sit next to a powered line, and I'll join them to the old pump with
a short pipe drag. Each pump costs $100, so two more pumps would roughly triple the
water supply for $200.

**Two new water pumps (Sep 1999).** Funds $9,833 → $9,602 ($231 for two pumps and the
joining pipe). Query on the second new pump: **Powered: Yes, 15,120 gallons/month**.
Being next to the powered line was enough to power it. Checking the first new pump,
then the underground water view, to make sure the pipes reach every neighbourhood.

The first new pump checks out too: **Powered: Yes, 15,120 gallons/month**. Total
pumping capacity is now about **63,000 gallons/month** (33,120 + 2 × 15,120), nearly
double what it was, for $231. Next: inspect the pipe layer for gaps, then run the
city and watch for the "Water Shortage" message to clear.

**Underground view (Sep 1999): the real water problem is pipe coverage, not pumps.**
Blue pipes and watered (blue-shaded) tiles only cover the middle of the city: a loop
round the oil plant, a patch by the park, and the pump plateau. The big western and
southern neighbourhoods, where most of the houses are, have **no pipes under them at
all**, apart from one line up to the north block. Those homes can never grow past
small houses. Next: run short pipe drags (≤8 tiles each, since longer ones stop
early) along the western streets, each starting on the end of an existing pipe so
the network stays joined.

Pipe plan: three trunks into the west, all starting on the existing main where it
ends at (268,268) by the park. One runs up-left through the north-west blocks, one
down-left through the southern blocks, and one through the middle. Each is a chain of
drags of 7 tiles or fewer, each starting where the last one ended. Zones pass water
on to neighbouring zone tiles (as they do power), so trunks a few blocks apart should
cover everything. Expected cost about $5 per tile.

The pipe trunks went in for $200 (funds $9,602 → $9,402). New blue lines now run into
the north-west, middle and south-west blocks. Watered tiles only show their blue
shading after the simulation recalculates, so I'm running the city about 20 seconds
before judging whether the trunks joined the main.

**Jan 2000 newspaper: "Plant Nearing Death".** The oil plant built in 1951 is near the
end of its ~50-year life. In 1951 the old plant died with no replacement, and the
population crashed from 4,642 to 1,054, so this time **I'll build a replacement
before it dies**. Same paper: mayor approval is **72%**, the highest since the 1930s
(up from 51% in 1976), Fred's Opinion says "Lazy Students!" (education is the next
complaint), and there's a hurricane warning.

Save AGENT027 (Sep 1999): population 4,763 (up from 4,413 in 1992), funds $9,402,
pollution 2,505 (lowest since the ordinances), R/C/I demand +2000 / −167 / −805.

Jun 2000: the game ran on after the paper closed, so I paused again. The underground
view shows the blue watered shading has grown only slightly around the park. The
western blocks are still unshaded even though the new trunks are visible, so at least
some trunks probably don't join the main. I'll check that after the power plant
decision, which is more urgent: the oil plant is about to die.

**Jan 2001 newspaper: "Time Running Out".** The Pause press didn't stop the game; it
ran on from Jun 2000 to Jan 2001. The plant is now at the very end of its life.
Approval 68%, and "Pollution Blows!" is back in Fred's Opinion. Replacing the plant is
now the top priority, ahead of water. I'm also checking why Speed → Pause keeps
failing, since every drift has cost the city years.

Jun 2001: the game is still running and the oil plant is still alive ($9,339).
Speed → Pause has now failed three times in a row, so I'm opening the Speed menu to
look at it directly, rather than assuming the fixed menu coordinates still hit
"Pause".

**Jan 2002 newspaper:** another "Time Running Out" front page. The plant is still alive
but on borrowed time. Approval 72%, and Fred's Opinion has moved on to "Taxes Suck!",
so tax cuts are worth considering once the plant is replaced. At cheetah speed a year
passes in seconds, and a newspaper appears every January. Closing a paper resumes
the game, so I now close the paper and pause in the same quick batch.

**Jan 2002: the oil plant has died.** Closing the paper and pausing in one batch worked
(*PAUSED* at Jan 2002, $9,307), but the plant site is already rubble. The 1951 lesson
says every month without power costs thousands of residents, so I'm rebuilding right
away:
- **Choice: another oil plant on the same site** (~$6,600). The site is flat and
  proven, and it already touches the city's power lines. Oil gave enough power for
  50 years with less smoke than coal.
- Gas or solar would be cheaper but much smaller, and I don't know their footprints
  or exact output on this terrain. Guessing wrong would mean more months of blackout.
- Funds afterwards are about $2,700, still above the $1,500 safety floor. Income is
  positive, so the treasury will rebuild.

**Mistake: I built a wind turbine instead of an oil plant.** Funds fell only $100
($9,307 → $9,207), and the status bar reads "Wind Power $100". The plant chooser's
layout changes as new plants are invented (wind in 1976, solar later), so the fixed
"oil" button position now lands on wind. A $100 lesson, not a disaster, but it shows
the toolmap's chooser positions are only valid early in the game. I'm reopening the
chooser to read the current layout before picking again.

A close-up of the plant site shows the wind turbine just north of the old plant, the
old plant's grey **rubble still in place**, and flashing red "no power" markers on
every power line. The whole city is in blackout, so the replacement plant can't wait.

The chooser now shows seven plants in a 3×3 grid: coal 200 MW $4,000, hydro 20 MW
$400, **oil 220 MW $6,600**, gas 50 MW $2,000, nuclear 500 MW $15,000, wind 4 MW $100,
solar 50 MW $1,300. Decision: **oil again**. Solar is cleaner and cheaper, but at
50 MW it's a quarter of the output that ran this city for 50 years, and a plant too
small for the city would mean rolling blackouts. Pollution Controls is already
holding pollution down, and nuclear is unaffordable. I've added the late-game chooser
positions to the toolmap (`power_plant_late.*`), plus a prompt rule to check the
status bar names the right plant before placing it.

The first oil placement didn't take: "Oil Power $6,600" was selected but funds stayed
at $9,207. The dead plant's rubble covers the site, and unlike 1951 the game won't
build over it. Clearing the old 4×4 footprint with the bulldozer first, then placing
the oil plant again.

Save AGENT028 (Jan 2002, in blackout): population 4,586, funds $9,207. My clearing
batch failed on a tool-name slip: "bulldozer" is the toolbar group, and the tool
itself is `demolish` (the same trap as "roads" vs `road`). Retrying with `demolish`.

**New oil plant built (Jan 2002).** After clearing the rubble with `demolish`, the
plant went in on the old site, and funds fell $9,207 → **$2,605** (−$6,602), which
proves the build. That leaves the city above the $1,500 floor with positive yearly
income. Running briefly at llama speed to let power spread, then checking that the
zones are powered again.

Feb 2002, paused after a short run. I queried one of the lots re-zoned as commercial
in the south-west. It's still trees, with **$256,000/acre** land value, no crime and no
pollution. That's prime land, so what holds it back isn't desirability; it's weak
commercial demand (it swung between −356 and +604 across the last saves). Next I'm
querying a developed block to confirm the new plant's power is reaching homes.

Querying a developed industrial building north-west of the plant shows **Powered: No**
and Watered: No. The new oil plant is built but not tied into the grid: clearing the
rubble likely also took out the wire tiles touching the old plant. Same fix as in 1951:
redraw a short power line starting inside the new plant out to the nearest existing
line, then re-query.

Close-up: the new plant sits on the old site, but a one-tile ring of rubble separates
it from the three existing wires (east, north-west, south-west). I'm bridging all three
with short power-line drags that start inside the plant, so the first wire lands on
its edge. Three routes in also keep one broken line from blacking out the city again.

The three bridge wires cost $10 (funds $2,595). After a month the north-west chemical
storage still read Powered: No, so I let the sim run to Jun 2002 and queried again
near the plant. That hit the police station (25 officers, $100/yr), whose query box
doesn't show power. Next I'm querying the plant itself for its output and load.

The plant query is clear: **Oil Power, 220 MW max, running at 0% of capacity**, age
0 of 50. It's built but feeds nothing, so the bridge wires didn't connect. The tiles
between the wires and the plant are probably still rubble. Opening the city map's
power layer to see exactly where the live grid stops before spending more.

An 8× close-up explains the 0%: the new plant sits about a tile north-west of the old
footprint. The old rubble still covers the strip on its south and east sides, and the
three wires only reach the plant's corners diagonally. In SimCity 2000 a wire has to
share a tile edge with the plant to connect. The city map's power layer will show
which wires are live before I re-route.

The power layer of the city map shows **every zone red, i.e. unpowered**. The whole
city has been dark since the plant died in Jan 2002. Next test: one straight wire
along the tile grid, from the plant's centre out through its south-east edge toward
the east wire. If funds drop, the rubble accepts wires and the edge connection is real.

The test wire cost only $2: just the far tile was built, so **rubble won't take power
lines**. Rather than demolish rubble next to a new $6,600 plant (one misclick would
destroy it), I'm routing around it: a wire out of the plant's clean north-west edge,
then down the west side to the south-west feeder that runs into the neighbourhoods.
After a short run I'll query the plant for its capacity.

Aug 2002: the plant still runs at 0%. The route-around wires added only a couple of
tiles ($4), because at this zoom the tile grid is too small to drag wires precisely.
I'm doing what a human player would: zoom in one step on the plant (it sits near the
centre of the view, so nothing moves off-screen), lay the connection tile by tile, then
zoom back out.

Zoomed in, the layout is clear. Rubble rings only the plant's two south-facing edges,
which is why every wire coming from the south-west and south-east stops short. The
north-east edge is clean ground. The fix: a wire straight out of the north-east edge
along the tile grid, then down onto the east feeder line. That gives an edge-to-edge
connection with no rubble in the way.

The north-east wires were built ($10, funds $2,579 in Sep 2002), but the plant query
still reads 0% of capacity. That figure may refresh only slowly, so I'm checking the
city map's power layer instead, which shows directly whether zones get power.

**Blackout is collapsing the city.** Native saves during the outage:

| Save | Date | Population | Funds | C demand | Pollution |
|---|---|---:|---:|---:|---:|
| AGENT028 | Jan 2002 | 4,586 | $9,207 | −365 | 2,234 |
| AGENT029 | Mar 2002 | 2,143 | $2,595 | −300 | 2,057 |
| AGENT030 | Aug 2002 | 947 | $2,589 | +545 | 1,354 |
| AGENT031 | Sep 2002 | 648 | $2,579 | +946 | 1,262 |

Same pattern as 1951: without power, buildings empty out within months. The new plant
is paid for, but until it's tied into the grid nothing else matters. Every other plan
is on hold until the plant shows more than 0% load.

**Power restored (Jan 2003).** After a few months of game time the plant query reads
**Running at 5% of Capacity**, up from 0%, so the north-east wire joined it to the grid.
The load is only 5% because about 85% of residents left during the 12-month outage.
Funds are $2,512. Lessons: (1) a dead plant's rubble blocks new wires, so connect
through a clean edge; (2) the plant's "% of capacity" is the quickest proof of a real
connection, but it takes a few game months to update; (3) zooming in one step makes
tile-accurate wiring possible without leaving the visible map. Next: let the city
refill and watch population in the saves.

Sep 2003, eight months after power returned: a close-up shows mostly small houses
and many dark, emptied lots where the blackout drove people out. The Population
window shows a 56% work force. Funds are flat at $2,512 (tax income arrives in
January). I'm letting it run into 2004 and reading the next save before deciding
anything. Spending now would push funds toward the $1,500 safety floor.

**Oct 2004 save (AGENT032): population 344, funds $2,397.** The decline continued even
after the plant reconnected. Demand is now high for everything (R +1811, C +2000,
I +1565): people want to come, but the city isn't giving them working zones. The plant
running at only ~5% suggests the reconnection reaches just a small part of the old
grid, and most neighbourhoods are still dark. Checking the power layer again to find
which feeder lines are cut.

The power layer shows the real problem. Only the plant and a little area around it
are yellow (powered), and every neighbourhood to the west and south-west is still red.
The north-east wire tied the plant to the **eastern** feeder only, which serves the
fire station and pump area: hence 5% load. The old **western** feeders, which ran the
homes, still end at the rubble on the plant's south-west side. Plan: zoom in, demolish
one rubble tile between the plant's south-west edge and the western feeder (single
clicks only, so the plant can't be hit), then wire through the gap.

The close-up shows a better route than demolishing anything. A wire stub already
touches the plant's south-west edge, but it ends one tile short of the lower western
feeder, and the gap is **clear ground, not rubble**. A short wire across that gap
should join the plant to the western neighbourhoods. Afterwards I'll check the plant's
load: it should jump well above 5% if the homes are back on the grid.

Jan 2005: the plant runs at **2%**, lower than before, and funds are $2,254 (slowly
falling, because tax income from ~300 residents no longer covers police and fire). The
south-west bridge didn't reconnect the western neighbourhoods. Either the wire didn't
land, or that lower feeder is itself cut further along. Inspecting the close-up next.

Second try at the south-west bridge worked. Dragging pole-to-pole, from a pole on the
stub to a pole on the western feeder, cost $8 (funds $2,254 → $2,246), and the
close-up shows new poles linking the two lines. (The first try likely missed both
lines, so nothing was built.) Letting a few months pass before checking the plant's load.

**Recovery is underway.** Save AGENT033 (Apr 2005): **population 2,479** (from 344 in
Oct 2004), funds $2,246, workforce 65%, EQ 79, demand R +2000 / C +1512 / I +1449.
The western neighbourhoods are lit and full of buildings again. The $8 south-west
bridge was the key connection: the first fix only reached the eastern feeder. The
lesson for the playbook: after rebuilding a plant, check the power map **for each
neighbourhood**, not just the plant's load. Zooming back out and letting the city refill.

Apr 2007: neighbourhoods look full again on screen, but funds keep drifting down slowly
($2,246 in Apr 2005 → $2,178 now, about $30/year). This is still above the $1,500
safety floor, so no cuts yet. I'm holding off on building while tax income catches up
with the returning residents, and checking the Population window for the current count.

**Full recovery.** Save AGENT034 (Oct 2007): **population 4,676** (from 344 three years
earlier), funds $2,178, demand R +2000 / C +929 / I −5, pollution 2,577, crime 1,030,
workforce 62%, EQ 79. The blackout is behind us, but the city is back at its old
~4,600 plateau, and money is now the binding constraint: only ~$700 above my $1,500
floor, after the $6,600 plant. Before any new growth push I'm reading the budget to
see where the money goes and whether a small tax or spending change can fund it.

**Budget, Oct 2007** (Budget window): property tax 7% brings in about $221/year.
Spending: police $100, fire $100, transit $18, ordinances $24. That's **about −$20/year**.
The deficit is small (30+ years of runway at $2,178), so I'm *not* raising taxes: R
demand is maxed, and higher taxes would only push residents away. I'm also not taking
a bond, because the interest would exceed the city's whole tax income. Decision: spend
the ~$700 above the floor only on cheap, high-value fixes. Water is the first suspect:
before the blackout the western half was dry, which keeps houses small. Checking the
water map now.

**Water map, Oct 2007:** almost the whole city is red (no water). Only a small yellow
patch near the top of the city has water. So the water system that served the city before
2002 has collapsed. The most likely cause is that the pumps lost power during the
blackout and sit on a feeder the new wires don't reach, or pipes broke where buildings
were rebuilt. Without water, homes stay small even at maximum demand, which matches the
old ~4,600 ceiling. Next: query the pumps by the pond to see if they're powered.

**Underground view, Oct 2007.** Water reaches only the plant district: the blue-shaded,
watered tiles stop at its west edge. The large western neighbourhoods, where most homes
are, have almost no pipes under them, so they've never had water. That's the clearest
cause of the ~4,600 ceiling: unwatered homes can't grow past small houses. Pipes cost
$3 a tile, so this is the cheapest growth fix available while money is tight. Plan:
three 8-tile trunks westward from the edge of the watered network (up-left, down-left,
and from its south side), each starting on a watered pipe so it joins the network.
Budget about $75.

**Pump check, Sep 2008.** After seven game months, the three new pipe trunks (~$74)
haven't spread the watered shading west at all. A query on a pump west of the fire
station: **Powered: Yes, 22,320 gallons/month**. The pumps survived the 2002 blackout and
are back on power, so the supply side is fine. The western pipes must not be joined to
the pumps' network. Pipes only carry water as one connected system, and an island of
pipes is as dry as no pipes. Next: in the underground view, trace the pipe run from the
pump plateau westward, find the break, and bridge it with a short drag.

**Feb 2009: cross-pipes laid, still dry; money is now the limit.** Two short cross-pipes
now join the dry western pipes to the watered grid, but the watered area didn't grow
after five game months. My best explanation is that the network is joined and **demand
is bigger than supply**: about 4,800 residents plus industry, and the game waters the
tiles nearest the pumps first. That points to more pumps. But funds are **$1,956**
(Sep 2008 save: pop 4,779, R +2000, C +734, I −443), close to my $1,500 safety floor,
and the budget runs about −$20/year. A mayor with an empty treasury raises revenue
before building, so the next move is the budget window: a small property-tax rise
(7%→8%) to fund a few $100 pumps over the next couple of years. Demand for homes is at
maximum, so a 1-point rise shouldn't scare off residents.

**Tax decision, Feb 2009.** Raised property tax from 7% to 8%. The budget's year-end
estimate went from **−$24 to +$1**, with income up from $215 to $241/yr. That stops
the slow slide toward the safety floor, but there's still no surplus for pumps. Demand
for homes is still at maximum (R +2000), so people want in badly enough to take a
little more tax. I'm trying one more notch (9%, about +$27/yr) and I'll watch whether
residential demand drops. If it falls sharply, I'll go back to 8%. I'm keeping police
and fire at 100%: crime is ~980, and both cost the same $100 whether the city grows or
not.

**Apr 2010: the tax rise worked.** After a full year at 9% the treasury rose from $1,956
to **$1,978**, the first rise since the 2002 blackout. That's only ~$25/yr, but money
has stopped draining. To test the "demand beats supply" water theory cheaply, I'm adding
**one** $100 pump beside the existing powered pumps, which leaves ~$1,878, still above
the floor. If the watered area grows after a few months, supply was the limit, and I'll
add pumps as money allows. If it doesn't, the western pipes are still cut off somewhere
and I'll go back to tracing.

**Feb 2011: pump #4 joined, still dry; demand turning.** The 4th pump ($100) is now
piped into the pump grid ($3), but the watered area hasn't grown west after another
four months. So supply probably wasn't the only limit, and the western pipes still
aren't getting water from the pumps. Save AGENT037 (Feb 2011): **pop 4,734, funds
$1,881**, crime down to 746 (from 961), pollution 2,332, **R +1766, C −1016, I −1155**.
Commercial and industrial demand have turned clearly negative since the tax went to
9%. I'll take it back to 8% once there's a buffer. Next: open the Water Supply map,
which shows actual watered tiles more clearly than the underground shading, and find
exactly where water stops.

**Water Supply map, Feb 2011: the real picture.** The whole city is **red (dry)**. Only a
tiny yellow patch next to the pumps has water. So the blue shading I'd been reading in
the underground view isn't "watered", and supply isn't the problem either: four
powered pumps make water, but **none of the city's pipe network is joined to them**.
Water stops right at the pump plateau. That explains why every pipe I added in the
west did nothing. Next: zoom in on the join between the pump grid and the pipe that
runs toward the oil plant, find the missing tile(s), and bridge it with a 1–2 tile pipe.

**Jun 2011: the water break was one missing tile.** Zoomed in 2x underground, the city's
trunk pipe ended in a **cyan end-cap** one tile short of the pump grid. A cyan cap marks
a pipe end that isn't joined to anything. One $3 pipe tile bridged the gap, and within
four game months the Water Supply map showed yellow (watered) tiles spreading from the
pumps into the middle of the city, where before only a speck by the pumps was watered.
Funds $1,875. Lesson: judge water from the **Water Supply map** (red = dry), not
the underground view's blue shading, and look for cyan end-caps to find breaks. Next:
let it run a couple of years so water spreads through the zones and homes can grow
denser, then read the saves.

**Jun 2012: first growth from water.** Save AGENT038: **pop 4,884**, a new high (from
4,734 in Feb 2011), funds **$1,889** (steady at the 9% tax), R +1880, C −852, I −1271.
The Water Supply map shows the centre watered, but the western neighbourhoods are still
red, so the western pipes must have more breaks like the first one. Next: scan the
western pipe network at 2x zoom for cyan end-caps and bridge each with single $3 tiles.
That's the cheapest growth available while money is near the floor.

**Correction, Jun 2012.** Looking closer at the western pipes, cyan dots appear at the end
of *every* pipe branch, including ones that are properly joined. So a cyan dot just
means an open end. It's only a break when it stops one tile short of another pipe, as
the first one did. The western zone grids all touch the main trunk, so the network
looks joined. The remaining dry west is now most likely **too little water**: four
pumps for ~4,900 people. Next: look at the pump plateau above ground and add pumps
beside the powered ones as money allows, keeping funds above $1,500.

**Pump #4 was never powered.** Above ground at 2x zoom, the pump I added in 2010 has a
yellow **lightning bolt** (the game's "no power" sign). It sits one tile below the
powered pump row, and unlike the 1999 pumps it doesn't touch a powered building. So the
"add supply" test never actually ran. Fix: a 2-tile power line (~$10) from inside the
powered fire station onto the pump, then check the bolt is gone and the Water Supply
map spreads further west.

**Aug 2012: pump #4 powered.** The 2-tile power line from the fire station connected
($8, funds $1,881), and the lightning bolt on the pump is gone. All four pumps now run.
Next: the Water Supply map shows whether the extra supply pushes water further west.

**Jan 2013: water spreading.** With all four pumps powered, the Water Supply map's yellow
(watered) area has crept further into the north-west of the city. Funds **$1,907**, still
inching up at the 9% tax. I'm letting it run about two game years without spending, so
homes on newly watered land can grow, then I'll read the save.

**Jun 2014: water didn't move the needle; jobs are the brake.** The save says
**4,606** people (down from 4,884 in Jun 2012), funds **$1,914**. With all four pumps
powered, the water map stopped changing after Jan 2013. Demand: homes **+1,815**, shops
**−1,222**, factories **−1,154**. People still want to move in, but businesses don't want
to open, and without jobs homes don't fill. Shop and factory demand turned negative
right after I raised property tax from 7% to 9% in 2009. That points to the tax as the
brake, not water.
**Decision:** open the budget and lower property tax to 8%. My 2009 estimate put 8% at
about break-even (+$1/yr), so the treasury should hold while businesses get a break.

**Jun 2014: property tax cut 9% → 8%.** Budget before the cut: $255/yr income, police
and fire $100 each, ordinances $21, transit $18, net **+$17**. After the cut the game
estimates **+$2** net and $1,916 at year end, so the treasury still holds. Police and
fire stay at 100% (crime 645 and falling, fire coverage needed). Now I'll run two game
years and check whether shop and factory demand turn positive again.

**Nov 2016: the tax cut is working.** Save AGENT040: **4,673** people (up from 4,606),
funds **$1,911** (flat, as the budget predicted). Shop demand recovered from **−1,222 to
−335** in about two years, and factory demand from −1,154 to −910. Home demand is at the
maximum (+2,000). Crime rose to 867, so watch it.
**Read:** the 9% tax was choking businesses, and cutting it is bringing them back. I'll
keep 8% for two more game years and see whether shop demand turns positive before
spending any of the thin treasury.

**Oct 2018: slow climb.** Save AGENT041: **4,754** people (+81 in two years), funds
**$1,905** (flat). Home demand is still at the maximum (+2,000). Shop demand slipped back
to −613 and factory demand improved to −777.
**Read:** people want to live here, so the limit is not desirability; it's that existing
homes can't grow denser. The Water Supply map still shows the west of the city dry, and
dry homes stay small. With about $400 above my $1,500 floor, the best use of money is
extending pipes into the west, which is cheap per tile and on screen. Next: underground
view to see where the western pipes stop.

**Oct 2018: pipe into the dry west.** In the underground view the eastern pipe grid is
watered (light blue), but the western pipes and the dry (red/yellow) homes around them
didn't clearly join it. I dragged a 5-tile pipe from inside the watered grid down-left
beside the western segment. Pipes join any pipe on a neighbouring tile, so running
alongside it is enough. Cost **$14** (funds $1,905 → $1,891). The Water Supply map now
shows more of the south-west centre watered. A strip on the far west and one on the
east are still red. Next: run two game years and read the save.

**Oct 2018: west pipe joined the network.** The underground view now shows almost the
entire pipe grid light blue (carrying water). The red/yellow "dry" markings that covered
the west-centre are down to a few small patches. Funds **$1,881**. That one short pipe
had joined two separate pipe networks, like the 2011 fix. If homes now grow denser,
water was the main cap on residential growth. Next: check the surface view, then run
time and read the save.
