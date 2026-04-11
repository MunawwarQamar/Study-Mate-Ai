from django.urls import path
from . import views

urlpatterns = [
    path('test/', views.test_page),
    path('', views.home),
    path('auth/', views.auth_page, name='auth'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('contact-us/', views.contact_us, name='contact_us'),
    #profile
    path('profile/', views.profile_page, name='profile_page'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    # Subjects
    path('subjects/' , views.all_subjects, name='all_subjects'),
    path('subjects/add/' , views.add_subject, name='add_subject'),
    path('subjects/edit/<int:id>/' , views.edit_subject, name='edit_subject'),
    path('subjects/delete/<int:id>/' , views.delete_subject, name='delete_subject'),
    # Study Plan
    path('study-plan/' , views.study_plan, name='study_plan'),
    path('study-plan/generate/' , views.generate_plan, name='generate_plan'),
    # Tasks
    path('tasks/' , views.all_tasks, name='all_tasks'),
    path('tasks/toggle/<int:id>/' , views.toggle_task, name='toggle_task'),

]
