import gradio as gr
import time
import json
import pdfplumber
import os
import uuid
from datetime import datetime


def extract_text_from_pdf(file_path):
    """Extract text from PDF file using pdfplumber"""
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"


def extract_text_from_file(file_path):
    """Extract text from various file formats"""
    if not file_path or not os.path.exists(file_path):
        return "No file uploaded or file not found."

    file_extension = os.path.splitext(file_path)[1].lower()

    try:
        if file_extension == ".pdf":
            return extract_text_from_pdf(file_path)
        elif file_extension in [".txt", ".doc", ".docx"]:
            # For now, handle TXT files. DOC/DOCX would need python-docx
            if file_extension == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            else:
                return f"File format {file_extension} is not yet supported. Please use PDF or TXT files."
        else:
            return f"Unsupported file format: {file_extension}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


# Simulate AI analysis function
def analyze_resume_content(resume_text, question_type):
    """Simulate resume analysis logic"""
    responses = {
        "Skills Assessment": f"Based on resume analysis, found the following skills: Python, Data Analysis, Machine Learning. Recommend strengthening Cloud Computing and DevOps skills.",
        "Experience Matching": f"Your work experience has high compatibility with target positions, especially in project management and team collaboration.",
        "Improvement Suggestions": f"Recommend adding quantified achievements to resume, such as 'Improved efficiency by 30%', 'Managed team of 10' and other specific data.",
        "Overall Evaluation": f"Resume structure is clear with rich content. Score: 8/10. Main strength is strong technical skills, needs improvement in industry keywords.",
    }

    # Simulate AI processing time
    time.sleep(1)

    return responses.get(question_type, "Please select a specific analysis type.")


def chat_with_resume(message, history, resume_file):
    """Handle chat conversation"""
    if not resume_file:
        bot_message = (
            "Please upload your resume file first, then I can help you analyze it."
        )
    else:
        # Extract text from the uploaded file
        extracted_text = extract_text_from_file(resume_file.name)

        # Check if text extraction was successful
        if extracted_text.startswith("Error") or extracted_text.startswith("No file"):
            bot_message = f"Failed to extract text from file: {extracted_text}"
        elif (
            "show text" in message.lower()
            or "display text" in message.lower()
            or "extract text" in message.lower()
        ):
            # Show extracted text if requested
            bot_message = f"**Extracted text from {os.path.basename(resume_file.name)}:**\n\n{extracted_text[:2000]}{'...' if len(extracted_text) > 2000 else ''}"
        else:
            # Use extracted text for analysis
            if "skill" in message.lower() or "技能" in message:
                bot_message = analyze_resume_content(
                    extracted_text, "Skills Assessment"
                )
            elif "experience" in message.lower() or "经验" in message:
                bot_message = analyze_resume_content(
                    extracted_text, "Experience Matching"
                )
            elif (
                "improve" in message.lower()
                or "suggest" in message.lower()
                or "建议" in message
            ):
                bot_message = analyze_resume_content(
                    extracted_text, "Improvement Suggestions"
                )
            elif (
                "evaluat" in message.lower()
                or "overall" in message.lower()
                or "评价" in message
                or "评分" in message
            ):
                bot_message = analyze_resume_content(
                    extracted_text, "Overall Evaluation"
                )
            else:
                bot_message = f"I have analyzed your resume file: {os.path.basename(resume_file.name)}. You can ask me about skills assessment, experience matching, improvement suggestions, or overall evaluation. You can also ask me to 'show text' to see the extracted content."

    # Add to chat history in messages format
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": bot_message})
    return "", history


def clear_chat():
    """Clear chat history"""
    return []


def quick_analyze(resume_file):
    """Quick analysis function"""
    if not resume_file:
        return "Please upload a resume file first."

    # Extract text from the uploaded file
    extracted_text = extract_text_from_file(resume_file.name)

    # Check if text extraction was successful
    if extracted_text.startswith("Error") or extracted_text.startswith("No file"):
        return f"**Analysis Failed**\n\n{extracted_text}"

    # Basic text analysis
    word_count = len(extracted_text.split())
    char_count = len(extracted_text)

    analysis = f"""
📄 **Quick Resume Analysis Report**

**File Information:** {os.path.basename(resume_file.name)}
**Text Length:** {word_count} words, {char_count} characters

**📝 Extracted Content Preview:**
{extracted_text[:500]}{'...' if len(extracted_text) > 500 else ''}

**🎯 Basic Analysis:**
- Document contains {word_count} words
- File format: {os.path.splitext(resume_file.name)[1].upper()}
- Content successfully extracted ✅

**💡 Quick Tips:**
1. Text has been successfully extracted from your resume
2. You can now ask specific questions about your content
3. Try asking: "show text" to see the full extracted content
4. Ask for skills assessment, experience matching, or improvement suggestions

**Next Steps:**
Use the chat interface to get detailed analysis of your resume content!
    """
    return analysis


