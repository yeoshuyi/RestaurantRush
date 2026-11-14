AI Tool: Claude 
### Exchange 1

### My prompt

"hi claude, i need your help. I want you to write a script for my presentation based on the class diagrams and sequence diagram, and the assignment brief. It should be in order according to how we did stage 1, 2 and 3, and the steps we took to reduce errors, etc. Please write the script to be around 15 mins long with clear segregations for 5 group members, thanks"

### Claude's Response 

"Here’s the script. I’ve followed the briefing’s suggested split (2 / 4 / 4 / 3 / 2 minutes) and assumed about 130 spoken words per minute, so it should land at roughly 15 minutes. I haven’t seen your code, so anything in [brackets] is a placeholder or a detail to confirm. I put you as Member 5, since the sequence diagram section is yours, but you can swap members around.

Part 1: Game overview and the three stages

Member 1 · 0:00 to 2:00
[On screen: title slide, then the Stage 1 / 2 / 3 timeline]

Hello everyone, we’re Group [X], and this is our presentation for SC2002 Restaurant Rush.

Restaurant Rush is a turn-based Java command-line game. You play the restaurant manager, and over 18 turns you direct your staff to seat customers, take orders, cook, serve and collect payment. To win, you must meet three targets: at least four customers paid, at least 45 dollars in revenue, and an average satisfaction of at least 60.

The brief asks us to build the game in three stages, and to work as if each new set of requirements arrives only after the previous stage is finished. So that’s what we did. In Stage 1 we built a complete baseline game with Regular customers, plus a Waiter, a Chef and a Cashier. In Stage 2 we extended the saved Stage 1 version with VIP and Critic customers. In Stage 3 we extended Stage 2 again, adding a Host, combo meals and a Happy Hour that the manager can trigger. Each stage is saved as a runnable commit, tagged stage-1, stage-2 and stage-3, so you can run any of them.

Throughout, we organised our code into three layers: Boundary for the console and input, Control for turn flow and staff actions, and Entity for the domain model. You’ll see this colour-coding in all our class diagrams.

Here’s how the next 13 minutes will go. First, a gameplay demo. Then our class diagrams and the evidence of how each stage changed the design. Then a sequence diagram of one complex use case. Finally, each of us will share our own contribution and learning. Over to [Member 2] for the demo.

Part 2: Gameplay demo, Stage 1 and Stage 2

Member 2 · 2:00 to 4:00
[On screen: screen recording of the console game]

Thanks, [Member 1]. I’ll start with Stage 1.

Each turn begins with a turn header and the restaurant’s state: the tables, the waiting queue and the current stats. Customers arrive according to a fixed schedule, join the queue, and start losing satisfaction the longer they wait.

As the manager, you give each staff member one action per turn. Here the waiter menu offers four choices: Wait, Seat, Take order or Serve. I’ll pick Seat, and the waiter seats the first customer at a free table. Next turn I choose Take order, and the customer picks a dish. The Chef then prepares it, one unit of preparation per turn. Once it’s ready, the Waiter serves it. The customer eats, becomes ready to pay on a later turn, and the Cashier collects payment, which frees the table.

You can see that if I pick something invalid, the game shows an error and lets me choose again instead of crashing.

Now Stage 2. Here, two new customer types arrive: a Critic on turn 4 and a VIP on turn 7. The Critic loses 12 satisfaction per waiting turn and always orders the most demanding dish on the menu. The VIP loses only 5 per turn and gets a 10 percent discount. As you can see, the menus and prompts are exactly the same as in Stage 1. The customers just behave differently, and that’s something [Member 4] will explain when we reach the class diagrams.

Now [Member 3] will show Stage 3.

Part 3: Gameplay demo, Stage 3 and results

Member 3 · 4:00 to 6:00
[On screen: screen recording of Stage 3, then the result screen]

Thanks, [Member 2]. In Stage 3 there are three new features.

First, the Host. Now, instead of only the Waiter, the Host also seats customers. You can see a new Host prompt each turn, and the manager chooses which waiting customer to seat. The Waiter can still seat people, so the Host frees the Waiter up for taking orders and serving.

Second, combo meals. A combo bundles two menu items into one priced item, like this Burger plus Pasta combo at 29 dollars 70. It takes more preparation units, so it ties up the Chef for longer, which is exactly why the Critic loves it.

Third, Happy Hour. At the start of a turn, the manager gets a one-time prompt: start Happy Hour or not. If I choose yes, it lasts two turns. Every waiting or ordered customer who isn’t at full satisfaction recovers 15 points each turn, and new orders get 20 percent off. So it’s a real trade-off: you give up some revenue to buy back satisfaction. I’ll show a concrete example in the sequence diagram later.

