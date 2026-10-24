# RestaurantRush Constrained-Random Verfication with Python For Functional Coverage

## Quick start
```bash
python dv/dv.py regress                      # directed tests + 200 random seeds, 100% coverage gate
python dv/dv.py regress --seeds 1000 -v      # more seeds, print every bin
python dv/dv.py regress --seed-base random   # fresh seeds (printed so you can reproduce)
python dv/dv.py run --seed 17 --profile chaos --dump   # one test, print its input script
python dv/dv.py replay tests/stage1/victory.txt --expect VICTORY
python -m unittest discover -s dv/tests -t dv          # DV self-tests
```