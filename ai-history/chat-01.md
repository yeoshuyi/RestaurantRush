AI Tool: Gemini 

### My prompt

"how to commit new entities. i want branch_name convention to be [type]/[desc] and
message convention
[type]: [desc]
eg.
fix: fixed some function"

### Gemini's Response 

"Here is how to set up your branch and break down the Stage 1 entity implementation into small, frequent, and clean commits matching your team's conventions.

1. Create and Switch to Your Feature Branch
Follow your [type]/[desc] branch convention:
```
git checkout -b feature/model-entities
```

2. Step-by-Step Frequent Commit Plan
Instead of committing everything at once, split the work into logical clusters. This creates a readable Git history for the TA auditing your Stage 1 commit history.

3. Verify Compilation Before Pushing
Before pushing to remote, ensure the entire package compiles without warnings or errors:
```
# Compile all source files
javac -d bin src/rush/model/*.java
```
Once verified, push your branch to GitHub:
```
git push -u origin feature/model-entities
```

Now you can open a Pull Request (PR) titled feat: implement Stage 1 model entities into main (or develop) for your teammates to review."

### My prompt

"i want to do orderstatus, customerstate, actionresult and customer, help me craft meaningful commit messages for each"

### Gemini's Response 

"Here are meaningful commit messages for each file following the [type]: [desc] convention, structured into distinct, frequent commits:

1. OrderStatus.java
Commit Message:
```
git add src/rush/model/OrderStatus.java
git commit -m "feat: add OrderStatus enum for kitchen and delivery lifecycle"
```
Why it's meaningful: Explains that the enum manages customer lifecycle transitions (from waiting in the queue to eating, checkout, or leaving).


2. CustomerState.java
Commit Message:
```
git add src/rush/model/CustomerState.java
git commit -m "feat: define CustomerState enum to track dining room progression"
```
Why it's meaningful: Explains that the enum manages customer lifecycle transitions (from waiting in the queue to eating, checkout, or leaving).


3. ActionResult.java
Commit Message:
```
git add src/rush/model/ActionResult.java
git commit -m "feat: implement ActionResult to support task validation without consuming turns"
```
Why it's meaningful: Directly references a key architectural requirement—handling success/failure feedback while protecting the staff member's turn from being wasted.

4. Customer.java
ommit Message:
```
git add src/rush/model/Customer.java
git commit -m "feat: create abstract Customer entity with satisfaction decay and eating timers"
```
Why it's meaningful: Highlights core domain behaviors (satisfaction loss, deterministic item selection, and eating state management) rather than just saying "added customer class".

Would you like the code implementation details for Customer and RegularCustomer verified against the exact method signatures in the class diagram before you commit them?"

### My prompt

"so can i commit messgae for customer.java with "full turn sequence, customer functions etc."

### Gemini's Response

"You should make it more specific. While "full turn sequence, customer functions etc." describes what you were thinking about, it has two issues for a git commit:

Missing standard type: It does not follow your team's [type]: [desc] convention.

Inaccurate scope: Customer.java does not handle the full turn sequence—the turn sequence is run by GameController / Restaurant. Customer.java only represents the individual customer and their personal state.
Here is how to adjust that exact idea into a proper, meaningful message:

Recommended Commit Messages
Best match to your idea:
```
git commit -m "feat: implement Customer entity with satisfaction decay and dining lifecycle"
```
Focusing on the customer's state machine & rules:
```
git commit -m "feat: add Customer base class tracking service state, item choice, and abandonment"
```
Short and clean:
```
git commit -m "feat: implement Customer state transitions and waiting decay"
```
These clearly tell your teammates and graders that Customer.java is responsible for customer-level logic (satisfaction, state transitions, choosing food, and leaving) without claiming it runs the entire game loop."

### My prompt

"explain the item choice in Customer.java"

### Gemini's Response

"The item choice logic in Customer.java determines what dish a customer orders when the Waiter takes their order. 
In your Stage 1 implementation, the method is defined as:
```
public MenuItem chooseItem(Menu m) {
    return m.get((id - 1) % m.size());
}
```

Here is how and why it works:
1. The Assignment Rule: Deterministic Food SelectionThe project brief sets two strict rules for how food is selected:   The player/manager never chooses the dish. The game must follow a documented deterministic rule or seeded randomness so that teaching assistants (TAs) and automated CI tests can reproduce exact runs.   
2. The Arithmetic Breakdown: (id - 1) % m.size()
In Java, lists are zero-indexed (0, 1, 2), while customer IDs start at 1 (C1, C2, C3, etc.). The standard Stage 1 menu has 3 items:
Index 0: Salad ($9.00, 1 unit)
Index 1: Burger ($15.00, 1 unit)
Index 2: Pasta ($18.00, 2 units)
Here is how the formula maps each of the 6 arrivals to an item:
Customer	id	Math: (id - 1) % 3	Menu Index	Chosen Item
C1	1	$(1 - 1) \pmod 3 = 0 \pmod 3$	0	Salad 
C2	2	$(2 - 1) \pmod 3 = 1 \pmod 3$	1	Burger 
C3	3	$(3 - 1) \pmod 3 = 2 \pmod 3$	2	Pasta 
C4	4	$(4 - 1) \pmod 3 = 0 \pmod 3$	0	Salad 
C5	5	$(5 - 1) \pmod 3 = 1 \pmod 3$	1	Burger 
C6	6	$(6 - 1) \pmod 3 = 2 \pmod 3$	2	Pasta 
The modulo operator % cycles infinitely through Salad $\rightarrow$ Burger $\rightarrow$ Pasta. 

Would you like to see why this matters for OOP?"
