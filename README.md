# Restaurant Rush

A turn-based command-line restaurant simulation game built in Java following the Model-View-Controller (MVC) architecture.

* **Repository:** [https://github.com/yeoshuyi/RestaurantRush](https://github.com/yeoshuyi/RestaurantRush)
* **Release:** Stage 1 (`stage-1`)

---

## 1. Directory Structure

```text
RestaurantRush/
├── README.md           # Project documentation and instructions
├── CONTRIBUTING.md     # Guidelines for team contributions
├── run.sh              # Build and execution script (macOS/Linux)
├── run.bat             # Build and execution script (Windows)
├── src/
│   └── rush/
│       ├── Main.java   # Application entry point
│       ├── ui/         # Console input, display formatting, and view bridge
│       ├── game/       # Game controller, turn loop, config, and statistics
│       └── model/      # Core entities (Restaurant, Customer, Staff, Order, Table)
└── docs/               # System architecture and UML design diagrams
