package rush.model;

/** VIP customer inherits all Customer logic while still executing VIP-specific methods, does not modify the main game loop */
public class VIPCustomer extends Customer {
    public VIPCustomer(int id, int arrivalTurn) {
        super(id, arrivalTurn);
    }

    /** VIP loses 5 satisfaction points per turn waiting or seated w/o being served */
    @Override
    public int waitPenalty() {
        return 5;
    }

    /** VIP gets 10% off = 90% of the original price, with half-up rounding up to the nearest cent */
    @Override
    public int computeBill(int baseCents) {
        return (baseCents * 90 + 50) / 100;
    }

    /** identifies customer type as VIP e.g. for reporting or console output formatting */
    @Override
    public CustomerType getType() {
        return CustomerType.VIP;
    }
}
