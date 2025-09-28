import gradio as gr
import requests
import time
import json
import pdfplumber
import os
import uuid
import threading
import subprocess
from datetime import datetime
from typing import Optional, Dict, List

# Resume text truncation configuration
MAX_RESUME_LENGTH = 50000  # Maximum character count
MAX_RESUME_WORDS = 8000  # Maximum word count
TRUNCATION_MESSAGE = "\n\n[Note: Resume content was too long and has been truncated for processing efficiency]"

# FastAPI service configuration
FASTAPI_BASE_URL = "http://localhost:8000"
FASTAPI_PROCESS = None


def start_fastapi_service():
    """Start FastAPI service"""
    global FASTAPI_PROCESS
    try:
        # Check if service is already running
        response = requests.get(f"{FASTAPI_BASE_URL}/", timeout=2)
        if response.status_code == 200:
            print("FastAPI service is already running")
            return True

    except:
        pass

    # Start FastAPI service
    try:
        FASTAPI_PROCESS = subprocess.Popen(
            [
                "python",
                "-m",
                "uvicorn",
                "model_service:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
                "--reload",
            ],
            cwd=os.path.dirname(__file__),
        )

        # Wait for service to start
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get(f"{FASTAPI_BASE_URL}/", timeout=2)
                if response.status_code == 200:
                    print("FastAPI service started successfully")
                    return True
            except:
                time.sleep(1)

        print("Failed to start FastAPI service")
        return False
    except Exception as e:
        print(f"Error starting FastAPI service: {e}")
        return False


def truncate_resume_text(text):
    """Truncate overly long resume text"""
    if not text or text.startswith("Error") or text.startswith("No file"):
        return text

    # Check character count
    if len(text) > MAX_RESUME_LENGTH:
        text = text[:MAX_RESUME_LENGTH]
        text += TRUNCATION_MESSAGE
        return text

    # Check word count
    words = text.split()
    if len(words) > MAX_RESUME_WORDS:
        truncated_words = words[:MAX_RESUME_WORDS]
        text = " ".join(truncated_words)
        text += TRUNCATION_MESSAGE
        return text

    return text


def extract_text_from_pdf(file_path):
    """Extract text from PDF file using pdfplumber"""
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        # Truncate overly long text
        text = text.strip()
        return truncate_resume_text(text)
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
            if file_extension == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                    return truncate_resume_text(text)
            else:
                return f"File format {file_extension} is not yet supported. Please use PDF or TXT files."
        else:
            return f"Unsupported file format: {file_extension}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


