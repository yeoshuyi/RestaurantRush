package rush;

import java.io.InputStream;
import java.io.PrintStream;
import java.util.Arrays;

import rush.control.GameConfig;
import rush.control.GameController;
import rush.ui.ConsoleUI;
import rush.ui.InputReader;

/** Entry Point, --echo flag for debugging */
public class Main {

    public static void main(String[] args) {
        boolean echo = Arrays.asList(args).contains("--echo");
        play(System.in, System.out, echo);
    }

    public static void play(InputStream in, PrintStream out, boolean echo) {
        out.println("RestaurantRush");
        ConsoleUI ui = new ConsoleUI(new InputReader(in, out, echo), out);
        try {
            new GameController(GameConfig.baseSetting(), ui).run();
        } catch (InputReader.InputEndedException e) {
            out.println("Error: " + e);
        }
        out.flush();
    }
}