At the end of turn 18, the game checks all three targets and prints a result. Each target is marked as met or missed, so you can see exactly why you won or lost. Here’s one winning run and one losing run [adjust to the runs you recorded].

Now [Member 4] will walk through our class diagrams.

Part 4: Class diagrams and evidence of change

Member 4 · 6:00 to 10:00
[On screen: Stage 1 class diagram, then Stage 2, then Stage 3, with the added and modified classes highlighted]

Thanks, [Member 3]. The brief asks us three things for each stage: what we added, what we modified, and what still works.

Stage 1. Our Stage 1 diagram has the three lanes: Boundary, Control and Entity. Main starts the game, and GameController runs the 18-turn loop. It talks to the UI only through the GameView interface, so ConsoleUI could be replaced without touching the game logic. The Restaurant class owns the tables, the waiting queue and the staff, which is composition. Staff is an abstract class with one shared perform method, which makes sure each staff member acts only once per turn. Every action returns an ActionResult, either ok or fail, so a bad choice becomes a message and a re-prompt rather than an exception.

We also built in two design principles early. First is encapsulation: the seat method on Restaurant is package-private, so staff must go through it. Second is polymorphism: Customer is abstract, with waitPenalty and getType left for subclasses, so GameController never checks a customer’s type.

Stage 2. When Stage 2 arrived, we added just two new classes: VIPCustomer and CriticCustomer. Each overrides only what is different: VIP overrides waitPenalty and computeBill, and Critic overrides waitPenalty and chooseItem. We modified the CustomerType enum by adding two constants, and the arrival schedule in the game configuration. Everything else stayed the same: GameController, Restaurant, ConsoleUI and the staff classes did not change at all. That’s the clearest evidence that the Stage 1 design was open for extension. And line count alone would undersell this, because what matters is that no existing control logic had to learn about the new types.

Stage 3. Stage 3 was a bigger change, because the features cut across several layers. We added three classes: Host, ComboMeal and HappyHour. We modified Restaurant, which now owns a Host and a HappyHour, applies Happy Hour recovery, and prices bills through quoteBill. We modified Customer by adding a recover method. We modified GameController by adding happyHourStart and hostChoice to the turn loop. We modified GameView and ConsoleUI by adding the Happy Hour and Host prompts. Even so, the customer subclasses, the Chef, the Cashier and the Waiter were untouched. One design note: quoteBill applies the VIP discount first, then the Happy Hour discount, and we documented that order on the diagram so everyone calculates prices the same way.

How we reduced errors. First, we built the stages in order and tagged a stage only after its tests and README were merged. Second, every class was written on its own branch and reviewed by a teammate through a pull request. Third, for each stage we ran the game with scripted input files, including a victory run and a defeat run, so we could check that earlier behaviour still works and still produces the same results. Finally, we compared each class diagram against the code, because the brief requires each diagram to match the stage it describes.

Now [Member 5] will take us through the sequence diagram.

Part 5: Sequence diagram

Member 5 (Felicia) · 10:00 to 13:00
[On screen: Stage 3 sequence diagram, scrolling through the turns]

Thanks, [Member 4]. For our sequence diagram we chose a Stage 3 use case: the life of one customer, Customer 1, when the manager chooses to start Happy Hour. The starting condition is turn 1: Customer 1, a Regular, is about to arrive, and Happy Hour hasn’t been used. The outcome is that Customer 1 pays 7 dollars 20 at satisfaction 100, whereas without Happy Hour they would have paid 9 dollars at satisfaction 92.

Turn 1. The Manager runs the game through Main, and GameController starts the loop. Each turn, GameController resets the staff, tells the ConsoleUI to show the header, and handles arrivals. It asks GameConfig whether someone arrives; this returns an Optional, so there’s an optional block guarded by “arrival present”. Then CustomerFactory creates the customer through CustomerType, and Customer 1 is admitted to the queue.

Next is the Happy Hour decision. GameController asks HappyHour whether it can activate, and only if so does the UI prompt the manager. This is an alternative fragment: if the manager chooses 1, Happy Hour activates with two turns left. If the manager chooses 0, nothing changes. Then Restaurant applies recovery, but Customer 1 is still at 100, so nothing happens.

Then come the staff steps. The Host seats Customer 1 at table 1, guarded by checks that the customer is waiting and that a table is free. The Waiter takes the order, which is a loop that continues until a task is used. Customer 1 picks a Salad at 9 dollars, Restaurant asks for a quote, the Regular price stays at 900 cents, and HappyHour applies 20 percent off to get 720. An Order is created with that price locked. The Chef prepares it, and it’s ready. At the end of the turn, Customer 1 is still waiting for service and loses 8 satisfaction, dropping to 92.

