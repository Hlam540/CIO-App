from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('select-role/', views.role_select, name='role_select'),
    path('role-management/', views.user_role_management, name='user_role_management'),
    path('role-management/<int:user_id>/history', views.admin_Change_History, name='admin_change_history'),
    path('profile/', views.user_profile, name='user_profile'),
    path('resources/', views.resource_directory, name='resource_directory'),
    path('constitution-summary/', views.constitution_summary, name='constitution_summary'),
    path('events/', views.event_calendar, name='event_calendar'),
    path('attendance/<int:event_id>/', views.mark_attendance, name='mark_attendance'), # added in attendance url
    path('dashboard/officer/', views.officer_dashboard, name='officer_dashboard'),
    path('dashboard/member/', views.member_dashboard, name='member_dashboard'),

    # Executive Member (Officer) views
    path('officer/members/', views.member_list, name='member_list'),
    path('officer/applications/', views.application_review, name='application_review'),
    path('officer/applications/<int:app_id>/<str:decision>/', views.application_decide, name='application_decide'),
    path('officer/documents/', views.document_management, name='document_management'),
    path('officer/edit-resource/<int:pk>/', views.edit_resource, name='edit_resource'),
    path('officer/exec-onboarding/', views.exec_onboarding, name='exec_onboarding'),
    path('officer/guides/', views.member_guide_management, name='member_guide_management'),

    # General Member views
    path('interest-hub/', views.interest_hub, name='interest_hub'),
    path('applications/apply/', views.membership_application, name='membership_application'),
    path('guides/', views.member_guide, name='member_guide'),
    path('my-attendance/', views.my_attendance, name='my_attendance'),

# Source / AI Citation
# AI Use: Generated with ChatGPT on 3/28/26 - "help me debug my urls addition for post and comments"
# modified to match project after debugging recs

    # messaging views, same idea as above
    path('messages/', views.post_list, name='post_list'),
    path('messages/create/', views.create_post, name='create_post'),
    path('messages/<int:post_id>/', views.post_detail, name='post_detail'),
]
