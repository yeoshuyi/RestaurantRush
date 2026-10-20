package rush.model;

import java.util.Optional;

/** Seats customers, takes orders and serves READY dishes. One task per turn. */
public class Waiter extends Staff {

    private int nextOrderId = 1;

    public Waiter() {
        super("Waiter");
    }

    public ActionResult seat(Customer c, WaitingQueue queue, Optional<Table> table) {
        if (!canAct()) {
            return busy();
        }
        if (c.getState() != CustomerState.WAITING) {
            return ActionResult.fail(c.getName() + " is not waiting in the queue.");
        }
        if (table.isEmpty() || !table.get().isFree()) {
            return ActionResult.fail("No free table.");
        }
        Table t = table.get();
        queue.remove(c);
        t.seat(c);
        c.seatAt(t);
        markActed();
        return ActionResult.ok("Waiter seats " + c.getName() + " at table " + t.getId() + ".");
    }

    public ActionResult takeOrder(Customer c, Menu menu) {
        if (!canAct()) {
            return busy();
        }
        if (c.getState() != CustomerState.SEATED) {
            return ActionResult.fail(c.getName() + " is not seated and waiting to order.");
        }
        MenuItem item = c.chooseItem(menu);
        Order order = new Order(nextOrderId++, c, item, c.computeBill(item.getPriceCents()));
        c.placeOrder(order);
        markActed();
        return ActionResult.ok("Waiter takes order " + order.describe() + " ("
                + Money.format(order.getBillCents()) + ", " + item.getPrepUnits() + " prep unit"
                + (item.getPrepUnits() == 1 ? "" : "s") + ").");
    }

    public ActionResult serve(Order o, int turn) {
        if (!canAct()) {
            return busy();
        }
        if (!o.isReady()) {
            return ActionResult.fail("Order " + o.describe() + " is not READY (status " + o.getStatus()
                    + ", " + o.getUnitsDone() + "/" + o.getItem().getPrepUnits() + " units done).");
        }
        if (o.getReadyTurn() >= turn) {
            return ActionResult.fail("Order " + o.describe() + " only became ready this turn. Serve next turn.");
        }
        o.markServed();
        o.getCustomer().onServed(turn);
        markActed();
        return ActionResult.ok("Waiter serves " + o.describe() + ".");
    }
}