Turn 2. Happy Hour recovers 15 points, so Customer 1 goes back to 100. The Waiter serves the order. Notice the guard that the order was ready on an earlier turn, not the same one.

Turn 3. Customer 1 finishes eating and becomes ready to pay, but there is no payment yet, because payment needs a later turn.

Turn 4. The Cashier collects payment: Customer 1 pays, the table is freed, and GameStats records 720 cents at satisfaction 100. This is where the manager’s choice shows up: they gave up 1 dollar 80 of revenue for 8 more points of satisfaction. A Critic also arrives this turn, but too late for the discount, because the price is locked at order time.

Turns 5 to 18 repeat the same pattern, shown as a reference fragment. After turn 18, GameStats evaluates the three targets, creates a GameResult, and the UI shows a victory or defeat.

To verify this diagram, I traced the actual game run turn by turn and compared the messages, guards and numbers against both the code and the Stage 3 class diagram [adjust to what you actually did].

Part 6: Individual contributions and key learning

All members · 13:00 to 15:00 (about 25 seconds each)

Member 1: I worked on [your classes/tasks]. My main learning was [one specific skill or concept], which I applied when [one project decision].

Member 2: I worked on [your classes/tasks]. The hardest part was [challenge], and I solved it by [solution].

Member 3: I worked on [your classes/tasks]. I learned [specific gain], and it changed how I [decision or habit].

Member 4: I worked on [your classes/tasks]. My biggest takeaway was how [a concept, such as polymorphism] let Stage 2 happen without touching existing code.

Member 5 (Felicia): I wrote GameController, ConsoleUI, CustomerFactory, WaiterTask and Main in Stage 1, the Stage 1 to Stage 2 README comparison, the Host, ComboMeal and HappyHour classes in Stage 3, and the Stage 3 sequence diagram. The hardest part was making the diagram match the code exactly, which I solved by tracing a real run. [Add one sentence on your key learning.]

Member 1 (closing): Thank you for watching. The README has our GitHub links, every member’s AI history and timestamps for this video.

Notes
Timing: that’s about 1,950 spoken words. Do a timed read-through, since Part 4 is the densest. Cut a sentence from the Stage 3 paragraph first if it runs long.
Please verify the details I inferred from the diagrams and your project history, such as the 15-point recovery, the scripted-input victory and defeat runs, and the exact ConsoleUI prompts, against your final code and recording.
README timestamps: the briefing asks for these, so note the start time of each part once you’ve recorded.

I can also put this into a Claude Doc or Word file so it’s easier to share with your group."

### My Response
"can you put this into a word document?"

### Claude's Response
* converted it to a word document 

### Exchange 2

### My prompt

"I’m presenting my individual contribution and reflection for our SC2002 group project, Restaurant Rush. Image 1 shows my teammates’ slides, which I want you to match for format and design: a small label line with the speaker’s name and role, a large headline, a “Key lesson” box, a code or evidence box, and a “Hardest part” or “How I applied it” box. Image 2 is the briefing’s reflection slide. Please create slides about my own work that answer its four questions:

1. What did I learn? A specific gain in knowledge or skill.
2. How did I apply it? Connect a course concept to a real project decision.
3. What challenged me? The hardest part and why it was difficult.
4. How did I solve it? My attempts, my solution, and what I learned.

Support each point with examples from my own work. My work was [ComboMeal, HappyHour and Host in Stage 3, customerfactory, waitertask and gamecontroller in Stage 1, tests/stage2/victory.txt and defeat.txt for stage 2 and the Stage 2 and 3 README comparisons]. Make it 2-3 slides that I can present in about under 1 minute. Before you start, tell me what other information you need, such as code snippets or results. Something that challenged me was integrating my work with my groupmates' as our method names did not match and it took me awhile to find the problem. To prove nothing broke, I also added the Stage 2 victory and defeat scripts. CI on GitHub failed on my README pull request until they were merged, and then all 18 checks passed. Another challenge was learning Git, because branches, pull requests and tags were all new to me. Include this in my third slide." 

### Claude's Response 

"Before I build, here's what I need. Only one image came through, your teammates' slides. I can match their layout from that, and I'm working from your four questions as you wrote them, so you don't need to resend the briefing slide unless it has extra wording or a marking rubric.

