package rush.control;

public enum WaiterTask {
    WAIT("Wait"),
    SEAT("Seat a customer"),
    TAKE_ORDER("Take an order"),
    SERVE("Serve an order");

    private final String label;

    WaiterTask(String label) {
        this.label = label;
    }

    public String getLabel() {
        return label;
    }
}