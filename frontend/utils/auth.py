"""
Session state auth helpers for Streamlit.
"""
import streamlit as st
from utils.api_client import login as api_login


def is_authenticated() -> bool:
    return bool(st.session_state.get("token") and st.session_state.get("user"))


def get_user() -> dict:
    return st.session_state.get("user", {})


def get_role() -> str:
    return get_user().get("role", "")


def has_role(*roles: str) -> bool:
    return get_role() in roles


def require_auth():
    """Call at the top of every page. Redirects to login if not authenticated."""
    if not is_authenticated():
        st.session_state["redirect_after_login"] = st.session_state.get("page", "home")
        st.session_state["page"] = "login"
        st.rerun()


def require_role(*roles: str):
    """Block access to page if user doesn't have one of the specified roles."""
    require_auth()
    if get_role() not in roles and get_role() != "admin":
        st.error("You don't have permission to view this page.")
        st.stop()


def do_login(email: str, password: str) -> bool:
    result = api_login(email, password)
    if result:
        st.session_state["token"] = result["access_token"]
        st.session_state["user"] = result["user"]
        return True
    return False


def do_logout():
    st.session_state.clear()


def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style='text-align:center; padding: 2rem 0 1rem'>
                <h1 style='font-size:2.5rem; margin:0'>🏗️</h1>
                <h2 style='margin:0.5rem 0 0'>Pipeline IQ</h2>
                <p style='color:#888; margin:0'>Hardware Direct Customer Intelligence</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@hardwaredirect.com.au")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter your email and password.")
            else:
                with st.spinner("Signing in…"):
                    if do_login(email, password):
                        redirect = st.session_state.pop("redirect_after_login", "home")
                        st.session_state["page"] = redirect
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
