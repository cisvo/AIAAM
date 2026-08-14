"""
auth.py
=======
Cổng đăng nhập TUỲ CHỌN cho FinDash-VN.

Đổi biến AUTH_MODE bên dưới để bật:
    "none"     -> không yêu cầu đăng nhập (mặc định — phù hợp khi demo/nộp bài)
    "password" -> yêu cầu 1 mật khẩu chung, đặt trong .streamlit/secrets.toml
                  dưới khoá [auth] password = "..."
    "oidc"     -> đăng nhập Google thật qua st.login(). Cần đăng ký OAuth Client
                  trên Google Cloud Console và khai báo redirect_uri, cookie_secret,
                  client_id, client_secret trong secrets.toml (xem file
                  .streamlit/secrets.toml.example và README.md).
"""
import streamlit as st

AUTH_MODE = "none"


def require_login() -> bool:
    """
    Trả về True nếu được phép vào app.
    Nếu chưa đăng nhập, vẽ màn hình đăng nhập rồi gọi st.stop() để dừng phần còn lại.
    """
    if AUTH_MODE == "none":
        return True

    if AUTH_MODE == "password":
        if st.session_state.get("authenticated"):
            return True
        st.title("🔒 FinDash-VN — Đăng nhập")
        pwd = st.text_input("Mật khẩu truy cập", type="password")
        if st.button("Đăng nhập", type="primary"):
            expected = st.secrets.get("auth", {}).get("password")
            if expected and pwd == expected:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Sai mật khẩu, hoặc chưa cấu hình [auth] password trong secrets.toml.")
        st.stop()
        return False

    if AUTH_MODE == "oidc":
        if not st.user.is_logged_in:
            st.title("🔒 FinDash-VN — Đăng nhập")
            st.write("Đăng nhập bằng tài khoản Google để tiếp tục.")
            st.button("Đăng nhập bằng Google", on_click=st.login, args=("google",))
            st.stop()
            return False
        with st.sidebar:
            st.caption(f"👋 Xin chào, {getattr(st.user, 'name', getattr(st.user, 'email', ''))}")
            st.button("Đăng xuất", on_click=st.logout, key="logout_btn")
        return True

    return True
