from django.contrib import admin
from .models import (
    UserProfile,
    MembershipApplication,
    Document,
    ConstitutionSummary,
    Event,
    AttendanceRecord,
    SubTeam,
    MemberGuide,
    Post, # added post comment to import
    Comment,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'role', 'is_user_administrator', 'setup_complete', 'rank_title', 'organization_name',
        'onboarding_completed', 'first_meeting_attended', 'date_joined_org',
    )
    list_filter = ('role', 'is_user_administrator', 'setup_complete')
    search_fields = (
        'user__username', 'user__email', 'organization_name',
        'cios_affiliations', 'rank_title',
    )


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'status', 'created_at', 'reviewed_by')
    list_filter = ('status',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'tag', 'uploaded_by', 'created_at')
    list_filter = ('tag',)
    search_fields = ('title', 'tag')


@admin.register(ConstitutionSummary)
class ConstitutionSummaryAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'created_by', 'created_at')
    list_filter = ('created_by',)
    search_fields = ('title', 'summary')
    ordering = ('order', 'title')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_date', 'start_time', 'location', 'created_by')
    list_filter = ('event_date',)
    search_fields = ('title', 'location', 'description')


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('member', 'event_name', 'event_date', 'present')
    list_filter = ('present', 'event_date')


@admin.register(SubTeam)
class SubTeamAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(MemberGuide)
class MemberGuideAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at')

@admin.register(Post) # based on above style, i added in the admin class for post w/ same title, author, time, content
class postAdmin(admin.ModelAdmin):
    list_display = ('message_title', 'message_author', 'message_time')
    search_fields = ('message_title', 'message_content')
    list_filter = ('message_time',)

@admin.register(Comment)
class commentAdmin(admin.ModelAdmin): # same idea for comment
    list_display = ('comment_author', 'comment_post', 'comment_time')
    search_fields = ('comment_content',)
    list_filter = ('comment_time',)

# tested on admin and post comments show up so all good
