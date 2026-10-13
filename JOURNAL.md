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
