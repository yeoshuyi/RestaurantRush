package rush.model;

import java.util.function.Supplier;

/** Common abstract class for staff member, implements turn logic */
public abstract class Staff {
    private final String name;
    private boolean actedThisTurn;

    protected Staff(String name) {
        this.name = name;
    }

    public boolean canAct() {
        return !actedThisTurn;
    }

    protected void markActed() {
        actedThisTurn = true;
    }

    public void resetTurn() {
        actedThisTurn = false;
    }

    public String getName() {
        return name;
    }

    protected ActionResult busy() {
        return ActionResult.fail(name + " has already acted this turn.");
    }

    //Run one action under the one-task-per-turn rule. A failed action does not use up the task.
    protected ActionResult perform(Supplier<ActionResult> action) {
        if (!canAct()) {
            return busy();
        }
        ActionResult result = action.get();
        if (result.isOk()) {
            markActed();
        }
        return result;
    }
    
}