# FastAPI client functions
class InterviewAPI:
    @staticmethod
    def create_interview(
        job_description: str, resume_content: str = ""
    ) -> Optional[Dict]:
        """创建面试会话"""
        try:
            data = {
                "job_description": job_description,
                "resume_file": resume_content if resume_content else None,
                "resume_session_id": None,
            }

            response = requests.post(
                f"{FASTAPI_BASE_URL}/api/interview/create", json=data, timeout=30
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error creating interview: {response.text}")
                return None
        except Exception as e:
            print(f"Error creating interview: {e}")
            return None

    @staticmethod
    def submit_answer(session_id: str, question_id: int, answer: str) -> Optional[Dict]:
        """提交问题回答"""
        try:
            data = {
                "session_id": session_id,
                "question_id": question_id,
                "answer": answer,
            }

            print(f"[GRADIO DEBUG] Submitting answer:")
            print(f"[GRADIO DEBUG] - session_id: {session_id}")
            print(f"[GRADIO DEBUG] - question_id: {question_id}")
            print(f"[GRADIO DEBUG] - answer length: {len(answer)}")
            print(f"[GRADIO DEBUG] - data: {data}")

            response = requests.post(
                f"{FASTAPI_BASE_URL}/api/interview/answer", json=data, timeout=30
            )

            print(f"[GRADIO DEBUG] Response status code: {response.status_code}")
            print(f"[GRADIO DEBUG] Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                result = response.json()
                print(f"[GRADIO DEBUG] Success response: {result}")
                return result
            else:
                print(f"[GRADIO DEBUG] Error response status: {response.status_code}")
                print(f"[GRADIO DEBUG] Error response text: {response.text}")
                print(f"Error submitting answer: {response.text}")
                return None
        except Exception as e:
            import traceback
            print(f"[GRADIO DEBUG] Exception in submit_answer: {str(e)}")
            print(f"[GRADIO DEBUG] Exception traceback: {traceback.format_exc()}")
            print(f"Error submitting answer: {e}")
            return None

    @staticmethod
    def get_conversation_history(session_id: str) -> Optional[Dict]:
        """获取对话历史"""
        try:
            response = requests.get(
                f"{FASTAPI_BASE_URL}/api/interview/conversation/{session_id}",
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting conversation: {response.text}")
                return None
        except Exception as e:
            print(f"Error getting conversation: {e}")
            return None

    @staticmethod
    def get_interview_summary(session_id: str) -> Optional[Dict]:
        """获取面试总结"""
        try:
            response = requests.get(
                f"{FASTAPI_BASE_URL}/api/interview/summary/{session_id}", timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting summary: {response.text}")
                return None
        except Exception as e:
            print(f"Error getting summary: {e}")
            return None


# Simulate AI analysis function for resume
def analyze_resume_content(resume_text, question_type):
    """Simulate resume analysis logic"""
    responses = {
        "Skills Assessment": f"Based on resume analysis, found the following skills: Python, data analysis, machine learning. Recommend strengthening cloud computing and DevOps skills.",
        "Experience Matching": f"Your work experience has high compatibility with the target position, especially in project management and team collaboration.",
        "Improvement Suggestions": f"Recommend adding quantified achievements to resume, such as specific data like 'improved efficiency by 30%', 'managed 10-person team'.",
        "Overall Evaluation": f"Resume structure is clear and content is rich. Rating: 8/10. Main advantage is strong technical skills, need to improve industry keywords.",
    }

    time.sleep(1)
    return responses.get(question_type, "Please select a specific analysis type.")


# Global variables for session management
sessions = {}
current_session = None
current_mode = "upload"  # upload, resume_chat, mock_interview
interview_session_id = None
current_question_id = None
question_start_time = None


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
        "job_description": "",
        "interview_session_id": None,
    }
    return session_id


def get_session_list():
    """Get formatted session list for sidebar"""
    if not sessions:
        return "No conversation records"

    session_list = []
    for session_id, session in sessions.items():
        icon = "📄" if session["type"] == "resume" else "🎤"
        active_mark = "★ " if session_id == current_session else ""
        session_list.append(
            f"{active_mark}{icon} {session['title']} ({session['created_at']})"
        )
    return "\n".join(session_list)


def handle_file_upload(file, job_desc):
    """Handle resume file upload and create new session"""
    if not file:
        return (
            None,
            "Please upload resume file",
            get_session_list(),
            gr.update(visible=True),
            gr.update(visible=False),
        )

    # Create new session
    filename = os.path.basename(file.name)
    session_id = create_new_session("resume", f"Resume: {filename}")
    sessions[session_id]["resume_file"] = file
    sessions[session_id]["job_description"] = job_desc or ""

    # Extract and analyze resume
    extracted_text = extract_text_from_file(file.name)

    analysis = f"""
📄 **Resume uploaded successfully!**

**File Info:** {filename}
**File Size:** {os.path.getsize(file.name)} bytes

**📝 Content Preview:**
{extracted_text[:300]}{'...' if len(extracted_text) > 300 else ''}

**🎯 Quick Analysis:**
- Document contains {len(extracted_text.split())} words
- File format: {os.path.splitext(file.name)[1].upper()}
- Content extraction successful ✅

**💡 Usage Suggestions:**
1. Switch to "Resume Review" mode for detailed analysis
2. Switch to "Mock Interview" mode to start interview practice
3. You can ask about skills assessment, experience matching, or improvement suggestions anytime

**Next Step:** Choose your desired feature mode!
    """

    # Add initial analysis to session
    sessions[session_id]["messages"] = [{"role": "assistant", "content": analysis}]

    global current_session
    current_session = session_id

    return (
        session_id,
        "",
        get_session_list(),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(choices=get_session_choices(), value=session_id),
    )


def switch_mode(mode):
    """Switch between resume chat and mock interview modes"""
    global current_mode, interview_session_id, current_question_id, current_session
    current_mode = mode

    if mode == "resume_chat":
        return (
            gr.update(value="**Resume Review Mode**"),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="**Job Description:** To be entered"),
        )
    else:  # mock_interview
        # 重置面试状态
        interview_session_id = None
        current_question_id = None

        # Get current session job description
        job_desc_text = "**Job Description:** To be entered"
        if current_session and current_session in sessions:
            job_description = sessions[current_session].get("job_description", "")
            if job_description.strip():
                # Limit display length to avoid taking up too much space
                display_desc = (
                    job_description[:200] + "..."
                    if len(job_description) > 200
                    else job_description
                )
                job_desc_text = f"**Job Description:** {display_desc}"

        return (
            gr.update(value="**Mock Interview Mode**"),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(value=job_desc_text),
        )


def start_interview():
    """开始模拟面试"""
    global interview_session_id, current_question_id, question_start_time, current_session

    if not current_session or current_session not in sessions:
        return "Please upload resume first", []

    session = sessions[current_session]
    job_description = session.get("job_description", "")

    if not job_description.strip():
        return "Please provide job description when uploading resume", []

    # 获取简历内容
    resume_content = ""
    if session.get("resume_file"):
        resume_content = extract_text_from_file(session["resume_file"].name)
        if resume_content.startswith("Error") or resume_content.startswith("No file"):
            resume_content = ""

    # 创建面试会话
    interview_data = InterviewAPI.create_interview(
        job_description=job_description, resume_content=resume_content
    )

    if not interview_data or not interview_data.get("success"):
        return "Failed to create interview session, please check service connection", []

    interview_session_id = interview_data["session_id"]
    sessions[current_session]["interview_session_id"] = interview_session_id

    first_question = interview_data.get("first_question", {})
    current_question_id = first_question.get("question_id", 1)
    question_start_time = time.time()

    interview_plan = interview_data.get("interview_plan", {})

    welcome_msg = f"""
🎤 **Interview Started!**

**Job Description:**
{job_description}

**Interview Info:**
- Total Questions: {interview_plan.get('total_questions', 'Unknown')}
- Estimated Time: 30 minutes
- Interview Type: Comprehensive Interview

**First Question:**
{first_question.get('question', 'Failed to load question')}


    """

    history = [{"role": "assistant", "content": welcome_msg}]

    return "", history


def submit_interview_answer(answer, history):
    """提交面试答案"""
    global interview_session_id, current_question_id, question_start_time

    print(f"[GRADIO DEBUG] submit_interview_answer called:")
    print(f"[GRADIO DEBUG] - interview_session_id: {interview_session_id}")
    print(f"[GRADIO DEBUG] - current_question_id: {current_question_id}")
    print(f"[GRADIO DEBUG] - answer: {answer}")

    if not interview_session_id or not current_question_id:
        print(f"[GRADIO DEBUG] Missing session or question ID")
        new_history = history + [
            {"role": "user", "content": answer},
            {"role": "assistant", "content": "Interview session not found, please restart the interview"},
        ]
        return "", new_history

    if not answer.strip():
        print(f"[GRADIO DEBUG] Empty answer provided")
        new_history = history + [
            {"role": "assistant", "content": "Please provide your answer before submitting"}
        ]
        return "", new_history

    print(f"[GRADIO DEBUG] About to call submit_answer API")

    # 提交答案
    result = InterviewAPI.submit_answer(
        session_id=interview_session_id, question_id=current_question_id, answer=answer
    )

    print(f"[GRADIO DEBUG] API call result: {result}")

    if not result or not result.get("success"):
        new_history = history + [
            {"role": "user", "content": answer},
            {"role": "assistant", "content": "Failed to submit answer, please try again"},
        ]
        return "", new_history

    # 获取反馈
    feedback = result.get("feedback", {})
    progress = result.get("progress", {})

    feedback_msg = f"""
✅ **Answer Submitted!**

**Your Answer:**
{answer}

**AI Evaluation Feedback:**
- **Score:** {feedback.get('score', 0)}/10
- **Strengths:** {', '.join(feedback.get('strengths', []))}
- **Improvement Suggestions:** {', '.join(feedback.get('improvements', []))}

**Detailed Feedback:**
{feedback.get('detailed_feedback', 'No detailed feedback available')}

**Interview Progress:** {progress.get('current_question', 0)}/{progress.get('total_questions', 0)} ({progress.get('completed_percentage', 0):.1f}%)
"""

    new_history = history + [
        {"role": "user", "content": answer},
        {"role": "assistant", "content": feedback_msg},
    ]

    # 检查是否有下一个问题
    if "next_question" in result:
        next_q = result["next_question"]
        current_question_id = next_q["question_id"]
        question_start_time = time.time()

        next_question_msg = f"""
---

**Next Question (#{current_question_id}):**
{next_q['question']}

Please continue with your answer! 💪
        """

        new_history.append({"role": "assistant", "content": next_question_msg})

    else:
        # 面试结束
        interview_session_id = None
        current_question_id = None

        completion_msg = """
🎉 **Congratulations! Interview Completed!**

Thank you for participating in this mock interview. You can:
1. View complete interview summary and evaluation
2. Start new interview practice
3. Return to resume review mode

All conversation records from this interview have been saved and you can review them anytime.
        """

        new_history.append({"role": "assistant", "content": completion_msg})

    return "", new_history


def get_interview_summary_display():
    """获取面试总结"""
    global interview_session_id

    if not interview_session_id:
        return "暂无面试会话"

    summary = InterviewAPI.get_interview_summary(interview_session_id)
    if not summary or not summary.get("success"):
        return "获取面试总结失败"

    summary_data = summary
    detailed_feedback = summary_data.get("detailed_feedback", {})

    summary_text = f"""
📊 **面试总结报告**

**基本信息:**
- 会话ID: {summary_data.get('session_id', '未知')}
- 面试状态: {'已完成' if summary_data.get('interview_completed') else '进行中'}
- 总评分: {summary_data.get('overall_score', 0)}/10
- 预计时长: {summary_data.get('duration_minutes', 0)}分钟

**答题统计:**
- 总问题数: {summary_data.get('summary', {}).get('total_questions', 0)}
- 已回答: {summary_data.get('summary', {}).get('answered_questions', 0)}
- 平均得分: {summary_data.get('summary', {}).get('average_score', 0)}

**分类评分:**
{chr(10).join([f"- {k}: {v}/10" for k, v in summary_data.get('summary', {}).get('category_scores', {}).items()])}

**详细反馈:**

**💪 优势:**
{chr(10).join(['- ' + s for s in detailed_feedback.get('strengths', [])])}

**📈 改进建议:**
{chr(10).join(['- ' + s for s in detailed_feedback.get('areas_for_improvement', [])])}

**🎯 推荐练习:**
{chr(10).join(['- ' + s for s in detailed_feedback.get('recommendations', [])])}
    """

    return summary_text


def chat_message(message, history, session_id):
    """Handle chat messages"""
    if not session_id or session_id not in sessions:
        new_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "请先上传简历开始对话"},
        ]
        return "", new_history

    session = sessions[session_id]

    if current_mode == "resume_chat":
        # Resume review chat
        if session["resume_file"]:
            extracted_text = extract_text_from_file(session["resume_file"].name)

            if "skill" in message.lower() or "技能" in message:
                bot_response = analyze_resume_content(
                    extracted_text, "Skills Assessment"
                )
            elif "experience" in message.lower() or "经验" in message:
                bot_response = analyze_resume_content(
                    extracted_text, "Experience Matching"
                )
            elif (
                "improve" in message.lower()
                or "suggest" in message.lower()
                or "建议" in message
            ):
                bot_response = analyze_resume_content(
                    extracted_text, "Improvement Suggestions"
                )
            elif (
                "evaluat" in message.lower()
                or "overall" in message.lower()
                or "评价" in message
                or "评分" in message
            ):
                bot_response = analyze_resume_content(
                    extracted_text, "Overall Evaluation"
                )
            else:
                bot_response = """我可以帮您分析简历! 您可以询问:

🔍 **技能评估** - 输入包含"技能"的问题
📊 **经验匹配** - 输入包含"经验"的问题
💡 **改进建议** - 输入包含"建议"的问题
📋 **整体评价** - 输入包含"评价"的问题

例如: "请分析我的技能"、"给出改进建议"等

您想了解什么方面呢?"""
        else:
            bot_response = "此会话中未找到简历文件"

    # Update session messages
    session["messages"].extend(
        [
            {"role": "user", "content": message},
            {"role": "assistant", "content": bot_response},
        ]
    )

    # Update chat history
    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": bot_response},
    ]

    return "", new_history


