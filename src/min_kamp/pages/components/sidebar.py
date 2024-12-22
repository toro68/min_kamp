import streamlit as st


def setup_sidebar() -> None:
    """Setter opp sidebar med navigasjon"""
    if st.session_state.authenticated:
        st.sidebar.title("Meny")
        st.sidebar.info(f"Innlogget som: {st.session_state.get('username', '')}")

        if st.sidebar.button("Administrer spillertropp", use_container_width=True):
            st.session_state.current_page = "oppsett"
            st.rerun()

        if st.sidebar.button("Velg kamptropp", use_container_width=True):
            st.session_state.current_page = "kamptropp"
            st.rerun()

        if st.sidebar.button("Bytteplan", use_container_width=True):
            st.session_state.current_page = "bytteplan"
            st.rerun()

        if st.sidebar.button("Kampinfo", use_container_width=True):
            st.session_state.current_page = "kamp"
            st.rerun()

        st.sidebar.markdown("---")
        if st.sidebar.button("Logg ut", type="secondary", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()
