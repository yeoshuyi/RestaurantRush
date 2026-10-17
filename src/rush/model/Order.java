package rush.model;

public class Order {
    private final int id;
    private final Customer customer;
    private final MenuItem item;
    private final int billCents;
    private int unitsDone;
    private OrderStatus status;
    private int readyTurn;

    public Order(int id, Customer customer, MenuItem item, int billCents) {
        this.id = id;
        this.customer = customer;
        this.item = item;
        this.billCents = billCents;
        this.unitsDone = 0;
        this.status = OrderStatus.PLACED;
        this.readyTurn = -1;
    }

    public int getId() { return id; }
    public Customer getCustomer() { return customer; }
    public MenuItem getItem() { return item; }
    public int getBillCents() { return billCents; }
    public int getUnitsDone() { return unitsDone; }
    public OrderStatus getStatus() { return status; }
    public int getReadyTurn() { return readyTurn; }

    public boolean isInKitchen() {
        return status == OrderStatus.PLACED || status == OrderStatus.IN_PREPARATION;
    }

    public boolean isReady() {
        return status == OrderStatus.READY;
    }

    public boolean isActive() {
        return status != OrderStatus.PAID && status != OrderStatus.CANCELLED;
    }

    void advance(int turn) {
        unitsDone++;
        if (unitsDone >= item.getPrepUnits()) {
            status = OrderStatus.READY;
            readyTurn = turn;
        } else {
            status = OrderStatus.IN_PREPARATION;
        }
    }

    void markServed() {
        this.status = OrderStatus.SERVED;
    }

    void markPaid() {
        this.status = OrderStatus.PAID;
    }

    void cancel() {
        this.status = OrderStatus.CANCELLED;
    }

    public String describe() {
        return "#" + id + " " + item.getName() + " (" + unitsDone + "/" + item.getPrepUnits() + " units) [" + status + "]";
    }
}
