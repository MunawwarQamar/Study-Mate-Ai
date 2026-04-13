from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Subject, UserSubject, User, StudyPlan, StudyPlanItem, StudySession, UserBadge
from openai import OpenAI
import json
from datetime import date, timedelta
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Sum
from django.utils import timezone


def dashboard(request):
    if not request.session.get('user_id'):
        return redirect('auth')

    user = User.objects.get(id=request.session['user_id'])
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    user_subjects = UserSubject.objects.filter(user=user).select_related('subject')

    todays_tasks = StudyPlanItem.objects.filter(
        user_subject__user=user,
        study_date=today
    ).select_related('user_subject__subject').order_by('status', 'study_date', 'id')

    weekly_tasks = StudyPlanItem.objects.filter(
        user_subject__user=user,
        study_date__range=[week_start, week_end]
    )

    completed_tasks_count = weekly_tasks.filter(status='completed').count()
    weekly_tasks_count = weekly_tasks.count()
    weekly_progress_percent = int((completed_tasks_count / weekly_tasks_count) * 100) if weekly_tasks_count else 0

    total_study_minutes = 0
    weekly_sessions = StudySession.objects.filter(
        user_subject__user=user,
        date__range=[week_start, week_end]
    )
    for session in weekly_sessions:
        total_study_minutes += session.duration_minutes

    total_study_hours = round(total_study_minutes / 60, 1)

    latest_session = StudySession.objects.filter(
        user_subject__user=user
    ).select_related('user_subject__subject').order_by('-date', '-created_at').first()

    continue_subject = None
    continue_percent = 0
    continue_last_studied_text = ''
    continue_total_minutes = 0

    if latest_session:
        continue_subject = latest_session.user_subject

        subject_tasks = StudyPlanItem.objects.filter(user_subject=continue_subject)
        subject_completed_tasks = subject_tasks.filter(status='completed').count()
        subject_total_tasks = subject_tasks.count()
        continue_percent = int((subject_completed_tasks / subject_total_tasks) * 100) if subject_total_tasks else 0

        continue_total_minutes = 0
        all_subject_sessions = StudySession.objects.filter(user_subject=continue_subject)
        for session in all_subject_sessions:
            continue_total_minutes += session.duration_minutes

        days_diff = (today - latest_session.date).days
        if days_diff == 0:
            continue_last_studied_text = 'Today'
        elif days_diff == 1:
            continue_last_studied_text = '1 day ago'
        else:
            continue_last_studied_text = f'{days_diff} days ago'

    context = {
        'user': user,
        'weekly_progress_percent': weekly_progress_percent,
        'completed_tasks_count': completed_tasks_count,
        'weekly_tasks_count': weekly_tasks_count,
        'todays_tasks_count': todays_tasks.count(),
        'total_study_hours': total_study_hours,
        'current_streak': user.current_streak,
        'xp_points': user.xp_points,
        'todays_tasks': todays_tasks,
        'user_subjects': user_subjects,
        'continue_subject': continue_subject,
        'continue_percent': continue_percent,
        'continue_last_studied_text': continue_last_studied_text,
        'continue_total_minutes': continue_total_minutes,
    }

    return render(request, 'dashboard.html', context)

@require_POST
def toggle_task_ajax(request, id):
    if not request.session.get('user_id'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)

    try:
        user = User.objects.get(id=request.session['user_id'])

        task = StudyPlanItem.objects.select_related('user_subject__user').get(
            id=id,
            user_subject__user=user
        )

        if task.status == 'pending':
            task.status = 'completed'
        else:
            task.status = 'pending'
        task.save()

        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        weekly_tasks = StudyPlanItem.objects.filter(
            user_subject__user=user,
            study_date__range=[week_start, week_end]
        )
        completed_tasks_count = weekly_tasks.filter(status='completed').count()
        weekly_tasks_count = weekly_tasks.count()
        weekly_progress_percent = int((completed_tasks_count / weekly_tasks_count) * 100) if weekly_tasks_count else 0

        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'status': task.status,
            'weekly_progress_percent': weekly_progress_percent,
            'completed_tasks_count': completed_tasks_count,
            'weekly_tasks_count': weekly_tasks_count,
        })

    except StudyPlanItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Task not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    

