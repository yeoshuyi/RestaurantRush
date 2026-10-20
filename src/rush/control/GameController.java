package rush.control;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

import rush.model.ActionResult;
import rush.model.Customer;
import rush.model.CustomerType;
import rush.model.Money;
import rush.model.Order;
import rush.model.Restaurant;

public class GameController {
    private final GameConfig config;
    private final Restaurant restaurant;
    private final GameStats stats;
    private final CustomerFactory factory;
    private final GameView view;
    private int turn;

    public GameController(GameConfig config, GameView view) {
        this.config = config;
        this.restaurant = new Restaurant(config.getTables(), config.getMenu());
        this.stats = new GameStats();
        this.factory = new CustomerFactory();
        this.view = view;
        this.turn = 0;
    }

    public GameResult run() {
        while (turn < config.getMaxTurns()) {
            playTurn();
        }
        GameResult result = stats.evaluate(config);
        view.showResult(result);
        return result;
    }

    private void playTurn() {
        turn++;
        restaurant.resetStaff();
        view.showTurnHeader(turn, config.getMaxTurns());
        handleArrivals();
        view.showState(restaurant, stats);
        waiterChoice();
        chefChoice();
        eatingAndPayment();
        waitingAndAbandonment();
        stats.recordTurnPlayed(turn);
        view.showEndOfTurn(turn, config.getMaxTurns(), stats);
    }

    private void handleArrivals() {
        Optional<CustomerType> arrival = config.arrivalAt(turn);
        arrival.ifPresent(type -> {
            Customer customer = factory.create(type, turn);
            restaurant.admit(customer);
            view.showMessage(customer.getName() + " arrives (" + type.getLabel() + ").");
        });
    }

    private void waiterChoice() {
        WaiterTask task = view.chooseWaiterTask(List.of(WaiterTask.values()));
        performWaiterTask(task).ifPresent(this::showActionResult);
    }

    private Optional<ActionResult> performWaiterTask(WaiterTask task) {
        switch (task) {
            case WAIT:
                view.showMessage("The waiter takes no action this turn.");
                return Optional.empty();
            case SEAT:
                return seatCustomer();
            case TAKE_ORDER:
                return takeCustomerOrder();
            case SERVE:
                return serveOrder();
            default:
                throw new IllegalArgumentException("Unsupported waiter task: " + task);
        }
    }

    private Optional<ActionResult> seatCustomer() {
        List<Customer> waiting = restaurant.getQueue().snapshot();
        if (waiting.isEmpty()) {
            view.showMessage("No customers are waiting to be seated.");
            return Optional.empty();
        }
        Optional<Customer> selected = view.chooseCustomer("Choose a customer to seat", waiting);
        if (selected.isEmpty()) {
            return Optional.empty();
        }
        return Optional.of(restaurant.getWaiter().seat(
                selected.get(), restaurant.getQueue(), restaurant.freeTable()));
    }

    private Optional<ActionResult> takeCustomerOrder() {
        List<Customer> awaitingOrder = restaurant.awaitingOrder();
        if (awaitingOrder.isEmpty()) {
            view.showMessage("No seated customers are waiting to order.");
            return Optional.empty();
        }
        Optional<Customer> selected = view.chooseCustomer("Choose a customer to take an order from", awaitingOrder);
        if (selected.isEmpty()) {
            return Optional.empty();
        }
        return Optional.of(restaurant.getWaiter().takeOrder(selected.get(), restaurant.getMenu()));
    }

    private Optional<ActionResult> serveOrder() {
        List<Order> orders = restaurant.activeOrders().stream()
                .filter(Order::isReady)
                .collect(Collectors.toList());
        if (orders.isEmpty()) {
            view.showMessage("No orders are ready to serve.");
            return Optional.empty();
        }
        Optional<Order> selected = view.chooseOrder("Choose an order to serve", orders);
        if (selected.isEmpty()) {
            return Optional.empty();
        }
        ActionResult result = restaurant.getWaiter().serve(selected.get(), turn);
        if (result.isOk()) {
            stats.recordServed();
        }
        return Optional.of(result);
    }

    private void chefChoice() {
        List<Order> orders = restaurant.kitchenOrders();
        if (orders.isEmpty()) {
            view.showMessage("The chef has no orders to prepare.");
            return;
        }
        Optional<Order> selected = view.chooseChefOrder(orders);
        if (selected.isEmpty()) {
            return;
        }
        showActionResult(restaurant.getChef().prepare(selected.get(), turn));
    }

    private void eatingAndPayment() {
        restaurant.finishEating(turn);
        restaurant.collectPayment(turn).ifPresent(customer -> {
            Order order = customer.getOrder();
            stats.recordPayment(order.getBillCents(), customer.getSatisfaction());
            view.showMessage(customer.getName() + " pays " + Money.format(order.getBillCents()) + ".");
        });
    }

    private void waitingAndAbandonment() {
        List<Customer> departed = restaurant.applyWaiting();
        for (Customer customer : departed) {
            stats.recordDeparture();
            view.showMessage(customer.getName() + " leaves unhappy.");
        }
    }

    private void showActionResult(ActionResult result) {
        if (result.isOk()) {
            view.showMessage(result.getMessage());
        } else {
            view.showError(result.getMessage());
        }
    }
}