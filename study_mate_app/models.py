from django.db import models

# Create your models here.

class User(models.Model):
    first_name = models.CharField(max_length=45)
    last_name = models.CharField(max_length=45)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField()
    password = models.CharField(max_length=255)
    daily_study_hours = models.DecimalField(max_digits=4, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

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
        {'pending' , 'Pending'},
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