@require_POST
def add_study_session_ajax(request):
    if not request.session.get('user_id'):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=401)

    try:
        user = User.objects.get(id=request.session['user_id'])
        user_subject_id = request.POST.get('user_subject_id')
        duration_minutes = request.POST.get('duration_minutes')
        notes = request.POST.get('notes', '').strip()
        session_date = request.POST.get('session_date')

        if not user_subject_id or not duration_minutes or not session_date:
            return JsonResponse({
                'success': False,
                'message': 'All required fields must be filled.'
            }, status=400)

        user_subject = UserSubject.objects.get(id=user_subject_id, user=user)

        session = StudySession.objects.create(
            user_subject=user_subject,
            duration_minutes=int(duration_minutes),
            notes=notes,
            date=session_date
        )

        User.objects.add_xp_and_streak(user)

        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        weekly_sessions = StudySession.objects.filter(
            user_subject__user=user,
            date__range=[week_start, week_end]
        )

        total_minutes = sum(item.duration_minutes for item in weekly_sessions)
        total_study_hours = round(total_minutes / 60, 1)

        return JsonResponse({
            'success': True,
            'message': 'Study session added successfully.',
            'session': {
                'subject': user_subject.subject.name,
                'duration_minutes': session.duration_minutes,
                'date': str(session.date),
                'notes': session.notes,
            },
            'stats': {
                'xp_points': user.xp_points,
                'current_streak': user.current_streak,
                'total_study_hours': total_study_hours,
            }
        })

    except UserSubject.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Subject not found.'
        }, status=404)
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Duration must be a valid number.'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    
    
def statistics(request):
    context = {
        'user': {
            'first_name': 'Munawwar',
        },
        'completed_tasks': 24,
        'total_study_hours': 42.5,
        'avg_daily_hours': 3.6,
        'current_streak': 7,

        'subject_stats': [
            {'name': 'Frontend Development', 'hours': 14, 'progress': 82},
            {'name': 'Database Systems', 'hours': 10, 'progress': 68},
            {'name': 'UI/UX Design', 'hours': 8, 'progress': 74},
            {'name': 'Python Practice', 'hours': 10.5, 'progress': 61},
        ],

        'leaderboard': [
            {'name': 'Munawwar', 'hours': 12.5},
            {'name': 'Rafeef', 'hours': 11},
            {'name': 'Basel', 'hours': 9.5},
            {'name': 'Majd', 'hours': 8},
        ],
    }
    return render(request, 'statistics.html', context)


def test_page(request):
    return render(request, 'test.html')
# Create your views here.
def home(request):
    return render(request, 'home.html')

def auth_page(request):
    if request.session.get('user_id'):
        return redirect('dashboard')
    
    return render(request, 'auth.html')

def register(request):
    if request.method == 'POST':
        errors = User.objects.validate_register(request.POST)

        if errors:
            for key, value in errors.items():
                messages.error(request, value)
            return redirect('auth')

        user = User.objects.create_user(request.POST)

        request.session['user_id'] = user.id
        return redirect('dashboard')

    return redirect('auth')


def login(request):
    if request.method == 'POST':
        errors = User.objects.validate_login(request.POST)

        if errors:
            for key, value in errors.items():
                messages.error(request, value)
            return redirect('auth')

        user = User.objects.filter(email=request.POST['email']).first()
        if not user:
            messages.error(request, "Invalid email or password.")
            return redirect('auth')

        request.session['user_id'] = user.id
        return redirect('dashboard')

    return redirect('auth')

def logout(request):
    request.session.flush()
    return redirect('auth')

def contact_us(request):
    return render(request, 'contact_us.html')


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
    latest_plan = StudyPlan.objects.filter(user=user).last()
    return render(request, 'study_plan/study_plan.html', {
        'user_subjects': user_subjects,
        'latest_plan': latest_plan,
        'days':['Monday', 'Tuesday', 'Wednesday', 'Thursday' , 'Friday', 'Saturday', 'Sunday']
    })

