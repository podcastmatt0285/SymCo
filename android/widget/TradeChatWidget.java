package PACKAGE_NAME;

public class TradeChatWidget extends ChatWidgetBase {
    public static final String ACTION_REFRESH = "PACKAGE_NAME.TRADE_CHAT_REFRESH";
    @Override public String getRoomId()        { return "trade"; }
    @Override public String getActionRefresh() { return ACTION_REFRESH; }
    @Override public String getRoomLabel()     { return "\uD83D\uDCCA TRADE CHAT"; }
}
