package rush.model;

//A menu item. Subclasses may derive price and prep units from other items.
public class MenuItem {

    private final String name;
    private final int priceCents;
    private final int prepUnits;

    public MenuItem(String name, int priceCents, int prepUnits) {
        if (priceCents < 0 || prepUnits < 1) {
            throw new IllegalArgumentException("Invalid menu item " + name);
        }
        this.name = name;
        this.priceCents = priceCents;
        this.prepUnits = prepUnits;
    }

    public String getName() {
        return name;
    }

    public int getPriceCents() {
        return priceCents;
    }

    public int getPrepUnits() {
        return prepUnits;
    }
}
