import gradio as gr
import pdfplumber
import anthropic
import json, re
import plotly.graph_objects as go
from pathlib import Path

# ── Client ────────────────────────────────────────────────────────────────────
client = anthropic.Anthropic()
MODEL  = "claude-opus-4-5"

# ── PDF extraction ────────────────────────────────────────────────────────────
def extract_pdf_text(path: str) -> str:
    try:
        parts = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                t = page.extract_text()
                if t:
                    parts.append(f"[PAGE {i+1}]\n{t}")
        return "\n\n".join(parts)
    except Exception as e:
        return f"[ERROR: {e}]"

def build_context(pdf_files) -> tuple[str, list[str]]:
    if not pdf_files:
        return "", []
    chunks, names = [], []
    for f in pdf_files:
        path = f.name if hasattr(f, "name") else str(f)
        name = Path(path).stem[:60]
        names.append(name)
        txt  = extract_pdf_text(path)
        chunks.append(f"=== PAPER: {name} ===\n{txt}")
    sep = "\n\n" + "="*60 + "\n\n"
    return sep.join(chunks), names

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM = """You are an expert quantitative financial analyst.
Respond ONLY with valid JSON (no markdown fences, no prose outside JSON).

JSON schema:
{
  "summary": "2-3 sentence executive summary",
  "key_metrics": [{"label":"","value":"","paper":"","note":""}],
  "signals": [{"strength":"green|amber|red","label":"","detail":"","paper":""}],
  "chart_data": {
    "type": "bar|line|scatter|none",
    "title": "",
    "x_label": "",
    "y_label": "",
    "series": [{"name":"","x":[],"y":[]}]
  },
  "analysis": "detailed analysis with numbers",
  "recommendation": "actionable recommendation"
}

Rules:
- Extract REAL numbers from papers only — never fabricate.
- signals: green=positive/buy, amber=caution, red=risk/sell.
- chart_data: fill with comparative numeric data from papers; type=none if no data.
"""

MODE_HINTS = {
    "📋 Trích xuất số liệu": "Extract specific numbers, statistics, tables from the papers.",
    "⚡ Tín hiệu đầu tư":    "Identify actionable buy/sell/hold signals from the research evidence.",
    "🔀 So sánh chiến lược": "Compare strategies, assets or methods with quantitative evidence.",
    "🎯 Khuyến nghị danh mục":"Synthesise findings into a concrete portfolio recommendation.",
    "💬 Hỏi tự do":          "Answer comprehensively using the paper content.",
}

def ask_claude(context: str, question: str, mode: str) -> dict:
    hint = MODE_HINTS.get(mode, "")
    user_msg = f"MODE: {hint}\n\nRESEARCH PAPERS:\n{context}\n\nQUESTION: {question}"
    resp = client.messages.create(
        model=MODEL, max_tokens=2048, system=SYSTEM,
        messages=[{"role":"user","content":user_msg}],
    )
    raw = resp.content[0].text.strip()
    raw = re.sub(r"^```[a-z]*\n?","",raw); raw = re.sub(r"\n?```$","",raw)
    return json.loads(raw)

# ── Plotly chart ──────────────────────────────────────────────────────────────
def build_chart(cd: dict):
    if not cd or cd.get("type","none") == "none":
        return None
    series = cd.get("series", [])
    if not series:
        x, y = cd.get("x",[]), cd.get("y",[])
        if x and y:
            series = [{"name": cd.get("title",""), "x": x, "y": y}]
    if not series:
        return None

    ctype  = cd.get("type","bar")
    colors = ["#1a73e8","#e8710a","#34a853","#9334e8","#ea4335","#00bcd4"]
    fig    = go.Figure()

    for i, s in enumerate(series):
        c = colors[i % len(colors)]
        sx, sy = s.get("x",[]), s.get("y",[])
        name   = s.get("name","")
        if ctype == "bar":
            fig.add_trace(go.Bar(name=name, x=sx, y=sy, marker_color=c))
        elif ctype == "line":
            fig.add_trace(go.Scatter(name=name, x=sx, y=sy,
                                     mode="lines+markers",
                                     line=dict(color=c,width=2)))
        elif ctype == "scatter":
            fig.add_trace(go.Scatter(name=name, x=sx, y=sy,
                                     mode="markers",
                                     marker=dict(color=c,size=9)))

    fig.update_layout(
        title=dict(text=cd.get("title",""), font=dict(size=14)),
        xaxis_title=cd.get("x_label",""),
        yaxis_title=cd.get("y_label",""),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Inter,sans-serif",size=12),
        margin=dict(l=50,r=20,t=50,b=50),
        barmode="group",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
    )
    fig.update_xaxes(showgrid=True,gridcolor="#f0f0f0")
    fig.update_yaxes(showgrid=True,gridcolor="#f0f0f0")
    return fig

# ── HTML result card ──────────────────────────────────────────────────────────
SC = {"green":"#1e8a44","amber":"#b45309","red":"#c0392b"}
SB = {"green":"#f0fdf4","amber":"#fffbeb","red":"#fef2f2"}
SI = {"green":"▲","amber":"◆","red":"▼"}

