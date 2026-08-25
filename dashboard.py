import streamlit as st
import json
import os
import io
import contextlib
from langchain_core.messages import HumanMessage
from main import build_graph

# Setup LangGraph
app = build_graph()

st.set_page_config(page_title="Risk Monitor Control Room", page_icon="🤖", layout="wide")

# Custom CSS for a Bloomberg-style dark mode feel
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .metric-card {
        background-color: #262730;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    h1, h2, h3 {
        color: #00d2ff;
    }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📂 Policy Management")
    
    docs_dir = "docs"
    current_policy = None
    if os.path.exists(docs_dir):
        pdf_files = [f for f in os.listdir(docs_dir) if f.endswith(".pdf")]
        if pdf_files:
            current_policy = pdf_files[0]
            
    if current_policy:
        st.success(f"**Active Policy:**\n\n{current_policy}")
    else:
        st.warning("No active policy found. AI is running blind!")
        
    uploaded_file = st.file_uploader("Upload New Policy PDF", type=["pdf"])
    if uploaded_file is not None:
        if st.button("Update Policy & Wipe Brain"):
            with st.spinner("Wiping AI memory and learning new rules... (approx 30s)"):
                if not os.path.exists(docs_dir):
                    os.makedirs(docs_dir)
                else:
                    for f in os.listdir(docs_dir):
                        if f.endswith(".pdf"):
                            os.remove(os.path.join(docs_dir, f))
                            
                file_path = os.path.join(docs_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                    
                import subprocess
                subprocess.run(["python", "ingest_docs.py"], capture_output=True)
                
                st.success("Brain updated! New policy is active.")
                time.sleep(2)
                st.rerun()

st.title("🤖 Multi-Agent Risk Control Room")
st.markdown("---")

col1, col2, col3 = st.columns(3)

def get_latest_metrics():
    audit_dir = "audit_reports"
    if not os.path.exists(audit_dir):
        return None
    files = sorted([f for f in os.listdir(audit_dir) if f.endswith('.json')], reverse=True)
    if not files:
        return None
    
    with open(os.path.join(audit_dir, files[0]), 'r') as f:
        data = json.load(f)
        return data

latest = get_latest_metrics()

with col1:
    val1 = f"${latest['metrics'].get('exposure', 0):,.2f}" if latest else "N/A"
    st.markdown(f'''
        <div class="metric-card">
            <p style="color: #a3a8b8; font-size: 14px; margin-bottom: 5px;">Total Exposure</p>
            <h2 style="margin: 0; padding: 0;">{val1}</h2>
        </div>
    ''', unsafe_allow_html=True)

with col2:
    val2 = f"{latest['metrics'].get('margin', 0)*100:.1f}%" if latest else "N/A"
    st.markdown(f'''
        <div class="metric-card">
            <p style="color: #a3a8b8; font-size: 14px; margin-bottom: 5px;">Margin Utilization</p>
            <h2 style="margin: 0; padding: 0;">{val2}</h2>
        </div>
    ''', unsafe_allow_html=True)
    
with col3:
    val3 = latest["policy_triggered"] if latest else "None"
    st.markdown(f'''
        <div class="metric-card">
            <p style="color: #a3a8b8; font-size: 14px; margin-bottom: 5px;">Last Policy Triggered</p>
            <h3 style="margin: 0; padding: 0; font-size: 18px;">{val3}</h3>
        </div>
    ''', unsafe_allow_html=True)

if not latest:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("🟢 **System Note:** Your dashboard is currently in a clean state. Click **'🚀 Run Full Risk Check'** below to initialize the AI and pull live metrics!")

st.markdown("---")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("💬 Live Agent Chat Feed")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Welcome to the Risk Control Room. Click a button below or type a custom command!", "avatar": "🤖"}
        ]
        
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar=msg.get("avatar", "🤖")):
            st.markdown(msg["content"])
            
    # Example prompts
    cols = st.columns(3)
    prompt = None
    if cols[0].button("🚀 Run Full Risk Check"):
        prompt = "Check my Binance Testnet account for any margin or exposure breaches. If it breaches, send an alert."
    elif cols[1].button("📰 Check Macro News Only"):
        prompt = "What is the current macro news sentiment?"
    elif cols[2].button("🗑️ Clear Chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Welcome to the Risk Control Room. Click a button below or type a custom command!", "avatar": "🤖"}
        ]
        st.rerun()
        
    chat_input = st.chat_input("Command the Risk Monitor...")
    if chat_input:
        prompt = chat_input

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt, "avatar": "👤"})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
            
        initial_state = {"messages": [HumanMessage(content=prompt)]}
        
        with st.spinner("Agents are collaborating..."):
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                events = app.stream(initial_state, {"recursion_limit": 20})
                
                for s in events:
                    # Capture standard output from Supervisor Gatekeeper (print statements)
                    printed_out = f.getvalue()
                    if printed_out.strip():
                        gatekeeper_msg = f"**[Supervisor Logic]**\n```text\n{printed_out.strip()}\n```"
                        st.session_state.messages.append({"role": "assistant", "content": gatekeeper_msg, "avatar": "🧠"})
                        with st.chat_message("assistant", avatar="🧠"):
                            st.markdown(gatekeeper_msg)
                        f.truncate(0)
                        f.seek(0)
                        
                    # Process LangGraph Node Outputs
                    for node_name, node_state in s.items():
                        if "messages" in node_state:
                            for m in node_state["messages"]:
                                safe_content = m.content.encode('ascii', 'replace').decode('ascii')
                                
                                avatar = "🤖"
                                if node_name == "Data_Agent": avatar = "📊"
                                elif node_name == "RAG_Agent": avatar = "📚"
                                elif node_name == "Alert_Agent": avatar = "🚨"
                                
                                agent_msg = f"**[{node_name}]**\n\n{safe_content}"
                                st.session_state.messages.append({"role": "assistant", "content": agent_msg, "avatar": avatar})
                                with st.chat_message("assistant", avatar=avatar):
                                    st.markdown(agent_msg)
                        
                        if "next" in node_state:
                            st.toast(f"Supervisor routed task to: {node_state['next']}")

            # Final stdout check in case something printed at the very end
            printed_out = f.getvalue()
            if printed_out.strip():
                gatekeeper_msg = f"**[Supervisor Final]**\n```text\n{printed_out.strip()}\n```"
                st.session_state.messages.append({"role": "assistant", "content": gatekeeper_msg, "avatar": "🧠"})
                with st.chat_message("assistant", avatar="🧠"):
                    st.markdown(gatekeeper_msg)
                    
        st.rerun()

