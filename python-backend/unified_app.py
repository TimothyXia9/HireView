import gradio as gr
import threading
import time
import json
import pdfplumber
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, List
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from imagine import ImagineClient
import re
from random import choice

# ================================
# FastAPI Backend Service (整合的model_service)
# ================================

# 创建FastAPI应用
fastapi_app = FastAPI(title="Interview Model Service", version="1.0.0")

# CORS配置
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置
HISTORY_FILE = "conversation_history.json"
SESSIONS_FILE = "sessions.json"
CONVERSATIONS_DIR = "conversations"
MAX_HISTORY = 50

# 确保对话目录存在
if not os.path.exists(CONVERSATIONS_DIR):
    os.makedirs(CONVERSATIONS_DIR)

# 初始化客户端
client = ImagineClient(
    debug=False,
    max_retries=3,
    endpoint="https://aisuite.cirrascale.com/apis/v2",
    api_key="755477ca-2fc5-4df7-b96b-a199b77c41ec",
)

# 数据模型
class InterviewCreateRequest(BaseModel):
    resume_session_id: Optional[str] = None
    resume_file: Optional[str] = None
    job_description: str

class InterviewAnswerRequest(BaseModel):
    session_id: str
    question_id: int
    answer: str

class Question(BaseModel):
    question_id: int
    question: str

class Feedback(BaseModel):
    score: float
    strengths: List[str]
    improvements: List[str]
    detailed_feedback: str

# 会话存储
sessions: Dict[str, Dict] = {}

# Session management functions
def load_sessions():
    global sessions
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                loaded_sessions = json.load(f)
            sessions = {}
            for session_id, session_data in loaded_sessions.items():
                cleaned_session = {
                    k: v for k, v in session_data.items()
                    if k not in ["interview_type", "difficulty_level", "duration_minutes"]
                }
                if "questions" in cleaned_session:
                    cleaned_questions = []
                    for q in cleaned_session["questions"]:
                        cleaned_q = {
                            k: v for k, v in q.items()
                            if k not in ["type", "time_limit"]
                        }
                        cleaned_questions.append(cleaned_q)
                    cleaned_session["questions"] = cleaned_questions
                sessions[session_id] = cleaned_session
            save_sessions()
        except Exception as e:
            print(f"[DEBUG] Error loading sessions: {e}")
            sessions = {}

def save_sessions():
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

def save_conversation_history(session_id: str, conversation_data: Dict):
    conversation_file = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
    with open(conversation_file, "w", encoding="utf-8") as f:
        json.dump(conversation_data, f, ensure_ascii=False, indent=2)

def load_conversation_history(session_id: str) -> Optional[Dict]:
    conversation_file = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
    if os.path.exists(conversation_file):
        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def update_conversation_history(session_id: str, role: str, message: str, extra_data: Optional[Dict] = None):
    conversation = load_conversation_history(session_id) or {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "conversation_history": [],
    }
    message_entry = {
        "role": role,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }
    if extra_data:
        message_entry.update(extra_data)
    conversation["conversation_history"].append(message_entry)
    save_conversation_history(session_id, conversation)

# Question generation functions
def generate_personalized_questions(job_description: str, resume_content: str, num_questions: int = 3) -> List[Question]:
    """生成个性化面试问题"""
    try:
        full_prompt = f"""
You are a professional HR interviewer. Please generate targeted interview questions based on the provided job description and candidate's resume.

Requirements:
1. Questions should target the candidate's specific experience and skills
2. Combine job requirements to focus on assessing fit
3. Questions should be layered, from shallow to deep

Write each question on a new line ending with ?
Do not use JSON, brackets, or any special formatting.
Just write plain questions, one per line.

Job Description:
{job_description}

Candidate Resume:
{resume_content}

Please generate {num_questions} targeted interview questions:
"""
        chat_messages = [{"role": "user", "content": full_prompt}]
        response = client.chat(
            messages=chat_messages,
            model="Llama-3.1-8B",
            max_tokens=1024,
            tools=[],
        )
        content = response.first_content
        questions = parse_plain_text_questions(content, num_questions)
        if len(questions) < num_questions:
            fallback_needed = num_questions - len(questions)
            fallback_questions = get_fallback_questions(fallback_needed)
            questions.extend(fallback_questions)
        return questions[:num_questions]
    except Exception as e:
        print(f"Error generating personalized questions: {e}")
        return get_fallback_questions(num_questions)

