from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('islamic/', views.islamic, name='islamic'),
    path('physical/', views.physical, name='physical'),
    path('knowledge/', views.knowledge, name='knowledge'),
    path('programming/', views.programming, name='programming'),
    path('stats/', views.stats, name='stats'),
    path('achievements/', views.achievements, name='achievements'),
    path('settings/', views.settings_view, name='settings'),

    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),

    path('my-system/', views.my_system, name='my_system'),

    # Health check (used by Render)
    path('health/', views.health_check, name='health_check'),

    # API (AJAX)
    path('api/update/', views.api_update, name='api_update'),
    path('api/custom-tasks/', views.api_custom_tasks, name='api_custom_tasks'),
    path('api/stats-data/', views.api_stats_data, name='api_stats_data'),
    path('api/settings/', views.api_settings, name='api_settings'),
    path('api/sections/', views.api_sections, name='api_sections'),
    path('api/habits/', views.api_habits, name='api_habits'),
    path('api/habit-log/', views.api_habit_log, name='api_habit_log'),
]
