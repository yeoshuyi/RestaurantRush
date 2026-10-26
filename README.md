# Restaurant Rush

A turn-based command-line restaurant simulation game built in Java following the Model-View-Controller (MVC) architecture.

* **Repository:** [https://github.com/yeoshuyi/RestaurantRush](https://github.com/yeoshuyi/RestaurantRush)
* **Release:** Stage 2 (`stage-2`)

> Stage 2 WIP

---

## 1. Directory Structure

```text
RestaurantRush/
├── README.md           # Project documentation and instructions
├── CONTRIBUTING.md     # Guidelines for team contributions
├── run.sh              # Build and execution script (macOS/Linux)
├── run.bat             # Build and execution script (Windows)
├── src/
│   └── rush/
│       ├── Main.java   # Application entry point
│       ├── ui/         # Console input, display formatting, and view bridge
│       ├── control/    # Game controller, turn loop, config, and statistics
│       └── model/      # Core entities (Restaurant, Customer, Staff, Order, Table)
├── tests/
│   └── stage1/
│       ├── victory.txt # script verifying victory condition
│       └── defeat.txt  # script verifying defeat condition
└── docs/               # System architecture and UML design diagrams
```

---

## 2. Build and Execution

### Prerequisites
* Java Development Kit (JDK 17 or higher recommended)

### Quick Run (Using Scripts)

* **macOS / Linux:**
```bash
chmod +x run.sh
./run.sh
```
* **Windows:**
```DOS
run.bat
```

### Manual Compilation and Execution
1. **Compile:**
```Bash
javac -d bin -sourcepath src src/rush/Main.java
```
2. **Run:**
```Bash
java -cp bin rush.Main
```

---
## 3. Test Verification

The application supports automated scripted playthroughs to verify deterministic customer choices, staff action validations, and game-ending states.

### Replaying Test Transcripts

Run the compiled application with an input script piped into standard input:

* **Victory Scenario:**
```bash
java -cp bin rush.Main < tests/stage1/victory.txt
```
* **Defeat Scenario:**
```bash
java -cp bin rush.Main < tests/stage1/defeat.txt
```
### Functional Coverage Verification with Constrained-Random Vectors

> The DV Script is written with heavy AI-assistance as an extra exploration outside of the project requirements. Please ignore it for grading.

`dv/` contains a Python (3.9+, standard library only) verification environment. It drives the game through stdin/stdout with constrained-random and directed inputs, and checks every run against a reference model and against assertions. It also measures functional coverage of turns, arrivals, Waiter, Chef, the order lifecycle, satisfaction and abandonment, eating and payment, results, print format and input robustness. It runs in GitHub CI as the `dv` job.

```bash
python dv/dv.py regress            # directed + 200 random seeds, 100% coverage gate
python -m unittest discover -s dv/tests -t dv
```

See [dv/README.md](dv/README.md) for details.

## 4. Stage Comparison

### Stage 1 → Stage 2 (Customer behaviour extension)

**Compare link:** https://github.com/yeoshuyi/RestaurantRush/compare/stage-1...stage-2

**What Stage 2 adds:** `VIPCustomer` and `CriticCustomer` alongside Regular customers. All customer types follow the same order and service flow. Type-specific behaviour is dispatched through overrides on `Customer` (`waitPenalty`, `computeBill`, `chooseItem`, `getType`), so the main game loop and turn controller have no type checks.

| Customer | Satisfaction loss per waiting turn | Bill | Special behaviour |
| --- | --- | --- | --- |
| Regular | 8 | Full price | None |
| VIP | 5 | 90% of base price (10% off), half-up rounding to the nearest cent | None |
| Critic | 12 | Full price | Always orders the most demanding dish |

**New files**
| File | Purpose |
| --- | --- |
| `src/rush/model/VIPCustomer.java` | VIP customer: 5-point wait penalty and 10% bill discount |
| `src/rush/model/CriticCustomer.java` | Critic customer: 12-point wait penalty and demanding-dish ordering rule |
| `tests/stage2/victory.txt` | Reproducible Stage 2 victory run |
| `tests/stage2/defeat.txt` | Reproducible Stage 2 defeat run |
| `dv/rrdv/covergroups/stage2.py`, `dv/rrdv/facts.py`, `dv/tests/test_stage2.py` | Stage 2 additions to the optional DV environment |

**Existing files changed**
| File | Change | Reason |
| --- | --- | --- |
| `src/rush/model/CustomerType.java` | Added the `VIP` and `CRITIC` literals | New customer types are registered in this enum, so the factory, controller and UI pick them up with no other changes |
| `src/rush/control/GameConfig.java` | Base-setting arrival schedule now has a Critic on turn 4 and a VIP on turn 7 | The brief requires a reproducible base-setting run with at least one VIP and one Critic. This replaces two Regular arrivals, so there are still six arrivals |
| `.github/workflows/ci.yml` | CI checks extended to cover Stage 2 features | Verifies the Stage 2 behaviour automatically |
| `README.md` | Added this Stage 2 documentation | Records the stage comparison and Critic behaviour |
| `dv/` files (`README.md`, `rrdv/__main__.py`, `assertions.py`, `covergroups/`, `model/game.py`, `sequences.py`, `spec.py`, `tests/test_dut_smoke.py`) | Updated for Stage 2 customer types | Keeps the optional DV environment in sync with the game rules (extra, not for grading) |

**Files deleted:** None.

### Critic behaviour
The Critic always orders the most demanding dish on the menu, meaning the dish with the most preparation units. Ties are broken by the higher price. On the standard menu this is Pasta (2 units, $18.00). The Critic also loses satisfaction faster than other customers (12 points per waiting turn instead of 8), so slow service is punished more heavily.

### Stage 2 reproducible runs
- Base-setting arrivals: turn 1 Regular, **turn 4 Critic**, **turn 7 VIP**, turns 10, 13 and 16 Regular (six arrivals in total)
- Victory: `java -cp bin rush.Main < tests/stage2/victory.txt`
- Defeat: `java -cp bin rush.Main < tests/stage2/defeat.txt`

### Stage 2 → Stage 3
(To be completed.)

## 5. Video Timestamps
(To be completed after recordi