def render_html(data: dict, names: list[str]) -> str:
    badges   = "".join(f'<span class="badge">{n[:50]}</span>' for n in names)
    summary  = data.get("summary","")
    metrics  = data.get("key_metrics",[])
    signals  = data.get("signals",[])
    analysis = data.get("analysis","").replace("\n","<br>")
    rec      = data.get("recommendation","").replace("\n","<br>")

    m_html = "".join(f"""
    <div class="metric-card">
      <div class="ml">{m.get('label','')}</div>
      <div class="mv">{m.get('value','')}</div>
      <div class="mn">{m.get('paper','')} {('· '+m['note']) if m.get('note') else ''}</div>
    </div>""" for m in metrics[:8])

    s_html = "".join(f"""
    <div class="sig" style="border-left:4px solid {SC.get(s.get('strength','amber'),'#888')};
                             background:{SB.get(s.get('strength','amber'),'#fff')};">
      <span style="color:{SC.get(s.get('strength','amber'),'#888')};font-size:18px">
        {SI.get(s.get('strength','amber'),'•')}
      </span>
      <div>
        <strong style="color:{SC.get(s.get('strength','amber'),'#333')}">
          {s.get('label','')}
        </strong>
        <div class="sd">{s.get('detail','')}</div>
        <div class="ss">{s.get('paper','')}</div>
      </div>
    </div>""" for s in signals)

    return f"""<style>
.rw{{font-family:Inter,sans-serif;font-size:13px;color:#1a1a1a;padding:4px}}
.badges{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}}
.badge{{background:#e8f0fe;color:#1a56db;padding:3px 9px;border-radius:12px;font-size:11px;font-weight:500}}
.st{{font-size:11px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:.06em;margin:16px 0 7px}}
.sumbox{{background:#f8f9ff;border:1px solid #d1d9ff;border-radius:8px;padding:12px 14px;line-height:1.65;color:#2d2d5e}}
.mgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:8px}}
.metric-card{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:10px 12px}}
.ml{{font-size:11px;color:#6b7280;margin-bottom:3px}}.mv{{font-size:20px;font-weight:600;color:#111827}}
.mn{{font-size:10px;color:#9ca3af;margin-top:3px}}
.sig{{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;border-radius:8px;margin-bottom:8px}}
.sd{{font-size:12px;color:#374151;margin-top:3px;line-height:1.5}}
.ss{{font-size:10px;color:#9ca3af;margin-top:4px}}
.abox{{background:#fafafa;border:1px solid #e5e7eb;border-radius:8px;padding:14px;line-height:1.75;color:#374151}}
.recbox{{background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px;line-height:1.7;color:#14532d;font-weight:500}}
</style>
<div class="rw">
  <div class="badges">{badges}</div>
  <div class="st">Tóm tắt</div>
  <div class="sumbox">{summary}</div>
  {"<div class='st'>Số liệu chính</div><div class='mgrid'>" + m_html + "</div>" if metrics else ""}
  {"<div class='st'>Tín hiệu đầu tư</div>" + s_html if signals else ""}
  <div class="st">Phân tích chi tiết</div>
  <div class="abox">{analysis}</div>
  {"<div class='st'>Khuyến nghị</div><div class='recbox'>" + rec + "</div>" if rec else ""}
</div>"""

# ── Core analyze function ─────────────────────────────────────────────────────
def analyze(pdf_files, question, mode, history):
    if not pdf_files:
        new_h = history + [{"role":"assistant",
                            "content":"⚠️ Vui lòng upload ít nhất 1 file PDF trước."}]
        yield new_h, None, "<p style='color:#aaa;padding:10px'>Chưa có kết quả</p>"
        return
    if not question.strip():
        new_h = history + [{"role":"assistant","content":"⚠️ Vui lòng nhập câu hỏi."}]
        yield new_h, None, "<p style='color:#aaa;padding:10px'>Chưa có kết quả</p>"
        return

    # Optimistic update
    pending = history + [
        {"role":"user","content": question},
        {"role":"assistant","content":"⏳ Đang đọc PDF và phân tích…"},
    ]
    yield pending, None, "<p style='color:#888;font-style:italic;padding:10px'>Đang phân tích…</p>"

    context, names = build_context(pdf_files)
    try:
        data = ask_claude(context, question, mode)
        html = render_html(data, names)
        fig  = build_chart(data.get("chart_data", {}))
        n    = len(names)
        reply = f"✅ Phân tích xong {n} paper{'s' if n>1 else ''}. Xem kết quả bên phải →"
        done  = history + [
            {"role":"user","content": question},
            {"role":"assistant","content": reply},
        ]
        yield done, fig, html
    except Exception as e:
        err   = f"❌ Lỗi: {e}"
        done  = history + [
            {"role":"user","content": question},
            {"role":"assistant","content": err},
        ]
        yield done, None, f"<p style='color:red;padding:10px'>{err}</p>"

