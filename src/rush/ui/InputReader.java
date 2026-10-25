package rush.ui;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;

/** Read user inputs */
public class InputReader {

    private final BufferedReader in;
    private final PrintStream out;
    private final boolean echo;

    /** Constructor takes in streams, echo for debug */
    public InputReader(InputStream in, PrintStream out, boolean echo) {
        this.in = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
        this.out = out;
        this.echo = echo;
    }

    /** Default constructor using sys console */
    public InputReader() {
        this(System.in, System.out, false);
    }

    /** Ask users for int input within min to max */
    public int readInt(String prompt, int min, int max) {
        if (min > max) {
            throw new IllegalArgumentException("min " + min + " is greater than max " + max);
        }
        while (true) {
            String line = readNextLine(prompt + " [" + min + "-" + max + "]: ");
            int value;
            try {
                value = Integer.parseInt(line);
            } catch (NumberFormatException e) {
                out.println("  '" + line + "' is not a whole number. Enter a number from " + min + " to " + max + ".");
                continue;
            }
            if (value < min || value > max) {
                out.println("  " + value + " is out of range. Enter a number from " + min + " to " + max + ".");
                continue;
            }
            return value;
        }
    }

    /** Ask users for yes/no input */
    public boolean readYesNo(String prompt) {
        while (true) {
            String line = readNextLine(prompt + " [y/n]: ").toLowerCase();
            switch (line) {
                case "y": case "yes": case "1":
                    return true;
                case "n": case "no": case "0":
                    return false;
                default:
                    out.println("  '" + line + "' is not a yes/no answer. Enter y or n.");
            }
        }
    }

    /** Ask user for string input */
    private String readNextLine(String prompt) {
        out.print(prompt);
        out.flush();
        try {
            String line;
            while ((line = in.readLine()) != null) {
                
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) {
                    //out.print(prompt);
                    out.flush();
                    continue;
                }
                if (echo) {
                    out.println(line);
                }
                return line;
            }
        } catch (IOException e) {
            throw new UncheckedIOException("Could not read input", e);
        }
        out.println();
        throw new InputEndedException();
    }

    /** Thrown when there is no input to read */
    public static class InputEndedException extends RuntimeException {
        public InputEndedException() {
            super("Input ended");
        }
    }
}
