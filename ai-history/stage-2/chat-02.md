AI Tool: Gemini

### My Prompt
"https://github.com/yeoshuyi/RestaurantRush
can you help me check"

### Gemini's Response
"The repository at [https://github.com/yeoshuyi/RestaurantRush](https://github.com/yeoshuyi/RestaurantRush) appears to be private or requires authentication, so its contents cannot be accessed directly.To check your code or repository setup, you can share:A directory listing / file tree (e.g., git status or the output of find src / tree).Specific classes or files you want reviewed against the Stage 1 specification (such as your Customer, Order, Table, Staff subclasses, or GameController).Git commit history & tags (e.g., git log --oneline or git tag -l) to verify whether the branch and tag structure matches the rubric requirements.   
Which specific file, test scenario, or branch would you like to review first?"

### My Prompt
"Its okay help me verify GameController and debug"

### Gemini's Response
"Bug 1: The Waiter task is not re-prompted on failure or cancelThe assignment brief explicitly states in Section 3.4:"An invalid choice must explain why it failed and let the manager choose again, without using up the staff task."   And in your Stage 1 Sequence Diagram:loop [until a Waiter task succeeds or WAIT]   
Currently, your code in waiterChoice() does this:
```
private void waiterChoice() {
    WaiterTask task = view.chooseWaiterTask(List.of(WaiterTask.values()));
    performWaiterTask(task).ifPresent(this::showActionResult);
}
```
If the manager:
1. Picks SEAT, but chooses 0) Back, OR
2. Picks a customer or table that returns an ActionResult.fail(reason) (e.g. attempting to serve an order that is not ready yet, or seating when no tables are free):   
Your current code prints the error or message and immediately ends the Waiter phase for that turn!   
The manager is never given the chance to choose again, wasting the waiter's turn.   
In the golden test transcript tests/stage1/victory.expected (turn 9) and defeat.expected (turn 7 and 13), when an action fails or the user cancels, the game immediately re-prompts: "Choose Waiter task [0-3]:

Bug 2: Filtering Order::isReady in serveOrder() breaks prompt & test replay
In GameController.serveOrder():
```
JavaList<Order> orders = restaurant.activeOrders().stream()
        .filter(Order::isReady)   // <--- Problem here!
        .collect(Collectors.toList());
if (orders.isEmpty()) {
    view.showMessage("No orders are ready to serve.");
    return Optional.empty();
}
```
1. UML Class Diagram & Sequence Diagram mismatch:
The Class Diagram specifies: 
chooseOrder(String prompt, List<Order> options) where activeOrders is passed directly.   
In stage1_sequence_diagram.drawio:
chooseOrder("Serve which order?", activeOrders)   

2. Breaks the Reproducible Defeat & Victory Runs:
In stage1_test_notes.md (Turn 9 in Victory run, Turn 11 in Defeat run):
"Turn 9: serving the Pasta is refused (not READY), so the Waiter waits"
"Turn 11: serving the Pasta is refused (1/2); wait"   
If you pre-filter orders so that only isReady() dishes appear, the player is told "No orders are ready to serve" without seeing the unready order list, and the domain validation in Waiter.serve(...) (which checks !o.isReady() and o.getReadyTurn() >= turn) can never be triggered or tested!

How to Fix GameController.java
Replace waiterChoice(), performWaiterTask(), and serveOrder() with this loop pattern:
```
private void waiterChoice() {
    while (restaurant.getWaiter().canAct()) {
        WaiterTask task = view.chooseWaiterTask(List.of(WaiterTask.values()));
        if (task == WaiterTask.WAIT) {
            view.showMessage("The waiter takes no action this turn.");
            break;
        }

        Optional<ActionResult> result = performWaiterTask(task);
        if (result.isPresent()) {
            showActionResult(result.get());
            if (result.get().isOk()) {
                break; // Action succeeded and consumed the task
            }
            // If result was fail (not ok), loop continues so manager can re-choose!
        }
        // If result was Optional.empty() (user chose 0/Back or list empty), loop continues!
    }
}

private Optional<ActionResult> performWaiterTask(WaiterTask task) {
    switch (task) {
        case SEAT:
            return seatCustomer();
        case TAKE_ORDER:
            return takeCustomerOrder();
        case SERVE:
            return serveOrder();
        default:
            return Optional.empty();
    }
}

private Optional<ActionResult> serveOrder() {
    // Pass ALL active orders so the player can attempt to serve,
    // allowing Waiter.serve() to enforce and report domain errors
    List<Order> orders = restaurant.activeOrders();
    if (orders.isEmpty()) {
        view.showMessage("No active orders to serve.");
        return Optional.empty();
    }
    Optional<Order> selected = view.chooseOrder("Choose an order to serve", orders);
    if (selected.isEmpty()) {
        return Optional.empty(); // User selected 0) Back
    }
    ActionResult result = restaurant.getWaiter().serve(selected.get(), turn);
    if (result.isOk()) {
        stats.recordServed();
    }
    return Optional.of(result);
}
```
Once you make that loop adjustment in GameController.java your program should run smoothly."

### My Prompt

"For README for stage 1, must i include the repository and active stage?"

### Gemini's Response

