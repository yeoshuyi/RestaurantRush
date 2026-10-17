package rush.model;

public final class ActionResult {
    private final boolean ok;
    private final String message;

    private ActionResult(boolean ok, String message) {
        this.ok = ok;
        this.message = message;
    }

    public static ActionResult ok(String message) {
        return new ActionResult(true, message);
    }

    public static ActionResult fail(String reason) {
        return new ActionResult(false, reason);
    }

    public boolean isOk() {
        return ok;
    }

    public String getMessage() {
        return message;
    }
}
