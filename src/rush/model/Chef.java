package rush.model;

public class Chef extends Staff {
    public Chef() {
        //Initialises Staff Constructor with name Chef
        super("Chef");
    }

    public ActionResult prepare(Order o, int turn) {
        if (!canAct()) {
            return busy();
        }
        if (!o.isInKitchen()) {
            return ActionResult.fail("Order " + o.describe() + " needs no more preparation (status "
                    + o.getStatus() + ").");
        }
        o.advance(turn);
        markActed();
        String progress = o.getUnitsDone() + "/" + o.getItem().getPrepUnits();
        if (o.isReady()) {
            return ActionResult.ok("Chef prepares " + o.describe() + " (" + progress + "): READY.");
        }
        return ActionResult.ok("Chef prepares " + o.describe() + " (" + progress + ").");
    }
}