**Code and evidence (one short snippet or fact per slide)**
1. **ComboMeal, HappyHour or Host:** the snippet you're proudest of, about 8 to 12 lines, like Amanda's `recover()` example. Which one best shows a course concept such as encapsulation, inheritance, polymorphism or a design principle?
2. **The method-name mismatch:** the actual names that didn't match, for example `getX()` in your code against `retrieveX()` in theirs. Also what the error looked like and how you found it (compiler error, a failing run, or reading their code).
3. **CustomerFactory, WaiterTask or GameController from Stage 1:** was a name from this one changed to fix the mismatch? If so, which?
4. **Victory and defeat scripts:** roughly what each one does, and what the CI output or terminal showed when it passed.
5. **CI failure:** what caused the failed check on your README PR (a missing script, or the Stage 2 files not yet being merged), and how you resolved it.
6. **README comparisons:** one concrete difference between Stages 2 and 3 that you wrote up, if it's useful as a number or fact.

**Reflection details**
7. **Git:** one specific moment where it clicked or went wrong, such as a branch conflict, tag confusion or a PR review comment.
8. **What you'd do differently:** one line, for example agreeing on method names in an interface or naming doc before coding.

**Format**
9. Do you want a PowerPoint file, or an editable slide-deck artifact I can build here? I'll match their style either way: small label line, serif headline, dark code box, "Key lesson" box and "Hardest part" or "How I applied it" box.

**Timing:** under a minute across 3 slides is about 20 seconds each, or roughly 130 to 150 spoken words in total. My plan is Slide 1 for what you learned and how you applied it, Slide 2 for the integration challenge and how you solved it, and Slide 3 for Git, CI and the Stage 2 proof scripts. I'll keep each slide's text short and give you a speaking line for each.

If you don't have some of these to hand, send what you have and I'll build around it. Real snippets are better than ones I invent, so I'll leave placeholders rather than fabricate code."

### My prompt 

"My teammate's `Restaurant` and `GameConfig` called `host.resetTurn()`, `happyHour.applyTo()` and `HappyHour.RECOVERY`, and my classes didn’t match. I also got `cannot find symbol` errors for `WaitingQueue` and `Table` when compiling `Host` on its own. The terminal wasn’t inside the repo (“not a git repository”), and files seemed to vanish when I switched branches. CI failures. 12 checks failed on your README PR until the Stage 2 test scripts were merged. On the test-files PR, all 18 checks passed. "This is my repo's code for Combomeal.java "package rush.model;
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
}" and this is the code for HappyHour.applyTo()"package rush.model;
/**
 * Happy Hour pricing policy (Stage 3). The manager may start it once per game at the
 * start of a turn; it lasts that turn and the next. While active, orders taken get 20% off
 * (after any customer discount) and customers still waiting recover satisfaction at turn start.
 */
public class HappyHour {
    public static final int DURATION = 2;
    public static final int RECOVERY = 15;
    private boolean used;
    private int turnsLeft;
    public boolean canActivate() {
        return !used;
    }
    /** Start Happy Hour now. Returns false if it was already used this game. */
    public boolean activate() {
        if (used) {
            return false;
        }
        used = true;
        turnsLeft = DURATION;
        return true;
    }
    public boolean isActive() {
        return turnsLeft > 0;
    }
    public boolean isUsed() {
        return used;
    }
    /** Active turns left, counting the current one. */
    public int getTurnsLeft() {
        return turnsLeft;
    }
    /** 20% off rounded half up to the cent while active; unchanged otherwise. */
    public int applyTo(int cents) {
        return isActive() ? (cents * 80 + 50) / 100 : cents;
    }
    /** Called once at the end of every turn. */
    public void endTurn() {
        if (turnsLeft > 0) {
            turnsLeft--;
        }
    }
}" I have attached a clearer screenshot of the design above, and I would like a downloadable pdf for the slide deck. also can I clarify what the CI means in your message above?" this is my code. I fixed the CI failure by reading the compiler errors, renaming, and recompiling with `javac -sourcepath src`. Please give me the slides in pdf"

### Claude's Response

"I’m checking the slide previews. Slide 1’s code box cuts off the last closing brace, so I’m fixing that and then checking slides 2 and 3.

Your 3-slide PDF, Felicia_SC2002_Reflection.pdf, matches your teammates’ design: label line, serif headline, dark code box, Key lesson box, and a Hardest part or How I applied it box. I kept the bottom-right corner clear for your webcam bubble.

What CI means: CI is continuous integration. Each time you open a pull request, GitHub automatically compiles the project and runs the project’s test scripts. Each automated check is one of those runs. Your README PR showed 12 failed checks because the Stage 2 victory and defeat scripts weren’t merged yet. On the test-files PR, all 18 passed. That is why I framed your scripts as proof that nothing broke.

Speaking lines (about 135 words, roughly 20 seconds per slide):

