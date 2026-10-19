package rush.model;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.List;

/* Stores customers that arrived but not seated */
public class WaitingQueue {
    private final Deque<Customer> customers = new ArrayDeque<>();

    public void enqueue(Customer c) {
        customers.addLast(c);
    }

    public boolean remove(Customer c) {
        return customers.remove(c);
    }

    public boolean isEmpty() {
        return customers.isEmpty();
    }

    public int size() {
        return customers.size();
    }

    /* For printing of snapshot of the current queue */
    public List<Customer> snapshot() {
        return List.copyOf(customers);
    }
}