package rush.model;

import java.util.Comparator;
import java.util.List;
import java.util.Optional;

public class Cashier extends Staff {

    public Cashier() {
        super("Cashier");
    }

    /* Charge ready to pay queue, cannot charge ready this turn */
    public Optional<Customer> collect(List<Customer> due, int turn) {
        if (!canAct()) {
            return Optional.empty();
        }
        Optional<Customer> next = due.stream().filter(c -> c.canPayOn(turn)).min(Comparator.comparingInt(Customer::getReadyToPayTurn).thenComparingInt(Customer::getId));
        next.ifPresent(c -> {
            c.pay();
            markActed();
        });
        return next;
    }
}
