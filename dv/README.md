# RestaurantRush Constrained-Random Verfication with Python For Functional Coverage

## Quick start
```bash
python dv/dv.py regress                      # stage 2 (default): directed + 200 random seeds, 100% coverage gate
python dv/dv.py regress --stage 1 --repo <stage-1 checkout>   # verify the stage-1 tag
python dv/dv.py regress --seeds 1000 -v      # more seeds, print every bin
python dv/dv.py regress --seed-base random   # fresh seeds (printed so you can reproduce)
python dv/dv.py run --seed 17 --profile chaos --dump   # one test, print its input script
python dv/dv.py replay tests/stage2/victory.txt --expect VICTORY
python -m unittest discover -s dv/tests -t dv          # DV self-tests
```
## Stages
`rrdv/spec.py` holds each stage's rules as data (`STAGE1`, `STAGE2`). Stage 2 registers
the `VIP` (loses 5/turn, 10% off, rounded half up to the cent) and `CRITIC` (loses 12/turn,
always orders the most demanding dish) customer kinds and swaps the turn-4 / turn-7
arrivals for a Critic and a VIP.