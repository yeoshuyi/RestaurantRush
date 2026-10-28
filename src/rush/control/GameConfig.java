package rush.control;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;

import rush.model.ComboMeal;
import rush.model.CustomerType;
import rush.model.Menu;
import rush.model.MenuItem;


public class GameConfig {
    private final int maxTurns;
    private final int tables;
    private final int targetPaid;
    private final int targetRevenueCents;
    private final int targetAvgSatisfaction;
    private final Map<Integer, CustomerType> arrivals;
    private final Menu menu;

    public GameConfig(int maxTurns, int tables, int targetPaid, int targetRevenueCents,
            int targetAvgSatisfaction, Map<Integer, CustomerType> arrivals, Menu menu) {
        this.maxTurns = maxTurns;
        this.tables = tables;
        this.targetPaid = targetPaid;
        this.targetRevenueCents = targetRevenueCents;
        this.targetAvgSatisfaction = targetAvgSatisfaction;
        this.arrivals = Collections.unmodifiableMap(new TreeMap<>(arrivals));
        this.menu = menu;
    }

    /** 18 turns, 2 tables, arrival at 1/4/7/10/13/16, win at 4 paid */
    /** Stage 2 addition, Critic at turn 4 and VIP at turn 7 **/
    /** Stage 3: the menu adds the three pair combos (Salad+Burger, Salad+Pasta, Burger+Pasta).
     **/
    public static GameConfig baseSetting() {
        Map<Integer, CustomerType> arrivals = new TreeMap<>();
        for (int turn : new int[] {1, 4, 7, 10, 13, 16}) {
            arrivals.put(turn, CustomerType.REGULAR);
        }
        arrivals.put(4, CustomerType.CRITIC);
        arrivals.put(7, CustomerType.VIP);
        MenuItem salad = new MenuItem("Salad", 900, 1);
        MenuItem burger = new MenuItem("Burger", 1500, 1);
        MenuItem pasta = new MenuItem("Pasta", 1800, 2);
        Menu menu = new Menu(List.of(salad, burger, pasta,
                new ComboMeal(salad, burger),
                new ComboMeal(salad, pasta),
                new ComboMeal(burger, pasta)));
        return new GameConfig(18, 2, 4, 4500, 60, arrivals, menu);
    }

    // May return null
    public Optional<CustomerType> arrivalAt(int turn) {
        return Optional.ofNullable(arrivals.get(turn));
    }

    public int getMaxTurns() {
        return maxTurns;
    }

    public int getTables() {
        return tables;
    }

    public int getTargetPaid() {
        return targetPaid;
    }

    public int getTargetRevenueCents() {
        return targetRevenueCents;
    }

    public int getTargetAvgSatisfaction() {
        return targetAvgSatisfaction;
    }

    public Menu getMenu() {
        return menu;
    }
}
