#!/usr/bin/env python3
"""
Demo script to test Vinschool AI Educational Support System.
Tests all major workflows: document upload, question answering, and homework grading.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.teaching_assistant.agent import TeachingAssistantAgent, QuestionContext
from agents.content_processor.agent import ContentProcessorAgent
from agents.grading.agent import GradingAgent, GradingCriteria
from domain.models.document import Document, DocumentType
from domain.models.assignment import Assignment
from workflow.daily_content_workflow import DailyContentWorkflow
from workflow.question_answering_workflow import QuestionAnsweringWorkflow
from workflow.homework_grading_workflow import HomeworkGradingWorkflow
from utils.logger import logger
from uuid import uuid4


async def demo_teaching_assistant():
    """Demo 1: Teaching Assistant - Question Answering"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    
    console = Console()
    
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]🎓 TEACHING ASSISTANT - QUESTION ANSWERING[/bold cyan]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    
    agent = TeachingAssistantAgent()
    
    # Test question
    context = QuestionContext(
        question="Làm thế nào để cộng các phân số có mẫu số khác nhau?",
        student_id="demo-student-001",
        grade=9,
        subject="Mathematics",
        class_name="9A1"
    )
    
    # Display question
    question_panel = Panel(
        f"[bold white]{context.question}[/bold white]\n\n"
        f"[dim]👤 Học sinh: Lớp {context.grade} | Môn: {context.subject}[/dim]",
        title="[bold yellow]📝 CÂU HỎI[/bold yellow]",
        border_style="yellow",
        box=box.ROUNDED
    )
    console.print(question_panel)
    
    console.print("\n[dim]⏳ Đang tạo câu trả lời...[/dim]")
    
    response = await agent.answer_question(context)
    
    # Create results table
    results_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    results_table.add_column("Label", style="cyan bold", no_wrap=True)
    results_table.add_column("Value")
    
    results_table.add_row("📊 Độ tin cậy:", f"[green]{response.confidence:.1%}[/green]")
    results_table.add_row(
        "🔗 Nguồn:", 
        f"[yellow]{', '.join(response.sources) if response.sources else 'Chưa có dữ liệu trong knowledge base'}[/yellow]"
    )
    results_table.add_row(
        "⚠️  Chuyển giáo viên:", 
        f"[red]Có[/red]" if response.escalate_to_teacher else f"[green]Không[/green]"
    )
    
    # Display answer
    answer_panel = Panel(
        f"[white]{response.answer}[/white]\n\n{results_table}",
        title="[bold green]✅ TRẢ LỜI[/bold green]",
        border_style="green",
        box=box.ROUNDED
    )
    console.print(answer_panel)
    
    return response


async def demo_content_summarization():
    """Demo 2: Content Summarization"""
    print("\n" + "="*60)
    print("📚 DEMO 2: CONTENT SUMMARIZATION")
    print("="*60)
    
    agent = TeachingAssistantAgent()
    
    sample_content = """
    Unit 9: Addition and Subtraction of Fractions
    
    In this lesson, we will learn:
    1. How to add fractions with the same denominator
    2. How to add fractions with different denominators
    3. How to subtract fractions
    
    Key Concepts:
    - Common denominator: The same bottom number in fractions
    - Numerator: The top number in a fraction
    - Like fractions: Fractions with the same denominator
    
    Example: 1/4 + 2/4 = 3/4
    When denominators are the same, just add the numerators!
    
    For different denominators, find the LCD (Least Common Denominator) first.
    """
    
    from agents.teaching_assistant.agent import SummaryRequest
    
    print("\n📄 Original Content:")
    print("-" * 60)
    print(sample_content)
    print("-" * 60)
    
    print("\n⏳ Generating summary...")
    
    summary = await agent.summarize_content(
        SummaryRequest(
            content=sample_content,
            target_audience="students",
            max_length=300
        )
    )
    
    print(f"\n✅ Summary for Students:\n{summary}")
    
    return summary


async def demo_exercise_generation():
    """Demo 3: Personalized Exercise Generation"""
    print("\n" + "="*60)
    print("✏️  DEMO 3: PERSONALIZED EXERCISE GENERATION")
    print("="*60)
    
    agent = TeachingAssistantAgent()
    
    print("\n👤 Student Profile:")
    print("   - Level: Intermediate")
    print("   - Subject: Mathematics")
    print("   - Topic: Fractions")
    
    print("\n⏳ Generating personalized exercises...")
    
    exercises = await agent.generate_personalized_exercises(
        student_level="intermediate",
        subject="Mathematics",
        topic="Addition and Subtraction of Fractions",
        num_exercises=3
    )
    
    print("\n✅ Generated Exercises:")
    for i, exercise in enumerate(exercises, 1):
        print(f"\n{i}. {exercise}")
    
    return exercises


