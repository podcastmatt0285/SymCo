package PACKAGE_NAME;

public class GlobalChatWidget extends ChatWidgetBase {
    public static final String ACTION_REFRESH = "PACKAGE_NAME.GLOBAL_CHAT_REFRESH";
    @Override public String getRoomId()        { return "global"; }
    @Override public String getActionRefresh() { return ACTION_REFRESH; }
    @Override public String getRoomLabel()     { return "\uD83C\uDF10 GLOBAL CHAT"; }
}
