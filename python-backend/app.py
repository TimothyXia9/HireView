import gradio as gr
import time
import json
import pdfplumber
import os


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


# Create Gradio interface
with gr.Blocks(title="AI Resume Analysis Assistant", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 AI Resume Analysis Assistant")
    gr.Markdown(
        "Upload your resume and I'll provide professional analysis and suggestions!"
    )

    with gr.Row():
        with gr.Column(scale=1):
            # File upload area
            resume_file = gr.File(
                label="📎 Upload Resume",
                file_types=[".pdf", ".doc", ".docx", ".txt"],
                type="filepath",
            )

            # Quick analysis button
            quick_btn = gr.Button("⚡ Quick Analysis", variant="primary")

            # Clear chat button
            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")

        with gr.Column(scale=2):
            # Chat interface
            chatbot = gr.Chatbot(
                label="💬 Chat with AI Assistant", height=400, type="messages"
            )

            # User input box
            msg = gr.Textbox(
                label="Enter Your Question",
                placeholder="For example: Analyze my skill level, give improvement suggestions...",
                lines=2,
            )

            # Submit button
            submit_btn = gr.Button("Send", variant="primary")

    # Quick analysis results display area
    with gr.Row():
        analysis_output = gr.Markdown()

    # Example questions
    gr.Examples(
        examples=[
            "Show text",
            "How would you assess my skill level?",
            "Does my work experience match the target position?",
            "Give me some resume improvement suggestions",
            "Please provide an overall evaluation of my resume",
        ],
        inputs=msg,
        label="💡 Sample Questions",
    )

    # Bind events
    submit_btn.click(
        chat_with_resume, inputs=[msg, chatbot, resume_file], outputs=[msg, chatbot]
    )

    msg.submit(
        chat_with_resume, inputs=[msg, chatbot, resume_file], outputs=[msg, chatbot]
    )

    quick_btn.click(quick_analyze, inputs=[resume_file], outputs=[analysis_output])

    clear_btn.click(clear_chat, outputs=[chatbot])

# Launch application
if __name__ == "__main__":
    try:
        print("Starting Gradio application...")
        print(f"Server will be available at: http://127.0.0.1:7860")

        demo.launch(
            share=False,  # Disable share for packaged apps
            server_name="127.0.0.1",  # Use localhost for packaged apps
            server_port=7860,  # Specify port
            show_error=True,  # Show error messages
            quiet=False,  # Show startup messages
            prevent_thread_lock=False,  # Allow blocking
            inbrowser=False,  # Don't auto-open browser
        )
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