def parse_plain_text_questions(content: str, expected_count: int) -> List[Question]:
    """解析纯文本格式的问题"""
    questions = []
    lines = content.strip().split("\n")
    question_id = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue
        skip_patterns = [
            r"^(questions?:?|here are|below are)",
            r"^(问题[:：]?|以下是)",
            r"^[\-=\*]{3,}",
            r"^(note|注意|说明)[:：]",
        ]
        should_skip = False
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                should_skip = True
                break
        if should_skip:
            continue
        cleaned_question = clean_question_text(line)
        if is_valid_question(cleaned_question):
            questions.append(Question(question_id=question_id, question=cleaned_question))
            question_id += 1
            if len(questions) >= expected_count:
                break
    return questions

def clean_question_text(text: str) -> str:
    """清理问题文本，移除不必要的格式"""
    patterns_to_remove = [
        r"^\d+[\.\)]\s*",
        r"^[Q]\d*[:：]?\s*",
        r"^[问]\d*[:：]?\s*",
        r"^[\-\*\+]\s*",
        r"^[•·]\s*",
    ]
    cleaned = text
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    if cleaned and not cleaned.endswith("?") and not cleaned.endswith("？"):
        question_indicators = [
            "how", "what", "why", "when", "where", "which", "who",
            "can you", "could you", "would you", "do you", "have you", "are you",
        ]
        if any(cleaned.lower().startswith(indicator) for indicator in question_indicators):
            cleaned += "?"
    return cleaned

def is_valid_question(text: str) -> bool:
    """验证是否是有效的问题"""
    if not text or len(text.strip()) < 10:
        return False
    has_question_mark = "?" in text or "？" in text
    question_words = [
        "how", "what", "why", "when", "where", "which", "who",
        "can", "could", "would", "do", "does", "did",
        "have", "has", "had", "are", "is", "was", "were", "will",
    ]
    has_question_word = any(word in text.lower() for word in question_words)
    invalid_patterns = [
        r"^(thank|thanks|here|below|above|note|please|kindly)",
        r"(sincerely|regards|best|cheers)$",
        r"^\d+$",
    ]
    for pattern in invalid_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False
    return has_question_mark or has_question_word

def get_fallback_questions(num_questions: int) -> List[Question]:
    """获取默认备用问题"""
    fallback_questions = [
        "Please introduce yourself and highlight your most relevant experience.",
        "Why are you interested in this position and our company?",
        "What are your long-term career goals and how does this role fit in?",
        "Describe a challenging problem you've solved in your previous work.",
        "What do you consider your greatest strength and how would it benefit this role?",
        "Tell me about a time when you had to learn a new technology or skill quickly.",
        "How do you handle working under pressure and tight deadlines?",
        "Describe a situation where you had to work with a difficult team member.",
        "What motivates you in your work?",
        "Where do you see yourself in 5 years?",
    ]
    questions = []
    for i in range(min(num_questions, len(fallback_questions))):
        questions.append(Question(question_id=i + 1, question=fallback_questions[i]))
    return questions

def chat_with_llama(messages: List[Dict[str, str]], context: str = "") -> str:
    try:
        system_prompt = f"""You are a professional interviewer AI assistant. {context}

Please provide constructive feedback based on the candidate's answer, including:
1. Strengths of the answer
2. Areas for improvement
3. Specific suggestions
4. Score from 1-10

Please maintain a professional and friendly tone."""
        chat_messages = [{"role": "system", "content": system_prompt}] + messages
        response = client.chat(messages=chat_messages, model="Llama-3.1-8B", max_tokens=512)
        return response.first_content
    except Exception as e:
        return f"Evaluation error: {str(e)}"

