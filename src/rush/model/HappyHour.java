package rush.model;

/**
 * Happy Hour pricing policy (Stage 3). The manager may start it once per game at the
 * start of a turn; it lasts that turn and the next. While active, orders taken get 20% off
 * (after any customer discount) and customers still waiting recover satisfaction at turn start.
 */
public class HappyHour {
    public static final int DURATION = 2;
    public static final int RECOVERY = 15;

    private boolean used;
    private int turnsLeft;

    public boolean canActivate() {
        return !used;
    }

    /** Start Happy Hour now. Returns false if it was already used this game. */
    public boolean activate() {
        if (used) {
            return false;
        }
        used = true;
        turnsLeft = DURATION;
        return true;
    }

    public boolean isActive() {
        return turnsLeft > 0;
    }

    public boolean isUsed() {
        return used;
    }

    /** Active turns left, counting the current one. */
    public int getTurnsLeft() {
        return turnsLeft;
    }

    /** 20% off rounded half up to the cent while active; unchanged otherwise. */
    public int applyTo(int cents) {
        return isActive() ? (cents * 80 + 50) / 100 : cents;
    }

    /** Called once at the end of every turn. */
    public void endTurn() {
        if (turnsLeft > 0) {
            turnsLeft--;
        }
    }
}