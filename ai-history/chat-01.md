AI Tool: Claude 
### Exchange 1
### My prompt
"hi claude, i need your help. I want you to write a script for my presentation on the above based on our thought process, and the assignment brief that I sent you previously. I think it has to be in order according to how we did stage 1, 2 and 3, and the steps we took to reduce errors, etc. I will be sending you the slides that our professor wanted us to follow, which will help build our script."

### Claude's Response 
"Your script is here: https://claude.ai/artifact/KWKzW4NLTTifdaMAHeGs5r .What’s in the script: It follows the briefing’s 15-minute split: overview, demo, diagrams and evidence, the use case and sequence diagram, and individual contributions.
Inside the diagram section it goes stage 1, then 2, then 3. It also covers how you reduced errors: scripted runs, the Python checks, CI, branch and PR review, and the tags. It ends with a timestamp table for your README."

### Exchange 2
### My prompt
"I’m presenting my individual contribution and reflection for our SC2002 group project, Restaurant Rush. Image 1 shows my teammates’ slides, which I want you to match for format and design: a small label line with the speaker’s name and role, a large headline, a “Key lesson” box, a code or evidence box, and a “Hardest part” or “How I applied it” box. Image 2 is the briefing’s reflection slide. Please create slides about my own work that answer its four questions:
What did I learn? A specific gain in knowledge or skill.
How did I apply it? Connect a course concept to a real project decision.
What challenged me? The hardest part and why it was difficult.
How did I solve it? My attempts, my solution, and what I learned.
Support each point with examples from my own work. My work was [ComboMeal, HappyHour and Host in Stage 3, customerfactory, waitertask and gamecontroller in Stage 1, tests/stage2/victory.txt and defeat.txt for stage 2 and the Stage 2 and 3 README comparisons]. Make it 2-3 slides that I can present in about under 1 minute. Before you start, tell me what other information you need, such as code snippets or results. Also something that challenged me was integrating my work 
with my groupmates' as our method names did not match and it took me awhile to find the problem. Please help to rephrase that as well." 

### Claude's Response 
"Your slide deck is ready as a 3-page PDF, Felicia_Individual_Reflection_Slides.pdf. It copies your teammate’s design: beige background, orange label line, serif headline, dark code box on the left, and the lesson, mini-code and “hardest part” boxes on the right.
What’s on the slides
Slide	Headline	Covers
1	A combo is just a menu item	Learned and applied: your real ComboMeal.java. Because ComboMeal extends MenuItem and Host extends Staff, Order, Chef and Waiter needed no changes. This is the Liskov substitution principle.
2	Parallel work has to line up	Challenged and solved: your real HappyHour.java. Teammates called host.resetTurn(), happyHour.applyTo() and HappyHour.RECOVERY before your classes had those names. You fixed it by reading the compiler errors, renaming, and recompiling with javac -sourcepath src.
3	Tests keep earlier stages safe	Evidence: the Stage 2 victory and defeat scripts, CI (12 checks failing on the README PR, 18 passing on the test-files PR), the README comparisons, and learning Git.

The label line names all your work: Stage 1 CustomerFactory, WaiterTask and GameController, the Stage 2 tests and README, and the Stage 3 ComboMeal, HappyHour and Host. The slides are about 20 seconds each. The bottom-right corner is left clear for your webcam, as on your teammates’ slides."