“For ComboMeal, I learned to extend an existing class instead of rewriting it. Because it extends MenuItem, Order, Chef and Waiter needed no changes. I applied encapsulation the same way in HappyHour, where callers just use applyTo.”
“My hardest part was integrating with my teammates. Their code called host.resetTurn(), happyHour.applyTo() and HappyHour.RECOVERY, and my names didn’t match. It took me a while to find, but I read each compiler error, renamed, and recompiled with javac -sourcepath src.”
“To prove nothing broke, I added the Stage 2 victory and defeat scripts. CI failed my README PR with 12 failed checks until they merged, then all 18 passed. Git was also new to me: branches, pull requests and tags.”

Please check these before presenting:

Host path: the slide 2 command assumes src/rush/model/Host.java, based on your package name. Change it if your path differs.
Branch name: the slide 3 command uses readme-stage2, the branch name you gave earlier.
Git fix: you told me the Git problems but not how you fixed them, so I didn’t invent a fix. If you have one, add one line to slide 3.
Lessons: the “Next time” style takeaways are my wording, so edit anything that doesn’t sound like you."

### My Prompt 
"hm, can the titles for the respective 3 slides be changed to be shorter? maybe slide 1 can be " a combo is just a menu item" and 2nd slide since its about integrating w my teammates slides the title can be " Parallen work has to line up" and the third slide can be "Tests keep earlier stages safe" Also i would like to apply the Liskov substituition principle in my first slide, and explain that the principle is a subtype that can stand in for its parent, so combos plug in as ordinary menu items. also, can you include the code for HappyHour.java in the second slide "public class HappyHour {
    public static final int DURATION = 2;
    public static final int RECOVERY = 15;

    private boolean used;
    private int turnsLeft;

    public boolean canActivate() {
        return !used;
    }

    /** Start Happy Hour now. Returns false if it was already used this game. */
    public boolean activate() {
        if (used) {
            return false;
        }
        used = true;
        turnsLeft = DURATION;
        return true;
    }

    public boolean isActive() {
        return turnsLeft > 0;
    }

    public boolean isUsed() {
        return used;
    }

    /** Active turns left, counting the current one. */
    public int getTurnsLeft() {
        return turnsLeft;
    }

    /** 20% off rounded half up to the cent while active; unchanged otherwise. */
    public int applyTo(int cents) {
        return isActive() ? (cents * 80 + 50) / 100 : cents;
    }

    /** Called once at the end of every turn. */
    public void endTurn() {
        if (turnsLeft > 0) {
            turnsLeft--;
        }
    }
}" and instead of "key lesson", replace it with "What I learned" for slide 1 and 3, and "What challenged me" for slide 2. Replace "Hardest Part" in slide 2 to be "How I solved it" instead, thanks"

### Claude's Response

"I’ve updated Felicia_SC2002_Reflection.pdf with your changes.

Titles: the three titles are now “A combo is just a menu item”, “Parallel work has to line up” and “Tests keep earlier stages safe”. I corrected “Parallen” to “Parallel” in your second title.
Slide 1: “What I learned” is now Liskov substitution: “A subtype can stand in for its parent, so combos plug in as ordinary menu items.” Under “How I applied it” I put that Order, Chef and Waiter take a MenuItem, so Stage 3 needed no changes to them.
Slide 2: the code box now shows HappyHour.java, with RECOVERY and applyTo highlighted because your teammates’ code calls them. The right side is “What challenged me” (the names that didn’t match your teammates’ calls, plus the cannot find symbol errors) and “How I solved it” (read each error, rename, recompile with javac -sourcepath src).
Slide 3: “Key lesson” is now “What I learned”. I left “Hardest part” as it was, since you only asked to change it on slide 2.

To make HappyHour fit in two columns, I left out the Javadoc comments. The code itself is unchanged, and the font is smaller than on the other slides (11px), so check it’s readable on your recording.

“Next time I’ll agree names first” is my wording of the lesson, so edit it if it doesn’t sound like you.

Suggested speaking lines (about 20 seconds each):

“My ComboMeal taught me the Liskov substitution principle: a subtype can stand in for its parent. Because ComboMeal extends MenuItem, Order, Chef and Waiter needed no changes.”
“Working in parallel meant my names had to line up with my teammates’ code. Their code called happyHour.applyTo() and HappyHour.RECOVERY, and mine didn’t match. I read each compiler error, renamed, and recompiled with javac -sourcepath src.”
“To prove nothing broke, I added the Stage 2 victory and defeat scripts. CI failed my README PR with 12 failed checks until they merged, then all 18 passed. Git was also new to me: branches, pull requests and tags."
