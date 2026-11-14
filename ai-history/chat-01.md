AI Tool: Claude 
### Exchange 1
### My prompt
"Attachments: SC2002_Restaurant_Rush_Group_Assignment.docx, ComboMeal.java, Customer.java, HappyHour.java, Host.java, Restaurant.java, GameConfig.java, GameController.java, GameView.java, ConsoleUI.java, defeat.txt, victory.txt, https://github.com/yeoshuyi/RestaurantRush/blob/main/README.md

stage 3 changes in order
1) new dv (shuyi settle)
2) new model.ComboMeal (felicia) 
3) new model.HappyHour (felicia) 
4) new model.Host (felicia) 
5) edit to model.Customer (amanda)
6) edit to model.Restaurant (amanda)
7) edit to control.GameConfig (amanda)
8) edit to control.GameView (kayne)
9) edit to control.GameController (kayne)
10) edit to ui.ConsoleUI (luis)
11) add victory.txt and defeat.txt for stage 3 (luis)
12) documentation update (shu yi)

help me draft an update for the readme documentation for stage 3 according to the changes we have made. write down the documentation here"

### Claude's Response 
"Fetching the README from the linked repository.

I’ll start by pulling the current README and the assignment brief so the Stage 3 section matches their format and requirements.

I read your current README and the Stage 3 section of the assignment brief. The brief requires, for each stage transition, the new files, the changed files with reasons, a compare link, and video timestamps. The README below is built around that. It replaces the whole file, since the current one still says “Stage 2 WIP”.

[Full draft README for Stage 3 was provided here]

Things to check before you commit:

1. Stage 1 → 2 section: I didn’t have the Stage 2 diff, so that part is a placeholder. The brief requires it too.
2. Test paths: I wrote `tests/stage3/`, matching your existing `tests/stage1/` convention. Adjust if the files live elsewhere.
3. DV row: I don’t know exactly what changed in `dv/`, so the wording is generic. Shu Yi should make it specific.
4. Compare links: they assume your tags are literally `stage-2` and `stage-3`.
5. Critic’s choice: I described it as “the most demanding dish” based on the comment in `victory.txt`, because I haven’t seen the Critic class. Check that the wording matches the code.
6. Video table: I left the timestamps blank, and I added a presenter column because the brief says each member explains a part."

### Exchange 2
### My prompt
"do we need the new section on stage 3 features? i want to keep it as the same format of the current readme so maybe just the extra stage comparison for 2 to 3 will do. and show the changes before and after."

### Claude's Response 
"Yes, you can drop it. The Stage 3 comparison table already covers what changed. One thing to keep: the brief says “a customer chooses a combo according to a rule you document”, so I put that rule in the comparison section as a short note.

The README then keeps its current format and has only these changes.

**1. Header (existing lines edited)**

```diff
-- **Release:** Stage 2 (`stage-2`)
+- **Release:** Stage 3 (`stage-3`)
 
-> Stage 2 WIP
```

**2. Directory tree (two lines edited)**

```diff
-│       └── model/      # Core entities (Restaurant, Customer, Staff, Order, Table)
+│       └── model/      # Core entities (Restaurant, Customer, Staff, Order, Table, Host, ComboMeal, HappyHour)
 ├── tests/
-│   └── stage1/
-│       ├── victory.txt # script verifying victory condition
-│       └── defeat.txt  # script verifying defeat condition
+│   └── stage3/
+│       ├── victory.txt # script verifying victory condition
+│       └── defeat.txt  # script verifying defeat condition
```

**3. Test Verification (paths only)**

```diff
-java -cp bin rush.Main < tests/stage1/victory.txt
+java -cp bin rush.Main < tests/stage3/victory.txt
-java -cp bin rush.Main < tests/stage1/defeat.txt
+java -cp bin rush.Main < tests/stage3/defeat.txt
```

You could also edit the DV paragraph to mention Host, combos and Happy Hour in its coverage list. That is optional.

**4. New section, added at the end as `## 4. Stage Comparison`**

```markdown
---

## 4. Stage Comparison

### Stage 2 → Stage 3

- **Compare:** https://github.com/yeoshuyi/RestaurantRush/compare/stage-2...stage-3
- `Menu.java` is unchanged.

Stage 3 adds the Host, ComboMeal and Happy Hour. `baseSetting()` now has a 6-item menu: Salad, Burger, Pasta, Salad+Burger, Salad+Pasta, Burger+Pasta.

**Combo choice rule:** customer N orders menu item `(N - 1) mod 6`, as in earlier stages, so C4, C5 and C6 order Salad+Burger, Salad+Pasta and Burger+Pasta. The Critic still picks the most demanding dish (Burger+Pasta in the base setting).

#### New files

| File | Purpose |
| --- | --- |
| `src/rush/model/ComboMeal.java` | `MenuItem` subclass of two items: summed prep units, price is 90% of the combined price rounded half up. |
| `src/rush/model/HappyHour.java` | Once-per-game, 2-turn pricing policy: 20% off new orders, 15 satisfaction recovery per active turn. |
| `src/rush/model/Host.java` | `Staff` subclass that seats one queued customer per turn. |
| `tests/stage3/victory.txt`, `tests/stage3/defeat.txt` | Scripted victory run (5 paid, $95.94, avg 84.6) and defeat run (0 paid, $0.00, N/A). |

#### Changed files

| File | Change | Reason |
| --- | --- | --- |
| `model/Customer.java` | Added `recover(int points)`. | Happy Hour recovery for waiting customers, capped at 100. The state check stays inside the entity. |
| `model/Restaurant.java` | Added `Host` and `HappyHour` fields and getters. `resetStaff()` resets the Host. `quoteBill()` applies Happy Hour after the VIP discount. Added `applyHappyHourRecovery()`. | Restaurant owns staff and pricing. The price is locked when the order is taken. |
| `control/GameConfig.java` | `baseSetting()` builds the 6-item menu with combos instead of `Menu.standard()`. | Makes combos playable with no change to Order, Chef or Waiter. |
| `control/GameView.java` | Added `chooseHappyHour()` and `chooseHostCustomer(...)`. | Two new manager decisions. The controller depends on the interface, not the console. |
| `control/GameController.java` | Added `happyHourStart()` and `hostChoice()` to the turn loop, and `HappyHour.endTurn()` at the end of each turn. | Wires the new decisions into the turn sequence. |
| `ui/ConsoleUI.java` | Implements the two new `GameView` methods. State display shows Happy Hour status and the Host. | Console display and input for the new features. |
| `dv/` | Extended reference model, assertions and coverage for the new features. | Keeps the DV regression valid for Stage 3. |
```

Three things to check:

- The Stage 1 → 2 comparison is still missing. The brief requires one per transition, so add it in the same format.
- The video timestamps and contributors sections are left out here. The brief says the README must list the video timestamps, so add that table before submission.
- Since there is no features section now, the Host and Happy Hour rules (turn order, 20% after VIP, 2-turn duration) are documented only in the Java comments and the test scripts. If a grader wants them in the README, one sentence each under the comparison table would cover it."

