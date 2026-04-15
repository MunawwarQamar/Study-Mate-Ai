from django.db import models
import re
import datetime
import bcrypt
from datetime import date, timedelta

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

# Create your models here.

class UserManager(models.Manager):
    def validate_register(self, data):
        errors={}
        first_name = data.get('first_name' , '').strip()
        if not first_name:
            errors['first_name'] = 'First name is required.'
        elif len(first_name) <= 2:
            errors['first_name'] = 'First name must be at least 2 characters long.'
        last_name = data.get('last_name' , '').strip()
        if not last_name:
            errors['last_name'] = 'Last name is required.'
        elif len(last_name) <= 2:
            errors['last_name'] = 'Last name must be at least 2 characters long.'
        email = data.get('email' , '').strip()
        if not email:
            errors['email'] = 'Email address is required.'
        elif not EMAIL_REGEX.match(email):
            errors['email'] = 'Invalid email'
        elif User.objects.filter(email=email).first():
            errors['email'] = 'This email address already exists. Please revise and try again.'
        password = data.get('password', '').strip()
        confirm_password=data.get('confirm_password', '').strip()
        if not password:
            errors['password'] = 'Password is required.'
        elif len(password) < 6 :
            errors['password'] = 'Password must be at least 6 characters.'
        if password != confirm_password:
            errors['confirm_password'] = 'Passwords do not match.'
        date_of_birth = data.get('date_of_birth' , '')
        if not date_of_birth:
            errors['date_of_birth'] = 'Date of Birth is required.'
        elif date_of_birth:
            date_of_birth= datetime.datetime.strptime(date_of_birth,'%Y-%m-%d').date()
            today=datetime.date.today()
            if date_of_birth > today:
                errors['date_of_birth'] = 'Date of Birth cannot be in the future. Please enter a valid Date of Birth.'
        return errors
    
    def create_user(self, data):
        first_name = data.get('first_name' , '').strip()
        last_name = data.get('last_name' , '').strip()
        email = data.get('email' , '').strip()
        date_of_birth = data.get('date_of_birth' , '')
        password = data.get('password' , '')
        password_hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User.objects.create(first_name=first_name , last_name=last_name , email=email , date_of_birth=date_of_birth , password=password_hashed)
        return user
    
    def update_profile(self, user, data, files):
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)

        uploaded_image = files.get('profile_image')
        avatar_choice = data.get('avatar_choice')

        if uploaded_image:
            user.profile_image = uploaded_image
        elif avatar_choice:
            user.profile_image = f'avatars/{avatar_choice}'

        password = data.get('password')
        if password:
            user.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        user.save()
        return user
    
    def validate_login(self , data):
        errors={}
        email = data.get('email' , '').strip()
        password = data.get('password' , '')

        if not email or not password:
            errors['user'] = 'Email and password are required.'
            return errors
        
        user = User.objects.filter(email=email).first()
        if not user:
            errors['user'] = 'Invalid email or password.'
            return errors
        
        user_password = user.password
        if not bcrypt.checkpw(password.encode(), user_password.encode()):
            errors['user'] = 'Invalid email or password.'

        return errors
    
    def get_user(self, data):
        email = data.get('email' , '').strip()
        return User.objects.filter(email=email).first()

