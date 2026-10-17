package rush.model;

public class RegularCustomer extends Customer{
    public RegularCustomer(int id, int arrivalTurn){
        super(id, arrivalTurn);
    }

    @Override
    public int waitPenalty(){
        return 8; // Regular customer penalty
    }

    @Override
    public CustomerType getType(){
        return CustomerType.REGULAR;
    }
}
