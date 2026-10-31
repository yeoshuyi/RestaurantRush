# RestaurantRush Constrained-Random Verfication with Python For Functional Coverage

## Quick start
```bash
python dv/dv.py regress                      # stage 3 (default): directed + 200 random seeds, 100% coverage gate
python dv/dv.py regress --stage 2 --repo <stage-2 checkout>   # verify the stage-2 tag
python dv/dv.py regress --stage 1 --repo <stage-1 checkout>   # verify the stage-1 tag
python dv/dv.py regress --seeds 1000 -v      # more seeds, print every bin
python dv/dv.py regress --seed-base random   # fresh seeds (printed so you can reproduce)
python dv/dv.py run --seed 17 --profile chaos --dump   # one test, print its input script
python dv/dv.py replay tests/stage3/victory.txt --expect VICTORY
python -m unittest discover -s dv/tests -t dv          # DV self-tests
```
## Stages
`rrdv/spec.py` holds each stage's rules as data (`STAGE1`, `STAGE2`, `STAGE3`). Stage 2 registers
the `VIP` (loses 5/turn, 10% off, rounded half up to the cent) and `CRITIC` (loses 12/turn,
always orders the most demanding dish) customer kinds and swaps the turn-4 / turn-7
arrivals for a Critic and a VIP.

Coverage facts that depend on who arrives when (who can abandon and on which turn,
which items can be cancelled, cheapest bills) are computed in `rrdv/facts.py`, so the
Stage 1 covergroups stay valid in Stage 2. Stage 2 adds `rrdv/covergroups/stage2.py`:

| Covergroup | What it checks |
|---|---|
| `cg_customer_kind` | kind at each arrival turn, kind x item (Critic must order Pasta), kind x fate |
| `cg_pricing` | kind x bill (only VIP gets 10% off), VIP bill amounts |
| `cg_kind_satisfaction` | per-kind decay by state, payment delay vs fastest path, abandonment state |

### Stage 3
`STAGE3` turns on the `host`, `combo` and `happy_hour` features and appends the three pair
combos to the menu. The reference model, monitor and assertions only add Stage 3 behaviour when
the feature is on, so the same DV still verifies the `stage-1` and `stage-2` tags with unchanged
bins (256 and 304). `rrdv/facts.py` accounts for the Host (one turn faster: earliest payment on
turn 4) and Happy Hour (departures can be delayed, bills lowered). Customers who recovered during
Happy Hour and Happy Hour orders are binned in `rrdv/covergroups/stage3.py` instead of the
Stage 1 / 2 groups. Directed Stage 3 scenarios are in `stage3_directed()` in `rrdv/sequences.py`.

| Covergroup | What it checks |
|---|---|
| `cg_host` | Host action, seats per turn (Host + Waiter), Waiter after a Host seat, pick, table |
| `cg_combo` | kind x combo, combo bills (full and Happy Hour), combo order fate |
| `cg_happy_hour` | start turn (incl. last turn / never), display, recovery state x full/capped, kind x HH order, HH bill values, price lock, delayed departures |
