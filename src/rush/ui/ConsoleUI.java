package rush.ui;

import java.io.PrintStream;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.OptionalDouble;

import rush.control.GameConfig;
import rush.control.GameResult;
import rush.control.GameStats;
import rush.control.GameView;
import rush.control.WaiterTask;
import rush.model.Customer;
import rush.model.Money;
import rush.model.Order;
import rush.model.Restaurant;
import rush.model.Table;

/** Console implementation of {@link GameView}. Displays state and reads choices only. */
public class ConsoleUI implements GameView {

    private static final String THICK = "=".repeat(60);
    private static final String THIN = "-".repeat(60);

    private final InputReader input;
    private final PrintStream out;

    public ConsoleUI(InputReader input, PrintStream out) {
        this.input = input;
        this.out = out;
    }

    @Override
    public void showTurnHeader(int turn, int maxTurns) {
        out.println();
        out.println(THICK);
        out.println(" TURN " + turn + " / " + maxTurns);
        out.println(THICK);
    }

    @Override
    public void showState(Restaurant r, GameStats stats) {
        out.println("Revenue: " + Money.format(stats.getRevenueCents())
                + "   Paid: " + stats.getPaidCount()
                + "   Avg satisfaction (paid): " + formatAverage(stats.averageSatisfaction()));
        List<Customer> queued = r.getQueue().snapshot();
        out.print("Waiting queue:");
        if (queued.isEmpty()) {
            out.print(" (empty)");
        }
        for (Customer c : queued) {
            out.print(" " + c.getName() + "[sat " + c.getSatisfaction() + "]");
        }
        out.println();
        out.println("Tables:");
        for (Table t : r.getTables()) {
            out.println("  Table " + t.getId() + ": "
                    + (t.isFree() ? "free" : describe(t.getOccupant())));
        }
        out.println("Staff: Waiter " + available(r.getWaiter().canAct(), "1 task")
                + " | Chef " + available(r.getChef().canAct(), "1 prep unit")
                + " | Cashier automatic, 1 payment");
        out.println(THIN);
    }

    @Override
    public WaiterTask chooseWaiterTask(List<WaiterTask> tasks) {
        out.println("Waiter tasks:");
        for (int i = 0; i < tasks.size(); i++) {
            out.println("  " + i + ") " + tasks.get(i).getLabel());
        }
        return tasks.get(input.readInt("Choose Waiter task", 0, tasks.size() - 1));
    }

    @Override
    public Optional<Customer> chooseCustomer(String prompt, List<Customer> options) {
        out.println(prompt);
        out.println("  0) Back");
        for (int i = 0; i < options.size(); i++) {
            out.println("  " + (i + 1) + ") " + describe(options.get(i)));
        }
        int choice = input.readInt("Choose customer", 0, options.size());
        return choice == 0 ? Optional.empty() : Optional.of(options.get(choice - 1));
    }

    @Override
    public Optional<Order> chooseOrder(String prompt, List<Order> options) {
        out.println(prompt);
        out.println("  0) Back");
        return pickOrder(options, "Choose order");
    }

    @Override
    public Optional<Order> chooseChefOrder(List<Order> options) {
        out.println("Chef: prepare which order?");
        out.println("  0) Wait");
        return pickOrder(options, "Choose Chef task");
    }

    private Optional<Order> pickOrder(List<Order> options, String prompt) {
        for (int i = 0; i < options.size(); i++) {
            out.println("  " + (i + 1) + ") " + describe(options.get(i)));
        }
        int choice = input.readInt(prompt, 0, options.size());
        return choice == 0 ? Optional.empty() : Optional.of(options.get(choice - 1));
    }

    @Override
    public void showMessage(String message) {
        out.println("  > " + message);
    }

    @Override
    public void showError(String reason) {
        out.println("  ! " + reason);
    }

    @Override
    public void showEndOfTurn(int turn, int maxTurns, GameStats stats) {
        out.println(THIN);
        out.println("End of turn " + turn + ": served " + stats.getServedCount()
                + " | unhappy departures " + stats.getUnhappyDepartures()
                + " | revenue " + Money.format(stats.getRevenueCents())
                + " | avg satisfaction " + formatAverage(stats.averageSatisfaction())
                + " | turns used " + stats.getTurnsUsed() + "/" + maxTurns);
    }

    @Override
    public void showResult(GameResult result) {
        GameStats s = result.getStats();
        GameConfig c = result.getConfig();
        out.println();
        out.println(THICK);
        out.println(" RESULT: " + (result.isVictory() ? "VICTORY" : "DEFEAT"));
        out.println(THICK);
        out.println("  Paid customers:   " + s.getPaidCount()
                + " (target >= " + c.getTargetPaid() + ") " + mark(result.isPaidMet()));
        out.println("  Revenue:          " + Money.format(s.getRevenueCents())
                + " (target >= " + Money.format(c.getTargetRevenueCents()) + ") "
                + mark(result.isRevenueMet()));
        out.println("  Avg satisfaction: " + formatAverage(s.averageSatisfaction())
                + " (target >= " + c.getTargetAvgSatisfaction() + ") "
                + mark(result.isSatisfactionMet()));
        out.println("  Served " + s.getServedCount() + " | unhappy departures "
                + s.getUnhappyDepartures() + " | turns used " + s.getTurnsUsed() + "/" + c.getMaxTurns());
    }

    private static String describe(Customer c) {
        StringBuilder sb = new StringBuilder();
        sb.append(c.getName()).append(" (").append(c.getType().getLabel()).append(") sat ")
                .append(c.getSatisfaction()).append(", ").append(c.getState());
        if (c.getOrder() != null) {
            sb.append(", order ").append(describeOrderStatus(c.getOrder()));
        }
        return sb.toString();
    }

    private static String describe(Order o) {
        return o.describe() + " [" + o.getStatus() + " " + progress(o) + "]";
    }

    private static String describeOrderStatus(Order o) {
        return "#" + o.getId() + " " + o.getItem().getName() + " " + o.getStatus() + " " + progress(o);
    }

    private static String progress(Order o) {
        return o.getUnitsDone() + "/" + o.getItem().getPrepUnits();
    }

    private static String available(boolean canAct, String what) {
        return canAct ? "(" + what + " available)" : "(done)";
    }

    private static String mark(boolean met) {
        return met ? "[met]" : "[MISSED]";
    }

    private static String formatAverage(OptionalDouble avg) {
        return avg.isPresent() ? String.format(Locale.ROOT, "%.1f", avg.getAsDouble()) : "N/A";
    }
}
