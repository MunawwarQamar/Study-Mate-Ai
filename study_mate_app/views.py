from django.shortcuts import render, redirect,JsonResponse
from .models import Subject, UserSubject, User, StudyPlan, StudyPlanItem
import anthropic
import json
from django.conf import settings
from datetime import date, timedelta

# Create your views here.
def home(request):
    pass

# ─── SUBJECTS ───

def all_subjects(request):
    user = User.objects.get(id=request.session['user_id'])
    user_subjects = UserSubject.objects.filter(user=user).select_related('subject')
    return render(request, 'subjects/all_subjects.html', {'user_subjects': user_subjects})

def add_subject(request):
    if request.method == 'POST':
        name = request.POST['name']
        exam_date = request.POST['exam_date']
        priority = request.POST['priority']
        errors = {}

        if len(name) < 2:
            errors['name'] = 'Subject name must be at least 2 characters.'
        if not exam_date:
            errors['exam_date'] = 'Exam date is required.'
        if priority not in ['low', 'medium', 'high']:
            errors['priority'] = 'Please select a valid priority.'

        if errors:
            return render(request, 'subjects/add_subject.html', {'errors': errors})

        user = User.objects.get(id=request.session['user_id'])
        subject = Subject.objects.create(name=name)
        UserSubject.objects.create(user=user, subject=subject, exam_date=exam_date, priority=priority)
        return redirect('all_subjects')

    return render(request, 'subjects/add_subject.html')

def edit_subject(request, id):
    user_subject = UserSubject.objects.get(id=id)
    if request.method == 'POST':
        name = request.POST['name']
        exam_date = request.POST['exam_date']
        priority = request.POST['priority']

        user_subject.subject.name = name
        user_subject.subject.save()
        user_subject.exam_date = exam_date
        user_subject.priority = priority
        user_subject.save()
        return redirect('all_subjects')

    return render(request, 'subjects/edit_subject.html', {'user_subject': user_subject})

def delete_subject(request, id):
    UserSubject.objects.get(id=id).delete()
    return redirect('all_subjects')


# ─── STUDY PLAN ───

def study_plan(request):
    user = User.objects.get(id=request.session['user_id'])
    user_subjects = UserSubject.objects.filter(user=user).select_related('subject')
    latest_plan = StudyPlan.objects.filter(user=user).prefetch_related('plan_items_user_subject_subject').last()
    return render(request, 'study_plan/study_plan.html', {
        'user_subjects': user_subjects,
        'latest_plan': latest_plan
    })

def generate_plan(request):
    if request.method == 'POST':
        user = User.objects.get(id=request.session['user_id'])
        available_hours = request.POST['available_hours']
        blocked_days = request.POST.getlist('blocked_days')
        user_subjects = UserSubject.objects.filter(user=user).select_related('subject')

        # Build subjects info for the AI
        subjects_info = []
        for us in user_subjects:
            subjects_info.append(
                f"- {us.subject.name} (Exam: {us.exam_date}, Priority: {us.priority})"
            )
        subjects_text = "\n".join(subjects_info)
        blocked_text = ", ".join(blocked_days) if blocked_days else "None"
        today = date.today()

        prompt = f"""
You are a smart study planner. Generate a 7-day study plan starting from {today}.

Student's subjects:
{subjects_text}

Available study hours per day: {available_hours} hours
Blocked days (no studying): {blocked_text}

Return ONLY a JSON array, no extra text, like this:
[
  {{"date": "YYYY-MM-DD", "subject": "Subject Name", "hours": 2}},
  {{"date": "YYYY-MM-DD", "subject": "Subject Name", "hours": 1.5}}
]

Rules:
- Skip blocked days completely
- Prioritize high priority subjects
- Split hours across subjects on the same day if needed
- Don't exceed available hours per day
- Focus on subjects with closer exam dates
"""

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()
        plan_data = json.loads(response_text)

        # Save the plan
        study_plan = StudyPlan.objects.create(
            user=user,
            week_start=today,
            generated_by_ai=response_text
        )

        # Save each item
        for item in plan_data:
            subject_name = item['subject']
            us = user_subjects.filter(subject__name=subject_name).first()
            if us:
                StudyPlanItem.objects.create(
                    study_plan=study_plan,
                    user_subject=us,
                    study_date=item['date'],
                    planned_hours=item['hours'],
                    status='pending'
                )

        return redirect('study_plan')
    return redirect('study_plan')


# ─── TASKS ───

def all_tasks(request):
    user = User.objects.get(id=request.session['user_id'])
    user_subjects = UserSubject.objects.filter(user=user)
    tasks = StudyPlanItem.objects.filter(
        user_subject__in=user_subjects
    ).select_related('user_subject__subject').order_by('study_date')

    subject_filter = request.GET.get('subject')
    status_filter = request.GET.get('status')

    if subject_filter:
        tasks = tasks.filter(user_subject_subject_id=subject_filter)
    if status_filter:
        tasks = tasks.filter(status=status_filter)

    return render(request, 'tasks/all_tasks.html', {
        'tasks': tasks,
        'user_subjects': user_subjects,
        'subject_filter': subject_filter,
        'status_filter': status_filter
    })

def toggle_task(request, id):
    if request.method == 'POST':
        task = StudyPlanItem.objects.get(id=id)
        if task.status == 'pending':
            task.status = 'completed'
        else:
            task.status = 'pending'
        task.save()
        return JsonResponse({'status': task.status})