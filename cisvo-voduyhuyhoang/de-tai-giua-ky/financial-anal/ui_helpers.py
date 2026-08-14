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
        st.dataframe(df, use_container_width=True, height=height, key=f"{key}_fallback")
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
              string (đoạn văn) hoặc pandas DataFrame (sẽ vẽ dạng bảng).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig, ax = plt.subplots(figsize=(8.27, 11.69))  # khổ A4
        ax.axis("off")
        y = 0.95
        ax.text(0.06, y, title, fontsize=18, weight="bold", va="top")
        y -= 0.045
        ax.text(0.06, y, f"Tạo lúc: {datetime.now():%d/%m/%Y %H:%M}", fontsize=9,
                va="top", color="gray")
        y -= 0.05

        for sec_title, content in sections:
            if y < 0.12:
                pdf.savefig(fig)
                plt.close(fig)
                fig, ax = plt.subplots(figsize=(8.27, 11.69))
                ax.axis("off")
                y = 0.95

            ax.text(0.06, y, sec_title, fontsize=13, weight="bold", va="top")
            y -= 0.04

            if isinstance(content, pd.DataFrame) and not content.empty:
                small = content.copy()
                if len(small) > 15:
                    small = small.head(15)
                table_text = small.round(4).to_string()
                ax.text(0.06, y, table_text, fontsize=7, va="top", family="monospace")
                y -= 0.03 * (len(small) + 3)
            else:
                ax.text(0.06, y, str(content), fontsize=10, va="top", wrap=True)
                y -= 0.06

            y -= 0.02

        pdf.savefig(fig)
        plt.close(fig)

    st.download_button(label, data=buf.getvalue(), file_name=filename,
                        mime="application/pdf", key=key)
