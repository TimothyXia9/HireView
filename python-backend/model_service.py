import os
import json
from random import choice
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from imagine import ImagineClient
import re

app = FastAPI(title="Interview Model Service", version="1.0.0")

# CORS配置
app.add_middleware(
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
    resume_session_id: Optional[str] = None  # 可选，关联已有简历会话
    resume_file: Optional[str] = None
    job_description: str  # 岗位描述


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


# 加载历史会话
def load_sessions():
    global sessions
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                loaded_sessions = json.load(f)

            # 清理旧会话数据中的不需要字段
            sessions = {}
            for session_id, session_data in loaded_sessions.items():
                # 移除不需要的字段
                cleaned_session = {
                    k: v
                    for k, v in session_data.items()
                    if k
                    not in ["interview_type", "difficulty_level", "duration_minutes"]
                }

                # 清理questions中的type和time_limit字段
                if "questions" in cleaned_session:
                    cleaned_questions = []
                    for q in cleaned_session["questions"]:
                        cleaned_q = {
                            k: v
                            for k, v in q.items()
                            if k not in ["type", "time_limit"]
                        }
                        cleaned_questions.append(cleaned_q)
                    cleaned_session["questions"] = cleaned_questions

                sessions[session_id] = cleaned_session

            # 保存清理后的会话数据
            save_sessions()

        except Exception as e:
            print(f"[DEBUG] Error loading sessions: {e}")
            sessions = {}


def save_sessions():
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


# 保存会话对话记录
def save_conversation_history(session_id: str, conversation_data: Dict):
    conversation_file = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
    with open(conversation_file, "w", encoding="utf-8") as f:
        json.dump(conversation_data, f, ensure_ascii=False, indent=2)


# 加载会话对话记录
def load_conversation_history(session_id: str) -> Optional[Dict]:
    conversation_file = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
    if os.path.exists(conversation_file):
        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


# 更新会话对话记录
def update_conversation_history(
    session_id: str, role: str, message: str, extra_data: Optional[Dict] = None
):
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


# 启动时加载会话
load_sessions()


from typing import List
import json


def generate_personalized_questions(
    job_description: str, resume_content: str, num_questions: int = 3
) -> List[Question]:
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

        print("Raw LLM Response:", response)

        # 取文本结果
        content = response.first_content
        print("LLM Content:", content)

        # 解析纯文本格式的问题
        questions = parse_plain_text_questions(content, num_questions)

        # 如果解析的问题不够，补充默认问题
        if len(questions) < num_questions:
            fallback_needed = num_questions - len(questions)
            fallback_questions = get_fallback_questions(fallback_needed)
            questions.extend(fallback_questions)

        return questions[:num_questions]

    except Exception as e:
        print(f"Error generating personalized questions: {e}")
        return get_fallback_questions(num_questions)


def parse_plain_text_questions(content: str, expected_count: int) -> List[Question]:
    """
    解析纯文本格式的问题
    支持多种常见的问题格式
    """
    questions = []
    lines = content.strip().split("\n")

    question_id = 1
    for line in lines:
        line = line.strip()

        # 跳过空行
        if not line:
            continue

        # 跳过明显的标题行或提示行
        skip_patterns = [
            r"^(questions?:?|here are|below are)",
            r"^(问题[:：]?|以下是)",
            r"^[\-=\*]{3,}",  # 分隔线
            r"^(note|注意|说明)[:：]",
        ]

        should_skip = False
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                should_skip = True
                break

        if should_skip:
            continue

        # 清理问题文本
        cleaned_question = clean_question_text(line)

        # 验证是否是有效问题
        if is_valid_question(cleaned_question):
            questions.append(
                Question(question_id=question_id, question=cleaned_question)
            )
            question_id += 1

            # 如果已经解析到足够的问题，提前结束
            if len(questions) >= expected_count:
                break

    return questions


def clean_question_text(text: str) -> str:
    """
    清理问题文本，移除不必要的格式
    """
    # 移除常见的编号格式
    patterns_to_remove = [
        r"^\d+[\.\)]\s*",  # 1. 或 1)
        r"^[Q]\d*[:：]?\s*",  # Q1: 或 Q:
        r"^[问]\d*[:：]?\s*",  # 问1: 或 问:
        r"^[\-\*\+]\s*",  # - 或 * 或 +
        r"^[•·]\s*",  # 项目符号
    ]

    cleaned = text
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    # 确保问题以问号结尾
    if cleaned and not cleaned.endswith("?") and not cleaned.endswith("？"):
        # 如果明显是问句但没有问号，添加问号
        question_indicators = [
            "how",
            "what",
            "why",
            "when",
            "where",
            "which",
            "who",
            "can you",
            "could you",
            "would you",
            "do you",
            "have you",
            "are you",
        ]
        if any(
            cleaned.lower().startswith(indicator) for indicator in question_indicators
        ):
            cleaned += "?"

    return cleaned


def is_valid_question(text: str) -> bool:
    """
    验证是否是有效的问题
    """
    if not text or len(text.strip()) < 10:  # 太短的文本
        return False

    # 检查是否包含问号或疑问词
    has_question_mark = "?" in text or "？" in text

    question_words = [
        "how",
        "what",
        "why",
        "when",
        "where",
        "which",
        "who",
        "can",
        "could",
        "would",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "are",
        "is",
        "was",
        "were",
        "will",
    ]
    has_question_word = any(word in text.lower() for word in question_words)

    # 过滤明显不是问题的文本
    invalid_patterns = [
        r"^(thank|thanks|here|below|above|note|please|kindly)",
        r"(sincerely|regards|best|cheers)$",
        r"^\d+$",  # 纯数字
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False

    return has_question_mark or has_question_word


def get_fallback_questions(num_questions: int) -> List[Question]:
    """
    获取默认备用问题
    """
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
        questions.append(
            Question(
                question_id=i + 1,
                question=fallback_questions[i],
            )
        )

    return questions


def chat_with_llama(messages: List[Dict[str, str]], context: str = "") -> str:
    try:
        # Build system prompt
        system_prompt = f"""You are a professional interviewer AI assistant. {context}

Please provide constructive feedback based on the candidate's answer, including:
1. Strengths of the answer
2. Areas for improvement
3. Specific suggestions
4. Score from 1-10

Please maintain a professional and friendly tone."""

        chat_messages = [{"role": "system", "content": system_prompt}] + messages

        response = client.chat(
            messages=chat_messages, model="Llama-3.1-8B", max_tokens=512
        )

        return response.first_content
    except Exception as e:
        return f"Evaluation error: {str(e)}"


@app.post("/api/interview/create")
async def create_interview(request: InterviewCreateRequest):
    try:
        session_id = f"interview_session_{uuid.uuid4().hex[:8]}"

        # 固定问题数量和参数
        total_questions = 3

        # 获取简历内容
        resume_content = ""
        if request.resume_session_id:
            resume_content = f"Resume from session {request.resume_session_id}"
        elif request.resume_file:
            # 如果提供了简历文件，使用文件内容
            resume_content = request.resume_file

        # 生成个性化问题
        if resume_content.strip():

            questions = generate_personalized_questions(
                request.job_description, resume_content, total_questions
            )
        else:
            raise HTTPException(status_code=400, detail="Resume content is required")

        # 创建会话
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "job_info": {
                "description": request.job_description,
            },
            "questions": [q.dict() for q in questions],
            "current_question": 0,
            "answers": [],
            "status": "in_progress",
        }

        sessions[session_id] = session_data
        save_sessions()

        # Save initial conversation record
        initial_message = "Starting mock interview"

        update_conversation_history(
            session_id,
            "system",
            initial_message,
            {
                "job_info": session_data["job_info"],
            },
        )

        # 记录第一个问题
        if questions:
            update_conversation_history(
                session_id,
                "assistant",
                questions[0].question,
                {
                    "question_id": questions[0].question_id,
                },
            )

        # 准备响应

        return {
            "success": True,
            "session_id": session_id,
            "interview_plan": {
                "total_questions": total_questions,
            },
            "first_question": questions[0].dict() if questions else None,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/answer")
async def submit_answer(request: InterviewAnswerRequest):
    try:
        print(
            f"[DEBUG] Received answer request: session_id={request.session_id}, question_id={request.question_id}"
        )

        if request.session_id not in sessions:
            print(f"[DEBUG] Session not found: {request.session_id}")
            raise HTTPException(status_code=404, detail="Session not found")

        session = sessions[request.session_id]
        print(f"[DEBUG] Session found, keys: {list(session.keys())}")

        questions = session["questions"]
        print(f"[DEBUG] Questions count: {len(questions)}")

        # 验证问题ID
        if request.question_id > len(questions) or request.question_id < 1:
            print(
                f"[DEBUG] Invalid question ID: {request.question_id}, total questions: {len(questions)}"
            )
            raise HTTPException(status_code=400, detail="Invalid question ID")

        current_question = questions[request.question_id - 1]
        print(f"[DEBUG] Current question keys: {list(current_question.keys())}")

        # 使用LLaMA生成反馈
        context = f"""
        Question: {current_question['question']}
        Answer: {request.answer}
        """

        print(f"[DEBUG] About to call chat_with_llama")

        messages = [
            {
                "role": "user",
                "content": f"Please evaluate this interview answer:\n{context}",
            }
        ]
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

        # 保存答案
        answer_data = {
            "question_id": request.question_id,
            "question": current_question["question"],
            "answer": request.answer,
            "feedback": feedback.dict(),
            "timestamp": datetime.now().isoformat(),
        }

        session["answers"].append(answer_data)
        session["current_question"] = request.question_id

        # 保存用户回答到对话记录
        update_conversation_history(
            request.session_id,
            "user",
            request.answer,
            {
                "question_id": request.question_id,
                "question_text": current_question["question"],
            },
        )

        # 保存AI反馈到对话记录
        update_conversation_history(
            request.session_id,
            "assistant",
            feedback_text,
            {
                "feedback_type": "evaluation",
                "score": feedback.score,
                "strengths": feedback.strengths,
                "improvements": feedback.improvements,
                "question_id": request.question_id,
            },
        )

        # 准备下一个问题
        next_question = None
        if request.question_id < len(questions):
            next_question = questions[request.question_id]
            # 保存下一个问题到对话记录
            update_conversation_history(
                request.session_id,
                "assistant",
                next_question["question"],
                {
                    "question_id": next_question["question_id"],
                },
            )
        else:
            session["status"] = "completed"
            # 保存面试结束消息
            update_conversation_history(
                request.session_id,
                "system",
                "thank you for completing the interview. The interview is now concluded.",
                {"interview_completed": True},
            )

        # 计算进度
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


@app.get("/api/interview/summary/{session_id}")
async def get_interview_summary(session_id: str):
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session = sessions[session_id]
        answers = session["answers"]

        if not answers:
            raise HTTPException(status_code=400, detail="No answers found")

        # 计算总体评分
        total_score = sum(answer["feedback"]["score"] for answer in answers)
        average_score = total_score / len(answers)

        # 简化评分统计，移除类型分组
        category_scores = {"overall": average_score}

        # 生成总体反馈
        strengths = ["Strong technical knowledge", "Good communication skills"]
        improvements = [
            "Could prepare more specific examples",
            "Answers could be more concise",
        ]
        recommendations = [
            "Practice STAR method for behavioral questions",
            "Prepare 2-3 in-depth technical project examples",
        ]

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


@app.get("/api/interview/session/{session_id}")
async def get_session_info(session_id: str):
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session = sessions[session_id]

        # 获取对话历史
        conversation_history = load_conversation_history(session_id)
        conversation_data = (
            conversation_history["conversation_history"] if conversation_history else []
        )

        return {
            "success": True,
            "session_id": session_id,
            "created_at": session["created_at"],
            "job_info": session["job_info"],
            "status": session["status"],
            "progress": {
                "current_question": session["current_question"],
                "total_questions": len(session["questions"]),
                "completed_percentage": (
                    session["current_question"] / len(session["questions"])
                )
                * 100,
            },
            "conversation_history": conversation_data,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/interview/conversation/{session_id}")
async def get_conversation_history(session_id: str):
    """获取会话的完整对话历史"""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        conversation_history = load_conversation_history(session_id)
        if not conversation_history:
            raise HTTPException(
                status_code=404, detail="Conversation history not found"
            )

        return {
            "success": True,
            "session_id": session_id,
            "created_at": conversation_history["created_at"],
            "conversation_history": conversation_history["conversation_history"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def get_sessions(
    user_id: Optional[str] = None, type: str = "all", limit: int = 20, offset: int = 0
):
    try:
        filtered_sessions = []

        for session_id, session_data in sessions.items():
            if type == "interview" or type == "all":
                filtered_sessions.append(
                    {
                        "session_id": session_id,
                        "type": "interview",
                        "created_at": session_data["created_at"],
                        "status": session_data["status"],
                        "title": f"{session_data['job_info']['title']} mock interview",
                    }
                )

        # 分页
        total = len(filtered_sessions)
        paginated_sessions = filtered_sessions[offset : offset + limit]

        return {
            "success": True,
            "sessions": paginated_sessions,
            "total": total,
            "has_more": offset + limit < total,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        # 删除会话数据
        del sessions[session_id]
        save_sessions()

        # 删除对话历史文件
        conversation_file = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
        if os.path.exists(conversation_file):
            os.remove(conversation_file)

        return {"success": True, "message": "Session deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Interview Model Service is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
