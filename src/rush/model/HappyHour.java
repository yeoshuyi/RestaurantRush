package rush.model;

public class HappyHour {
    public static final int DURATION_TURNS = 2;
    private static final int DISCOUNT_PERCENT_OF_BILL = 80; // pay 80% = 20% off
    private static final int SATISFACTION_RECOVERY = 15;
    private static final int MAX_SATISFACTION = 100;
 
    private boolean usedThisGame = false;
    private int remainingTurns = 0;
 
    /** Switch Happy Hour on. Returns false if it was already used this game. */
    public boolean activate() {
        if (usedThisGame) {
            return false;
        }
        usedThisGame = true;
        remainingTurns = DURATION_TURNS;
        return true;
    }
 
    public boolean isActive() {
        return remainingTurns > 0;
    }
 
    public boolean canActivate() {
        return !usedThisGame;
    }
 
    /** For display, e.g. "Happy Hour: 2 turn(s) left". */
    public int getRemainingTurns() {
        return remainingTurns;
    }
 
    /** Call once at the end of every turn so the duration counts down. */
    public void endTurn() {
        if (remainingTurns > 0) {
            remainingTurns--;
        }
    }
 
    /**
     * Price locked when the order is taken. Pass the bill AFTER the VIP discount.
     * Returns the bill unchanged when Happy Hour is not active.
     */
    public int applyDiscount(int billCents) {
        if (!isActive()) {
            return billCents;
        }
        return (billCents * DISCOUNT_PERCENT_OF_BILL + 50) / 100;
    }
 
    /** New satisfaction for a waiting customer at the start of an active turn (capped at 100). */
    public int recover(int satisfaction) {
        if (!isActive()) {
            return satisfaction;
        }
        return Math.min(MAX_SATISFACTION, satisfaction + SATISFACTION_RECOVERY);
    }
}