class StudySessionManager(models.Manager):
    def log_session(self, user_subject, duration_minutes, notes, session_date, study_plan_item=None):
        if study_plan_item:
            existing = self.filter(study_plan_item=study_plan_item).first()
            if existing:
                existing.duration_minutes = duration_minutes
                existing.notes = notes
                existing.date = session_date
                existing.save()
                return existing
            
        session = self.create(user_subject=user_subject, duration_minutes=duration_minutes, notes=notes , date=session_date, study_plan_item=study_plan_item)
        xp = max(1, duration_minutes // 10)
        user_subject.user.add_xp_and_streak(xp, session_date)

        return session
    
    def remove_session(self, study_plan_item):
        sessions = self.filter(study_plan_item=study_plan_item)
        
        if not sessions.exists():
            return 0
        
        total_xp_to_remove = sum(
            max(1, session.duration_minutes // 10) 
            for session in sessions
        )
        
        session_date = sessions.first().date
        user = study_plan_item.user_subject.user
        
        deleted_count, _ = sessions.delete()
        
        if deleted_count > 0:
            user.xp_points = max(0, user.xp_points - total_xp_to_remove)
            today = date.today()
            if session_date == today:
                has_sessions_today = StudySession.objects.filter(
                    user_subject__user=user,
                    date=today
                ).exists()
                
                if not has_sessions_today:
                    yesterday = today - timedelta(days=1)
                
                    if user.last_study_date == today:
                        if StudySession.objects.filter(
                            user_subject__user=user,
                            date=yesterday
                        ).exists():
                            user.current_streak = max(0, user.current_streak - 1)
                            user.last_study_date = yesterday
                        else:
                            user.current_streak = 0
                            user.last_study_date = None
            user.recheck_badges()
            user.save()
        
        return total_xp_to_remove
        
    def weekly_data(self, user):
        today = date.today()
        start = today - timedelta(days=6)


        result = {}
        for i in range(7):
            day = start + timedelta(days=i)
            result[str(day)] = 0

        sessions = self.filter(
            user_subject__user=user,
            date__range=[start, today]
        )
        
        for session in sessions:
            day=str(session.date)
            hours = session.duration_minutes / 60
            result[day] += hours

        for day in result:
            result[day] = round(result[day], 2)
        
        return result

class User(models.Model):
    first_name = models.CharField(max_length=45)
    last_name = models.CharField(max_length=45)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField()
    password = models.CharField(max_length=255)
    daily_study_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    profile_image = models.ImageField(upload_to='profile_images/', default='profile_images/default_avatar.jpg', blank=True, null=True)
    xp_points = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = UserManager()

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
    
    def add_xp_and_streak(self, xp=5, session_date=None):
        self.xp_points += xp
        study_date = session_date or date.today()
        today = date.today()

        if study_date == today:
            if self.last_study_date != today:
                if self.last_study_date == today - timedelta(days=1):
                    self.current_streak += 1
                else:
                    self.current_streak = 1
                self.last_study_date = today
        self.save()
        self.check_badges()

    def check_badges(self):
        from .models import Badge, UserBadge
        badges = Badge.objects.all()

        for badge in badges:
            if self.xp_points >= badge.xp_required:
                already_earned = UserBadge.objects.filter(
                    user=self,
                    badge=badge
                ).exists()

                if not already_earned:
                    UserBadge.objects.create(
                        user=self,
                        badge=badge
                    )

    def recheck_badges(self):
        from .models import Badge, UserBadge
        
        badges_to_remove = Badge.objects.filter(xp_required__gt=self.xp_points)
        
        UserBadge.objects.filter(
            user=self,
            badge__in=badges_to_remove
        ).delete()

    def get_xp_progress(self):
        level = 0
        xp_needed_for_this_level = 100 
        remaining_xp = self.xp_points
        
        while remaining_xp >= xp_needed_for_this_level:
            remaining_xp = remaining_xp - xp_needed_for_this_level
            level = level + 1
            xp_needed_for_this_level = xp_needed_for_this_level + 100  
        
        next_level_xp = xp_needed_for_this_level
        
        return {
            'level': level,
            'current_xp': remaining_xp,
            'next_level_xp': next_level_xp,
            'progress_percent': int((remaining_xp / next_level_xp) * 100)
        }

    def get_next_badge(self):
        badges = Badge.objects.all().order_by('xp_required')
        for badge in badges:
            already_has = UserBadge.objects.filter(user=self, badge=badge).exists()
            if not already_has and self.xp_points < badge.xp_required:
                return badge
        return None
    
    def profile_edition(self, first_name, last_name, email, password=None, profile_image=None):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email

        if profile_image:
            self.profile_image = profile_image

        if password:
            self.password = bcrypt.hashpw(
                password.encode(), bcrypt.gensalt()
            ).decode()

        self.save()

class Badge(models.Model):
    name = models.CharField(max_length=50)
    xp_required = models.IntegerField()
    icon = models.ImageField(upload_to='badges/', blank=True, null=True)

    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

class Subject(models.Model):
    name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    users = models.ManyToManyField(User, through='UserSubject', related_name='subjects')

    def __str__(self):
        return self.name

class UserSubject(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='user_subjects')

    exam_date = models.DateField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} - {self.subject} ({self.priority})'

class StudyPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='study_plans')

    week_start = models.DateField()
    generated_by_ai = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.first_name} {self.week_start}'

class StudyPlanItem(models.Model):
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='plan_items')
    user_subject = models.ForeignKey(UserSubject, on_delete=models.CASCADE, related_name='plan_items')

    study_date = models.DateField()
    planned_hours = models.DecimalField(max_digits=4, decimal_places=2)
    STATUS_CHOICES = [
        ('pending' , 'Pending'),
        ('completed' , 'Completed')
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.study_date}'

class StudySession(models.Model):
    user_subject = models.ForeignKey(UserSubject, on_delete=models.CASCADE, related_name='sessions')
    study_plan_item = models.ForeignKey('StudyPlanItem', on_delete=models.CASCADE, null=True, blank=True, related_name='task_sessions')

    duration_minutes = models.IntegerField()
    notes = models.TextField(blank=True)
    date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = StudySessionManager()

    def __str__(self):
        return f'{self.date}'

class ProgressSummary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')

    week_start = models.DateField()
    total_minutes = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.first_name} {self.week_start}'

class Notification(models.Model):
    TYPE_CHOICES = [
        ('daily reminder', 'Daily Reminder'),
        ('weekly reminder', 'Weekly Reminder'),
        ('system alert', 'System Alert'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')

    type = models.CharField(max_length=35, choices=TYPE_CHOICES)
    message = models.TextField()
    status = models.CharField(max_length=35, choices=STATUS_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.first_name} {self.type}'

class StudyRoom(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='study_rooms')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')

    name = models.CharField(max_length=100)
    exam_date = models.DateField()
    max_members = models.IntegerField()

    description = models.TextField(blank=True)
    session_goal = models.TextField(blank=True)
    scheduled_time = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=50, blank=True)
    meeting_link = models.URLField(blank=True)
    shared_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    users = models.ManyToManyField(User, through='RoomMember', related_name='study_rooms')

    def __str__(self):
        return f'{self.name} ({self.subject.name})'
class RoomMember(models.Model):
    room = models.ForeignKey(StudyRoom, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_memberships')
    
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} in {self.room}'