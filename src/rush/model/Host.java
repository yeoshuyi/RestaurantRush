package rush.model;

public class Host {
    private boolean seatedThisTurn = false;
 
    /** Call at the start of every turn. */
    public void startTurn() {
        seatedThisTurn = false;
    }
 
    /** True if the Host has not yet seated anyone this turn. */
    public boolean canSeat() {
        return !seatedThisTurn;
    }
 
    /**
     * Seat the next queued customer if the Host has not acted yet this turn.
     * Returns true if a customer was seated.
     */
    public boolean seatNext(WaitingQueue queue, Table table) {
        if (seatedThisTurn || queue.isEmpty() || table == null) {
            return false;
        }
        // TODO: replace with your existing seating call, e.g. the one Waiter uses.
        // Customer next = queue.poll();
        // table.seat(next);
        seatedThisTurn = true;
        return true;
    }
}