def get_session_choices():
    """获取会话选择列表"""
    if not sessions:
        return []

    choices = []
    for session_id, session in sessions.items():
        icon = "📄" if session["type"] == "resume" else "🎤"
        choices.append(
            (f"{icon} {session['title']} ({session['created_at']})", session_id)
        )
    return choices


def select_conversation(session_choice):
    """选择对话记录"""
    global current_session, current_mode

    if not session_choice or session_choice not in sessions:
        return (
            [],
            get_session_list(),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(choices=get_session_choices()),
        )

    current_session = session_choice
    session = sessions[session_choice]

    # 恢复对话历史
    history = session.get("messages", [])

    # 切换到聊天界面
    return (
        history,
        get_session_list(),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(choices=get_session_choices()),
    )


def new_conversation():
    """Start a new conversation"""
    global current_session, current_mode, interview_session_id, current_question_id
    current_session = None
    current_mode = "upload"
    interview_session_id = None
    current_question_id = None
    return (
        [],
        get_session_list(),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(choices=get_session_choices(), value=None),
    )


# Custom CSS for styling
custom_css = """
.sidebar {
    background-color: #f8f9fa;
    padding: 20px;
    border-right: 1px solid #e5e7eb;
    height: 100vh;
    overflow-y: auto;
}

.main-content {
    height: 100vh;
    display: flex;
    flex-direction: column;
}

.upload-area {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 60vh;
    border: 2px dashed #d1d5db;
    border-radius: 12px;
    margin: 20px;
    background-color: #f9fafb;
}

.chat-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 20px;
}

.mode-switcher {
    background-color: #f3f4f6;
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 20px;
}

.logo {
    font-size: 24px;
    font-weight: bold;
    color: #1f2937;
    margin-bottom: 30px;
    text-align: center;
}

.interview-config {
    background-color: #f0f9ff;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
    border: 1px solid #0ea5e9;
    max-height: 150px;
    overflow-y: auto;
}

.session-list {
    cursor: pointer;
    font-size: 14px;
    line-height: 1.5;
}

.session-list:hover {
    background-color: #f3f4f6;
}

.job-description-display {
    max-height: 80px;
    overflow-y: auto;
    word-wrap: break-word;
    font-size: 14px;
    line-height: 1.4;
}
"""

