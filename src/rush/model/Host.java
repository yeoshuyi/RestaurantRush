package rush.model;

/** Seats at most one queued customer per turn, in addition to the Waiter's task (Stage 3). */
public class Host extends Staff {
    public Host() {
        super("Host");
    }

    public ActionResult seat(Customer c, Restaurant r){
        return perform(() -> r.seat(c,getName()));
    }
}