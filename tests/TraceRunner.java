import com.sun.jdi.*;
import com.sun.jdi.connect.Connector;
import com.sun.jdi.connect.LaunchingConnector;
import com.sun.jdi.event.*;
import com.sun.jdi.request.*;

import javax.tools.JavaCompiler;
import javax.tools.ToolProvider;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.stream.*;

/**
 * Trace-logging wrapper for rush.Main.
 *
 * Compiles src/ into out/trace, launches rush.Main in a debuggee JVM via JDI, feeds it the
 * given input script on stdin, and logs every method entry/exit (with arguments and return
 * values) and every exception thrown inside the rush.* packages. Game output is interleaved
 * into the same log, prefixed with "OUT|".
 *
 * Usage (from repo root, JDK 17+):
 *   java tests/TraceRunner.java [script] [logfile]
 * Defaults: tests/stage3/victory.txt -> tests/stage3/victory.trace.log
 */
public class TraceRunner {

    private static PrintWriter log;
    private static final Map<ThreadReference, Integer> depth = new HashMap<>();

    public static void main(String[] args) throws Exception {
        Path script = Paths.get(args.length > 0 ? args[0] : "tests/stage3/victory.txt");
        Path logFile = Paths.get(args.length > 1 ? args[1]
                : script.toString().replaceFirst("\\.txt$", "") + ".trace.log");
        Path classes = Paths.get("out", "trace");

        compile(Paths.get("src"), classes);

        LaunchingConnector connector = Bootstrap.virtualMachineManager().defaultConnector();
        Map<String, Connector.Argument> cargs = connector.defaultArguments();
        cargs.get("main").setValue("rush.Main");
        cargs.get("options").setValue("-cp " + classes.toAbsolutePath());
        VirtualMachine vm = connector.launch(cargs);

        log = new PrintWriter(Files.newBufferedWriter(logFile), true);
        log.println("# trace of rush.Main < " + script);

        Process proc = vm.process();
        Thread feeder = new Thread(() -> {
            try (OutputStream stdin = proc.getOutputStream()) {
                Files.copy(script, stdin);
            } catch (IOException ignored) {
                // debuggee exited before consuming all input
            }
        });
        Thread outPump = pump(proc.getInputStream(), "OUT| ");
        Thread errPump = pump(proc.getErrorStream(), "ERR| ");

        EventRequestManager erm = vm.eventRequestManager();

        MethodEntryRequest entry = erm.createMethodEntryRequest();
        entry.addClassFilter("rush.*");
        entry.setSuspendPolicy(EventRequest.SUSPEND_EVENT_THREAD);
        entry.enable();

        MethodExitRequest exit = erm.createMethodExitRequest();
        exit.addClassFilter("rush.*");
        exit.setSuspendPolicy(EventRequest.SUSPEND_EVENT_THREAD);
        exit.enable();

        ExceptionRequest exc = erm.createExceptionRequest(null, true, true);
        exc.addClassFilter("rush.*");
        exc.setSuspendPolicy(EventRequest.SUSPEND_EVENT_THREAD);
        exc.enable();

        feeder.start();
        outPump.start();
        errPump.start();

        long events = 0;
        boolean running = true;
        while (running) {
            EventSet set = vm.eventQueue().remove();
            for (Event ev : set) {
                if (ev instanceof MethodEntryEvent e) {
                    onEntry(e);
                    events++;
                } else if (ev instanceof MethodExitEvent e) {
                    onExit(e);
                    events++;
                } else if (ev instanceof ExceptionEvent e) {
                    onException(e);
                } else if (ev instanceof VMDisconnectEvent) {
                    running = false;
                }
            }
            set.resume();
        }

        outPump.join();
        errPump.join();
        int code = proc.waitFor();
        synchronized (log) {
            log.println("# exit code " + code + ", " + events + " method events");
        }
        log.close();
        System.out.println("Trace written to " + logFile + " (" + events + " method events)");
    }

    private static void compile(Path src, Path dest) throws IOException {
        JavaCompiler javac = ToolProvider.getSystemJavaCompiler();
        Files.createDirectories(dest);
        List<String> argv = new ArrayList<>(List.of("-g", "-d", dest.toString()));
        try (Stream<Path> files = Files.walk(src)) {
            files.filter(p -> p.toString().endsWith(".java")).forEach(p -> argv.add(p.toString()));
        }
        if (javac.run(null, null, null, argv.toArray(new String[0])) != 0) {
            throw new IllegalStateException("compilation failed");
        }
    }

    private static Thread pump(InputStream in, String prefix) {
        return new Thread(() -> {
            try (BufferedReader r = new BufferedReader(new InputStreamReader(in))) {
                String line;
                while ((line = r.readLine()) != null) {
                    synchronized (log) {
                        log.println(prefix + line);
                    }
                }
            } catch (IOException ignored) {
                // stream closed on VM exit
            }
        });
    }

    private static void onEntry(MethodEntryEvent e) {
        ThreadReference t = e.thread();
        int d = depth.merge(t, 1, Integer::sum) - 1;
        String argStr;
        try {
            argStr = t.frame(0).getArgumentValues().stream()
                    .map(TraceRunner::fmt).collect(Collectors.joining(", "));
        } catch (Exception ex) {
            argStr = "?";
        }
        write(d, "-> " + sig(e.method()) + "(" + argStr + ")");
    }

    private static void onExit(MethodExitEvent e) {
        ThreadReference t = e.thread();
        int d = depth.merge(t, -1, Integer::sum);
        String ret = e.method().returnTypeName().equals("void") ? "" : " = " + fmt(e.returnValue());
        write(d, "<- " + sig(e.method()) + ret);
    }

    private static void onException(ExceptionEvent e) {
        int d = depth.getOrDefault(e.thread(), 0);
        String where = e.location().declaringType().name() + ":" + e.location().lineNumber();
        String caught = e.catchLocation() == null ? "uncaught"
                : "caught at " + e.catchLocation().declaringType().name() + ":" + e.catchLocation().lineNumber();
        write(d, "!! " + e.exception().referenceType().name() + " thrown at " + where + " (" + caught + ")");
    }

    private static void write(int d, String msg) {
        synchronized (log) {
            log.println("    ".repeat(Math.max(d, 0)) + msg);
        }
    }

    private static String sig(Method m) {
        String cls = m.declaringType().name().replaceFirst("^rush\\.", "");
        return cls + "." + m.name();
    }

    private static String fmt(Value v) {
        if (v == null) return "null";
        if (v instanceof StringReference s) return '"' + s.value() + '"';
        if (v instanceof PrimitiveValue) return v.toString();
        ObjectReference o = (ObjectReference) v;
        ReferenceType type = o.referenceType();
        String simple = type.name().substring(type.name().lastIndexOf('.') + 1);
        if (type instanceof ClassType ct && ct.isEnum()) {
            Field name = ct.fieldByName("name");
            if (name != null && o.getValue(name) instanceof StringReference s) {
                return simple + "." + s.value();
            }
        }
        return simple + "@" + o.uniqueID();
    }
}
