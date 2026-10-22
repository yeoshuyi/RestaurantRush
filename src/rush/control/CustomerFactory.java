package rush.control;

import java.util.Objects;

import rush.model.Customer;
import rush.model.CustomerType;

public class CustomerFactory {
    private int nextId = 1;

    public Customer create(CustomerType type, int turn) {
        Objects.requireNonNull(type, "type");
        return type.create(nextId++, turn);
    }
}