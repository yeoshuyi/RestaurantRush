package rush.model;

/** Seats customers, takes orders and serves READY dishes. One task per turn. */
public class Waiter extends Staff {

    private int nextOrderId = 1;

    public Waiter() {
        super("Waiter");
    }

    public ActionResult seat(Customer c, Restaurant r) {
        //seating is done by calling Restaurant object's seat method
        //Waiter should not hold references to Table and Waiting Queue
        return perform(() -> r.seat(c, getName()));
    }

    //takeOrder method passes in Restaurant object
    //takeOrder needs quoteBill() to store the associated price of Order
    public ActionResult takeOrder(Customer c, Restaurant r) {
        return perform(() -> {
            if (c.getState() != CustomerState.SEATED) {
                return ActionResult.fail(c.getName() + " is not seated and waiting to order.");
            }
            MenuItem item = c.chooseItem(r.getMenu());
            Order order = new Order(nextOrderId++, c, item, r.quoteBill(c, item));
            c.placeOrder(order);
            return ActionResult.ok("Waiter takes order " + order.describe() + " ("
                    + Money.format(order.getBillCents()) + ", " + item.getPrepUnits() + " prep unit"
                    + (item.getPrepUnits() == 1 ? "" : "s") + ").");
        });
    }

    public ActionResult serve(Order o, int turn) {
        return perform(() -> {
            if (!o.isReady()) {
                return ActionResult.fail("Order " + o.describe() + " is not READY (status " + o.getStatus()
                        + ", " + o.getUnitsDone() + "/" + o.getItem().getPrepUnits() + " units done).");
            }
            if (o.getReadyTurn() >= turn) {
                return ActionResult.fail("Order " + o.describe() + " only became ready this turn. Serve next turn.");
            }
            o.markServed();
            o.getCustomer().onServed(turn);
            return ActionResult.ok("Waiter serves " + o.describe() + ".");
        });
    }
}
