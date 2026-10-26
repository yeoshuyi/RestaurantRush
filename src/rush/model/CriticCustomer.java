package rush.model;

import java.util.Comparator;

/**
 * Critic customer:
 * Satisfaction loss - 12 per waiting turn
 * Pays full price
 * Special behaviour - always orders the most demanding dish on the menu
 * (most preparation units, ties broken by the higher price), e.g. Pasta.
 */

public class CriticCustomer extends Customer {
    public CriticCustomer(int id, int arrivalTurn) {
        super(id, arrivalTurn);
    }

    @Override
    public int waitPenalty() {
        return 12;
    }

    @Override
    public MenuItem chooseItem(Menu m) {
        return m.getItems().stream()
                .max(Comparator.comparingInt(MenuItem::getPrepUnits)
                        .thenComparingInt(MenuItem::getPriceCents))
                .orElseThrow();
    }

    @Override
    public CustomerType getType() {
        return CustomerType.CRITIC;
    }
}