# 启动FastAPI服务
print("正在启动FastAPI模型服务...")
if start_fastapi_service():
    print("FastAPI服务启动成功")
else:
    print("FastAPI服务启动失败")

# Create Gradio interface
with gr.Blocks(
    title="HireView - AI Resume & Interview Assistant",
    css=custom_css,
    theme=gr.themes.Soft(),
) as demo:

    with gr.Row():
        # Left Sidebar
        with gr.Column(scale=1, elem_classes="sidebar"):
            gr.Markdown("# 🎯 HireView", elem_classes="logo")

            new_chat_btn = gr.Button("+ New Conversation", variant="primary", size="sm")

            gr.Markdown("### Conversation History")

            # Conversation selection dropdown
            session_dropdown = gr.Dropdown(
                label="Select Conversation",
                choices=get_session_choices(),
                interactive=True,
                value=current_session,
            )

            session_list = gr.Markdown(get_session_list())

        # Main Content Area
        with gr.Column(scale=3, elem_classes="main-content"):
            # Hidden session state
            session_state = gr.State(value=None)

            # Upload Interface (visible initially)
            with gr.Column(
                visible=True, elem_classes="upload-area"
            ) as upload_interface:
                gr.Markdown("# Welcome to HireView", elem_classes="text-center")
                gr.Markdown("Upload your resume and job description to get started")

                with gr.Row():
                    with gr.Column():
                        resume_upload = gr.File(
                            label="📄 Upload Resume",
                            file_types=[".pdf", ".doc", ".docx", ".txt"],
                            type="filepath",
                        )

                        job_description = gr.Textbox(
                            label="💼 Job Description (Optional)",
                            placeholder="Paste the job description here to get more targeted advice...",
                            lines=8,
                        )

                        upload_btn = gr.Button(
                            "Start Analysis", variant="primary", size="lg"
                        )

            # Chat Interface (hidden initially)
            with gr.Column(visible=False) as chat_interface:
                # Mode switcher
                with gr.Row(elem_classes="mode-switcher"):
                    mode_display = gr.Markdown("**Resume Review Mode**")
                    resume_mode_btn = gr.Button(
                        "Resume Review", variant="secondary", size="sm"
                    )
                    interview_mode_btn = gr.Button(
                        "Mock Interview", variant="secondary", size="sm"
                    )

                # Interview configuration (hidden initially)
                with gr.Column(
                    visible=False, elem_classes="interview-config"
                ) as interview_config:
                    gr.Markdown("### 🎤 Interview Configuration")

                    # Display user-entered job description
                    job_description_display = gr.Markdown(
                        value="**Job Description:** To be entered",
                        elem_classes="job-description-display",
                    )

                    start_interview_btn = gr.Button(
                        "Start Interview", variant="primary"
                    )

                # Chat area
                chatbot = gr.Chatbot(
                    label="AI Assistant",
                    height=500,
                    show_label=False,
                    elem_classes="chat-container",
                    type="messages",
                )

                # Resume chat input (visible initially in chat mode)
                with gr.Row(visible=True) as resume_input_area:
                    with gr.Column(scale=4):
                        chat_input = gr.Textbox(
                            placeholder="Ask resume-related questions: skills assessment, improvement suggestions, etc.",
                            show_label=False,
                            lines=1,
                        )
                    with gr.Column(scale=1):
                        send_btn = gr.Button("Send", variant="primary")

                # Interview input area (hidden initially)
                with gr.Row(visible=False) as interview_input_area:
                    with gr.Column(scale=4):
                        interview_input = gr.Textbox(
                            placeholder="Answer the interview question above...",
                            show_label=False,
                            lines=3,
                        )
                    with gr.Column(scale=1):
                        interview_send_btn = gr.Button(
                            "Submit Answer", variant="primary"
                        )

                # Interview summary (hidden initially)
                with gr.Row(visible=False) as summary_area:
                    summary_btn = gr.Button(
                        "View Interview Summary", variant="secondary"
                    )

    # Event handlers
    upload_btn.click(
        handle_file_upload,
        inputs=[resume_upload, job_description],
        outputs=[
            session_state,
            chat_input,
            session_list,
            upload_interface,
            chat_interface,
            session_dropdown,
        ],
    )

    send_btn.click(
        chat_message,
        inputs=[chat_input, chatbot, session_state],
        outputs=[chat_input, chatbot],
    )

    chat_input.submit(
        chat_message,
        inputs=[chat_input, chatbot, session_state],
        outputs=[chat_input, chatbot],
    )

    # Interview start
    start_interview_btn.click(
        start_interview,
        inputs=[],
        outputs=[interview_input, chatbot],
    )

    interview_send_btn.click(
        submit_interview_answer,
        inputs=[interview_input, chatbot],
        outputs=[interview_input, chatbot],
    )

    interview_input.submit(
        submit_interview_answer,
        inputs=[interview_input, chatbot],
        outputs=[interview_input, chatbot],
    )

    # Mode switching
    resume_mode_btn.click(
        lambda: switch_mode("resume_chat"),
        outputs=[
            mode_display,
            resume_input_area,
            interview_input_area,
            interview_config,
            job_description_display,
        ],
    )

    interview_mode_btn.click(
        lambda: switch_mode("mock_interview"),
        outputs=[
            mode_display,
            resume_input_area,
            interview_input_area,
            interview_config,
            job_description_display,
        ],
    )

    # Session selection
    session_dropdown.change(
        select_conversation,
        inputs=[session_dropdown],
        outputs=[
            chatbot,
            session_list,
            upload_interface,
            chat_interface,
            session_dropdown,
        ],
    )

    # New conversation
    new_chat_btn.click(
        new_conversation,
        outputs=[
            chatbot,
            session_list,
            upload_interface,
            chat_interface,
            session_dropdown,
        ],
    )

    # Summary display
    summary_btn.click(
        get_interview_summary_display,
        outputs=[chatbot],
    )

# Launch application
if __name__ == "__main__":
    try:
        print("正在启动Gradio应用...")
        print(f"服务地址: http://127.0.0.1:7863")

        demo.launch(
            share=False,
            server_name="127.0.0.1",
            server_port=7863,
            show_error=True,
            quiet=False,
            prevent_thread_lock=False,
            inbrowser=True,
        )
    except Exception as e:
        print(f"启动应用时出错: {e}")
        import traceback

        traceback.print_exc()
        input("按Enter退出...")
    finally:
        # 清理FastAPI进程
        if FASTAPI_PROCESS:
            FASTAPI_PROCESS.terminate()
