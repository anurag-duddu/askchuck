"""
AskChuck Streamlit UI
A conversational interface to Charles Owen's Structured Planning methodology.
"""

import streamlit as st

from src.generation.rag_chain import AskChuckRAG

# Page configuration
st.set_page_config(
    page_title="AskChuck - Structured Planning Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
    <style>
    .main {
        padding: 1rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .source-citation {
        background-color: #f0f2f6;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem 0;
        font-size: 0.9em;
    }
    .figure-container {
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "rag_chain" not in st.session_state:
    with st.spinner("Initializing AskChuck RAG system..."):
        st.session_state.rag_chain = AskChuckRAG()


def display_sources(sources: list):
    """Display source citations in an expander."""
    if not sources:
        return

    with st.expander(f"📚 Sources ({len(sources)})", expanded=False):
        for i, source in enumerate(sources, 1):
            display = source.get("display", "")
            st.markdown(
                f'<div class="source-citation">{i}. {display}</div>',
                unsafe_allow_html=True,
            )


def display_figures(figures: list):
    """Display figures with captions."""
    if not figures:
        return

    st.markdown("### Figures")

    for fig in figures:
        url = fig.get("url", "")
        caption = fig.get("caption", "")
        document = fig.get("document", "")
        fig_num = fig.get("figure_number", "")

        with st.container():
            st.markdown(
                f'<div class="figure-container">',
                unsafe_allow_html=True,
            )

            if url:
                try:
                    st.image(url, caption=f"Figure {fig_num}: {caption}", use_container_width=True)
                    st.caption(f"Source: {document}")
                except Exception as e:
                    st.warning(f"Could not load figure: {e}")
            else:
                st.warning("Figure URL not available")

            st.markdown("</div>", unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.title("🎓 AskChuck")
    st.markdown("---")

    st.markdown(
        """
        **About**

        AskChuck is your AI assistant for understanding Charles Owen's Structured Planning methodology from IIT Institute of Design.

        Ask questions about:
        - Functions and Design Factors
        - Information Structures
        - Abstraction Ladders
        - VTCON and RELATN
        - And more!
        """
    )

    st.markdown("---")

    if st.button("🆕 New Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")

    # Settings
    with st.expander("⚙️ Settings"):
        top_k = st.slider(
            "Number of chunks to retrieve",
            min_value=1,
            max_value=10,
            value=5,
            help="More chunks = more context but slower",
        )
        st.session_state.top_k = top_k

        include_figures = st.checkbox(
            "Include figures",
            value=True,
            help="Retrieve and display relevant figures",
        )
        st.session_state.include_figures = include_figures

# Main chat interface
st.title("💬 Chat with AskChuck")
st.markdown("Ask me anything about Charles Owen's Structured Planning methodology!")
st.markdown("---")

# Display chat messages
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]

    with st.chat_message(role):
        st.markdown(content)

        # Display sources for assistant messages
        if role == "assistant" and "sources" in message:
            display_sources(message["sources"])

        # Display figures for assistant messages
        if role == "assistant" and "figures" in message:
            display_figures(message["figures"])

# Chat input
if prompt := st.chat_input("Ask a question about Structured Planning..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Prepare conversation history
            history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in st.session_state.messages[:-1]  # Exclude current question
            ]

            # Query RAG chain
            result = st.session_state.rag_chain.query(
                question=prompt,
                conversation_history=history,
                include_figures=st.session_state.get("include_figures", True),
                top_k=st.session_state.get("top_k", 5),
            )

            # Display answer
            answer = result.get("answer", "")
            st.markdown(answer)

            # Display sources
            sources = result.get("sources", [])
            display_sources(sources)

            # Display figures
            figures = result.get("figures", [])
            display_figures(figures)

            # Add to conversation history
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "figures": figures,
                }
            )
