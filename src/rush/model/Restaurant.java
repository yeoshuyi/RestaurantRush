package rush.model;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/** Holds instance of menu, staffs, customers, tables */
public class Restaurant {

    private final List<Table> tables = new ArrayList<>();
    private final WaitingQueue queue = new WaitingQueue();
    private final Menu menu;
    private final List<Customer> customers = new ArrayList<>();
    private final Waiter waiter = new Waiter();
    private final Chef chef = new Chef();
    private final Cashier cashier = new Cashier();

    public Restaurant(int tableCount, Menu menu) {
        for (int i = 1; i <= tableCount; i++) {
            tables.add(new Table(i));
        }
        this.menu = menu;
    }

    public void resetStaff() {
        waiter.resetTurn();
        chef.resetTurn();
        cashier.resetTurn();
    }

    /** Customer enqueue */
    public void admit(Customer c) {
        customers.add(c);
        queue.enqueue(c);
    }

    public Optional<Table> freeTable() {
        return tables.stream().filter(Table::isFree).findFirst();
    }

    /** Customer-specific pricing is calculated inside Restaurant class, not in Waiter class. */
    public int quoteBill(Customer c, MenuItem item) {
        return c.computeBill(item.getPriceCents());
    }

    /** Seat a queued customer at the first free table. Package-private: only staff may seat. */
    ActionResult seat(Customer c, String byWhom) {
        if (c.getState() != CustomerState.WAITING) {
            return ActionResult.fail(c.getName() + " is not waiting in the queue.");
        }
        Optional<Table> table = freeTable();
        if (table.isEmpty()) {
            return ActionResult.fail("No free table.");
        }
        queue.remove(c);
        c.seatAt(table.get());
        return ActionResult.ok(byWhom + " seats " + c.getName() + " at table " + table.get().getId() + ".");
    }

    /** Seated customers who have not ordered yet */
    public List<Customer> awaitingOrder() {
        return customersIn(CustomerState.SEATED);
    }

    /** Orders that have not been served or cancelled yet, oldest first */
    public List<Order> activeOrders() {
        return orders().filter(Order::isActive).collect(Collectors.toList());
    }

    /** Orders the Chef can still work on, oldest first */
    public List<Order> kitchenOrders() {
        return orders().filter(Order::isInKitchen).collect(Collectors.toList());
    }

    public List<Customer> readyToPay() {
        return customersIn(CustomerState.READY_TO_PAY);
    }

    /** Customers who have neither paid nor left, in arrival order */
    public List<Customer> presentCustomers() {
        return customers.stream().filter(Customer::isPresent).collect(Collectors.toList());
    }

    /** Customers served on an earlier turn finish eating */
    public List<Customer> finishEating(int turn) {
        return customers.stream().filter(c -> c.finishEating(turn)).collect(Collectors.toList());
    }

    /** Cashier charges at most one READY_TO_PAY customer */
    public Optional<Customer> collectPayment(int turn) {
        return cashier.collect(readyToPay(), turn);
    }

    /* Every customer still waiting for a table or food loses, 0 satisfaction leaves */
    public List<Customer> applyWaiting() {
        List<Customer> left = new ArrayList<>();
        for (Customer c : presentCustomers()) {
            if (!c.isWaitingForService()) {
                continue;
            }
            c.loseSatisfaction();
            if (c.hasGivenUp()) {
                queue.remove(c);
                c.leave();
                left.add(c);
            }
        }
        return left;
    }

    private List<Customer> customersIn(CustomerState state) {
        return customers.stream().filter(c -> c.getState() == state).collect(Collectors.toList());
    }

    private Stream<Order> orders() {
        return customers.stream()
                .map(Customer::getOrder)
                .filter(o -> o != null)
                .sorted(Comparator.comparingInt(Order::getId));
    }

    public List<Table> getTables() {
        return Collections.unmodifiableList(tables);
    }

    public WaitingQueue getQueue() {
        return queue;
    }

    public Menu getMenu() {
        return menu;
    }

    public List<Customer> getCustomers() {
        return Collections.unmodifiableList(customers);
    }

    public Waiter getWaiter() {
        return waiter;
    }

    public Chef getChef() {
        return chef;
    }

    public Cashier getCashier() {
        return cashier;
    }
}
