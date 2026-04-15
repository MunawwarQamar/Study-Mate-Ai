from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/add-session-ajax/', views.add_study_session_ajax, name='add_study_session_ajax'),
    path('statistics/', views.statistics, name='statistics'),
    path('study-rooms/', views.study_rooms, name='study_rooms'),
    path('study-rooms/data/', views.study_rooms_data_ajax, name='study_rooms_data_ajax'),
    path('study-rooms/join/<int:room_id>/', views.join_room_ajax, name='join_room_ajax'),
    path('study-rooms/details/<int:room_id>/', views.room_details_ajax, name='room_details_ajax'),
    path('study-rooms/create/', views.create_room_ajax, name='create_room_ajax'),
    path('study-rooms/leave/<int:room_id>/', views.leave_room_ajax, name='leave_room_ajax'),
    path('notifications/', views.notifications_page, name='notifications_page'),
    path('', views.home),
    path('auth/', views.auth_page, name='auth'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('contact-us/', views.contact_us, name='contact_us'),
    #profile
    path('profile/', views.profile_page, name='profile_page'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('admin-messages/', views.contact_messages_list, name='contact_messages'),
    path('admin-messages/<int:message_id>/mark-read/', views.mark_message_read, name='mark_message_read'),
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