# Global variables for session management
sessions = {}
current_session = None
current_mode = "upload"  # upload, resume_chat, mock_interview

def create_new_session(session_type, title):
    """Create a new session"""
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "id": session_id,
        "type": session_type,
        "title": title,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "messages": [],
        "resume_file": None,
        "job_description": ""
    }
    return session_id

def get_session_list():
    """Get formatted session list for sidebar"""
    if not sessions:
        return "No conversations yet"

    session_list = []
    for session_id, session in sessions.items():
        session_list.append(f"🗨️ {session['title']} ({session['created_at']})")
    return "\n".join(session_list)

def handle_file_upload(file, job_desc):
    """Handle resume file upload and create new session"""
    if not file:
        return None, "Please upload a resume file", get_session_list(), gr.update(visible=True), gr.update(visible=False), []

    # Create new session
    filename = os.path.basename(file.name)
    session_id = create_new_session("resume", f"Resume: {filename}")
    sessions[session_id]["resume_file"] = file
    sessions[session_id]["job_description"] = job_desc or ""

    # Extract and analyze resume
    extracted_text = extract_text_from_file(file.name)
    analysis = quick_analyze(file)

    # Add initial analysis to session
    initial_message = f"Resume uploaded successfully! {analysis}"
    sessions[session_id]["messages"] = [
        {"role": "assistant", "content": initial_message}
    ]

    global current_session
    current_mode = "resume_chat"
    current_session = session_id

    # Return session info and initial chat history
    initial_chat = [{"role": "assistant", "content": initial_message}]

    return session_id, "", get_session_list(), gr.update(visible=False), gr.update(visible=True), initial_chat

def switch_mode(mode):
    """Switch between resume chat and mock interview modes"""
    global current_mode
    current_mode = mode

    if mode == "resume_chat":
        return (
            gr.update(value="**📄 Resume Review Mode**"),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(variant="primary"),  # Resume button active
            gr.update(variant="secondary")  # Interview button inactive
        )
    else:  # mock_interview
        return (
            gr.update(value="**🎤 Mock Interview Mode**"),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(variant="secondary"),  # Resume button inactive
            gr.update(variant="primary")  # Interview button active
        )

def chat_message(message, history, session_id):
    """Handle chat messages"""
    if not session_id or session_id not in sessions:
        new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": "Please upload a resume first to start chatting."}]
        return "", new_history

    session = sessions[session_id]

    if current_mode == "resume_chat":
        # Resume review chat
        if session["resume_file"]:
            extracted_text = extract_text_from_file(session["resume_file"].name)

            if "skill" in message.lower() or "技能" in message:
                bot_response = analyze_resume_content(extracted_text, "Skills Assessment")
            elif "experience" in message.lower() or "经验" in message:
                bot_response = analyze_resume_content(extracted_text, "Experience Matching")
            elif "improve" in message.lower() or "suggest" in message.lower() or "建议" in message:
                bot_response = analyze_resume_content(extracted_text, "Improvement Suggestions")
            elif "evaluat" in message.lower() or "overall" in message.lower() or "评价" in message or "评分" in message:
                bot_response = analyze_resume_content(extracted_text, "Overall Evaluation")
            else:
                bot_response = f"I'm here to help you improve your resume! You can ask me about:\n\n• Skills assessment\n• Experience matching\n• Improvement suggestions\n• Overall evaluation\n\nWhat would you like to know?"
        else:
            bot_response = "No resume file found in this session."

    else:  # mock_interview
        # Mock interview chat
        interview_questions = [
            "Tell me about yourself and your background.",
            "Why are you interested in this position?",
            "What's your greatest strength?",
            "Describe a challenging project you've worked on.",
            "Where do you see yourself in 5 years?"
        ]

        # Simple mock interview logic
        question_count = len([msg for msg in session.get("messages", []) if msg["role"] == "assistant" and "Question" in msg.get("content", "")])

        if question_count < len(interview_questions):
            bot_response = f"**Interview Question {question_count + 1}:**\n\n{interview_questions[question_count]}\n\nTake your time to answer, and I'll provide feedback!"
        else:
            bot_response = "Great job! You've completed all the interview questions. Based on your responses, here's my feedback: Your answers show good preparation and enthusiasm. Consider adding more specific examples to strengthen your responses."

    # Update session messages
    session["messages"].extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": bot_response}
    ])

    # Update chat history - use messages format
    new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": bot_response}]

    return "", new_history

