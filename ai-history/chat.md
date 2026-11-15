# AI History Log — RestaurantRush

| | |
|---|---|
| **AI tools used** | Claude, Claude Code |
| **Exchanges** | 4 |

## Contents

1. [Exchange 1 — Design Verification Harness](#exchange-1--design-verification-harness)
2. [Exchange 2 — Function Trace Log Script Generation](#exchange-2--function-trace-log-script-generation)
3. [Exchange 3 — AST Tree Parsing Script Generation](#exchange-3--ast-tree-parsing-script-generation)
4. [Exchange 4 — Making Videos for Presentation](#exchange-4--making-videos-for-presentation)

---

## Exchange 1 — Design Verification Harness

**Tool:** Claude
**Purpose:** Design Verification Harness

### Prompt 1.1

> Current test script simply injects hardcoded inputs (from `victory.txt` and `defeat.txt`) via input redirection of `System.in`:
>
> ```bash
> java main < victory.txt
> ```
>
> **Issues:**
> - Not integrated with CI/CD pipeline
> - Functional coverage not validated (no edge case)
>
> **Recommendation:**
> - C++ based constraint random test vectors with automated assertion
> - Automation through `test.sh` / `test.bat`, integrated with GitHub CI/CD (for cross deployment)
>
> Evaluate DV proposal and outline steps for full coverage test. Example of output log attached.

### Response 1.1

#### Evaluating the DV proposal for RestaurantRush

**Summary**

The diagnosis is correct. The current test is a smoke test: it shows that two fixed scripts run to completion, but it checks nothing along the way and covers almost no edge cases.

The direction of the proposal is right: constrained-random stimulus, automated checking, and CI gating. Two parts of the implementation work against it, though: C++ as the stimulus language, and pre-generated "test vectors". The proposal also leaves out what actually makes constrained-random useful: a reference model (oracle), a functional coverage model, and seed-based reproducibility.

**Evaluation of each point**

| Proposal item | Verdict | Reasoning |
|---|---|---|
| Diagnosis: no CI, no edge cases | ✅ Agree | Also missing: no assertions at all. The only pass condition is "didn't crash." |
| Constrained-random stimulus | ✅ Agree, with changes | Valid menu choices depend on the current state. For example, "Serve" needs a READY order, and the customer list changes every turn. Open-loop vectors generated in advance will drift out of sync and mostly test the input-rejection path. The driver has to be closed-loop: read the state, then choose a legal action using weights, plus a controlled rate of deliberately illegal inputs. |
| C++ as the testbench language | ❌ Not recommended | The design under test is Java. C++ would mean a second toolchain on every CI runner (gcc, clang, MSVC), communicating only by scraping stdout, and no access to internal state. The one good argument for a separate language is an independent reference model. You get most of that benefit by writing the model separately from the engine code, in Java or Python. |
| "Automated assertion" | ⚠️ Underspecified | Assertions need a specification to check against, and none exists yet. The rules below had to be inferred from the log. |
| `test.sh` + `test.bat` | ⚠️ Avoid | Two scripts will drift apart over time. Gradle or Maven already runs the same way on every OS. |
| GitHub CI, "cross deployment" | ✅ Agree | I read "cross deployment" as cross-platform testing. That would be an OS × JDK matrix. |
| Missing: coverage model and closure criteria | ❌ Gap | Without coverage bins and a closure target, "full coverage" can't be measured. Random runs alone don't prove anything was exercised. |
| Missing: determinism | ❌ Gap | If menu items or customer types come from a `Random`, it needs to be seedable. Otherwise a failure can't be reproduced. |

**A finding the current test missed**

The log shows this every time the waiter chooses a non-zero task:

```text
Choose Waiter task [0-3]: Choose Waiter task [0-3]: Choose a customer to seat
```

This means the first input was rejected and the prompt repeated. Turn 14 also shows a double prompt before "takes no action." There are two likely causes:

1. A CRLF or blank-line problem in the input files.
2. A bug in how the menu reads input, such as `nextInt()` followed by `nextLine()`.

Either way, the current setup can't tell a correct rejection from a swallowed input. This is a good first directed test to write.

**Rules inferred from the log, as assertion candidates**

- Satisfaction drops by 8 per turn while a customer is WAITING, SEATED, or ORDERED. It stops changing once SERVED (C1 stays at 76).
- A customer arrives every 3 turns (turns 1, 4, 7, 10, 13, 16).
- Status moves strictly in this order: WAITING → SEATED → ORDERED → SERVED → READY_TO_PAY (the turn after serving) → paid at end of that turn. No state is skipped.
- Each turn: the waiter does at most 1 task, the chef adds at most 1 prep unit, and the cashier takes at most 1 payment.
- An order is READY exactly when prep units equal required units. Prep units only go up and never exceed the required count.
- Each table holds at most one customer, and it becomes free when that customer pays.
- Paid ≤ served ≤ orders taken.
- Revenue equals the sum of paid order prices.
- Average satisfaction is the mean satisfaction of paid customers: (76 + 60 + 36) / 3 = 57.3 ✔.
- The result is VICTORY only if paid ≥ 4, revenue ≥ $45, and average satisfaction ≥ 60.

**Steps to full coverage**

1. **Write a verification plan.** Turn the rules above into a spec. Map each rule to a check (assertion or scoreboard) and to one or more coverage bins. This becomes the sign-off document.

2. **Make the game testable.** This is the most important step.
   - Separate the game engine from the console UI.
   - Pass a `Random(seed)`, the input stream, and the output stream into the constructor.
   - Expose a state snapshot, or add a `--json` output mode so a black-box driver can read state without scraping text.

3. **Write directed tests (JUnit 5).**
   - Convert `victory.txt` and `defeat.txt` into tests that assert on the final state, not just that the game finished.
   - Add one test per rule.
   - Add boundary tests: exactly 4 paid customers, exactly $45.00, an average that lands on 60.0 exactly, and averages like 59.95 where the displayed value rounds up but the true value fails.

4. **Write input robustness tests.**
   - Out-of-range numbers, negative numbers, non-numeric input, empty lines, CRLF line endings.
   - Running out of input mid-game (does the game crash, or end cleanly?).
   - "Back" from every submenu: does it still use up the waiter's task for that turn?
   - Selecting an action with no valid targets.

5. **Build a reference model and scoreboard.** Write a separate, deliberately simple model of the rules. Each turn, step it alongside the real engine and compare the full state.

6. **Build a closed-loop constrained-random driver.**
   - Run in-process using jqwik (property-based testing for Java, which also shrinks failures to a minimal case).
   - Use weighted legal actions, plus about 5% illegal inputs.
   - Add strategy profiles (greedy, idle-heavy, chaotic) to reach different parts of the state space.
   - Print the seed on every failure so it can be replayed.

7. **Define functional coverage bins.**
   - Customer status × action attempted, including illegal combinations.
   - Every status transition.
   - Order type × number of prep units.
   - Tables: both occupied, two customers READY_TO_PAY in the same turn (cashier contention).
   - Waiting queue lengths 0, 1, 2, and 3 or more.
   - A customer's satisfaction reaching the threshold that triggers an unhappy departure. This never happened in the log: C4 reached 36 and stayed.
   - Every customer type. The "(Regular)" label suggests other types exist.
   - Each result: VICTORY, plus DEFEAT crossed with each subset of missed targets.
   - Merge coverage across all seeds. Fill remaining gaps with directed tests or by adjusting the weights.

8. **Add code coverage and assertion-quality checks.**
   - JaCoCo with thresholds as a starting point, for example ≥ 90% line and ≥ 85% branch coverage.
   - PIT mutation testing, to confirm the assertions actually catch bugs and don't just run the code.

9. **Set up CI in GitHub Actions.**
   - Matrix of {ubuntu, windows, macos} × {JDK 17, 21}. Windows is where the CRLF problem would show up.
   - Pull requests run directed tests plus about 200 random seeds.
   - A nightly run uses about 10k seeds.
   - Upload coverage reports and failing seeds as build artifacts.
   - Block merges when tests fail or coverage drops.

   ```yaml
   strategy:
     matrix:
       os: [ubuntu-latest, windows-latest, macos-latest]
       java: [17, 21]
   steps:
     - uses: actions/checkout@v4
     - uses: actions/setup-java@v4
       with: { distribution: temurin, java-version: "${{ matrix.java }}" }
     - run: ./gradlew test jacocoTestCoverageVerification -Pseeds=200
   ```

10. **Define closure (sign-off) criteria.**
    - 100% of functional coverage bins are hit, or each unhit bin is documented as unreachable.
    - Code coverage thresholds are met.
    - Mutation score is above the agreed target.
    - No failing seeds in the last N nightly runs.

I can draft the verification plan as a document, or write the engine/UI split and the jqwik driver if you share the Java source.

---

### Prompt 1.2

> Okay, will be targeting python based verification that hooks on `Main.java` API, interacting through redirection of `System.in` and `System.out` to the python script. Outline the DV coverage bins based on the assignment document, and propose the Python DV structure.

### Response 1.2

*I'll read the assignment spec, then map its rules to coverage bins and a Python testbench structure.*

*[Ran a command]*

I've read the brief and checked it against your log. The coverage bins and the Python testbench structure are below.

#### Two things to settle before writing the testbench

1. **Your log already breaks a rule in the brief.** Section 3.4 says an invalid choice must explain why it failed and then ask again. The log shows `Choose Waiter task [0-3]: Choose Waiter task [0-3]:` with no explanation between the two prompts, and turn 14 does the same. Either an input is being rejected without a message (a spec violation), or input is being read wrongly. This should be the first directed test.

2. **Prompts may never reach Python.** The Python driver waits for a prompt before answering. Java's `System.out.print()` with no newline isn't guaranteed to reach a pipe straight away, so the driver could wait forever. Add `System.out.flush()` after every prompt in `Main.java`, and have the harness treat a timeout as a hang failure.

#### Coverage bins

S1, S2 and S3 mean Stage 1, 2 and 3. A bin only counts when the build at that stage's tag is tested. "Unreachable" bins are documented and left out of closure.

**CG1: Turn and arrivals** (S1, §2.1, §3.2 step 1)

| Coverpoint | Bins |
|---|---|
| Arrival turn | 1, 4, 7, 10, 13, 16 (assert: no arrivals on other turns, 6 in total) |
| Queue length at turn start | 0, 1, 2, 3, ≥4 |
| Tables occupied | 0, 1, 2 |
| Cross: queue length × free tables | Includes "queue ≥1 and both tables full" (staff constrained, which video segment 2 asks for) |

**CG2: Waiter** (S1, §3.2 step 2, §3.4)

| Coverpoint | Bins |
|---|---|
| Action | Wait, Seat, Take order, Serve |
| Seat pick | Head of queue, not head of queue (manager sets priority) |
| Table assigned | Table 1, Table 2, a table freed in the previous turn |
| Illegal action × reason | Seat with empty queue, Seat with no free table, Take with no unordered seated customer, Serve with nothing READY. Each must show an explanation, ask again, and not use up the task |
| Back from submenu | Back from each of Seat, Take and Serve, followed by a different valid action in the same turn |

**CG3: Chef** (S1, §3.2 steps 2–3)

| Coverpoint | Bins |
|---|---|
| Action | Prepare, Wait while orders are pending, no orders (automatic) |
| Same-turn prep | Chef prepares an order the waiter took this turn |
| Choice | 1 order pending, ≥2 pending (priority choice); for Pasta, starting a second order while one is partly done |
| Prep transition | PLACED→READY (1 unit), PLACED→IN_PREPARATION, IN_PREPARATION→READY |

**CG4: Order lifecycle** (S1, §3.2 step 3)

| Coverpoint | Bins |
|---|---|
| Item × final status | {Salad, Burger, Pasta} × {PAID, cancelled, unfinished at turn 18} |
| READY timing | Served the turn after becoming READY, served ≥2 turns after |
| Cancelled at status | PLACED, IN_PREPARATION, READY (is a READY dish "unfinished"? The brief doesn't say) |
| Assertion, not bin | A dish that became READY this turn is never offered for serving this turn |

**CG5: Customer, satisfaction and abandonment** (S1, §3.2 step 5)

| Coverpoint | Bins |
|---|---|
| Status transitions | Every legal edge: WAITING→SEATED→ORDERED→SERVED→READY_TO_PAY→PAID, plus WAITING/SEATED/ORDERED→LEFT |
| Abandoned from | WAITING, SEATED with no order, ORDERED |
| Arrival turn × abandoned | A Regular can only abandon if it arrives on turn 1 (leaves end of turn 13) or turn 4 (end of turn 16). Arrivals on turns 7–16 can't abandon, so those bins are unreachable |
| Hitting 0 | Clamped (e.g. 4 − 8 → 0); exactly 0 (may only be reachable via Happy Hour, so the model decides) |
| No loss while | SERVED, eating, READY_TO_PAY, and on the turn of being served |

**CG6: Eating and payment** (S1, §3.2 step 4)

| Coverpoint | Bins |
|---|---|
| Eating | SERVED → READY_TO_PAY after exactly one full turn |
| Cashier contention | 2 customers READY_TO_PAY in the same turn (oldest pays first, the other the turn after) |
| Payment timing | Pays on the first allowed turn, pays one turn late because of contention |
| End-of-game leftovers | READY_TO_PAY but unpaid at turn 18; served but unpaid; the turn-16 arrival never pays (assertion) |
| Table reuse | A table freed by payment or abandonment is seated the next turn |

**CG7: Metrics and result** (S1, §2.1, §3.5)

| Coverpoint | Bins |
|---|---|
| Paid count | 0, 1, 2, 3, 4, 5 (6 is an illegal bin and must never be hit) |
| Revenue | <$45, exactly $45 (e.g. 3 Salads + 1 Pasta), >$45 |
| Average satisfaction | N/A, <60, exactly 60.0, >60, true value 59.95–59.99 (displays as "60.0" but must be a defeat) |
| Unhappy departures | 0, 1, ≥2 |
| Result | VICTORY; DEFEAT × all 7 combinations of missed targets (e.g. 4 Salads = paid OK but revenue missed; 3 Pastas = revenue OK but paid missed) |

**CG8: Input robustness** (S1, §3.4)

Cross every prompt type (Waiter task, customer, order, Chef) with: index too high, negative, non-numeric, empty line, extra whitespace, CRLF line ending, end of input. Each should show an explanation, ask again, and not use up the task. Your team needs to decide what happens at end of input.

**CG9: Customer types** (S2, §4.2)

| Coverpoint | Bins |
|---|---|
| Type × loss per turn | Regular 8, VIP 5, Critic 12 |
| Type × item × bill | The VIP 10% discount on each item ($8.10 / $13.50 / $16.20) |
| Type × abandonment | Critic can abandon (arrivals on turns 1, 4, 7, 10); VIP can never abandon in 18 turns (100 − 5×18 = 10), so that bin is unreachable |
| Critic behaviour | Whatever your team defines and documents, with one bin per branch |
| Configuration | The base run has at least 1 VIP and 1 Critic, and still 6 arrivals |

**CG10: Host, ComboMeal, Happy Hour** (S3, §4.3)

| Coverpoint | Bins |
|---|---|
| Host | Seats 0 or 1 per turn; Host and Waiter both seat in one turn (fills both tables); Host with empty queue or no free table; a second Host seat in one turn is rejected |
| Combo | Each allowed pair × units (2, 3, 4?) × price (e.g. Salad+Pasta $24.30 / 3 units) |
| Happy Hour activation turn | 1, middle of the game, 17, 18 (only one turn of effect); a second activation is rejected |
| Happy Hour display | Remaining 2, remaining 1 |
| Happy Hour pricing | Order taken before, during or after Happy Hour; price is locked when the order is taken |
| Happy Hour recovery | +15 while waiting or seated and unserved; capped at 100; no recovery while SERVED |
| Stacking × rounding | VIP + Happy Hour (Burger → $10.80); VIP + Happy Hour + combo rounding case (Salad+Pasta: 24.30 × 0.9 × 0.8 = 17.496 → $17.50) |

**Spec gaps to settle before writing the reference model.** The model needs one fixed answer for each:

- Does "oldest first" for the cashier mean earliest arrival, or earliest to become READY_TO_PAY?
- Does a READY order count as "unfinished" when its customer abandons?
- In Stage 3, does Happy Hour recovery come before or after arrival at the start of a turn?
- For stacked discounts, is the price rounded at each step or once at the end?
- Does "Back" use up the task?
- What happens at end of input?

#### Python DV structure

```text
dv/
├── harness/
│   ├── dut.py          # JavaDUT: build, start `java Main` via subprocess pipes, send(), expect(prompt, timeout), save transcript
│   ├── monitor.py      # Turns stdout text into TurnSnapshot, Event (arrive/seat/order/prep/serve/pay/leave) and Result objects
│   ├── model.py        # Reference model: a separate Python version of the rules, configured per stage
│   ├── scoreboard.py   # Steps the model with the same actions and compares full state with the monitor each turn
│   ├── checkers.py     # Fixed invariants, independent of the model (see list below)
│   ├── sequencer.py    # Policies: given a snapshot and a prompt, choose an input (weighted legal moves + illegal injection)
│   ├── coverage.py     # Covergroups CG1–CG10, crosses, unreachable/illegal bins, JSON output per seed
│   └── config.py       # Stage, seed, weights, timeouts
├── sequences/          # Directed scenarios: victory, defeat, abandonment, contention, $45 boundary, Happy Hour on turn 18…
├── tests/
│   ├── test_directed.py
│   ├── test_robustness.py   # CG8
│   └── test_random.py       # Seeded, run with --seeds N
├── tools/
│   ├── merge_cov.py    # Merge coverage JSON from all seeds into one HTML report with holes listed
│   └── replay.py       # Re-run a failing seed or transcript
└── .github/workflows/dv.yml
```

**How the parts connect.** Each prompt is the sync point. The driver reads stdout until it sees a prompt, then the monitor turns that text into a snapshot. Next the scoreboard compares the snapshot with the model, and coverage records the bins it hit. Last, the sequencer picks the next input and the driver sends it.

```python
PROMPT = re.compile(r"Choose (?P<kind>[\w ]+) \[0-(?P<max>\d+)\]: $")

while (m := dut.expect(PROMPT, timeout=5)):
    snap = monitor.update(dut.drain())        # parse everything printed since the last prompt
    scoreboard.check(snap, model)             # compare full state each turn
    cov.sample(snap, m["kind"])
    choice = seq.next(snap, m["kind"], int(m["max"]))  # constrained-random or directed
    model.apply(choice) if seq.is_legal(choice, snap) else model.expect_reprompt()
    dut.send(f"{choice}\n")
monitor.parse_result(dut.drain()); scoreboard.check_result(model)
```

**Design notes:**

- **Things the game chooses itself** (food choice, customer type) are read from the output, such as `takes order #3 Pasta` and `arrives (VIP)`, and passed into the model. A separate check then compares them with your team's documented rule or seed. That way the model doesn't have to copy your random number generator.
- **Fixed invariants in `checkers.py`:**
  - Satisfaction stays in [0, 100].
  - At most 1 Waiter task, 1 prep unit, 1 payment and 1 Host seat per turn.
  - Prep units only go up.
  - Each table has at most one customer.
  - Paid ≤ served.
  - Revenue = sum of paid bills and is never more than $90 in Stage 1.
  - Average satisfaction = mean satisfaction recorded at payment.
  - Turn count is always 18.
- **Constrained-random:** weights are set per policy (greedy, idle-heavy, chaotic, contention-seeking), with about 5% illegal inputs. Every failure prints its seed and saves its transcript, so `replay.py` can reproduce it exactly. If you want failures shrunk to a minimal case automatically, Hypothesis's `RuleBasedStateMachine` fits this closed loop.
- **Coverage:** a plain dict-based `coverage.py` is enough. If you'd rather use SystemVerilog-style covergroup syntax, pyvsc offers it. Unreachable bins (VIP abandonment, a turn-7 Regular abandoning, a sixth payment) are declared explicitly, so they show as excluded rather than as holes.
- **Stage awareness:** `--stage N` sets the model's rules and which covergroups are active. Run the S1 directed suite against stage-2 and stage-3 too, to show earlier behaviour still works (§4.4).

**CI matrix:** {ubuntu, windows, macos} × {JDK 17, 21} × {stage-1, stage-2, stage-3 tags}. Pull requests run directed tests plus about 200 seeds. A nightly run uses about 5–10k seeds and merges coverage. CI uploads the coverage HTML and failing transcripts as artifacts. Merges are blocked on any scoreboard mismatch or a drop in bins hit.

**Closure:** every reachable bin in CG1–CG10 is hit for the stages tested, and the unreachable list is reviewed. On top of that, the scoreboard has no mismatches across the nightly seeds, and the S1 directed suite passes on all three tags. The passing runs also give you the reproducible victory and defeat runs the brief requires for Stage 1 (§4.1).

I can save this as a verification plan doc in the "Official RestaurantRush" project, or start on `dut.py`, `monitor.py` and `model.py` against `Main.java` if you share the source.

### Prompt 1.3

> Next, the reference model.

### Response 1.3

I've built the DV environment in `dv/`, and against the current Java it passes **222/222 tests at 100% functional coverage (256 bins)**. It runs the real `rush.Main` through stdin/stdout, uses only the Python standard library, and needed no Java changes. I haven't committed anything, and the new CI job hasn't run on GitHub yet; I checked it locally only.

**What it does:**

- **Hook:** compiles `src/` into its own build folder (it doesn't touch `out/`) and pipes generated input into the game.
- **Reference model** (`dv/rrdv/model/`): a Python copy of the six turn steps that predicts the exact transcript. It matches the Java output byte for byte on both existing test scripts.
- **Constrained-random stimulus:** five profiles (greedy, random, lazy, chaos, and a mostly-greedy mix). Every choice is drawn from what the game will actually offer at that prompt, filtered by hard and soft rules. It also feeds bad input (junk text, overflow numbers, blank and comment lines, CRLF line endings, input cut off early) and odd but valid answers like `+2`, `02` and full-width digits.
- **Checks:** a scoreboard that compares model and game turn by turn and as a full text diff (this is the print verification), plus 21 assertions, each tagged with the clause of the brief it enforces.
- **Coverage:** 9 covergroups covering the areas you listed. Bins that can't happen under the base setting are marked with the reason. For example, only C1 and C2 can ever abandon, because it takes 12 unserved turns. A bin that should be impossible counts as a failure if it's hit.
- **Expandable:** rules live as data in `spec.py`, and coverage groups register per stage. `dv/README.md` has the step-by-step for stages 2 and 3.
- **CI:** a new `dv` job in `ci.yml` runs on Linux, macOS and Windows with Python 3.10 and 3.13. Push and PR runs use fixed seeds so results reproduce; a nightly run uses fresh random seeds. It uploads the coverage report and any failing input scripts, and fails below 100% coverage. I used 3.10/3.13 rather than the 3.9/3.12 in the plan because 3.9 is end-of-life; the code still runs on 3.9.

**Evidence the checks work:**

- 25 runs with random seed bases (5,550 tests) all passed at 100% coverage.
- I injected 13 one-line bugs into a scratch copy of the Java code, and the DV caught every one that changes behaviour. The few it didn't catch can't change behaviour under the base setting; for example, there is never more than one customer waiting to pay.

**A problem in your existing tests:** `tests/stage1/victory.txt` actually ends in DEFEAT (3 paid, $42, average 57.3). The script assumes a Chef prompt every turn, but the game shows none when the kitchen is empty. So the turn-1 Chef `0` gets read as turn 2's Waiter choice, and every input after that is one step off. I left the file alone, and CI only checks that the game and model agree on it, so CI stays green. `python dv/dv.py run --seed 0 --profile greedy --dump` prints a script that wins (5 paid, $66, average 79.2) if you want a replacement.

**Change log for porting:** `dv/PORTING_LOG.md` lists every added file with its purpose. It also has a table of the three edits to existing files (`ci.yml`, `.gitignore`, `README.md`) and the exact diff to apply.

**To run it yourself:**

```bash
python dv/dv.py regress
python -m unittest discover -s dv/tests -t dv
```

*[Changed 27 files — e.g. `customer.py` +70, `order.py` +50, `restaurant.py` +68 … — total +3,561 / −7]*

### Prompt 1.4

> Is there any bugs in our current code based on ur DV?

### Response 1.4

No. Across every run (the 222-test regression plus the 25-seed sweep, about 5,500 games) the Java code broke none of the Stage 1 rules the DV checks. No assertion fired, no impossible coverage bin was hit, and the model and the game never disagreed.

**The one real defect I found is in a test file, not the game code:**

`tests/stage1/victory.txt` ends in DEFEAT. The script expects a Chef prompt every turn, but the game skips that prompt when the kitchen is empty. From turn 1 onwards every input is one step off, so the "reproducible victory run" required by the brief (4.1) doesn't currently reproduce a victory.

**Some behaviour isn't against the brief but is worth knowing about:**

- **Code that can never run.** In `Waiter.serve()` the "only became ready this turn. Serve next turn." check can never trigger, because the Waiter always acts before the Chef. The `isWaitingForService()` guard in `Customer.loseSatisfaction()` duplicates the filter already in `Restaurant.applyWaiting()`. These are harmless, though the first is a useful safety net if the turn order ever changes.
- **Unusual input is accepted.** `Integer.parseInt` takes `+2`, `007`, `-0` and full-width digits like `２` as valid choices. This is fine under the brief, but it may surprise a marker.
- **Seat when the tables are full.** The game lists customers to pick from and only then says "No free table." It handles this correctly (it explains why and re-prompts without using up the task), but checking for a free table before showing the list would be smoother.
- **Cosmetic output.**
  - The chef and serve lists repeat the status: `#3 Pasta (0/2 units) [PLACED] [PLACED 0/2]`.
  - When input runs out, the game prints the Java class name: `Error: rush.ui.InputReader$InputEndedException: Input ended.`

The DV can only catch wrong behaviour against the brief's Stage 1 rules under the base setting. It says nothing about design quality such as the UML or OOP structure. Also, I wrote the reference model after reading the Java, so if the Java misreads the brief, the model could copy the same mistake. The 21 assertions are taken straight from the brief rather than from the model, which is what guards against that, and they all pass.

Fixing `victory.txt` is the only change I'd call necessary. Want me to replace it with the winning greedy script, with turn-by-turn comments?

---

## Exchange 2 — Function Trace Log Script Generation

**Tool:** Claude Code
**Purpose:** Function Trace Log Script Generation

### Session setup

```text
> /remote-control
/remote-control requires a claude.ai subscription. Run /login to sign in with your claude.ai account.

> /login
Login successful
```

### Prompt 2.1

> Write me a simple Java wrapper to do trace logging on the entire `rush.Main` app. Put this script in tests directory. I want it to output entire trace log of stage 3 `victory.txt` run.

### Response 2.1

I wrote `tests/TraceRunner.java` and ran it on the stage 3 victory script. It wrote the complete trace to `tests/stage3/victory.trace.log`, which is 10,941 lines.

**How to run it** (from the repo root):

```bash
java tests/TraceRunner.java                                    # defaults to tests/stage3/victory.txt
java tests/TraceRunner.java tests/stage3/defeat.txt            # other scripts work too
java tests/TraceRunner.java <script> <logfile>                 # custom output path
```

You don't need to compile anything first, and it adds no dependencies. It uses JDI (the Java debugger API that comes with the JDK).

**What it does:**

- Compiles `src/` with debug info into `out/trace/`, so it doesn't touch the `out/` build that `run.sh` uses.
- Starts `rush.Main` in a separate JVM under the debugger and feeds it the script on stdin.
- Logs, for everything in `rush.*`:
  - every method entry with its arguments, and every exit with its return value
  - every exception thrown, marked as caught or uncaught
- Indents each line by call depth. The game's own console output is mixed into the same log with an `OUT|` prefix.

**Sample from the end of the run:**

```text
                -> control.GameResult.isSatisfactionMet()
                <- control.GameResult.isSatisfactionMet = true
OUT|   Avg satisfaction: 84.6 (target >= 60) [met]
...
        <- control.GameController.run = GameResult@1716
    <- Main.play
<- Main.main
# exit code 0, 10390 method events
```

The run took about 3.6 seconds. The game exited with code 0 and no exceptions were thrown.

**Limitations:**

- The `OUT|` lines arrive through a separate pipe, so they can land a few lines away from the call that printed them.
- Objects show as `Type@id`, not their full contents. Strings, numbers and enum values show their actual values.
- A few compiler-generated enum constructor arguments show as `?`.

Git will ignore the log because `.gitignore` already excludes `*.log`. I haven't committed anything.

*📄 Output file: `TraceRunner.java`*

---

## Exchange 3 — AST Tree Parsing Script Generation

**Tool:** Claude Code
**Purpose:** AST Tree Parsing Script Generation

### Prompt 3.1

> Under tests dir, similar to how we generate trace log for sequence diagram, make me an AST tree parser to verify class diagram. This AST tree parser should use std library to output a human readable AST log, that can then be used to verify our class diagram with AI.

### Response 3.1

*Progress notes during the session:*

- *I'll look at the existing trace-log setup and project layout first.*
- *TraceRunner is JDK-only, so I'll build the parser on the JDK's Compiler Tree API (`com.sun.source.tree`); next I'm checking which language features the source uses.*
- *Plan approved. Writing `tests/AstRunner.java` now.*
- *Enum `values()`/`valueOf()` are leaking through because javac marks them as explicit, and the `CustomerType --> Customer` edge shows a misleading multiplicity of 1 via `BiFunction`. I'll fix both next.*
- *Now the README updates.*

**Final response:**

I've added `tests/AstRunner.java`. It parses `src/` and writes a readable log of every class and how the classes relate, which you can hand to AI along with `class_diagram.pdf` to check the diagram. It only uses the JDK's built-in compiler API, the same way `TraceRunner.java` works, so there's nothing extra to install or build. I ran it on the current code and it produced a full log of **33 types and 117 relationships**. I only ran it on JDK 21; it avoids newer syntax so it should work on 17, but I didn't test that.

```bash
java tests/AstRunner.java                                # src -> tests/class_diagram.ast.log
java tests/AstRunner.java src tests/class_diagram.ast.log
```

**What's in the log:**

- **One block per type:** whether it's a class, abstract class, interface or enum, with its file and line number. Then what it extends and implements, enum constants, fields, constructors and methods. Members use UML notation: `+ - # ~` for visibility, plus `{static}`, `{final}` and `{abstract}` tags.
- **A relationships section:**
  - Inheritance: extends (`--|>`) and implements (`..|>`).
  - Associations (`-->`): one class holds another in a field. Each shows the field name and a multiplicity: `1`, `0..1` for `Optional`, `0..*` for lists, maps and arrays.
  - Dependencies (`..>`): one class uses another without storing it, with the reason (param, return, local, new, call, static).
  - Nested types (`+--`).
- **`[creates]` marker:** added when a field gets a new object in its declaration or constructor, e.g. `Restaurant --> Host [creates]`. That's a hint for composition (filled diamond) versus aggregation (hollow diamond), but the AI or you still makes the final call.

**Two things to know when reading it:**

- **Hidden members:** the default constructors and enum `values()`/`valueOf()` that Java adds automatically are left out, since diagrams don't usually show them.
- **`CustomerType --> Customer`:** this link exists only through a `BiFunction<…, Customer>` field. It's marked `via generic BiFunction` instead of a multiplicity, so the AI doesn't read it as a direct one-to-one link.

I also updated `README.md`: there's a new section next to the trace-logging one, and both runners are now in the directory tree. The generated log is already gitignored (`*.log`). Nothing is committed yet.

---

## Exchange 4 — Making Videos for Presentation

**Tool:** Claude
**Purpose:** Making videos for presentation

### Prompt 4.1

> https://github.com/yeoshuyi/RestaurantRush
>
> See the theme and color scheme of this slide.
>
> Make me a short animation for 3 things (20 sec each):
>
> 1. Showing how Python DV latches onto Java, with alt model generated by AI, and coverage bins
> 2. Showing how AST tree walks the entire repo and generates the tree and method functions
> 3. Showing how trace log walks the victory sequence

### Response 4.1

*Progress notes during the session:*

- *I'll look at your repo to get the details right, then build three 20-second animations in that cream / slate / rust style.* — [Ran 5 commands, loaded tools, used a tool]
- *Java's available, so I'll run the real tools to pull genuine output for the animations.* — [Ran 15 commands, read 13 files, created a file]
- *Looks good. Now I'll render each scene to an MP4 so you can drop them straight into your video.* — [Ran 2 commands, read a file, shared files]

**Final response:**

I made three 20-second animations, each a 1080p MP4 in the same style as your slide: warm cream background, slate text, rust highlights and serif headings. Each has a caption line along the bottom, like your narration bar.

To get real content, I ran your `AstRunner` and `TraceRunner` on the repo and ran a short DV regression. The class names, log lines, relationship count, payments and final result in the clips come from that real output, not made-up examples.

**`1-python-dv.mp4`:**
- `driver.py` slides in and locks onto the Java game.
- The test script feeds both the real game and the "Alt model (Python), AI-generated".
- The scoreboard ticks off matching turns and ends on "0 mismatches".
- The coverage grid of all 396 bins fills up seed by seed, with one bar per covergroup (all 15), and ends on "100% · coverage gate passed".

**`2-ast-walk.mp4`:**
- Lights up all 32 files under `src/rush` one by one while their type headers fill the log, counting up to 33 types.
- Zooms into `GameController.java`: its syntax tree builds node by node while the real log block is written out.
- Changes to a relationship diagram (Staff and Customer subclasses, Restaurant and its fields, ConsoleUI implementing GameView, ComboMeal holding two MenuItems) and finishes on "33 types · 117 relationships".

**`3-trace-log.mp4`:**
- A playhead moves across turns 1–18, showing arrivals, payments and the Happy Hour on turns 13–14.
- Real trace lines scroll in sync, the five payments fill the target bars, and it ends on `GameStats.evaluate() → RESULT: VICTORY` (5 paid, $95.94, average satisfaction 84.6).

**Check the 100% coverage claim:** the first clip shows 100% coverage after 200 seeds, which is what your DV README says. My shorter 40-seed run reached 98.2%, so it's worth running the full 200 seeds once to confirm before you narrate that line.

The HTML file is the player I recorded the clips from. Open it in a browser to scrub, pause or play all three in a row (60 seconds), or to change wording and record again.
