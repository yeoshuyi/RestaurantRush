# Restaurant Rush

A turn-based command-line restaurant simulation game built in Java following the Model-View-Controller (MVC) architecture.

* **Repository:** [https://github.com/yeoshuyi/RestaurantRush](https://github.com/yeoshuyi/RestaurantRush)
* **Release:** Stage 3 (`stage-3`)


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
│       └── model/      # Core entities (Restaurant, Customer, Staff, Order, Table,
│                       #   Host, ComboMeal, HappyHour)
├── tests/
│   ├── stage1/         # victory.txt, defeat.txt
│   ├── stage2/         # victory.txt, defeat.txt
│   └── stage3/
│       ├── victory.txt # script verifying victory condition (Host, combos, Happy Hour)
│       └── defeat.txt  # script verifying defeat condition
├── dv/                 # Python constrained-random verification environment
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
java -cp bin rush.Main < tests/stage3/victory.txt
```
* **Defeat Scenario:**
```bash
java -cp bin rush.Main < tests/stage3/defeat.txt
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

**Compare link:** https://github.com/yeoshuyi/RestaurantRush/compare/Stage-1...Stage-2

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
**Compare link:** https://github.com/yeoshuyi/RestaurantRush/compare/Stage-2...Stage-3

**What Stage 3 adds:** a `Host` staff role, `ComboMeal` menu items and a `HappyHour` pricing policy. A combo is an ordinary `MenuItem` subclass, so `Order`, `Chef` and `Waiter` are unchanged. `Menu.java` is also unchanged. The Host and Happy Hour are two new manager decisions added to the turn loop through `GameView`.

| Feature | Rule |
| --- | --- |
| Host | Seats at most one queued customer per turn, before the Waiter acts, in addition to the Waiter's task. The Waiter can still seat customers. |
| ComboMeal | Preparation units are the sum of both components. Price is 90% of the combined price, half-up rounding to the nearest cent. |
| Happy Hour | Manager starts it once per game at the start of a turn. It lasts that turn and the next, and the remaining duration is shown. Orders taken while active get 20% off, applied after the VIP discount, and the price is locked when the order is taken. At the start of each active turn, customers still waiting for a table or food recover 15 satisfaction (max 100). |

The Stage 3 base-setting menu has six items:

| Item | Price | Units |
| --- | --- | --- |
| Salad | $9.00 | 1 |
| Burger | $15.00 | 1 |
| Pasta | $18.00 | 2 |
| Salad+Burger | $21.60 | 2 |
| Salad+Pasta | $24.30 | 3 |
| Burger+Pasta | $29.70 | 3 |

**New files**
| File | Purpose |
| --- | --- |
| `src/rush/model/ComboMeal.java` | `MenuItem` subclass of two items: summed prep units, 90% price rounded half up |
| `src/rush/model/HappyHour.java` | Once-per-game 2-turn pricing policy: 20% discount, 15-point recovery, `endTurn()` countdown |
| `src/rush/model/Host.java` | `Staff` subclass that seats one queued customer per turn |
| `tests/stage3/victory.txt` | Reproducible Stage 3 victory run |
| `tests/stage3/defeat.txt` | Reproducible Stage 3 defeat run |
| *(Shu Yi: list the new dv files, e.g. covergroups and tests for stage 3)* | Stage 3 additions to the optional DV environment |

**Existing files changed**
| File | Change | Reason |
| --- | --- | --- |
| `src/rush/model/Customer.java` | Added `recover(int points)` | Happy Hour recovery. Raises satisfaction only while the customer is waiting, capped at 100, so the state check stays inside the entity |
| `src/rush/model/Restaurant.java` | Added `Host` and `HappyHour` fields and getters. `resetStaff()` now resets the Host. `quoteBill()` applies Happy Hour after the customer's own discount. Added `applyHappyHourRecovery()` | Restaurant already owns staff and pricing, so the VIP-then-Happy-Hour order is decided in one place and the price is locked when the order is taken |
| `src/rush/control/GameConfig.java` | `baseSetting()` builds the six-item menu with the three combos instead of `Menu.standard()` | Makes combos playable with no change to Order, Chef or Waiter |
| `src/rush/control/GameView.java` | Added `chooseHappyHour()` and `chooseHostCustomer(List<Customer>)` | Two new manager decisions. The controller depends on the interface, not on the console |
| `src/rush/control/GameController.java` | Added `happyHourStart()` and `hostChoice()` to the turn loop, and `HappyHour.endTurn()` at the end of each turn | Wires the new decisions into the turn sequence |
| `src/rush/ui/ConsoleUI.java` | Implements the two new `GameView` methods. The state display shows Happy Hour status and the Host in the staff line | Console input and display for the new features |
| `.github/workflows/ci.yml` | *(only if changed in Stage 3)* | Verifies the Stage 3 behaviour automatically |
| `dv/` files | *(Shu Yi: list changed files)* Updated for Host, combos and Happy Hour | Keeps the optional DV environment in sync with the game rules (extra, not for grading) |
| `README.md` | Added this Stage 3 documentation | Records the stage comparison and combo choice rule |

**Files deleted:** None.

### Combo choice rule
Customer N orders menu item `(N - 1) mod menu size`, as in earlier stages. With the six-item menu this gives C1 Salad, C3 (VIP) Pasta, C4 Salad+Burger, C5 Salad+Pasta and C6 Burger+Pasta. The Critic still orders the most demanding dish, so with combos on the menu it now orders Burger+Pasta (3 units, $29.70, winning the tie with Salad+Pasta on price). `CriticCustomer.java` is not changed. Adding or reordering menu items changes which item each customer picks.

### Stage 3 reproducible runs
- Victory: `java -cp bin rush.Main < tests/stage3/victory.txt`. Result: 5 paid, $95.94, average satisfaction 84.6. Happy Hour is started on turn 13.
- Defeat: `java -cp bin rush.Main < tests/stage3/defeat.txt`. Nobody is seated and Happy Hour is never started. Result: 0 paid, $0.00, average N/A. The Critic leaves at turn 12 and the first Regular at turn 13.

## 5. Video Timestamps
(To be completed after recording)