async def demo_homework_grading():
    """Demo 4: Automated Homework Grading"""
    print("\n" + "="*60)
    print("✅ DEMO 4: AUTOMATED HOMEWORK GRADING")
    print("="*60)
    
    # Create sample assignment
    assignment = Assignment(
        id=uuid4(),
        title="Fraction Practice Problems",
        teacher_id=uuid4(),
        student_id=uuid4(),
        class_name="9A1",
        subject="Mathematics",
        max_score=100.0,
    )
    
    # Simulate student submission
    submission_text = """
    Problem 1: 1/4 + 2/4 = 3/4 ✓
    
    Problem 2: 1/3 + 1/6 = 2/6 + 1/6 = 3/6 = 1/2 ✓
    
    Problem 3: 2/5 - 1/5 = 1/5 ✓
    
    Problem 4: 3/4 - 1/8 = 6/8 - 1/8 = 5/8 ✓
    
    Problem 5: 1/2 + 1/3 = 3/6 + 2/6 = 5/6 ✓
    """
    
    assignment.submit(file_path="demo_submission.txt", extracted_text=submission_text)
    
    print("\n📝 Student Submission:")
    print("-" * 60)
    print(submission_text)
    print("-" * 60)
    
    # Create rubric
    rubric = [
        GradingCriteria(
            criteria_name="Correctness",
            max_points=60,
            description="Accuracy of answers and calculations"
        ),
        GradingCriteria(
            criteria_name="Work Shown",
            max_points=25,
            description="Clear demonstration of problem-solving steps"
        ),
        GradingCriteria(
            criteria_name="Presentation",
            max_points=15,
            description="Neatness and organization"
        )
    ]
    
    print("\n⏳ AI is grading the homework...")
    
    agent = GradingAgent()
    result = await agent.grade_assignment(assignment, rubric)
    
    print(f"\n✅ GRADING RESULTS")
    print("-" * 60)
    print(f"Total Score: {result.total_score}/{assignment.max_score}")
    print(f"\nCriteria Scores:")
    for criteria, score in result.criteria_scores.items():
        print(f"  - {criteria}: {score}")
    
    print(f"\n💬 Feedback:\n{result.feedback}")
    
    if result.strengths:
        print(f"\n💪 Strengths:")
        for strength in result.strengths:
            print(f"  - {strength}")
    
    if result.improvements:
        print(f"\n📈 Areas for Improvement:")
        for improvement in result.improvements:
            print(f"  - {improvement}")
    
    return result


async def demo_complete_workflow():
    """Demo 5: Complete Workflow - Upload to Question to Grading"""
    print("\n" + "="*60)
    print("🔄 DEMO 5: COMPLETE END-TO-END WORKFLOW")
    print("="*60)
    
    print("\n📌 This demo simulates the complete teacher-student flow:")
    print("   1. Teacher uploads content")
    print("   2. Content is processed and embedded")
    print("   3. Student asks a question")
    print("   4. Student submits homework")
    print("   5. Homework is auto-graded")
    
    # Note: This requires actual file for document processing
    print("\n⚠️  Note: Full document processing requires actual files.")
    print("   Skipping file upload demo (requires PPTX/DOCX files)")
    print("   Showing question and grading workflows instead...")
    
    # Use question answering workflow
    workflow = QuestionAnsweringWorkflow()
    
    print("\n📚 Step 1: Student asks a question...")
    result = await workflow.handle_question(
        student_id="demo-student-001",
        question="What is the least common denominator?",
        grade=9,
        subject="Mathematics"
    )
    
    print(f"   ✅ Answer provided")
    print(f"   Confidence: {result['confidence']:.2%}")
    print(f"   Escalated: {'Yes' if result['escalated'] else 'No'}")
    
    print("\n✅ Complete workflow demo finished!")


async def main():
    """Run all demos"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║  🎓 VINSCHOOL AI EDUCATIONAL SUPPORT SYSTEM - DEMO  🎓  ║")
    print("╚" + "="*58 + "╝")
    
    try:
        # Run demos
        await demo_teaching_assistant()
        await demo_content_summarization()
        await demo_exercise_generation()
        await demo_homework_grading()
        await demo_complete_workflow()
        
        print("\n" + "="*60)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n💡 Tips:")
        print("   - To use with real documents, add files to /data folder")
        print("   - Configure your LLM provider in .env")
        print("   - Start the API: uvicorn api.main:app --reload")
        print("   - Access docs: http://localhost:8000/docs")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
