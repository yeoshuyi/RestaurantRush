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
import rush.model.HappyHour;

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
        happyHourStart();
        view.showState(restaurant, stats);
        hostChoice();
        waiterChoice();
        chefChoice();
        eatingAndPayment();
        waitingAndAbandonment();
        restaurant.getHappyHour().endTurn();
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

    /** Stage 3: offer Happy Hour when unused */
    /** Stage 3: apply the turn-start recovery if active. */
    private void happyHourStart() {
        HappyHour happyHour = restaurant.getHappyHour();
        if (happyHour.canActivate() && view.chooseHappyHour()) {
            happyHour.activate();
            view.showMessage("Happy Hour starts: " + HappyHour.DURATION
                    + " turns (this turn and next), 20% off new orders.");
        }
        for (Customer c : restaurant.applyHappyHourRecovery()) {
            view.showMessage(c.getName() + " recovers to " + c.getSatisfaction() + " (Happy Hour).");
        }
    }

    /** Stage 3: Host can seat at most one queued customer, before the waiter acts. */
    private void hostChoice() {
        List<Customer> waiting = restaurant.getQueue().snapshot();
        if (waiting.isEmpty()) {
            view.showMessage("The host has no customers to seat.");
            return;
        }
        if (restaurant.freeTable().isEmpty()) {
            view.showMessage("The host has no free table.");
            return;
        }
        view.chooseHostCustomer(waiting)
                .ifPresent(c -> showActionResult(restaurant.getHost().seat(c, restaurant)));
    }

    private void waiterChoice() {
        while (restaurant.getWaiter().canAct()) {
            WaiterTask task = view.chooseWaiterTask(List.of(WaiterTask.values()));
            if (task == WaiterTask.WAIT) {
                view.showMessage("The waiter takes no action this turn.");
                break;
            }

            Optional<ActionResult> result = performWaiterTask(task);
            if (result.isPresent()) {
                showActionResult(result.get());
                if (result.get().isOk()) {
                    break; // Action succeeded and consumed the task
                }
                // If result was fail (not ok), loop continues so manager can re-choose waiter task
            }
            // If result was Optional.empty() (user chose 0/Back or list empty), loop continues!
        }
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
            return Optional.of(restaurant.getWaiter().seat(selected.get(), restaurant));
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
        return Optional.of(restaurant.getWaiter().takeOrder(selected.get(), restaurant));
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
