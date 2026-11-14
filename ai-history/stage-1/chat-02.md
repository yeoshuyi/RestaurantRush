# Chat 02 – Refactoring the Staff one-task-per-turn check

- **Tool:** Claude
- **Date:** 22 October 2026

**What this chat covers:** After writing the Stage 1 code, I noticed that the Waiter and Chef
methods (`seat()`, `takeOrder()`, `serve()`, `prepare()`) all repeated the same `canAct()` check
and `markActed()` call. I asked Claude whether moving this into the `Staff` base class was better
OO practice. Claude suggested two options: a template method in `Staff` that takes a lambda
(Option A), or one class per staff action (Option B).

## Full conversation

---

### Me (prompt 1)

Read my project code, it is a restaurant-based command line interface game with the following turned based rules:

```text
1 Arrivals The scheduled customer joins the waiting queue with satisfaction 100.
2 Manager choices Waiter: choose at most one task, or Wait: seat one queued customer at a free table,
take one seated customer’s order, or serve one READY order.
Chef: choose at most one order to advance by one preparation unit, or Wait. The
Chef may work on an order the Waiter took this turn.
3 Kitchen and serving The Waiter acts before the Chef. When an order’s last preparation unit is done, it
becomes READY. A dish can be served only if it was already READY when the Waiter
acts, so a dish finished this turn is served next turn at the earliest. Serving sets it to
SERVED.
4 Eating and payment A customer served on an earlier turn finishes one full turn of eating and becomes
READY_TO_PAY. The Cashier automatically handles at most one READY_TO_PAY
customer per turn, oldest first. A customer who became READY_TO_PAY this turn
pays next turn at the earliest. Payment adds the bill to revenue, marks the customer
and order PAID, and frees the table.
5 Waiting and
abandonment
At turn end, every waiting or seated customer who has not been served loses
satisfaction (Regular: 8 points, minimum 0). A customer who reaches 0 leaves
without paying: cancel any unfinished order and free the table. Customers who are
served, eating or ready to pay lose nothing.
6 Result The game always runs all 18 turns; there is no early ending. After turn 18: Victory if all
three targets in Section 2.1 are met, otherwise Defeat.
```

read the code first and let me consult you on how to make the code with better OO practices. Don't reply yet.

### Claude

I’ve read through all of it: the model, control and UI packages, the run scripts, the Stage 1 test transcripts, and the assignment brief. Go ahead with your questions whenever you’re ready.

---

### Me (prompt 2)

upon formulating the code, I realised that the staff (waiter and chef) have some recurring checks before the start of their turn. In waiter and Chef classes : seat(), takeOrder(), serve() and prepare() methods all asks the if-condition (!canAct()), and requires as markActed(). To incorporate better design practice, should I create an abstract based class: perform in Staff that Waiter and Chef can check to also incorporate the Single Responsibility Principle?

### Claude

Yes, but I’d tweak the framing. The duplication you spotted is real, and pulling it into Staff is a good move. However, the main reason isn’t SRP, and an abstract perform() that each subclass overrides won’t quite fit, because the Waiter has three different actions with different parameters.

#### Why it’s worth doing

The real gain is enforcing an invariant in one place. The brief says an invalid choice “must explain why it failed and let the manager choose again, without using up the staff task.” Right now each method gets this right only because you remembered to put markActed() after every validation. If someone adds a fourth Waiter action, or the Host in Stage 3, and calls markActed() too early, the rule silently breaks. Centralising it means subclasses can’t get it wrong.

For your report, describe it as the Template Method pattern: Staff owns the fixed skeleton (check budget, run action, consume budget only on success), and subclasses supply the variable step. You can argue SRP mildly (“Staff owns the one-action-per-turn rule; Waiter/Chef own only their task rules”), but don’t lean on it too hard, since a marker will see it’s mostly DRY plus invariant protection.

#### Option A: template method taking a lambda (lightest change)

```java
public abstract class Staff {
    private final String name;
    private boolean actedThisTurn;

    // Template method: subclasses cannot override the skeleton
    protected final ActionResult perform(Supplier<ActionResult> action) {
        if (!canAct()) {
            return ActionResult.fail(name + " has already acted this turn.");
        }
        ActionResult result = action.get();
        if (result.isOk()) {
            actedThisTurn = true;   // budget consumed only on success
        }
        return result;
    }

    public boolean canAct() { return !actedThisTurn; }
    public void resetTurn() { actedThisTurn = false; }
    public String getName() { return name; }
}
```

```java
public ActionResult prepare(Order o, int turn) {
    return perform(() -> {
        if (!o.isInKitchen()) {
            return ActionResult.fail("Order " + o.describe() + " needs no more preparation.");
        }
        o.advance(turn);
        return ActionResult.ok("Chef prepares " + o.describe() + (o.isReady() ? ": READY." : "."));
    });
}
```

markActed() and busy() disappear from the subclasses entirely. That’s the point.

#### Option B: each action as its own object (Command + Template Method)

```java
public abstract class StaffAction {
    protected abstract Optional<String> validate();   // reason if invalid
    protected abstract String execute();              // mutate state, return message
}

// in Staff
protected final ActionResult perform(StaffAction a) {
    if (!canAct()) return busy();
    Optional<String> err = a.validate();
    if (err.isPresent()) return ActionResult.fail(err.get());
    String msg = a.execute();
    markActed();
    return ActionResult.ok(msg);
}
```

With SeatAction, TakeOrderAction, ServeAction and PrepareAction as subclasses, this separates “is it legal?” from “do it,” which is cleaner. It also pays off in Stage 3: the Host also seats customers, so SeatAction gets reused by both Waiter and Host with zero duplicated validation. It also gives you nicer class-diagram material, with a clear abstract class and polymorphic dispatch.

#### Which I’d pick

For Stage 1, I’d go with Option A: it’s a small, safe change and keeps the stage simple. Then consider moving to Option B at Stage 3 when the Host arrives, and document that move in your README transition notes as “we extracted seating into a reusable action because a second role needed it.” That’s exactly the kind of justified design evolution the “Thinking and development process” criterion rewards.

Two small things to watch:

- Cashier: it has a different shape (it returns Optional&lt;Customer> and never “fails”), so don’t force it through perform. Just leave it using canAct() directly; that’s fine.
- A bug you’ll want to fix in the same pass: Waiter.seat() calls t.seat(c) and then c.seatAt(t), which calls t.seat(this) again. It’s harmless now, but let one object own that relationship (I’d keep it in Customer.seatAt).
