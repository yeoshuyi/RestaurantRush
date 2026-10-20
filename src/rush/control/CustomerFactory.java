package rush.control;

import java.util.Objects;

import rush.model.Customer;
import rush.model.CustomerType;
import rush.model.RegularCustomer;

public class CustomerFactory {
    private int nextId = 1;

    public Customer create(CustomerType type, int turn) {
        Objects.requireNonNull(type, "type");
        switch (type) {
            case REGULAR:
                return new RegularCustomer(nextId++, turn);
            default:
                throw new IllegalArgumentException("Unsupported customer type: " + type);
        }
    }
}