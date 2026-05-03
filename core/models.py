from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extends the default Django User with CIO-specific role information.
    Each user has a role: either an Executive Member (officer/president)
    or a General Member.
    """

    ROLE_CHOICES = [
        ('executive', 'Executive Member'),
        ('general', 'General Member'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='general')
    is_user_administrator = models.BooleanField(
        default=False,
        help_text='Designates a backend-managed User Administrator for role management only.',
    )
    setup_complete = models.BooleanField(
        default=False,
        help_text='Whether the user has completed initial role selection after signup.',
    )
    organization_name = models.CharField(max_length=200, blank=True, default='')
    cios_affiliations = models.TextField(
        blank=True,
        default='',
        help_text='Comma-separated list of CIOs this user belongs to.',
    )
    rank_title = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Specific position (e.g., Member, Treasurer, President).',
    )
    onboarding_completed = models.BooleanField(default=False)
    first_meeting_attended = models.BooleanField(default=False)
    emergency_contact_name = models.CharField(max_length=120, blank=True, default='')
    emergency_contact_relationship = models.CharField(max_length=80, blank=True, default='')
    emergency_contact_phone = models.CharField(max_length=30, blank=True, default='')
    date_joined_org = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def is_executive(self):
        return self.role == 'executive'

    @property
    def is_general(self):
        return self.role == 'general'

    @property
    def is_user_admin(self):
        return self.is_user_administrator


class MembershipApplication(models.Model):
    """Application submitted by a prospective or existing member for review."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]

    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    reason = models.TextField(help_text="Why do you want to join?")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.applicant.get_full_name() or self.applicant.username} - {self.get_status_display()}"


class Document(models.Model):
    """A tagged resource that can be an external link or uploaded file."""
    CATEGORY_CHOICES = [
        ('general', 'Document Management'),
        ('onboarding', 'Exec Onboarding'),
    ]
    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general'
    )
    url = models.URLField(blank=True, default='')
    file = models.FileField(upload_to='documents/', blank=True, null=True)
    tag = models.CharField(max_length=50, help_text="Category tag, e.g. Budget, Minutes, Constitution")
    description = models.TextField(blank=True, default='')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} [#{self.tag}]"

    @property
    def resource_url(self):
        if self.file:
            return self.file.url
        return self.url

    @property
    def is_upload(self):
        return bool(self.file)


class ConstitutionSummary(models.Model):
    """Short, readable constitution highlights for members."""

    title = models.CharField(max_length=200)
    summary = models.TextField()
    order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='constitution_summaries')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return self.title


class Event(models.Model):
    """Basic event listing for upcoming meetings and locations."""

    title = models.CharField(max_length=200)
    event_date = models.DateField()
    location = models.CharField(max_length=200)
    start_time = models.TimeField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event_date', 'start_time', 'title']

    def __str__(self):
        return f"{self.title} ({self.event_date})"


class AttendanceRecord(models.Model):
    """Tracks a member's attendance at an event."""

    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    event = models.ForeignKey(
        Event,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records',
    )
    event_name = models.CharField(max_length=200)
    event_date = models.DateField()
    present = models.BooleanField(default=True)
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='recorded_attendance'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-event_date']

    def __str__(self):
        status = "Present" if self.present else "Absent"
        return f"{self.member.username} - {self.event_name} ({status})"


class SubTeam(models.Model):
    """A sub-team or committee within the CIO."""

    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name


class MemberGuide(models.Model):
    """A guide or instruction document for new members."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='guides')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

# Source / AI Citation
# Description: comment/post model
# https://docs.djangoproject.com/en/6.0/ref/models/options/
# AI Use: Generated with ChatGPT on 3/28/26 - "help me come up with a Django comment/post model that includes title, content, author, time, ordering"
# modified to match project settings and debugged for this particular fit

class Post(models.Model):
    message_title = models.CharField(max_length=200) # title of the post
    message_content = models.TextField() # content of post

    message_author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts') # if user deleted, posts too, check all user posts if needed
    message_time = models.DateTimeField(auto_now_add=True) # store time made

    class Meta:
        ordering = ['-message_time'] # ordering post (newest first)
    
    def __str__(self):
        return self.message_title # what shows in admin panel

class Comment(models.Model):
    comment_post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments') # post for comment
    comment_author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments') # who wrote comment
    comment_content = models.TextField() # whats in comment
    comment_time = models.DateTimeField(auto_now_add=True) # when made

    class Meta:
        ordering = ['comment_time'] # this time oldest to newest for convo

    def __str__(self):
        return f"Comment by {self.comment_author.username} on {self.comment_post.message_title}" # good for debugging

class AdminChangeLog(models.Model):
    """Tracks the changes made by admin for each user."""

    changed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="changes_made")
    affected_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="changes_received")
    old_role = models.CharField(max_length=50)
    new_role = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.changed_by} changed {self.affected_user} from {self.old_role} to {self.new_role}"
