# API Documentation

## 简历审查服务 (Resume Review Service)

### 1. 上传简历并开始审查会话

**POST** `/api/resume/upload`

上传简历文件并创建新的审查会话。

**Request:**

```
Content-Type: multipart/form-data

Body:
- file: 简历文件 (支持 PDF, DOC, DOCX)
- user_id: 用户ID (可选)
```

**Response:**

```json
{
	"success": true,
	"session_id": "resume_session_12345",
	"message": "简历上传成功，已开始分析",
	"resume_analysis": {
		"summary": "简历概述",
		"strengths": ["优势1", "优势2"],
		"areas_for_improvement": ["改进点1", "改进点2"],
		"suggestions": ["建议1", "建议2"]
	}
}
```

### 2. 简历审查对话

**POST** `/api/resume/chat`

与 AI 进行简历修改的对话交流。

**Request:**

```json
{
	"session_id": "resume_session_12345",
	"message": "用户的问题或请求",
	"message_type": "question" // question, request_revision, general
}
```

**Response:**

```json
{
	"success": true,
	"session_id": "resume_session_12345",
	"response": "AI的回复和建议",
	"suggestions": [
		{
			"title": "修改建议标题",
			"descripetion": "修改理由"
		}
	],
	"conversation_history": [
		{
			"role": "user",
			"message": "用户消息",
			"timestamp": "2025-09-27T10:00:00Z"
		},
		{
			"role": "assistant",
			"message": "AI回复",
			"timestamp": "2025-09-27T10:00:05Z"
		}
	]
}
```

### 3. 获取简历审查会话历史

**GET** `/api/resume/session/{session_id}`

获取指定会话的完整对话历史。

**Response:**

```json
{
  "success": true,
  "session_id": "resume_session_12345",
  "created_at": "2025-09-27T09:00:00Z",
  "resume_info": {
    "filename": "resume.pdf",
    "analysis_summary": "简历分析摘要"
  },
  "conversation_history": [...]
}
```

## 模拟面试服务 (Mock Interview Service)

### 1. 创建模拟面试会话

**POST** `/api/interview/create`

基于简历和目标岗位创建模拟面试会话。

**Request:**

```json
{
	"resume_session_id": "resume_session_12345",
	"resume_file": "文件上传",
	"job_description": "岗位描述"
}
```

**Response:**

```json
{
	"success": true,
	"session_id": "interview_session_67890",
	"interview_plan": {
		"total_questions": 8,
		"estimated_duration": "30分钟",
		"question_categories": [
			{
				"category": "技术问题",
				"count": 4
			},
			{
				"category": "行为问题",
				"count": 4
			}
		]
	},
	"first_question": {
		"question_id": 1,
		"question": "请简单介绍一下你自己",
		"type": "behavioral",
		"time_limit": 180
	}
}
```

### 2. 回答面试问题

**POST** `/api/interview/answer`

提交面试问题的回答。

**Request:**

```json
{
	"session_id": "interview_session_67890",
	"question_id": 1,
	"answer": "用户的回答内容",
	"answer_duration": 120 // 回答用时(秒)
}
```

**Response:**

```json
{
	"success": true,
	"session_id": "interview_session_67890",
	"feedback": {
		"score": 8.5,
		"strengths": ["回答完整", "逻辑清晰"],
		"improvements": ["可以增加具体例子"],
		"detailed_feedback": "详细的反馈内容"
	},
	"next_question": {
		"question_id": 2,
		"question": "描述一个你解决过的技术难题",
		"type": "technical",
		"time_limit": 300
	},
	"progress": {
		"current_question": 2,
		"total_questions": 8,
		"completed_percentage": 12.5
	}
}
```

### 3. 获取面试总结

**GET** `/api/interview/summary/{session_id}`

获取完整面试的总结和评估。

**Response:**

```json
{
	"success": true,
	"session_id": "interview_session_67890",
	"interview_completed": true,
	"overall_score": 7.8,
	"duration_minutes": 28,
	"summary": {
		"total_questions": 8,
		"answered_questions": 8,
		"average_score": 7.8,
		"category_scores": {
			"technical": 8.2,
			"behavioral": 7.4
		}
	},
	"detailed_feedback": {
		"strengths": ["技术知识扎实", "表达能力强"],
		"areas_for_improvement": ["可以准备更多具体案例", "回答可以更加简洁"],
		"recommendations": ["多练习STAR法则回答行为问题", "准备2-3个深度技术项目案例"]
	},
	"question_details": [
		{
			"question_id": 1,
			"question": "请简单介绍一下你自己",
			"answer": "用户回答",
			"score": 8.0,
			"feedback": "回答详细反馈"
		}
	]
}
```

### 4. 获取面试会话历史

**GET** `/api/interview/session/{session_id}`

获取面试会话的详细信息。

**Response:**

```json
{
	"success": true,
	"session_id": "interview_session_67890",
	"created_at": "2025-09-27T10:00:00Z",
	"job_info": {
		"title": "软件工程师",
		"company": "公司名称",
		"description": "岗位描述"
	},
	"status": "completed", // in_progress, completed, abandoned
	"progress": {
		"current_question": 8,
		"total_questions": 8,
		"completed_percentage": 100
	}
}
```

## 通用接口

### 1. 获取用户所有会话

**GET** `/api/sessions`

**Query Parameters:**

-   user_id: 用户 ID
-   type: session 类型 (resume, interview, all)
-   limit: 返回数量限制 (默认 20)
-   offset: 偏移量 (默认 0)

**Response:**

```json
{
	"success": true,
	"sessions": [
		{
			"session_id": "resume_session_12345",
			"type": "resume",
			"created_at": "2025-09-27T09:00:00Z",
			"status": "active",
			"title": "软件工程师简历审查"
		},
		{
			"session_id": "interview_session_67890",
			"type": "interview",
			"created_at": "2025-09-27T10:00:00Z",
			"status": "completed",
			"title": "软件工程师模拟面试"
		}
	],
	"total": 2,
	"has_more": false
}
```

### 2. 删除会话

**DELETE** `/api/session/{session_id}`

**Response:**

```json
{
	"success": true,
	"message": "会话已删除"
}
```

## 错误响应格式

所有错误响应都遵循以下格式：

```json
{
	"success": false,
	"error_code": "INVALID_SESSION",
	"message": "会话不存在或已过期",
	"details": "详细错误信息(可选)"
}
```

**常见错误码:**

-   `INVALID_SESSION`: 无效的会话 ID
-   `FILE_TOO_LARGE`: 文件过大
-   `UNSUPPORTED_FORMAT`: 不支持的文件格式
-   `SESSION_EXPIRED`: 会话已过期
-   `RATE_LIMIT_EXCEEDED`: 请求频率过高
-   `INVALID_PARAMETERS`: 参数错误