def clear_chat():
    return [], None, "<p style='color:#aaa;padding:10px'>Chưa có kết quả</p>"

# ── Preset questions ──────────────────────────────────────────────────────────
PRESETS = [
    ("📊 Sharpe ratio",
     "Liệt kê Sharpe ratio của tất cả các portfolio trong papers, có và không có crypto."),
    ("🪙 ETH vs BTC",
     "So sánh hiệu quả đa dạng hóa của Ethereum và Bitcoin với số liệu cụ thể."),
    ("⚡ Tín hiệu mua/bán",
     "Xác định các tín hiệu đầu tư crypto từ kết quả nghiên cứu."),
    ("📈 CAAR cổ tức VN",
     "Trích xuất toàn bộ CAAR và t-statistic của sự kiện cổ tức dược phẩm Việt Nam."),
    ("🎯 Danh mục tối ưu",
     "Đề xuất chiến lược danh mục tối ưu kết hợp crypto và tài sản truyền thống."),
    ("📉 Rủi ro & biến động",
     "Phân tích rủi ro (volatility, max drawdown, kurtosis) của các tài sản trong papers."),
    ("🔀 Naive vs tối ưu hóa",
     "So sánh hiệu suất Naive 1/N vs Markowitz, Max Sharpe, Max Utility."),
    ("💹 Tác động short-selling",
     "Short-selling ảnh hưởng thế nào đến hiệu suất danh mục? Số liệu thay đổi ra sao?"),
]

# ── UI ────────────────────────────────────────────────────────────────────────
CSS = """
#header{text-align:center;padding:18px 0 6px}
#header h1{font-size:22px;font-weight:700;color:#1a1a2e;margin:0}
#header p{color:#6b7280;font-size:13px;margin:4px 0 0}
.preset-btn button{text-align:left!important;font-size:12px!important;
                   padding:6px 10px!important;border-radius:6px!important}
#result-html{max-height:68vh;overflow-y:auto;border:1px solid #e5e7eb;
             border-radius:8px;padding:2px}
footer{display:none!important}
"""

with gr.Blocks(css=CSS, title="Investment Paper Analyzer") as demo:

    gr.HTML("""<div id="header">
      <h1>📑 Investment Paper Analyzer</h1>
      <p>Upload PDF papers • Hỏi bằng tiếng Việt hoặc tiếng Anh •
         Nhận số liệu, tín hiệu đầu tư & biểu đồ tương tác</p>
    </div>""")

    with gr.Row():
        # ── Sidebar ───────────────────────────────────────────────────────────
        with gr.Column(scale=1, min_width=240):
            gr.Markdown("#### 📂 Upload Papers")
            pdf_input = gr.File(
                label=None, file_types=[".pdf"],
                file_count="multiple", height=130,
            )
            gr.Markdown("#### ⚙️ Chế độ")
            mode_sel = gr.Radio(
                choices=list(MODE_HINTS.keys()),
                value="📋 Trích xuất số liệu",
                label=None,
            )
            gr.Markdown("#### 🚀 Gợi ý nhanh")
            preset_btns = []
            for lbl, _ in PRESETS:
                b = gr.Button(lbl, size="sm", elem_classes="preset-btn")
                preset_btns.append(b)
            gr.Markdown("---")
            clear_btn = gr.Button("🗑️ Xóa hội thoại", size="sm", variant="secondary")

        # ── Chat ──────────────────────────────────────────────────────────────
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="Hội thoại", height=420,
                type="messages",
                placeholder="Upload PDF → nhập câu hỏi → nhấn Gửi",
            )
            with gr.Row():
                q_box   = gr.Textbox(
                    placeholder="Nhập câu hỏi (Enter để gửi)…",
                    lines=2, show_label=False, scale=5,
                )
                send_btn = gr.Button("Gửi ↗", variant="primary", scale=1, min_width=80)

        # ── Results ───────────────────────────────────────────────────────────
        with gr.Column(scale=2):
            gr.Markdown("#### 📊 Biểu đồ")
            chart_out  = gr.Plot(show_label=False, min_height=280)
            gr.Markdown("#### 🧾 Phân tích & Tín hiệu")
            result_html = gr.HTML(
                value="<p style='color:#aaa;padding:14px'>Kết quả sẽ hiện ở đây.</p>",
                elem_id="result-html",
            )

    # ── Wiring ────────────────────────────────────────────────────────────────
    INPUTS  = [pdf_input, q_box, mode_sel, chatbot]
    OUTPUTS = [chatbot, chart_out, result_html]

    send_btn.click(analyze, INPUTS, OUTPUTS)
    q_box.submit(analyze, INPUTS, OUTPUTS)
    clear_btn.click(clear_chat, outputs=OUTPUTS)

    # Preset buttons: fill question box → auto-submit
    for btn, (_, q) in zip(preset_btns, PRESETS):
        btn.click(
            fn=lambda q=q: q,
            outputs=q_box,
        ).then(analyze, INPUTS, OUTPUTS)

demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
