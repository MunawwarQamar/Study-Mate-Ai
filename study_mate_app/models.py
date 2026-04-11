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

    def add_xp_and_streak(self, user, xp=5):
        user.xp_points += xp
        today = date.today()

        if user.last_study_date == today - timedelta(days=1):
            user.current_streak += 1
        elif user.last_study_date != today:
            user.current_streak = 1

        user.last_study_date = today
        user.save()
        badges = Badge.objects.all()

        for badge in badges:
            if user.xp_points >= badge.xp_required:
                already_earned = UserBadge.objects.filter(user=user, badge=badge).exists()
                if not already_earned:
                    UserBadge.objects.create(user=user, badge=badge)

    def get_xp_progress(self, user):
        level = user.xp_points // 100
        current_xp = user.xp_points % 100

        return {
            'level': level,
            'current_xp': current_xp,
            'next_level_xp': 100,
            'progress_percent': int((current_xp / 100) * 100)
        }

    def get_next_badge(self, user):
        badges = Badge.objects.all().order_by('xp_required')
        for badge in badges:
            already_has = UserBadge.objects.filter(user=user, badge=badge).exists()
            if not already_has and user.xp_points < badge.xp_required:
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
    def log_session(self, user_subject, duration_minutes, notes, session_date):
        session = self.create(user_subject=user_subject, duration_minutes=duration_minutes, notes=notes , session_date=session_date)
        user = user_subject.user
        User.objects.add_xp_and_streak(user)

        return session
    
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
            result[day] += session.duration_minutes / 60
        
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

class Badge(models.Model):
    name = models.CharField(max_length=50)
    xp_required = models.IntegerField()
    icon = models.ImageField(upload_to='badges/', blank=True, null=True)

    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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