# FastAPI Routes
@fastapi_app.post("/api/interview/create")
async def create_interview(request: InterviewCreateRequest):
    try:
        session_id = f"interview_session_{uuid.uuid4().hex[:8]}"
        total_questions = 3
        resume_content = ""
        if request.resume_session_id:
            resume_content = f"Resume from session {request.resume_session_id}"
        elif request.resume_file:
            resume_content = request.resume_file
        if resume_content.strip():
            questions = generate_personalized_questions(request.job_description, resume_content, total_questions)
        else:
            raise HTTPException(status_code=400, detail="Resume content is required")
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "job_info": {"description": request.job_description},
            "questions": [q.dict() for q in questions],
            "current_question": 0,
            "answers": [],
            "status": "in_progress",
        }
        sessions[session_id] = session_data
        save_sessions()
        initial_message = "Starting mock interview"
        update_conversation_history(session_id, "system", initial_message, {"job_info": session_data["job_info"]})
        if questions:
            update_conversation_history(session_id, "assistant", questions[0].question, {"question_id": questions[0].question_id})
        return {
            "success": True,
            "session_id": session_id,
            "interview_plan": {"total_questions": total_questions},
            "first_question": questions[0].dict() if questions else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.post("/api/interview/answer")
async def submit_answer(request: InterviewAnswerRequest):
    try:
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        session = sessions[request.session_id]
        questions = session["questions"]
        if request.question_id > len(questions) or request.question_id < 1:
            raise HTTPException(status_code=400, detail="Invalid question ID")
        current_question = questions[request.question_id - 1]
        context = f"""
        Question: {current_question['question']}
        Answer: {request.answer}
        """
        messages = [{"role": "user", "content": f"Please evaluate this interview answer:\n{context}"}]
        feedback_text = chat_with_llama(messages, context)
        score = 7.5
        strengths = ["Complete answer"]
        improvements = ["Could include specific examples"]
        feedback = Feedback(
            score=score,
            strengths=strengths,
            improvements=improvements,
            detailed_feedback=feedback_text,
        )
        answer_data = {
            "question_id": request.question_id,
            "question": current_question["question"],
            "answer": request.answer,
            "feedback": feedback.dict(),
            "timestamp": datetime.now().isoformat(),
        }
        session["answers"].append(answer_data)
        session["current_question"] = request.question_id
        update_conversation_history(request.session_id, "user", request.answer, {
            "question_id": request.question_id,
            "question_text": current_question["question"],
        })
        update_conversation_history(request.session_id, "assistant", feedback_text, {
            "feedback_type": "evaluation",
            "score": feedback.score,
            "strengths": feedback.strengths,
            "improvements": feedback.improvements,
            "question_id": request.question_id,
        })
        next_question = None
        if request.question_id < len(questions):
            next_question = questions[request.question_id]
            update_conversation_history(request.session_id, "assistant", next_question["question"], {
                "question_id": next_question["question_id"],
            })
        else:
            session["status"] = "completed"
            update_conversation_history(request.session_id, "system",
                "thank you for completing the interview. The interview is now concluded.",
                {"interview_completed": True})
        progress = {
            "current_question": request.question_id + 1,
            "total_questions": len(questions),
            "completed_percentage": (request.question_id / len(questions)) * 100,
        }
        sessions[request.session_id] = session
        save_sessions()
        response_data = {
            "success": True,
            "session_id": request.session_id,
            "feedback": feedback.dict(),
            "progress": progress,
        }
        if next_question:
            response_data["next_question"] = next_question
        return response_data
    except Exception as e:
        import traceback
        print(f"[DEBUG] Exception in submit_answer: {str(e)}")
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/api/interview/summary/{session_id}")
async def get_interview_summary(session_id: str):
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        session = sessions[session_id]
        answers = session["answers"]
        if not answers:
            raise HTTPException(status_code=400, detail="No answers found")
        total_score = sum(answer["feedback"]["score"] for answer in answers)
        average_score = total_score / len(answers)
        category_scores = {"overall": average_score}
        strengths = ["Strong technical knowledge", "Good communication skills"]
        improvements = ["Could prepare more specific examples", "Answers could be more concise"]
        recommendations = ["Practice STAR method for behavioral questions", "Prepare 2-3 in-depth technical project examples"]
        return {
            "success": True,
            "session_id": session_id,
            "interview_completed": session["status"] == "completed",
            "overall_score": round(average_score, 1),
            "summary": {
                "total_questions": len(session["questions"]),
                "answered_questions": len(answers),
                "average_score": round(average_score, 1),
                "category_scores": category_scores,
            },
            "detailed_feedback": {
                "strengths": strengths,
                "areas_for_improvement": improvements,
                "recommendations": recommendations,
            },
            "question_details": answers,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/api/interview/conversation/{session_id}")
async def get_conversation_history_api(session_id: str):
    """获取会话的完整对话历史"""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        conversation_history = load_conversation_history(session_id)
        if not conversation_history:
            raise HTTPException(status_code=404, detail="Conversation history not found")
        return {
            "success": True,
            "session_id": session_id,
            "created_at": conversation_history["created_at"],
            "conversation_history": conversation_history["conversation_history"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@fastapi_app.get("/")
async def root():
    return {"message": "Interview Model Service is running"}

# 启动时加载会话
load_sessions()

# ================================
# Gradio Frontend (整合的integrated_app)
# ================================

# Resume text truncation configuration
MAX_RESUME_LENGTH = 50000
MAX_RESUME_WORDS = 8000
TRUNCATION_MESSAGE = "\n\n[Note: Resume content was too long and has been truncated for processing efficiency]"

# FastAPI service configuration
FASTAPI_BASE_URL = "http://localhost:8000"

def truncate_resume_text(text):
    """Truncate overly long resume text"""
    if not text or text.startswith("Error") or text.startswith("No file"):
        return text
    if len(text) > MAX_RESUME_LENGTH:
        text = text[:MAX_RESUME_LENGTH]
        text += TRUNCATION_MESSAGE
        return text
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
import requests

class InterviewAPI:
    @staticmethod
    def create_interview(job_description: str, resume_content: str = "") -> Optional[Dict]:
        """创建面试会话"""
        try:
            data = {
                "job_description": job_description,
                "resume_file": resume_content if resume_content else None,
                "resume_session_id": None,
            }
            response = requests.post(f"{FASTAPI_BASE_URL}/api/interview/create", json=data, timeout=30)
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
            response = requests.post(f"{FASTAPI_BASE_URL}/api/interview/answer", json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                print(f"Error submitting answer: {response.text}")
                return None
        except Exception as e:
            print(f"Error submitting answer: {e}")
            return None

    @staticmethod
    def get_conversation_history(session_id: str) -> Optional[Dict]:
        """获取对话历史"""
        try:
            response = requests.get(f"{FASTAPI_BASE_URL}/api/interview/conversation/{session_id}", timeout=10)
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
            response = requests.get(f"{FASTAPI_BASE_URL}/api/interview/summary/{session_id}", timeout=10)
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
gradio_sessions = {}
current_session = None
current_mode = "upload"
interview_session_id = None
current_question_id = None
question_start_time = None

def create_new_session(session_type, title):
    """Create a new session"""
    session_id = str(uuid.uuid4())[:8]
    gradio_sessions[session_id] = {
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
    if not gradio_sessions:
        return "No conversation records"
    session_list = []
    for session_id, session in gradio_sessions.items():
        icon = "📄" if session["type"] == "resume" else "🎤"
        active_mark = "★ " if session_id == current_session else ""
        session_list.append(f"{active_mark}{icon} {session['title']} ({session['created_at']})")
    return "\n".join(session_list)

def handle_file_upload(file, job_desc):
    """Handle resume file upload and create new session"""
    if not file:
        return (None, "Please upload resume file", get_session_list(), gr.update(visible=True), gr.update(visible=False))
    filename = os.path.basename(file.name)
    session_id = create_new_session("resume", f"Resume: {filename}")
    gradio_sessions[session_id]["resume_file"] = file
    gradio_sessions[session_id]["job_description"] = job_desc or ""
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
    gradio_sessions[session_id]["messages"] = [{"role": "assistant", "content": analysis}]
    global current_session
    current_session = session_id
    return (session_id, "", get_session_list(), gr.update(visible=False), gr.update(visible=True), gr.update(choices=get_session_choices(), value=session_id))

def switch_mode(mode):
    """Switch between resume chat and mock interview modes"""
    global current_mode, interview_session_id, current_question_id, current_session
    current_mode = mode
    if mode == "resume_chat":
        return (gr.update(value="**Resume Review Mode**"), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(value="**Job Description:** To be entered"))
    else:
        interview_session_id = None
        current_question_id = None
        job_desc_text = "**Job Description:** To be entered"
        if current_session and current_session in gradio_sessions:
            job_description = gradio_sessions[current_session].get("job_description", "")
            if job_description.strip():
                display_desc = job_description[:200] + "..." if len(job_description) > 200 else job_description
                job_desc_text = f"**Job Description:** {display_desc}"
        return (gr.update(value="**Mock Interview Mode**"), gr.update(visible=False), gr.update(visible=True), gr.update(visible=True), gr.update(value=job_desc_text))

def start_interview():
    """开始模拟面试"""
    global interview_session_id, current_question_id, question_start_time, current_session
    if not current_session or current_session not in gradio_sessions:
        return "Please upload resume first", []
    session = gradio_sessions[current_session]
    job_description = session.get("job_description", "")
    if not job_description.strip():
        return "Please provide job description when uploading resume", []
    resume_content = ""
    if session.get("resume_file"):
        resume_content = extract_text_from_file(session["resume_file"].name)
        if resume_content.startswith("Error") or resume_content.startswith("No file"):
            resume_content = ""
    interview_data = InterviewAPI.create_interview(job_description=job_description, resume_content=resume_content)
    if not interview_data or not interview_data.get("success"):
        return "Failed to create interview session, please check service connection", []
    interview_session_id = interview_data["session_id"]
    gradio_sessions[current_session]["interview_session_id"] = interview_session_id
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
    if not interview_session_id or not current_question_id:
        new_history = history + [{"role": "user", "content": answer}, {"role": "assistant", "content": "Interview session not found, please restart the interview"}]
        return "", new_history
    if not answer.strip():
        new_history = history + [{"role": "assistant", "content": "Please provide your answer before submitting"}]
        return "", new_history
    result = InterviewAPI.submit_answer(session_id=interview_session_id, question_id=current_question_id, answer=answer)
    if not result or not result.get("success"):
        new_history = history + [{"role": "user", "content": answer}, {"role": "assistant", "content": "Failed to submit answer, please try again"}]
        return "", new_history
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
    new_history = history + [{"role": "user", "content": answer}, {"role": "assistant", "content": feedback_msg}]
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
    if not session_id or session_id not in gradio_sessions:
        new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": "请先上传简历开始对话"}]
        return "", new_history
    session = gradio_sessions[session_id]
    if current_mode == "resume_chat":
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
                bot_response = """我可以帮您分析简历! 您可以询问:

🔍 **技能评估** - 输入包含"技能"的问题
📊 **经验匹配** - 输入包含"经验"的问题
💡 **改进建议** - 输入包含"建议"的问题
📋 **整体评价** - 输入包含"评价"的问题

例如: "请分析我的技能"、"给出改进建议"等

您想了解什么方面呢?"""
        else:
            bot_response = "此会话中未找到简历文件"
    session["messages"].extend([{"role": "user", "content": message}, {"role": "assistant", "content": bot_response}])
    new_history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": bot_response}]
    return "", new_history

def get_session_choices():
    """获取会话选择列表"""
    if not gradio_sessions:
        return []
    choices = []
    for session_id, session in gradio_sessions.items():
        icon = "📄" if session["type"] == "resume" else "🎤"
        choices.append((f"{icon} {session['title']} ({session['created_at']})", session_id))
    return choices

def select_conversation(session_choice):
    """选择对话记录"""
    global current_session, current_mode
    if not session_choice or session_choice not in gradio_sessions:
        return ([], get_session_list(), gr.update(visible=True), gr.update(visible=False), gr.update(choices=get_session_choices()))
    current_session = session_choice
    session = gradio_sessions[session_choice]
    history = session.get("messages", [])
    return (history, get_session_list(), gr.update(visible=False), gr.update(visible=True), gr.update(choices=get_session_choices()))

def new_conversation():
    """Start a new conversation"""
    global current_session, current_mode, interview_session_id, current_question_id
    current_session = None
    current_mode = "upload"
    interview_session_id = None
    current_question_id = None
    return ([], get_session_list(), gr.update(visible=True), gr.update(visible=False), gr.update(choices=get_session_choices(), value=None))

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

# ================================
# 应用启动
# ================================

def start_fastapi_server():
    """启动FastAPI服务器"""
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")

def create_gradio_interface():
    """创建Gradio界面"""
    with gr.Blocks(title="HireView - AI Resume & Interview Assistant", css=custom_css, theme=gr.themes.Soft()) as demo:
        with gr.Row():
            # Left Sidebar
            with gr.Column(scale=1, elem_classes="sidebar"):
                gr.Markdown("# 🎯 HireView", elem_classes="logo")
                new_chat_btn = gr.Button("+ New Conversation", variant="primary", size="sm")
                gr.Markdown("### Conversation History")
                session_dropdown = gr.Dropdown(
                    label="Select Conversation",
                    choices=get_session_choices(),
                    interactive=True,
                    value=current_session,
                )
                session_list = gr.Markdown(get_session_list())

            # Main Content Area
            with gr.Column(scale=3, elem_classes="main-content"):
                session_state = gr.State(value=None)

                # Upload Interface
                with gr.Column(visible=True, elem_classes="upload-area") as upload_interface:
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
                            upload_btn = gr.Button("Start Analysis", variant="primary", size="lg")

                # Chat Interface
                with gr.Column(visible=False) as chat_interface:
                    # Mode switcher
                    with gr.Row(elem_classes="mode-switcher"):
                        mode_display = gr.Markdown("**Resume Review Mode**")
                        resume_mode_btn = gr.Button("Resume Review", variant="secondary", size="sm")
                        interview_mode_btn = gr.Button("Mock Interview", variant="secondary", size="sm")

                    # Interview configuration
                    with gr.Column(visible=False, elem_classes="interview-config") as interview_config:
                        gr.Markdown("### 🎤 Interview Configuration")
                        job_description_display = gr.Markdown(
                            value="**Job Description:** To be entered",
                            elem_classes="job-description-display",
                        )
                        start_interview_btn = gr.Button("Start Interview", variant="primary")

                    # Chat area
                    chatbot = gr.Chatbot(
                        label="AI Assistant",
                        height=500,
                        show_label=False,
                        elem_classes="chat-container",
                        type="messages",
                    )

                    # Resume chat input
                    with gr.Row(visible=True) as resume_input_area:
                        with gr.Column(scale=4):
                            chat_input = gr.Textbox(
                                placeholder="Ask resume-related questions: skills assessment, improvement suggestions, etc.",
                                show_label=False,
                                lines=1,
                            )
                        with gr.Column(scale=1):
                            send_btn = gr.Button("Send", variant="primary")

                    # Interview input area
                    with gr.Row(visible=False) as interview_input_area:
                        with gr.Column(scale=4):
                            interview_input = gr.Textbox(
                                placeholder="Answer the interview question above...",
                                show_label=False,
                                lines=3,
                            )
                        with gr.Column(scale=1):
                            interview_send_btn = gr.Button("Submit Answer", variant="primary")

                    # Interview summary
                    with gr.Row(visible=False) as summary_area:
                        summary_btn = gr.Button("View Interview Summary", variant="secondary")

        # Event handlers
        upload_btn.click(
            handle_file_upload,
            inputs=[resume_upload, job_description],
            outputs=[session_state, chat_input, session_list, upload_interface, chat_interface, session_dropdown],
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

        resume_mode_btn.click(
            lambda: switch_mode("resume_chat"),
            outputs=[mode_display, resume_input_area, interview_input_area, interview_config, job_description_display],
        )

        interview_mode_btn.click(
            lambda: switch_mode("mock_interview"),
            outputs=[mode_display, resume_input_area, interview_input_area, interview_config, job_description_display],
        )

        session_dropdown.change(
            select_conversation,
            inputs=[session_dropdown],
            outputs=[chatbot, session_list, upload_interface, chat_interface, session_dropdown],
        )

        new_chat_btn.click(
            new_conversation,
            outputs=[chatbot, session_list, upload_interface, chat_interface, session_dropdown],
        )

        summary_btn.click(
            get_interview_summary_display,
            outputs=[chatbot],
        )

    return demo

if __name__ == "__main__":
    print("正在启动HireView统一应用...")

    # 在后台启动FastAPI服务器
    fastapi_thread = threading.Thread(target=start_fastapi_server, daemon=True)
    fastapi_thread.start()

    # 等待FastAPI服务器启动
    print("等待FastAPI服务器启动...")
    time.sleep(3)

    # 创建并启动Gradio界面
    print("正在启动Gradio界面...")
    demo = create_gradio_interface()

    try:
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