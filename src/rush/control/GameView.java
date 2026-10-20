package rush.control;

import java.util.List;
import java.util.Optional;

import rush.model.Customer;
import rush.model.Order;
import rush.model.Restaurant;

/** Bridge between User Interface and Controller */
public interface GameView {
    void showTurnHeader(int turn, int maxTurns);

    void showState(Restaurant restaurant, GameStats stats);

    WaiterTask chooseWaiterTask(List<WaiterTask> tasks);

    Optional<Customer> chooseCustomer(String prompt, List<Customer> options);

    Optional<Order> chooseOrder(String prompt, List<Order> options);

    Optional<Order> chooseChefOrder(List<Order> options);

    void showMessage(String message);

    void showError(String reason);

    void showEndOfTurn(int turn, int maxTurns, GameStats stats);

    void showResult(GameResult result);
}
