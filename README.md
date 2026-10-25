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
