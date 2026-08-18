import streamlit as st
import os
import subprocess
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from main import build_graph

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Risk Monitor AI", page_icon="🛡️", layout="wide")

# ==========================================
# PREMIUM AESTHETICS (CUSTOM CSS)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Dark Theme & Glassmorphism Background */
    .stApp {
        background: radial-gradient(circle at top right, #1a1a2e, #16213e, #0f3460);
        color: #e0e0e0;
    }
    
    /* Vibrant Gradient Text */
    h1 {
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    
    .subtitle {
        text-align: center;
        color: #a0aec0;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* Chat Message Bubbles */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        color: #121212;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 2rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 242, 254, 0.5);
        color: #000;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-bottom: 2px solid #00f2fe;
    }
    
    /* File Uploader Container */
    [data-testid="stFileUploadDropzone"] {
        background-color: rgba(0, 242, 254, 0.05);
        border: 2px dashed rgba(0, 242, 254, 0.4);
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    
    [data-testid="stFileUploadDropzone"]:hover {
        background-color: rgba(0, 242, 254, 0.1);
        border-color: #00f2fe;
    }
</style>
""", unsafe_allow_html=True)

st.title("Risk Monitor Multi-Agent System")
st.markdown("<p class='subtitle'>AI-Powered Live Binance Position & Policy Tracking</p>", unsafe_allow_html=True)

# Verify Anthropic Key
if not os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") == "your_key_here":
    st.error("⚠️ ANTHROPIC_API_KEY is not set. Please update your .env file.")
    st.stop()

# Initialize session state for chat history and graph
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

# Create tabs
tab1, tab2 = st.tabs(["💬 AI Risk Chat", "📚 Knowledge Base"])

# ==========================================
# TAB 1: CHAT INTERFACE
# ==========================================
with tab1:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("E.g., Check the risk for my Binance account..."):
        # Add user message to state and display
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process with the Graph
        with st.chat_message("assistant"):
            # Create a status container to show internal thoughts
            status_container = st.status("Agent is thinking...", expanded=True)
            
            graph = st.session_state.graph
            
            # We start a fresh graph run with the user's prompt
            events = graph.stream(
                {"messages": [HumanMessage(content=prompt)]},
                {"recursion_limit": 20}
            )
            
            final_message = "Task completed."
            
            try:
                for s in events:
                    for node_name, node_state in s.items():
                        if "messages" in node_state and len(node_state["messages"]) > 0:
                            # Get the last message generated by this node
                            last_msg = node_state["messages"][-1]
                            status_container.write(f"**{node_name}**: {last_msg.content}")
                            final_message = last_msg.content
                        if "next" in node_state:
                            status_container.write(f"_*Supervisor routed to: {node_state['next']}*_")
                            
                status_container.update(label="Finished execution!", state="complete", expanded=False)
                
                # Display final message outside of the status container
                st.markdown(final_message)
                st.session_state.messages.append({"role": "assistant", "content": final_message})
                    
            except Exception as e:
                status_container.update(label="Error occurred", state="error")
                st.error(f"An error occurred: {e}")

# ==========================================
# TAB 2: KNOWLEDGE BASE (PDF RAG)
# ==========================================
with tab2:
    st.header("Vector Database Management")
    st.markdown("Upload your risk policy PDFs here. The agent will read them to evaluate live exposure.")
    
    DOCS_FOLDER = "docs"
    os.makedirs(DOCS_FOLDER, exist_ok=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Upload New Policy")
        uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"], label_visibility="collapsed")
        
        if uploaded_file is not None:
            file_path = os.path.join(DOCS_FOLDER, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Saved `{uploaded_file.name}` to knowledge base.")
            
    with col2:
        st.subheader("Current Policy Documents")
        existing_files = [f for f in os.listdir(DOCS_FOLDER) if f.endswith('.pdf')]
        
        if existing_files:
            for file in existing_files:
                st.markdown(f"- 📄 `{file}`")
        else:
            st.info("No policy documents found in the `docs/` folder.")
            
        st.markdown("---")
        
        st.subheader("Pinecone Synchronization")
        st.markdown("Run the chunking and embedding pipeline to update the AI's memory.")
        
        if st.button("🚀 Synchronize Pinecone Index", use_container_width=True):
            if not existing_files:
                st.warning("Please upload a PDF first.")
            else:
                with st.spinner("Processing documents & uploading embeddings to Pinecone... (This may take a minute)"):
                    try:
                        result = subprocess.run(
                            ["python", "ingest_docs.py"],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result.returncode == 0:
                            st.success("Successfully synchronized Pinecone Index!")
                            with st.expander("View Sync Logs"):
                                st.code(result.stdout)
                        else:
                            st.error("Synchronization failed!")
                            with st.expander("View Error Logs"):
                                st.code(result.stderr or result.stdout)
                    except Exception as e:
                        st.error(f"Failed to execute ingestion script: {e}")
