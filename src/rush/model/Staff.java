package rush.model;

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
    
}
