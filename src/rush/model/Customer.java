package rush.model;

public abstract class Customer {
    private final int id;
    private final int arrivalTurn;
    private int satisfaction;
    private CustomerState state;
    private Table table;
    private Order order;
    private int servedTurn;
    private int readyToPayTurn;

    public Customer(int id, int arrivalTurn) {
        this.id = id;
        this.arrivalTurn = arrivalTurn;
        this.satisfaction = 100;
        this.state = CustomerState.WAITING;
        this.table = null;
        this.order = null;
        this.servedTurn = -1;
        this.readyToPayTurn = -1;
    }

    public abstract int waitPenalty();
    public abstract CustomerType getType();

    // compute full price for regular customer
    public int computeBill(int baseCents) {
        return baseCents;
    }

    public MenuItem chooseItem(Menu m) {
        // Deterministic rule for food item choice
        return m.get((id - 1) % m.size());
    }

    public boolean isWaitingForService() {
        return state == CustomerState.WAITING || state == CustomerState.SEATED || state == CustomerState.ORDERED;
    }

    public void loseSatisfaction() {
        if (isWaitingForService()) {
            satisfaction = Math.max(0, satisfaction - waitPenalty());
        }
    }

    public boolean hasGivenUp() {
        return satisfaction == 0;
    }

    public boolean finishEating(int currentTurn) {
        if (state == CustomerState.SERVED && servedTurn < currentTurn) {
            state = CustomerState.READY_TO_PAY;
            readyToPayTurn = currentTurn;
            return true;
        }
        return false;
    }

    public boolean canPayOn(int currentTurn) {
        return state == CustomerState.READY_TO_PAY && readyToPayTurn < currentTurn;
    }

    void seatAt(Table t) {
        this.table = t;
        this.state = CustomerState.SEATED;
        t.seat(this);
    }

    void placeOrder(Order o) {
        this.order = o;
        this.state = CustomerState.ORDERED;
    }

    void onServed(int turn) {
        this.state = CustomerState.SERVED;
        this.servedTurn = turn;
    }

    void pay() {
        this.state = CustomerState.PAID;
        if (table != null) {
            table.release();
        }
    }

    void leave() {
        this.state = CustomerState.LEFT;
        if (order != null) {
            order.cancel();
        }
        if (table != null) {
            table.release();
        }
    }

    public int getId() { return id; }
    public int getArrivalTurn() { return arrivalTurn; }
    public int getSatisfaction() { return satisfaction; }
    public CustomerState getState() { return state; }
    public Table getTable() { return table; }
    public Order getOrder() { return order; }
    public int getServedTurn() { return servedTurn; }
    public int getReadyToPayTurn() { return readyToPayTurn; }
    public String getName() {
        return "C" + id;
    }
}