"Yes, you must include both, but here is how they apply to your README.md at Stage 1 versus the final submission:
1. The Repository Link (Mandatory by Brief)
In Section 6.1 (What to submit) of the assignment brief, the requirements state:
Item: READMEContents: "Repository URL, stage comparisons (Section 5) and video timestamps"
In addition, Section 5 (Design evidence) notes that your Git evidence and tagged releases (stage-1, stage-2, stage-3) will be graded directly from the repository.
Therefore, your README.md must display your team's GitHub URL clearly near the top (e.g. [https://github.com/yeoshuyi/RestaurantRush](https://github.com/yeoshuyi/RestaurantRush)).
2. The Active Stage (Best Practice for Multi-Stage Evaluation)While you don't need a formal metadata tag called "active stage," stating the current stage version in the README is strongly recommended:
Why it matters:
When a TA or automated grading script checks out your tag:
```
git checkout stage-1
```
The version of README.md present at that commit should clearly state:
Current Release: Stage 1 — Basic Restaurant Operation (Tag: stage-1)
Authentic Git Evolution:
In stage-1, the README explains how to run the Stage 1 game, the 18-turn loop, and the two Stage 1 test scripts (victory.txt and defeat.txt).   
When you later implement Stage 2 on top of Stage 1, you update the README to state Stage 2 — Customer Behaviour Extension (Tag: stage-2) and fill in the transition log ($1 \rightarrow 2$).   
In Stage 3, you finalize it with the full Stage 3 info, all transition logs ($1 \rightarrow 2$ and $2 \rightarrow 3$), and the recorded video timestamps.   
Summary Checklist for Stage 1 README: For your current stage-1 tag, make sure your README.md includes:
Repository Link: [https://github.com/yeoshuyi/RestaurantRush](https://github.com/yeoshuyi/RestaurantRush) (or your group's fork/repo).   
Current Stage Indicator: Indicating that this commit represents Stage 1 (stage-1).   
Build & Run Instructions: Clear javac and java commands to compile and run.   
Test Run Instructions: How to execute or replay the victory and defeat test scripts.   
Placeholders for Future Stages: Leave brief placeholders/headers for the Stage transitions and video timestamps, which will be filled in when reaching those milestones." 

### My Prompt

"wait why do we need to get a video timestamp? isnt that at the end of stage 3?"

### Gemini's Response

"Yes, the video recording and its timestamps are only required at the end of Stage 3 (for final submission).

The assignment brief groups all deliverables in the summary table under Section 6.1 (What to submit):

README (Repository URL, stage comparisons, and video timestamps)

Because that table describes the final project submission package, it lists the video timestamps alongside the stage comparisons.

What Belongs in the README Right Now (Stage 1)
For your stage-1 git tag:

You do NOT need video timestamps now.

You do not even have the video yet, because the video is an 8-minute walkthrough demonstrating the entire finished project (Stages 1 through 3) after all features are implemented.

Leaving that section out completely—or simply keeping a 1-line placeholder like ## Video Walkthrough (To be added in Stage 3)—is the proper way to handle it for your Stage 1 commit.

Your Stage 1 README.md only needs to focus on:

1.Repository link

2.Project structure

3.How to build and run the game (run.sh / run.bat)

4.How to replay and verify the Stage 1 tests (victory.txt / defeat.txt)

Would you like me to draft a README so it remains 100% focused on Stage 1?"

### My Prompt

"for test runs, do i have to create 2 files one victory and one defeat? what folder should i name it"

### Gemini Response

"Yes. Section 4.1 of the assignment brief specifically requires:
"Stage 1 must: compile and run on its own at tag stage-1; contain no Stage 2 or Stage 3 features; include one reproducible victory run and one reproducible defeat run in your test notes."   
Having automated scripts for both runs ensures:
1. Anyone testing your repository can reproduce the victory and defeat conditions without manual typing.
2. You can record the required reproducible runs for the final video walkthrough and report. 

What folder should you name it?
Store them in:
```
tests/stage1/
```
Inside your project root, create that folder and place the two files inside:
```
RestaurantRush/
├── tests/
│   └── stage1/
│       ├── victory.txt
│       └── defeat.txt
```

This matches the paths documented in your README.md and scripts:

./run.sh tests/stage1/victory.txt

./run.sh tests/stage1/defeat.txt

Would you like to run ./run.sh tests/stage1/victory.txt in your terminal now to check if it completes with the RESULT: VICTORY banner?
"

### My Prompt

"ok for the architechture tree what description do i put beside victory.txt and defeat.txt"

### Gemini's Response

"In your repository directory tree, keep the descriptions short, consistent, and focused on automated verification.

Here is the exact format to use:
```
RestaurantRush/
├── README.md           # Project documentation and instructions
├── CONTRIBUTING.md     # Guidelines for team contributions
├── run.sh              # Build and execution script (macOS/Linux)
├── run.bat             # Build and execution script (Windows)
├── src/
│   └── rush/
│       ├── Main.java   # Application entry point
│       ├── ui/         # Console input, display formatting, and view bridge
│       ├── game/       # Game controller, turn loop, config, and statistics
│       └── model/      # Core entities (Restaurant, Customer, Staff, Order, Table)
├── tests/
│   └── stage1/
│       ├── victory.txt # Deterministic script verifying victory condition
│       └── defeat.txt  # Deterministic script verifying defeat condition
└── docs/               # System architecture and UML design diagrams
```

Why these descriptions work well:
"Deterministic script verifying victory condition" highlights to your marker/grader that the test runs deterministically without manual intervention.

"Deterministic script verifying defeat condition" satisfies the Section 4.1 requirement requiring one reproducible victory and one reproducible defeat run.

The structure aligns neatly with the rest of your # comments in the tree."









