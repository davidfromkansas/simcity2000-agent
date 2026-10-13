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