def generate_plan(request):
    if request.method == 'POST':
        user = User.objects.get(id=request.session['user_id'])
        available_hours = request.POST['available_hours']
        blocked_days = request.POST.getlist('blocked_days')
        user_subjects = UserSubject.objects.filter(user=user).select_related('subject')

        # Mock AI plan
        plan_data = []
        current_date = date.today()
        subjects_list = list(user_subjects)
        days_added = 0

        while days_added < 7:
            day_name = current_date.strftime('%A')
            if day_name not in blocked_days:
                for us in subjects_list:
                    plan_data.append({
                        "date": str(current_date),
                        "subject": us.subject.name,
                        "hours": round(float(available_hours) / len(subjects_list), 1)
                    })
                days_added += 1
            current_date += timedelta(days=1)

        # Save the plan
        study_plan = StudyPlan.objects.create(
            user=user,
            week_start=date.today(),
            generated_by_ai="mock"
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

#Todo:replace with real Ai when credits are avaliable

# def generate_plan(request):
#     if request.method == 'POST':
#         user = User.objects.get(id=request.session['user_id'])
#         available_hours = request.POST['available_hours']
#         blocked_days = request.POST.getlist('blocked_days')
#         user_subjects = UserSubject.objects.filter(user=user).select_related('subject')

#         # Build subjects info for the AI
#         subjects_info = []
#         for us in user_subjects:
#             subjects_info.append(
#                 f"- {us.subject.name} (Exam: {us.exam_date}, Priority: {us.priority})"
#             )
#         subjects_text = "\n".join(subjects_info)
#         blocked_text = ", ".join(blocked_days) if blocked_days else "None"
#         today = date.today()

#         prompt = f"""
# You are a smart study planner. Generate a 7-day study plan starting from {today}.

# Student's subjects:
# {subjects_text}

# Available study hours per day: {available_hours} hours
# Blocked days (no studying): {blocked_text}

# Return ONLY a JSON array, no extra text, like this:
# [
#   {{"date": "YYYY-MM-DD", "subject": "Subject Name", "hours": 2}},
#   {{"date": "YYYY-MM-DD", "subject": "Subject Name", "hours": 1.5}}
# ]

# Rules:
# - Skip blocked days completely
# - Prioritize high priority subjects
# - Split hours across subjects on the same day if needed
# - Don't exceed available hours per day
# - Focus on subjects with closer exam dates
# """

#         client = OpenAI(
#             api_key="",
#             base_url=""
#         )
#         response = client.chat.completions.create(
#              model="grok-4-latest",
#              messages=[{"role": "user", "content": prompt}]
#         )
#         response_text = response.choices[0].message.content.strip()
#         plan_data = json.loads(response_text)

#         # Save each item
#         for item in plan_data:
#             subject_name = item['subject']
#             us = user_subjects.filter(subject__name=subject_name).first()
#             if us:
#                 StudyPlanItem.objects.create(
#                     study_plan=study_plan,
#                     user_subject=us,
#                     study_date=item['date'],
#                     planned_hours=item['hours'],
#                     status='pending'
#                 )

#         return redirect('study_plan')
#     return redirect('study_plan')


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
        tasks = tasks.filter(user_subject_id = subject_filter)
    if status_filter:
        tasks = tasks.filter(status = status_filter)

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
            task.save()
            duration_minutes = int(float(task.planned_hours) * 60)
            StudySession.objects.log_session(
                user_subject=task.user_subject,
                duration_minutes=duration_minutes,
                notes=f"Completed planned study: {task.user_subject.subject.name}",
                session_date=task.study_date
            )
        else:
            task.status = 'pending'
            task.save()
        return JsonResponse({'status': task.status})

def profile_page(request):
    if not request.session.get('user_id'):
        return redirect('auth')
    
    user = User.objects.get(id=request.session['user_id'])

    sessions = StudySession.objects.filter(user_subject__user=user)
    total_minutes = 0
    for session in sessions:
        total_minutes += session.duration_minutes
    total_hours = round(total_minutes / 60, 2)

    xp_data = user.get_xp_progress()
    earned_badges = UserBadge.objects.filter(user=user).select_related('badge')
    next_badge = user.get_next_badge()
    weekly_data = StudySession.objects.weekly_data(user)

    context = {
        'user': user,
        'total_hours': total_hours,
        'xp_data': xp_data,
        'earned_badges': earned_badges,
        'next_badge': next_badge,
        'weekly_data': weekly_data
    }

    return render(request, 'profile_page.html' , context=context)

def edit_profile(request):
    if not request.session.get('user_id'):
        return redirect('auth')
    user = User.objects.get(id=request.session['user_id'])

    if request.method == 'POST':
        user.profile_edition(
            first_name=request.POST['first_name'],
            last_name=request.POST['last_name'],
            email=request.POST['email'],
            password=request.POST.get('password'),
            profile_image=request.FILES.get('profile_image')
        )
        return redirect('profile_page')

    return render(request, 'edit_profile.html', {'user': user})
