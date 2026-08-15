"""
ui_helpers.py
=============
Các hàm tiện ích dùng chung cho giao diện:
    - show_table(): bảng dữ liệu nâng cao (streamlit-aggrid) — tự fallback về
      st.dataframe nếu chưa cài streamlit-aggrid hoặc bị lỗi.
    - export_csv_button / export_excel_button / export_pdf_button: xuất báo cáo.

PDF được vẽ bằng matplotlib (PdfPages) thay vì fpdf2, vì font mặc định của
matplotlib (DejaVu Sans) hiển thị đúng dấu tiếng Việt — fpdf2 dùng font Latin-1
mặc định sẽ mất dấu.
"""
import io
from datetime import datetime

import pandas as pd
import streamlit as st


def show_table(df: pd.DataFrame, key: str, height: int = 350, editable_cols: list | None = None):
    """
    Hiển thị bảng dữ liệu. Ưu tiên streamlit-aggrid (sort/filter/resize cột,
    kiểu Excel); nếu chưa cài hoặc lỗi thì rơi về st.dataframe.
    Trả về DataFrame đã chỉnh sửa (nếu editable_cols được bật và dùng AgGrid),
    ngược lại trả về chính df gốc.
    """
    if df is None or df.empty:
        st.info("Không có dữ liệu để hiển thị.")
        return df

    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(sortable=True, filter=True, resizable=True)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        if editable_cols:
            for c in editable_cols:
                if c in df.columns:
                    gb.configure_column(c, editable=True)
        grid_res = AgGrid(
            df, gridOptions=gb.build(), height=height, key=key,
            update_mode=GridUpdateMode.VALUE_CHANGED, fit_columns_on_grid_load=True,
        )
        return pd.DataFrame(grid_res["data"])
    except Exception:
        st.dataframe(df, width="stretch", height=height, key=f"{key}_fallback")
        return df


def export_csv_button(df: pd.DataFrame, filename: str, label: str, key: str):
    if df is None or df.empty:
        return
    csv_bytes = df.to_csv(index=True).encode("utf-8-sig")  # utf-8-sig để Excel mở đúng dấu tiếng Việt
    st.download_button(label, data=csv_bytes, file_name=filename, mime="text/csv", key=key)


def export_excel_button(sheets: dict, filename: str, label: str, key: str):
    """sheets: dict {tên_sheet: DataFrame}"""
    sheets = {k: v for k, v in sheets.items() if v is not None and not v.empty}
    if not sheets:
        return
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe_name = name[:31]  # giới hạn tên sheet Excel
            df.to_excel(writer, sheet_name=safe_name)
    st.download_button(
        label, data=buf.getvalue(), file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=key,
    )


def export_pdf_button(title: str, sections: list, filename: str, label: str, key: str):
    """
    sections: list các tuple (tiêu_đề_phần, nội_dung) trong đó nội_dung là
              string (đoạn văn) hoặc pandas DataFrame (sẽ vẽ dạng bảng thật qua
              matplotlib.table — KHÔNG dùng font monospace vì font monospace mặc định
              của matplotlib không có đủ dấu tiếng Việt, gây vỡ chữ).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    LEFT, WIDTH = 0.06, 0.88
    TOP, BOTTOM = 0.95, 0.08
    VN_FONT = "DejaVu Sans"  # font mặc định của matplotlib — hỗ trợ dấu tiếng Việt đúng

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        state = {}

        def new_page():
            if "fig" in state:
                pdf.savefig(state["fig"])
                plt.close(state["fig"])
            fig, ax = plt.subplots(figsize=(8.27, 11.69))  # khổ A4
            ax.axis("off")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            state.update(fig=fig, ax=ax, y=TOP)

        new_page()
        ax = state["ax"]
        ax.text(LEFT, state["y"], title, fontsize=18, weight="bold", va="top", fontfamily=VN_FONT)
        state["y"] -= 0.045
        ax.text(LEFT, state["y"], f"Tạo lúc: {datetime.now():%d/%m/%Y %H:%M}", fontsize=9,
                va="top", color="gray", fontfamily=VN_FONT)
        state["y"] -= 0.06

        for sec_title, content in sections:
            if state["y"] < BOTTOM + 0.08:
                new_page()
            ax = state["ax"]
            ax.text(LEFT, state["y"], sec_title, fontsize=13, weight="bold", va="top", fontfamily=VN_FONT)
            state["y"] -= 0.04

            if isinstance(content, pd.DataFrame) and not content.empty:
                small = content.copy()
                if len(small) > 12:
                    small = small.head(12)
                display_df = small.copy()
                for col in display_df.columns:
                    if pd.api.types.is_numeric_dtype(display_df[col]):
                        display_df[col] = display_df[col].map(lambda v: f"{v:.4g}" if pd.notna(v) else "")
                    else:
                        display_df[col] = display_df[col].astype(str)
                label_col_name = display_df.index.name or "Tài sản"
                display_df = display_df.reset_index()
                display_df.rename(columns={display_df.columns[0]: label_col_name}, inplace=True)

                n_rows = len(display_df) + 1  # +1 cho hàng tiêu đề cột
                row_h = 0.03
                table_height = n_rows * row_h

                if state["y"] - table_height < BOTTOM:
                    new_page()
                    ax = state["ax"]
                    ax.text(LEFT, state["y"], f"{sec_title} (tiếp theo)", fontsize=13,
                            weight="bold", va="top", fontfamily=VN_FONT)
                    state["y"] -= 0.04

                # Bề rộng cột theo độ dài chữ (cột nhãn đầu tiên được nới thêm hệ số 1.6
                # vì thường dài hơn do chứa cả tên loại tài sản + mã).
                raw_widths = []
                for i, col in enumerate(display_df.columns):
                    max_len = max([len(str(col))] + [len(str(v)) for v in display_df[col]])
                    raw_widths.append(max_len * (1.6 if i == 0 else 1.0))
                total_w = sum(raw_widths) or 1
                col_widths = [w / total_w for w in raw_widths]

                tbl = ax.table(
                    cellText=display_df.values.tolist(),
                    colLabels=[str(c) for c in display_df.columns],
                    cellLoc="right", colWidths=col_widths,
                    bbox=[LEFT, state["y"] - table_height, WIDTH, table_height],
                )
                tbl.auto_set_font_size(False)
                tbl.set_fontsize(7)
                for (row, col), cell in tbl.get_celld().items():
                    cell.set_text_props(fontfamily=VN_FONT)
                    if col == 0:
                        cell.set_text_props(fontfamily=VN_FONT, ha="left")
                state["y"] -= table_height + 0.03
            else:
                ax.text(LEFT, state["y"], str(content), fontsize=10, va="top",
                        wrap=True, fontfamily=VN_FONT)
                state["y"] -= 0.06

            state["y"] -= 0.02

        pdf.savefig(state["fig"])
        plt.close(state["fig"])

    st.download_button(label, data=buf.getvalue(), file_name=filename,
                        mime="application/pdf", key=key)
