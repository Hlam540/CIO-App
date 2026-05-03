import calendar
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from .models import (
    MembershipApplication,
    Document,
    Event,
    AttendanceRecord,
    MemberGuide,
    Post, # added post/comment again
    Comment,
    AdminChangeLog
)
from functools import wraps


def executive_required(view_func):
    """Decorator that restricts a view to executive members only."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.profile.is_executive:
            return HttpResponseForbidden("Access restricted to executive members.")
        return view_func(request, *args, **kwargs)
    return wrapper


def user_admin_required(view_func):
    """Decorator that restricts a view to backend-managed User Administrators only."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.profile.is_user_admin:
            return HttpResponseForbidden("Access restricted to User Administrators.")
        return view_func(request, *args, **kwargs)
    return wrapper


def home(request):
    """Public landing page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


@login_required
def dashboard_redirect(request):
    """
    Role-Based Landing Logic:
    1. If the user has not completed setup → Role Selection page
    2. Executive Members → Officer Dashboard
    3. General Members → Member Home
    """
    profile = request.user.profile
    if not profile.setup_complete:
        return redirect('role_select')
    if profile.is_user_admin:
        return redirect('user_role_management')
    if profile.is_executive:
        return redirect('officer_dashboard')
    return redirect('member_dashboard')


@login_required
def role_select(request):
    """Mandatory role selection for first-time users after OAuth signup."""
    profile = request.user.profile

    if profile.setup_complete:
        return redirect('dashboard')

    if request.method == 'POST':
        chosen_role = request.POST.get('role')
        if chosen_role in ('executive', 'general'):
            profile.role = chosen_role
            profile.setup_complete = True
            profile.save()
            messages.success(request, f"Welcome! You signed up as {profile.get_role_display()}.")
            return redirect('dashboard')

    return render(request, 'core/role_select.html')


@executive_required
def officer_dashboard(request):
    """Dashboard for Executive Members with organization statistics."""
    from .models import UserProfile, Post

    total_members = User.objects.count()
    executive_count = UserProfile.objects.filter(role='executive').count()
    general_count = UserProfile.objects.filter(role='general').count()

    total_attendance = AttendanceRecord.objects.filter(member__profile__role='general').count()
    present_records = AttendanceRecord.objects.filter(member__profile__role='general', present=True).count()
    attendance_rate = round((present_records / total_attendance) * 100) if total_attendance > 0 else 0

    total_posts = Post.objects.count()
    total_documents = Document.objects.count()

    today = timezone.localdate()
    upcoming_event_count = Event.objects.filter(event_date__gte=today).count()

    return render(request, 'core/officer_dashboard.html', {
        'user': request.user,
        'profile': request.user.profile,
        'total_members': total_members,
        'executive_count': executive_count,
        'general_count': general_count,
        'attendance_rate': attendance_rate,
        'total_attendance': total_attendance,
        'total_posts': total_posts,
        'total_documents': total_documents,
        'upcoming_event_count': upcoming_event_count,
    })


@login_required
def member_dashboard(request):
    """Dashboard for General Members."""
    return render(request, 'core/member_dashboard.html', {
        'user': request.user,
        'profile': request.user.profile,
    })


@user_admin_required
def user_role_management(request):
    """Allow User Administrators to view users and change non-admin app roles."""
    if request.method == 'POST':
        profile = get_object_or_404(
            User.objects.select_related('profile'),
            pk=request.POST.get('user_id'),
        ).profile
        new_role = request.POST.get('role')

        if new_role in ('executive', 'general'):
            old_role = profile.role
            profile.role = new_role
            profile.save(update_fields=['role'])
            if old_role != new_role:
                AdminChangeLog.objects.create(
                    changed_by=request.user,
                    affected_user=profile.user,
                    old_role=old_role,
                    new_role=new_role,
                )
            messages.success(request, f"Updated {profile.user.username} to {profile.get_role_display()}.")
        else:
            messages.error(request, "Choose a valid application role.")
        return redirect('user_role_management')

    profiles = User.objects.select_related('profile').order_by('first_name', 'username')
    return render(request, 'core/user_role_management.html', {
        'profiles': profiles,
    })


# ─── Executive Member Views ───────────────────────────────────────────

@executive_required
def member_list(request):
    """View all members and their contact information."""

    executives = User.objects.select_related('profile').filter(profile__role='executive').order_by('first_name', 'username') # updated to show current exec members

    members = User.objects.select_related('profile').filter(profile__role='general').order_by('first_name', 'username')

    return render(request, 'core/officer/member_list.html', {'executives': executives, 'members': members})


@executive_required
def application_review(request):
    """List all membership applications for review."""
    applications = MembershipApplication.objects.select_related('applicant').order_by('-created_at')
    return render(request, 'core/officer/application_review.html', {'applications': applications})


@executive_required
def application_decide(request, app_id, decision):
    """Approve or deny a membership application."""
    if request.method != 'POST':
        return redirect('application_review')
    application = get_object_or_404(MembershipApplication, pk=app_id)
    if decision in ('approved', 'denied'):
        application.status = decision
        application.reviewed_by = request.user
        application.save()
    if decision == 'approved': # adding in so user becomes active in system flow
        profile = application.applicant.profile
        profile.setup_complete = True
        profile.save()
    return redirect('application_review')


@executive_required
def document_management(request):
    """Manage tagged resource links and uploaded files."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        url = request.POST.get('url', '').strip()
        tag = request.POST.get('tag', '').strip()
        if "#" in tag:
            tag = tag.replace("#", "").strip()
        description = request.POST.get('description', '').strip()
        uploaded_file = request.FILES.get('file')
        if title and tag and (url or uploaded_file):
            Document.objects.create(
                title=title,
                url=url,
                file=uploaded_file,
                tag=tag,
                description=description, uploaded_by=request.user,
                category='general',
            )
            messages.success(request, "Resource saved successfully.")
        else:
            messages.error(request, "Provide a title, tag, and either a URL or a file upload.")
        return redirect('document_management')

    #documents = Document.objects.select_related('uploaded_by').order_by('-created_at')
    documents = Document.objects.filter(category='general').select_related('uploaded_by').order_by('-created_at')
    tags = Document.objects.filter(category='general').values_list('tag', flat=True).distinct()
    selected_tag = request.GET.get('tag')
    if selected_tag:
        documents = documents.filter(tag=selected_tag)
    return render(request, 'core/officer/document_management.html', {
        'documents': documents,
        'tags': tags,
        'selected_tag': selected_tag,
    })