def new_conversation():
    """Start a new conversation"""
    global current_session, current_mode
    current_session = None
    current_mode = "upload"
    return [], get_session_list(), gr.update(visible=True), gr.update(visible=False)

# Custom CSS for OpenAI-like styling
custom_css = """
/* Remove default gradio margins and paddings */
.gradio-container {
    max-width: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* Main layout - full viewport height */
.main-container {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
    display: flex !important;
}

/* Sidebar styling */
.sidebar {
    background-color: #f8f9fa;
    padding: 20px;
    border-right: 1px solid #e5e7eb;
    height: 100vh !important;
    max-height: 100vh !important;
    width: 280px;
    min-width: 280px;
    overflow-y: auto;
    flex-shrink: 0;
}

/* Main content area */
.main-content {
    height: 100vh !important;
    max-height: 100vh !important;
    display: flex;
    flex-direction: column;
    flex: 1;
    overflow: hidden;
}

/* Upload area - centered */
.upload-area {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100vh !important;
    border: 2px dashed #d1d5db;
    border-radius: 12px;
    margin: 20px;
    background-color: #f9fafb;
    overflow: hidden;
}

/* Chat interface layout */
.chat-interface {
    height: 100vh !important;
    max-height: 100vh !important;
    display: flex;
    flex-direction: column;
    padding: 20px;
    overflow: hidden;
}

/* Mode switcher - fixed height */
.mode-switcher {
    background-color: #f3f4f6;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
    flex-shrink: 0;
    height: 70px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Mode display styling */
.mode-display {
    flex: 1;
    margin-right: 20px;
}

/* Mode buttons container */
.mode-buttons {
    display: flex;
    gap: 10px;
}

/* Mode button styling */
.mode-btn {
    padding: 8px 16px !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

.mode-btn.active {
    background-color: #3b82f6 !important;
    color: white !important;
    border-color: #3b82f6 !important;
}

.mode-btn.inactive {
    background-color: #e5e7eb !important;
    color: #6b7280 !important;
    border-color: #d1d5db !important;
}

/* Chat area - takes remaining space */
.chat-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
}

/* Chatbot container - scrollable */
.chatbot-container {
    flex: 1;
    overflow-y: auto !important;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    margin-bottom: 15px;
    min-height: 0;
}

/* Input area - fixed height */
.input-area {
    flex-shrink: 0;
    border-top: 1px solid #e5e7eb;
    padding-top: 15px;
    height: 80px;
    max-height: 80px;
}

/* Session list - scrollable */
.session-list {
    max-height: 50vh;
    overflow-y: auto;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 10px;
    margin-top: 10px;
}

.logo {
    font-size: 24px;
    font-weight: bold;
    color: #1f2937;
    margin-bottom: 20px;
    text-align: center;
    flex-shrink: 0;
}

/* Job description textarea */
.job-desc-area {
    max-height: 200px !important;
    height: 200px !important;
}

/* Remove gradio's default scroll behaviors */
.gradio-row, .gradio-column {
    min-height: 0 !important;
}

/* Override gradio defaults */
.gradio-container .block {
    border: none !important;
    box-shadow: none !important;
}

/* Ensure no body scrolling */
body {
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Fix gradio container */
#root {
    height: 100vh !important;
    overflow: hidden !important;
}

/* Prevent overflow on main elements */
.app {
    height: 100vh !important;
    overflow: hidden !important;
}

/* Specific gradio component adjustments */
.gr-file-upload {
    max-height: 150px !important;
}

.gr-textbox {
    max-height: inherit !important;
}

/* Button spacing */
.gr-button {
    margin: 5px 0 !important;
}
"""

