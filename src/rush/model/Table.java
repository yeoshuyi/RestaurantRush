package rush.model;

public class Table {
    private final int id;
    private Customer occupant;

    public Table(int id) {
        this.id = id;
        this.occupant = null;
    }

    public int getId() {
        return id;
    }

    public boolean isFree() {
        return occupant == null;
    }

    public Customer getOccupant() {
        return occupant;
    }

    // Package-private functions .seat() and .release() so only Staff in rush.model can modify the table state
    void seat(Customer c) {
        this.occupant = c;
    }

    void release() {
        this.occupant = null;
    }
}