@executive_required
def edit_resource(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        document.title = request.POST.get("title", "").strip()
        document.tag = request.POST.get("tag", "").strip()
        if "#" in document.tag:
            document.tag = document.tag.replace("#", "").strip()
        document.description = request.POST.get("description", "").strip()

        url = request.POST.get("url", "").strip()
        if url:
            document.url = url
            document.file = None

        if request.FILES.get("file"):
            document.file = request.FILES.get("file")
            document.url = ""

        if not document.title or not document.tag or not (document.url or document.file):
            messages.error(request, "Provide a title, tag, and either a URL or a file upload.")
            return redirect("edit_resource", pk=document.pk)

        document.save()

        return redirect("document_management")

    return render(request, "core/officer/edit_resource.html", {"document": document})


@executive_required
def exec_onboarding(request):
    """Manage tagged resource links and uploaded exec onboarding documents"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        url = request.POST.get('url', '').strip()
        tag = request.POST.get('tag', '').strip()
        description = request.POST.get('description', '').strip()
        uploaded_file = request.FILES.get('file')
        if title and tag and (url or uploaded_file):
            Document.objects.create(
                title=title,
                url=url,
                file=uploaded_file,
                tag=tag,
                description=description, uploaded_by=request.user,
                category='onboarding',
            )
            messages.success(request, "Resource saved successfully.")
        else:
            messages.error(request, "Provide a title, tag, and either a URL or a file upload.")
        return redirect('exec_onboarding')

    #documents = Document.objects.select_related('uploaded_by').order_by('-created_at')
    documents = Document.objects.filter(category='onboarding').select_related('uploaded_by').order_by('-created_at')
    tags = Document.objects.filter(category='onboarding').values_list('tag', flat=True).distinct()
    selected_tag = request.GET.get('tag')
    if selected_tag:
        documents = documents.filter(tag=selected_tag)
    return render(request, 'core/officer/exec_onboarding.html', {
        'documents': documents,
        'tags': tags,
        'selected_tag': selected_tag,
    })


@executive_required
def member_guide_management(request):
    """Create and manage onboarding guides for new members."""
    if request.method == 'POST':
        if request.POST.get('action') == 'delete':
            guide = get_object_or_404(MemberGuide, pk=request.POST.get('guide_id'))
            guide.delete()
            messages.success(request, "Guide deleted successfully.")
            return redirect('member_guide_management')

        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if title and content:
            MemberGuide.objects.create(
                title=title,
                content=content,
                created_by=request.user,
            )
            messages.success(request, "Guide published successfully.")
        else:
            messages.error(request, "Both title and content are required.")
        return redirect('member_guide_management')

    guides = MemberGuide.objects.select_related('created_by').all()
    return render(request, 'core/officer/member_guide_management.html', {
        'guides': guides,
    })


# ─── General Member Views ─────────────────────────────────────────────

@login_required
def interest_hub(request):
    """Public-facing view of the club's mission."""
    return render(request, 'core/member/interest_hub.html')


@login_required
def member_guide(request):
    """View new member guides and instructions."""
    guides = MemberGuide.objects.select_related('created_by').all()
    return render(request, 'core/member/member_guide.html', {'guides': guides})


@login_required
def membership_application(request):
    """Allow members to submit a membership application for officer review."""
    existing_applications = MembershipApplication.objects.filter(applicant=request.user).order_by('-created_at')

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        has_pending_application = existing_applications.filter(status='pending').exists()
        if has_pending_application:
            messages.error(request, "You already have a pending application.")
        elif reason:
            MembershipApplication.objects.create(applicant=request.user, reason=reason)
            messages.success(request, "Your application was submitted for review.")
            return redirect('membership_application')
        else:
            messages.error(request, "Tell us why you want to join before submitting.")

    return render(request, 'core/member/membership_application.html', {
        'applications': existing_applications,
        'has_pending_application': existing_applications.filter(status='pending').exists(),
    })


@login_required
def my_attendance(request):
    """View personal attendance history."""
    records = AttendanceRecord.objects.filter(member=request.user)
    total = records.count()
    present_count = records.filter(present=True).count()
    rate = round((present_count / total) * 100) if total > 0 else 0
    return render(request, 'core/member/my_attendance.html', {
        'records': records,
        'total': total,
        'present_count': present_count,
        'rate': rate,
    })


@login_required
def user_profile(request):
    """Display and update the signed-in user's profile information."""
    profile = request.user.profile

    if request.method == 'POST':
        profile.organization_name = request.POST.get('organization_name', '').strip()
        profile.cios_affiliations = request.POST.get('cios_affiliations', '').strip()
        profile.rank_title = request.POST.get('rank_title', '').strip()
        profile.onboarding_completed = request.POST.get('onboarding_completed') == 'on'
        profile.first_meeting_attended = request.POST.get('first_meeting_attended') == 'on'
        profile.emergency_contact_name = request.POST.get('emergency_contact_name', '').strip()
        profile.emergency_contact_relationship = request.POST.get('emergency_contact_relationship', '').strip()
        profile.emergency_contact_phone = request.POST.get('emergency_contact_phone', '').strip()
        profile.save()
        messages.success(request, "Your profile was updated successfully.")
        return redirect('user_profile')

    affiliations = [item.strip() for item in profile.cios_affiliations.split(',') if item.strip()]
    milestones = [
        {'label': 'Completed Onboarding', 'done': profile.onboarding_completed},
        {'label': 'First Meeting Attended', 'done': profile.first_meeting_attended},
    ]

    return render(request, 'core/profile.html', {
        'profile': profile,
        'affiliations': affiliations,
        'milestones': milestones,
    })


@login_required
def resource_directory(request):
    """Centralized links directory for all members."""
    selected_tag = request.GET.get('tag')
    resources = Document.objects.filter(category='general').select_related('uploaded_by').order_by('-created_at')
    tags = Document.objects.filter(category='general').values_list('tag', flat=True).distinct().order_by('tag')
    if selected_tag:
        resources = resources.filter(tag=selected_tag)

    return render(request, 'core/resource_directory.html', {
        'resources': resources,
        'tags': tags,
        'selected_tag': selected_tag,
    })


@login_required
def constitution_summary(request):
    """Upload and view constitution files."""
    if request.method == 'POST':
        if not request.user.profile.is_executive:
            return HttpResponseForbidden("Access restricted to executive members.")

        title = request.POST.get('document_title', '').strip()
        description = request.POST.get('document_description', '').strip()
        uploaded_file = request.FILES.get('constitution_file')

        if title and uploaded_file:
            Document.objects.create(
                title=title,
                file=uploaded_file,
                tag='Constitution',
                description=description,
                uploaded_by=request.user,
                category='general',
            )
            messages.success(request, "Constitution file uploaded successfully.")
        else:
            messages.error(request, "Provide a title and constitution file to upload.")
        return redirect('constitution_summary')

    constitution_documents = (
        Document.objects.filter(category='general', tag__iexact='Constitution')
        .select_related('uploaded_by')
        .order_by('-created_at')
    )
    return render(request, 'core/constitution_summary.html', {
        'constitution_documents': constitution_documents,
    })

@executive_required
def mark_attendance(request, event_id): # for marking attendance
    event = get_object_or_404(Event, id=event_id)
    members = User.objects.select_related('profile').filter(
        profile__role='general',
        profile__is_user_administrator=False,
        profile__setup_complete=True,
    ).order_by('first_name', 'username')
    existing_records = {
        record.member_id: record.present
        for record in AttendanceRecord.objects.filter(
            event=event,
            member__in=members,
        )
    }

    if request.method == 'POST':
        for member in members:
            present = request.POST.get(f"user_{member.id}") == 'on'

            AttendanceRecord.objects.filter(
                member=member,
                event=event,
            ).delete()
            AttendanceRecord.objects.create(
                member=member,
                event=event,
                event_name=event.title,
                event_date=event.event_date,
                present=present,
                recorded_by=request.user
            )

        messages.success(request, "Attendance updated successfully.")
        return redirect('event_calendar')

    return render(request, 'core/officer/mark_attendance.html', {
        'event': event,
        'members': members,
        'existing_records': existing_records,
    })

@login_required
def event_calendar(request):
    if request.method == 'POST':
        if not request.user.profile.is_executive:
            return HttpResponseForbidden("Access restricted to executive members.")

        title = request.POST.get('title', '').strip()
        event_date = parse_date(request.POST.get('event_date', '').strip())
        start_time_value = request.POST.get('start_time', '').strip()
        start_time = parse_time(start_time_value) if start_time_value else None
        location = request.POST.get('location', '').strip()
        description = request.POST.get('description', '').strip()

        if title and event_date and location:
            Event.objects.create(
                title=title,
                event_date=event_date,
                start_time=start_time,
                location=location,
                description=description,
                created_by=request.user,
            )
            messages.success(request, "Event added successfully.")
        else:
            messages.error(request, "Provide an event title, date, and location.")
        return redirect('event_calendar')

    today = timezone.localdate()
    year = today.year
    month = today.month

    cal = calendar.Calendar(firstweekday=calendar.SUNDAY).monthdayscalendar(year, month)

    events = Event.objects.filter(
        event_date__year=year,
        event_date__month=month
    ).order_by('event_date')

    events_by_day = {}
    for event in events:
        day = event.event_date.day
        events_by_day.setdefault(day, []).append(event)

    upcoming_events = Event.objects.filter(event_date__gte=today).order_by('event_date', 'start_time', 'title')
    past_events = Event.objects.filter(event_date__lt=today).order_by('-event_date', 'start_time', 'title')

    return render(request, 'core/event_calendar.html', {
        'calendar': cal,
        'events_by_day': events_by_day,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'can_manage_events': request.user.profile.is_executive,
    })

# Source / AI Citation
# Description: comment/post views
# https://docs.djangoproject.com/en/6.0/topics/auth/default/
# AI Use: Generated with ChatGPT on 3/28/26 - "help me come up with a Django comment/post views that doesn't break existing structure and includes showing new comments,sending errors when necessary"
# modified to match project settings and debugged for this particular fit

@login_required
def post_list(request):
    """show all message board posts."""

    posts = Post.objects.select_related('message_author').prefetch_related('comments').all() # get all posts from database
    return render(request, 'core/post_list.html', {'posts': posts}) # send posts to template so frontend can make visibile

@login_required
def post_detail(request, post_id):
    """show one post and allow logged-in users to add comments."""
    post = get_object_or_404(
        Post.objects.select_related('message_author').prefetch_related('comments__comment_author'),
        pk=post_id,
    ) # get post or return 404
    if request.method == 'POST':
        content = request.POST.get('content', '').strip() # if user submits comment form, get text

        if content: # create comment if not empty
            Comment.objects.create(comment_post=post, comment_author=request.user, comment_content=content,) # link comment to post, user, text
            messages.success(request, "Reply added successfully.") # success shown
            return redirect('post_detail', post_id=post.id) # reload page show new comment
        messages.error(request, "comment can't be empty.") # error if empty
    
    return render(request, 'core/post_detail.html', {'post': post}) # post page w post data'
        
@login_required
def create_post(request):
    """allow any logged-in user to create a new discussion thread."""

    if request.method == 'POST': # if form submitted
        title = request.POST.get('title', '').strip() # get title content
        content = request.POST.get('content', '').strip()

        if title and content: # only create if both exist
            Post.objects.create(message_title=title, message_content=content, message_author=request.user)
            messages.success(request, "post created successfully.") # show success like above
            return redirect('post_list') # and go back to list page
        messages.error(request, "both title and content required.")
    return render(request, 'core/create_post.html') # show create post form

@user_admin_required
def admin_Change_History(request, user_id):
    user = get_object_or_404(User, id=user_id)
    logs = AdminChangeLog.objects.filter(affected_user=user).order_by('-timestamp')

    return render(request, 'core/admin_change_history.html', {
        'selected_user': user,
        'logs': logs
    })
