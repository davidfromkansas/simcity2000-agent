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
