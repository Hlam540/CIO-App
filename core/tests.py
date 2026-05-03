from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import (
    AdminChangeLog,
    AttendanceRecord,
    Comment,
    Document,
    Event,
    MembershipApplication,
    Post,
    UserProfile,
)


class UserAdministratorTests(TestCase):
    def setUp(self):
        self.user_admin = User.objects.create_user(
            username='roleadmin',
            password='testpass123',
            first_name='Role',
            last_name='Admin',
            email='roleadmin@example.com',
        )
        self.executive = User.objects.create_user(
            username='execmember',
            password='testpass123',
            first_name='Exec',
            last_name='Member',
            email='exec@example.com',
        )
        self.general = User.objects.create_user(
            username='generalmember',
            password='testpass123',
            first_name='General',
            last_name='Member',
            email='general@example.com',
        )

        UserProfile.objects.filter(user=self.user_admin).update(
            role='general',
            setup_complete=True,
            is_user_administrator=True,
        )
        UserProfile.objects.filter(user=self.executive).update(role='executive', setup_complete=True)
        UserProfile.objects.filter(user=self.general).update(role='general', setup_complete=True)

    def test_user_admin_dashboard_redirects_to_role_management(self):
        self.client.login(username='roleadmin', password='testpass123')

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(response, reverse('user_role_management'))

    def test_user_admin_can_view_role_management_page(self):
        self.client.login(username='roleadmin', password='testpass123')

        response = self.client.get(reverse('user_role_management'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Role Management')
        self.assertContains(response, 'exec@example.com')

    def test_user_admin_can_change_non_admin_roles(self):
        self.client.login(username='roleadmin', password='testpass123')

        response = self.client.post(
            reverse('user_role_management'),
            {'user_id': self.general.id, 'role': 'executive'},
        )

        self.assertRedirects(response, reverse('user_role_management'))
        self.general.refresh_from_db()
        self.assertEqual(self.general.profile.role, 'executive')
        self.assertFalse(self.general.profile.is_user_admin)
        self.assertTrue(
            AdminChangeLog.objects.filter(
                changed_by=self.user_admin,
                affected_user=self.general,
                old_role='general',
                new_role='executive',
            ).exists()
        )

    def test_non_admin_cannot_access_admin_change_history(self):
        self.client.login(username='generalmember', password='testpass123')

        response = self.client.get(reverse('admin_change_history', args=[self.general.id]))

        self.assertEqual(response.status_code, 403)

    def test_user_admin_can_view_admin_change_history(self):
        AdminChangeLog.objects.create(
            changed_by=self.user_admin,
            affected_user=self.general,
            old_role='general',
            new_role='executive',
        )
        self.client.login(username='roleadmin', password='testpass123')

        response = self.client.get(reverse('admin_change_history', args=[self.general.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'generalmember')
        self.assertContains(response, 'executive')

    def test_user_admin_is_redirected_away_from_profile(self):
        self.client.login(username='roleadmin', password='testpass123')

        response = self.client.get(reverse('user_profile'))

        self.assertRedirects(response, reverse('user_role_management'))

    def test_user_admin_is_redirected_away_from_officer_features(self):
        self.client.login(username='roleadmin', password='testpass123')

        response = self.client.get(reverse('member_list'))

        self.assertRedirects(response, reverse('user_role_management'))

    def test_non_admin_cannot_access_role_management(self):
        self.client.login(username='generalmember', password='testpass123')

        response = self.client.get(reverse('user_role_management'))

        self.assertEqual(response.status_code, 403)


class MessagingViewsTests(TestCase):
    def setUp(self):
        self.executive = User.objects.create_user(
            username='execuser',
            password='testpass123',
            first_name='Exec',
            last_name='Member',
        )
        self.member = User.objects.create_user(
            username='memberuser',
            password='testpass123',
            first_name='General',
            last_name='Member',
        )

        UserProfile.objects.filter(user=self.executive).update(role='executive', setup_complete=True)
        UserProfile.objects.filter(user=self.member).update(role='general', setup_complete=True)

        self.post = Post.objects.create(
            message_title='Weekly Meeting',
            message_content='Agenda and reminders for this week.',
            message_author=self.executive,
        )

    def test_post_list_renders_message_fields(self):
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.get(reverse('post_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Weekly Meeting')
        self.assertContains(response, 'Agenda and reminders for this week.')
        self.assertNotContains(response, 'No posts yet.')

    def test_member_can_reply_to_post(self):
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.post(
            reverse('post_detail', args=[self.post.id]),
            {'content': 'I can make it to the meeting.'},
        )

        self.assertRedirects(response, reverse('post_detail', args=[self.post.id]))
        self.assertEqual(Comment.objects.count(), 1)

        comment = Comment.objects.get()
        self.assertEqual(comment.comment_post, self.post)
        self.assertEqual(comment.comment_author, self.member)
        self.assertEqual(comment.comment_content, 'I can make it to the meeting.')

    def test_post_detail_shows_existing_replies(self):
        Comment.objects.create(
            comment_post=self.post,
            comment_author=self.member,
            comment_content='Can someone share the location?',
        )
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.get(reverse('post_detail', args=[self.post.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Can someone share the location?')
        self.assertContains(response, 'General Member')

    def test_member_can_create_posts(self):
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.post(
            reverse('create_post'),
            {
                'title': 'Study Group Thread',
                'content': 'Anyone want to coordinate prep before the next meeting?',
            },
        )

        self.assertRedirects(response, reverse('post_list'))
        self.assertTrue(
            Post.objects.filter(
                message_title='Study Group Thread',
                message_author=self.member,
            ).exists()
        )

    def test_executive_can_create_posts(self):
        self.client.login(username='execuser', password='testpass123')

        response = self.client.post(
            reverse('create_post'),
            {
                'title': 'Volunteer Signup',
                'content': 'Please reply if you can help at the activities fair.',
            },
        )

        self.assertRedirects(response, reverse('post_list'))
        self.assertTrue(
            Post.objects.filter(
                message_title='Volunteer Signup',
                message_author=self.executive,
            ).exists()
        )

    def test_post_list_shows_author_role_label(self):
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.get(reverse('post_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Executive Member')


class EventAttendanceTests(TestCase):
    def setUp(self):
        self.executive = User.objects.create_user(
            username='execuser',
            password='testpass123',
            first_name='Exec',
            last_name='Member',
            email='exec@example.com',
        )
        self.member = User.objects.create_user(
            username='memberuser',
            password='testpass123',
            first_name='General',
            last_name='Member',
            email='member@example.com',
        )

        UserProfile.objects.filter(user=self.executive).update(role='executive', setup_complete=True)
        UserProfile.objects.filter(user=self.member).update(role='general', setup_complete=True)

    def test_executive_can_create_event_from_calendar(self):
        self.client.login(username='execuser', password='testpass123')

        response = self.client.post(
            reverse('event_calendar'),
            {
                'title': 'General Body Meeting',
                'event_date': '2026-05-05',
                'start_time': '18:30',
                'location': 'Newcomb Hall',
                'description': 'Monthly planning meeting.',
            },
        )

        self.assertRedirects(response, reverse('event_calendar'))
        self.assertTrue(
            Event.objects.filter(
                title='General Body Meeting',
                location='Newcomb Hall',
                created_by=self.executive,
            ).exists()
        )

    def test_executive_can_update_attendance_without_duplicates(self):
        event = Event.objects.create(
            title='Workshop',
            event_date='2026-05-06',
            location='Rice Hall',
            created_by=self.executive,
        )
        self.client.login(username='execuser', password='testpass123')

        self.client.post(reverse('mark_attendance', args=[event.id]), {f'user_{self.member.id}': 'on'})
        self.client.post(reverse('mark_attendance', args=[event.id]), {})

        records = AttendanceRecord.objects.filter(member=self.member, event_name='Workshop')
        self.assertEqual(records.count(), 1)
        self.assertFalse(records.get().present)
        self.assertEqual(records.get().event, event)

    def test_attendance_updates_are_scoped_to_event_id(self):
        first_event = Event.objects.create(
            title='Workshop',
            event_date='2026-05-06',
            location='Rice Hall',
            created_by=self.executive,
        )
        second_event = Event.objects.create(
            title='Workshop',
            event_date='2026-05-06',
            location='Newcomb Hall',
            created_by=self.executive,
        )
        self.client.login(username='execuser', password='testpass123')

        self.client.post(reverse('mark_attendance', args=[first_event.id]), {f'user_{self.member.id}': 'on'})
        self.client.post(reverse('mark_attendance', args=[second_event.id]), {})

        self.assertTrue(
            AttendanceRecord.objects.filter(member=self.member, event=first_event, present=True).exists()
        )
        self.assertTrue(
            AttendanceRecord.objects.filter(member=self.member, event=second_event, present=False).exists()
        )

    def test_attendance_update_excludes_executive_members(self):
        event = Event.objects.create(
            title='Members Only Workshop',
            event_date='2026-05-07',
            location='Rice Hall',
            created_by=self.executive,
        )
        self.client.login(username='execuser', password='testpass123')

        response = self.client.get(reverse('mark_attendance', args=[event.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'General Member')
        self.assertNotContains(response, 'exec@example.com')

        self.client.post(
            reverse('mark_attendance', args=[event.id]),
            {
                f'user_{self.member.id}': 'on',
                f'user_{self.executive.id}': 'on',
            },
        )

        self.assertTrue(AttendanceRecord.objects.filter(member=self.member).exists())
        self.assertFalse(AttendanceRecord.objects.filter(member=self.executive).exists())

    def test_officer_dashboard_attendance_rate_uses_general_members_only(self):
        AttendanceRecord.objects.create(
            member=self.member,
            event_name='Workshop',
            event_date='2026-05-07',
            present=True,
            recorded_by=self.executive,
        )
        AttendanceRecord.objects.create(
            member=self.executive,
            event_name='Workshop',
            event_date='2026-05-07',
            present=False,
            recorded_by=self.executive,
        )
        self.client.login(username='execuser', password='testpass123')

        response = self.client.get(reverse('officer_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '100%')

    def test_general_member_cannot_access_officer_dashboard(self):
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.get(reverse('officer_dashboard'))

        self.assertEqual(response.status_code, 403)

    def test_member_dashboard_links_to_attendance_history(self):
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.get(reverse('member_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Attendance')
        self.assertContains(response, reverse('my_attendance'))

    def test_past_events_still_allow_attendance_updates_for_executives(self):
        event = Event.objects.create(
            title='Past Workshop',
            event_date='2026-04-01',
            location='Rice Hall',
            created_by=self.executive,
        )
        self.client.login(username='execuser', password='testpass123')

        response = self.client.get(reverse('event_calendar'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Past Workshop')
        self.assertContains(response, reverse('mark_attendance', args=[event.id]))


class ResourceDirectoryTests(TestCase):
    def setUp(self):
        self.executive = User.objects.create_user(
            username='execuser',
            password='testpass123',
        )
        self.member = User.objects.create_user(
            username='memberuser',
            password='testpass123',
        )

        UserProfile.objects.filter(user=self.executive).update(role='executive', setup_complete=True)
        UserProfile.objects.filter(user=self.member).update(role='general', setup_complete=True)

    def test_member_resource_directory_excludes_onboarding_documents(self):
        Document.objects.create(
            title='Public Budget',
            url='https://example.com/budget',
            tag='Budget',
            uploaded_by=self.executive,
            category='general',
        )
        Document.objects.create(
            title='Officer Transition Notes',
            url='https://example.com/private',
            tag='President',
            uploaded_by=self.executive,
            category='onboarding',
        )
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.get(reverse('resource_directory'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Budget')
        self.assertNotContains(response, 'Officer Transition Notes')
        self.assertNotContains(response, '#President')

    def test_edit_resource_handles_missing_required_post_fields(self):
        document = Document.objects.create(
            title='Public Budget',
            url='https://example.com/budget',
            tag='Budget',
            uploaded_by=self.executive,
            category='general',
        )
        self.client.login(username='execuser', password='testpass123')

        response = self.client.post(
            reverse('edit_resource', args=[document.id]),
            {'title': 'Updated Budget'},
        )

        self.assertRedirects(response, reverse('edit_resource', args=[document.id]))
        document.refresh_from_db()
        self.assertEqual(document.tag, 'Budget')


class ConstitutionFileTests(TestCase):
    def setUp(self):
        self.executive = User.objects.create_user(
            username='execuser',
            password='testpass123',
        )
        self.member = User.objects.create_user(
            username='memberuser',
            password='testpass123',
        )

        UserProfile.objects.filter(user=self.executive).update(role='executive', setup_complete=True)
        UserProfile.objects.filter(user=self.member).update(role='general', setup_complete=True)

    def test_executive_can_upload_constitution_file(self):
        self.client.login(username='execuser', password='testpass123')
        constitution_file = SimpleUploadedFile(
            'constitution.pdf',
            b'constitution contents',
            content_type='application/pdf',
        )

        response = self.client.post(
            reverse('constitution_summary'),
            {
                'document_title': 'Official CIO Constitution',
                'document_description': 'Approved spring version.',
                'constitution_file': constitution_file,
            },
        )

        self.assertRedirects(response, reverse('constitution_summary'))
        document = Document.objects.get(title='Official CIO Constitution')
        self.assertEqual(document.tag, 'Constitution')
        self.assertEqual(document.category, 'general')
        self.assertEqual(document.description, 'Approved spring version.')
        self.assertEqual(document.uploaded_by, self.executive)
        self.assertTrue(document.file.name.endswith('constitution.pdf'))

    def test_member_cannot_upload_constitution_file(self):
        self.client.login(username='memberuser', password='testpass123')
        constitution_file = SimpleUploadedFile(
            'constitution.pdf',
            b'constitution contents',
            content_type='application/pdf',
        )

        response = self.client.post(
            reverse('constitution_summary'),
            {
                'document_title': 'Official CIO Constitution',
                'constitution_file': constitution_file,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Document.objects.exists())

    def test_member_does_not_see_upload_form(self):
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.get(reverse('constitution_summary'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Upload Constitution')
        self.assertContains(response, 'No constitution file has been published yet.')

    def test_member_can_view_uploaded_constitution_file(self):
        Document.objects.create(
            title='Official CIO Constitution',
            url='https://example.com/constitution.pdf',
            tag='Constitution',
            uploaded_by=self.executive,
            category='general',
        )
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.get(reverse('constitution_summary'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Uploaded Constitution Files')
        self.assertContains(response, 'Official CIO Constitution')
        self.assertNotContains(response, 'No constitution file has been published yet.')
        self.assertNotContains(response, 'Constitution Coming Soon')


class MembershipApplicationTests(TestCase):
    def setUp(self):
        self.executive = User.objects.create_user(
            username='execuser',
            password='testpass123',
        )
        self.member = User.objects.create_user(
            username='memberuser',
            password='testpass123',
        )

        UserProfile.objects.filter(user=self.executive).update(role='executive', setup_complete=True)
        UserProfile.objects.filter(user=self.member).update(role='general', setup_complete=True)

    def test_member_can_submit_membership_application(self):
        self.client.login(username='memberuser', password='testpass123')

        response = self.client.post(
            reverse('membership_application'),
            {'reason': 'I want to help with community events.'},
        )

        self.assertRedirects(response, reverse('membership_application'))
        self.assertTrue(
            MembershipApplication.objects.filter(
                applicant=self.member,
                reason='I want to help with community events.',
                status='pending',
            ).exists()
        )

    def test_officer_review_page_shows_submitted_application(self):
        MembershipApplication.objects.create(
            applicant=self.member,
            reason='I want to help with community events.',
        )
        self.client.login(username='execuser', password='testpass123')

        response = self.client.get(reverse('application_review'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'I want to help with community events.')
