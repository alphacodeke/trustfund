from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


def send_registration_email(user):
    subject = "Welcome to the Scholarship & Bursary Management System"
    message = f"""
Dear {user.get_full_name()},

Welcome to the Transparent Scholarship and Bursary Allocation Management System!

Your account has been successfully created.
Username: {user.username}

You can now log in and apply for available scholarships and bursaries.

Best regards,
Scholarship Management Team
"""
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception:
        pass


def send_application_submitted_email(application):
    user = application.student
    subject = f"Application Submitted: {application.scholarship.name}"
    message = f"""
Dear {user.get_full_name()},

Your application for "{application.scholarship.name}" has been successfully submitted.

Application Details:
- Scholarship: {application.scholarship.name}
- Type: {application.scholarship.get_scholarship_type_display()}
- Amount: ${application.scholarship.amount:,.2f}
- Submitted: {application.submitted_at.strftime('%B %d, %Y')}
- Status: Pending Review

You will be notified once your application has been reviewed.

Best regards,
Scholarship Management Team
"""
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception:
        pass


def send_application_approved_email(application):
    user = application.student
    subject = f"Congratulations! Your Application Has Been Approved"
    message = f"""
Dear {user.get_full_name()},

Congratulations! We are pleased to inform you that your application for 
"{application.scholarship.name}" has been APPROVED.

Award Details:
- Scholarship/Bursary: {application.scholarship.name}
- Amount Awarded: ${application.scholarship.amount:,.2f}
- Academic Year: {application.scholarship.academic_year}

Admin Notes: {application.review_notes or 'N/A'}

Please log in to your dashboard to view more details about your award and payment information.

Best regards,
Scholarship Management Team
"""
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception:
        pass


def send_application_rejected_email(application):
    user = application.student
    subject = f"Application Status Update: {application.scholarship.name}"
    message = f"""
Dear {user.get_full_name()},

Thank you for applying for "{application.scholarship.name}".

After careful review, we regret to inform you that your application has not been 
successful at this time.

Reason: {application.review_notes or 'Not specified'}

We encourage you to apply for other available scholarships and bursaries.
Please log in to your dashboard to view other opportunities.

Best regards,
Scholarship Management Team
"""
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception:
        pass