with col_right:
    st.subheader("📄 Post-Mortem Audit Trail")
    audit_dir = "audit_reports"
    if os.path.exists(audit_dir):
        files = sorted([f for f in os.listdir(audit_dir) if f.endswith('.json')], reverse=True)
        if files:
            for file in files[:5]: # Show latest 5
                with open(os.path.join(audit_dir, file), 'r') as f:
                    data = json.load(f)
                    with st.expander(f"Alert: {file.split('.')[0]}"):
                        st.json(data)
                        
                        metrics = data.get('metrics', {})
                        # Generate HTML Report
                        html_report = f"""
                        <html>
                        <head><title>Risk Audit Report</title></head>
                        <body style="font-family: Arial, sans-serif; padding: 20px;">
                            <h2>Risk Audit Report</h2>
                            <p><strong>Timestamp:</strong> {data.get('timestamp')}</p>
                            <hr>
                            <p><strong>Portfolio:</strong> {metrics.get('portfolio')}</p>
                            <p><strong>Total Exposure:</strong> ${metrics.get('exposure', 0):,.2f}</p>
                            <p><strong>Margin Utilization:</strong> {metrics.get('margin', 0)*100:.1f}%</p>
                            <br>
                            <p><strong>Status:</strong> {data.get('policy_triggered')}</p>
                            <p><strong>Action Taken:</strong> {data.get('action')}</p>
                            <br>
                            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #00d2ff; color: #333;">
                                <strong>AI Decision Details (Human Readable):</strong><br><br>
                                {data.get('policy_details', 'No details available.').replace('\n', '<br>')}
                            </div>
                        </body>
                        </html>
                        """
                        st.download_button(
                            label="⬇️ Download HTML Report",
                            data=html_report,
                            file_name=f"Audit_Report_{file.split('.')[0]}.html",
                            mime="text/html",
                            key=f"dl_{file}"
                        )
        else:
            st.info("No audit reports found yet.")
            
        if files:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Clear All Reports"):
                for file in files:
                    try:
                        os.remove(os.path.join(audit_dir, file))
                    except:
                        pass
                st.rerun()
    else:
        st.info("Audit directory not found.")
