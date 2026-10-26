package rush.model;

import java.util.function.BiFunction;

/** Added VIP and CRITIC as new customer types */
public enum CustomerType {
    REGULAR("Regular", RegularCustomer::new),
    VIP("VIP", VIPCustomer::new), 
    CRITIC("Critic", CriticCustomer::new);

    private final String label;
    private final BiFunction<Integer, Integer, Customer> constructor;

    CustomerType(String label, BiFunction<Integer, Integer, Customer> constructor) {
        this.label = label;
        this.constructor = constructor;
    }

    public String getLabel() {
        return label;
    }

    /** Build a customer of this type with the given id and arrival turn. */
    public Customer create(int id, int arrivalTurn) {
        return constructor.apply(id, arrivalTurn);
    }
}
