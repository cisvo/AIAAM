"""
chatbot.py
==========
Trợ lý chatbot dùng Anthropic Claude API, có ngữ cảnh (context) về tài sản /
danh mục đầu tư mà người dùng đang xem trên dashboard.

Người dùng tự nhập API key của họ (không hard-code trong source).
"""
DEFAULT_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT_TEMPLATE = """Bạn là trợ lý tài chính cho một dashboard đầu tư (FinDash-VN).
Nhiệm vụ: trả lời câu hỏi của người dùng về cổ phiếu, tiền điện tử và danh mục đầu tư mà
họ đang xem trên dashboard, dựa trên NGỮ CẢNH bên dưới khi liên quan. Trả lời ngắn gọn,
rõ ràng, bằng tiếng Việt trừ khi người dùng hỏi bằng tiếng Anh. Nếu không chắc chắn về
một con số cụ thể, hãy nói rõ đó là ước tính chứ không khẳng định chắc chắn. Bạn không
đưa ra khuyến nghị mua/bán chắc chắn — chỉ phân tích, giải thích khái niệm và diễn giải
số liệu, luôn nhắc rằng đây không phải là lời khuyên đầu tư.

NGỮ CẢNH HIỆN TẠI TRÊN DASHBOARD:
{context}
"""


def build_context(asset_class=None, symbol=None, summary_info=None,
                   portfolio_tickers=None, port_stats=None) -> str:
    lines = []
    if asset_class and symbol:
        lines.append(f"- Đang xem: {asset_class} - {symbol}")
        if summary_info:
            for k, v in list(summary_info.items())[:8]:
                lines.append(f"  {k}: {v}")
    if portfolio_tickers:
        lines.append(f"- Danh mục đang phân tích: {', '.join(portfolio_tickers)}")
        if port_stats:
            er = port_stats.get("expected_return_annual")
            vol = port_stats.get("volatility_annual")
            sharpe = port_stats.get("sharpe_ratio")
            if er is not None:
                lines.append(f"  Lợi suất kỳ vọng (năm): {er:.2%}")
            if vol is not None:
                lines.append(f"  Độ biến động (năm): {vol:.2%}")
            if sharpe is not None:
                lines.append(f"  Sharpe ratio: {sharpe:.2f}")
    if not lines:
        lines.append("- (Người dùng chưa chọn tài sản hoặc danh mục nào trên dashboard)")
    return "\n".join(lines)


def get_client(api_key: str):
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def ask_chatbot(client, messages: list, context: str, model: str = DEFAULT_MODEL,
                 max_tokens: int = 1024) -> str:
    """
    messages: lịch sử hội thoại dạng [{"role": "user"/"assistant", "content": str}, ...]
    Trả về: chuỗi câu trả lời văn bản của Claude.
    """
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text")