# Create Gradio interface with OpenAI-like layout
with gr.Blocks(title="HireView - AI Resume & Interview Assistant", css=custom_css, theme=gr.themes.Soft()) as demo:

    with gr.Row(elem_classes="main-container"):
        # Left Sidebar
        with gr.Column(scale=1, elem_classes="sidebar"):
            gr.Markdown("# 🎯 HireView", elem_classes="logo")

            new_chat_btn = gr.Button("+ New Conversation", variant="primary", size="sm")

            gr.Markdown("### Recent Conversations")
            session_list = gr.Markdown(get_session_list(), elem_classes="session-list")

        # Main Content Area
        with gr.Column(scale=3, elem_classes="main-content"):
            # Hidden session state
            session_state = gr.State(value=None)

            # Upload Interface (visible initially)
            with gr.Column(visible=True, elem_classes="upload-area") as upload_interface:
                gr.Markdown("# Welcome to HireView")
                gr.Markdown("Upload your resume and job description to get started")

                with gr.Column():
                    resume_upload = gr.File(
                        label="📄 Upload Resume",
                        file_types=[".pdf", ".doc", ".docx", ".txt"],
                        type="filepath"
                    )

                    job_description = gr.Textbox(
                        label="💼 Job Description (Optional)",
                        placeholder="Paste the job description here to get more targeted advice...",
                        lines=6,
                        elem_classes="job-desc-area"
                    )

                    upload_btn = gr.Button("Start Analysis", variant="primary", size="lg")

            # Chat Interface (hidden initially)
            with gr.Column(visible=False, elem_classes="chat-interface") as chat_interface:
                # Mode switcher
                with gr.Row(elem_classes="mode-switcher"):
                    mode_display = gr.Markdown("**📄 Resume Review Mode**", elem_classes="mode-display")
                    with gr.Column(elem_classes="mode-buttons"):
                        with gr.Row():
                            resume_mode_btn = gr.Button("📄 Resume Review", variant="primary", size="sm", elem_classes="mode-btn")
                            interview_mode_btn = gr.Button("🎤 Mock Interview", variant="secondary", size="sm", elem_classes="mode-btn")

                # Chat area - takes remaining space
                with gr.Column(elem_classes="chat-area"):
                    chatbot = gr.Chatbot(
                        label="AI Assistant",
                        height=400,
                        show_label=False,
                        elem_classes="chatbot-container",
                        type="messages"
                    )

                    # Resume chat input (visible initially in chat mode)
                    with gr.Row(visible=True, elem_classes="input-area") as resume_input_area:
                        with gr.Column(scale=4):
                            chat_input = gr.Textbox(
                                placeholder="Ask me about your resume: skills assessment, improvement suggestions, etc.",
                                show_label=False,
                                lines=1,
                                max_lines=1
                            )
                        with gr.Column(scale=1):
                            send_btn = gr.Button("Send", variant="primary")

                    # Interview input area (hidden initially)
                    with gr.Row(visible=False, elem_classes="input-area") as interview_input_area:
                        with gr.Column(scale=4):
                            interview_input = gr.Textbox(
                                placeholder="Answer the interview question above...",
                                show_label=False,
                                lines=1,
                                max_lines=2
                            )
                        with gr.Column(scale=1):
                            interview_send_btn = gr.Button("Submit Answer", variant="primary")

    # Event handlers
    upload_btn.click(
        handle_file_upload,
        inputs=[resume_upload, job_description],
        outputs=[session_state, chat_input, session_list, upload_interface, chat_interface, chatbot]
    )

    send_btn.click(
        chat_message,
        inputs=[chat_input, chatbot, session_state],
        outputs=[chat_input, chatbot]
    )

    chat_input.submit(
        chat_message,
        inputs=[chat_input, chatbot, session_state],
        outputs=[chat_input, chatbot]
    )

    interview_send_btn.click(
        chat_message,
        inputs=[interview_input, chatbot, session_state],
        outputs=[interview_input, chatbot]
    )

    interview_input.submit(
        chat_message,
        inputs=[interview_input, chatbot, session_state],
        outputs=[interview_input, chatbot]
    )

    # Mode switching
    resume_mode_btn.click(
        lambda: switch_mode("resume_chat"),
        outputs=[mode_display, resume_input_area, interview_input_area, resume_mode_btn, interview_mode_btn]
    )

    interview_mode_btn.click(
        lambda: switch_mode("mock_interview"),
        outputs=[mode_display, resume_input_area, interview_input_area, resume_mode_btn, interview_mode_btn]
    )

    # New conversation
    new_chat_btn.click(
        new_conversation,
        outputs=[chatbot, session_list, upload_interface, chat_interface]
    )

# Launch application
if __name__ == "__main__":
    try:
        print("Starting Gradio application...")
        print(f"Server will be available at: http://127.0.0.1:7860")

        demo.launch(
            share=False,  # Disable share for packaged apps
            server_name="127.0.0.1",  # Use localhost for packaged apps
            server_port=7861,  # Use different port
            show_error=True,  # Show error messages
            quiet=False,  # Show startup messages
            prevent_thread_lock=False,  # Allow blocking
            inbrowser=True,  # Auto-open browser
        )
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
