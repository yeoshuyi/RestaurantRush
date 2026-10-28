package rush.model;

import java.util.List;

/**
 * A combo of two existing menu items (Stage 3).
 * Preparation units are the sum of both parts; the price is 90% of their combined
 * price, rounded half up to the nearest cent. Example: Salad + Pasta = $24.30, 3 units.
 * Everything else (Order, Chef, Waiter) treats a combo as an ordinary MenuItem.
 * ComboMeal
 */
public class ComboMeal extends MenuItem {
    private final MenuItem first;
    private final MenuItem second;
 
    public ComboMeal(MenuItem first, MenuItem second) {
        super(first.getName() + "+" + second.getName(),
                priceOf(first, second),
                first.getPrepUnits() + second.getPrepUnits());
        this.first = first;
        this.second = second;
    }
 
    /** 90% of the combined price in integer cents, rounded half up. */
    public static int priceOf(MenuItem first, MenuItem second) {
        return ((first.getPriceCents() + second.getPriceCents()) * 90 + 50) / 100;
    }

    public List<MenuItem> getComponents() {
        return List.of(first, second);
    }
}