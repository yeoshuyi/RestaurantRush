package rush.model;

public class ComboMeal {
    private static final int COMBO_PERCENT = 90;
 
    private final String name;
    private final MenuItem first;
    private final MenuItem second;
 
    public ComboMeal(String name, MenuItem first, MenuItem second) {
        if (first == null || second == null) {
            throw new IllegalArgumentException("A combo needs two menu items");
        }
        this.name = name;
        this.first = first;
        this.second = second;
    }
 
    public String getName() {
        return name;
    }
 
    public MenuItem getFirst() {
        return first;
    }
 
    public MenuItem getSecond() {
        return second;
    }
 
    /** Preparation units = sum of the two components. */
    public int getPrepUnits() {
        return first.getPrepUnits() + second.getPrepUnits();
    }
 
    /** 90% of the combined price, half-up to the nearest cent. */
    public int getPriceCents() {
        int combined = first.getPriceCents() + second.getPriceCents();
        return (combined * COMBO_PERCENT + 50) / 100;
    }
 
    @Override
    public String toString() {
        return name + " (" + first.getName() + " + " + second.getName() + ")";
    }
}
