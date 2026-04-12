from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.http import HttpResponseForbidden
import uuid

from .models import User, StudentProfile, Scholarship, Application, Document, Payment, Notification
from .forms import (
    StudentRegistrationForm, LoginForm, StudentProfileForm,
    ApplicationForm, DocumentUploadForm, ScholarshipForm,
    ApplicationReviewForm, PaymentForm, UserUpdateForm
)
from .email_utils import (
    send_registration_email, send_application_submitted_email,
    send_application_approved_email, send_application_rejected_email
)


def home(request):
    scholarships = Scholarship.objects.filter(status='active').order_by('-created_at')[:6]
    stats = {
        'total_scholarships': Scholarship.objects.count(),
        'active_scholarships': Scholarship.objects.filter(status='active').count(),
        'total_applications': Application.objects.count(),
        'approved_applications': Application.objects.filter(status='approved').count(),
    }
    return render(request, 'core/home.html', {'scholarships': scholarships, 'stats': stats})


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_registration_email(user)
            Notification.objects.create(
                user=user,
                title="Welcome!",
                message="Your account has been created successfully. Start exploring available scholarships."
            )
            messages.success(request, "Registration successful! Please log in.")
            return redirect('login')
    else:
        form = StudentRegistrationForm()
    return render(request, 'core/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            if user.is_admin_user():
                return redirect('admin_dashboard')
            return redirect('student_dashboard')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})


@login_required
def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')


@login_required
def dashboard(request):
    if request.user.is_admin_user():
        return redirect('admin_dashboard')
    return redirect('student_dashboard')


# ===================== STUDENT VIEWS =====================

@login_required
def student_dashboard(request):
    if request.user.is_admin_user():
        return redirect('admin_dashboard')
    user = request.user
    applications = Application.objects.filter(student=user).select_related('scholarship')
    notifications = Notification.objects.filter(user=user, is_read=False)[:5]
    available_scholarships = Scholarship.objects.filter(status='active')
    stats = {
        'total': applications.count(),
        'pending': applications.filter(status='pending').count(),
        'approved': applications.filter(status='approved').count(),
        'rejected': applications.filter(status='rejected').count(),
    }
    return render(request, 'core/student_dashboard.html', {
        'applications': applications[:5],
        'notifications': notifications,
        'available_scholarships': available_scholarships[:4],
        'stats': stats,
    })


@login_required
def profile(request):
    user = request.user
    try:
        student_profile = user.student_profile
    except StudentProfile.DoesNotExist:
        student_profile = None

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = StudentProfileForm(request.POST, instance=student_profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = StudentProfileForm(instance=student_profile)

    return render(request, 'core/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@login_required
def scholarships_list(request):
    scholarships = Scholarship.objects.filter(status='active').order_by('-created_at')
    scholarship_type = request.GET.get('type', '')
    if scholarship_type:
        scholarships = scholarships.filter(scholarship_type=scholarship_type)
    return render(request, 'core/scholarships_list.html', {
        'scholarships': scholarships,
        'scholarship_type': scholarship_type,
    })


@login_required
def scholarship_detail(request, pk):
    scholarship = get_object_or_404(Scholarship, pk=pk)
    already_applied = False
    if not request.user.is_admin_user():
        already_applied = Application.objects.filter(student=request.user, scholarship=scholarship).exists()
    return render(request, 'core/scholarship_detail.html', {
        'scholarship': scholarship,
        'already_applied': already_applied,
    })


@login_required
def apply_scholarship(request, pk):
    if request.user.is_admin_user():
        return HttpResponseForbidden("Admins cannot apply for scholarships.")
    scholarship = get_object_or_404(Scholarship, pk=pk)

    if not scholarship.is_open:
        messages.error(request, "This scholarship is no longer accepting applications.")
        return redirect('scholarship_detail', pk=pk)

    if Application.objects.filter(student=request.user, scholarship=scholarship).exists():
        messages.warning(request, "You have already applied for this scholarship.")
        return redirect('my_applications')

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.student = request.user
            application.scholarship = scholarship
            application.save()
            send_application_submitted_email(application)
            Notification.objects.create(
                user=request.user,
                title="Application Submitted",
                message=f"Your application for '{scholarship.name}' has been submitted successfully."
            )
            messages.success(request, "Application submitted successfully!")
            return redirect('upload_documents', application_id=application.id)
    else:
        form = ApplicationForm()

    return render(request, 'core/apply_scholarship.html', {
        'form': form,
        'scholarship': scholarship,
    })


@login_required
def upload_documents(request, application_id):
    application = get_object_or_404(Application, pk=application_id, student=request.user)
    documents = application.documents.all()

    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.application = application
            doc.original_filename = request.FILES['file'].name
            doc.save()
            messages.success(request, "Document uploaded successfully!")
            return redirect('upload_documents', application_id=application_id)
    else:
        form = DocumentUploadForm()

    return render(request, 'core/upload_documents.html', {
        'form': form,
        'application': application,
        'documents': documents,
    })


@login_required
def my_applications(request):
    applications = Application.objects.filter(student=request.user).select_related('scholarship')
    return render(request, 'core/my_applications.html', {'applications': applications})


@login_required
def application_detail(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if not request.user.is_admin_user() and application.student != request.user:
        return HttpResponseForbidden()
    documents = application.documents.all()
    payment = None
    try:
        payment = application.payment
    except Payment.DoesNotExist:
        pass
    return render(request, 'core/application_detail.html', {
        'application': application,
        'documents': documents,
        'payment': payment,
    })


@login_required
def notifications(request):
    notifs = Notification.objects.filter(user=request.user)
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'core/notifications.html', {'notifications': notifs})


# ===================== ADMIN VIEWS =====================

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin_user():
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@admin_required
def admin_dashboard(request):
    total_applications = Application.objects.count()
    pending = Application.objects.filter(status='pending').count()
    under_review = Application.objects.filter(status='under_review').count()
    approved = Application.objects.filter(status='approved').count()
    rejected = Application.objects.filter(status='rejected').count()
    total_students = User.objects.filter(role='student').count()
    total_scholarships = Scholarship.objects.count()
    active_scholarships = Scholarship.objects.filter(status='active').count()
    total_allocated = Payment.objects.filter(status='processed').aggregate(total=Sum('amount'))['total'] or 0
    recent_applications = Application.objects.select_related('student', 'scholarship').order_by('-submitted_at')[:10]

    return render(request, 'core/admin_dashboard.html', {
        'total_applications': total_applications,
        'pending': pending,
        'under_review': under_review,
        'approved': approved,
        'rejected': rejected,
        'total_students': total_students,
        'total_scholarships': total_scholarships,
        'active_scholarships': active_scholarships,
        'total_allocated': total_allocated,
        'recent_applications': recent_applications,
    })


@login_required
@admin_required
def admin_applications(request):
    applications = Application.objects.select_related('student', 'scholarship').order_by('-submitted_at')
    status_filter = request.GET.get('status', '')
    scholarship_filter = request.GET.get('scholarship', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    if scholarship_filter:
        applications = applications.filter(scholarship_id=scholarship_filter)
    scholarships = Scholarship.objects.all()
    return render(request, 'core/admin_applications.html', {
        'applications': applications,
        'status_filter': status_filter,
        'scholarship_filter': scholarship_filter,
        'scholarships': scholarships,
        'status_choices': Application.STATUS_CHOICES,
    })


@login_required
@admin_required
def admin_review_application(request, pk):
    application = get_object_or_404(Application, pk=pk)
    documents = application.documents.all()
    payment = None
    try:
        payment = application.payment
    except Payment.DoesNotExist:
        pass

    if request.method == 'POST':
        form = ApplicationReviewForm(request.POST, instance=application)
        if form.is_valid():
            old_status = application.status
            app = form.save(commit=False)
            app.reviewed_by = request.user
            app.reviewed_at = timezone.now()
            app.save()

            # Update scholarship slots
            if app.status == 'approved' and old_status != 'approved':
                app.scholarship.filled_slots += 1
                app.scholarship.save()
                # Create payment record
                Payment.objects.get_or_create(
                    application=app,
                    defaults={
                        'amount': app.scholarship.amount,
                        'reference_number': f"PAY-{uuid.uuid4().hex[:8].upper()}",
                        'status': 'pending',
                    }
                )
                send_application_approved_email(app)
                Notification.objects.create(
                    user=app.student,
                    title="Application Approved!",
                    message=f"Congratulations! Your application for '{app.scholarship.name}' has been approved."
                )
            elif app.status == 'rejected' and old_status != 'rejected':
                if old_status == 'approved':
                    app.scholarship.filled_slots = max(0, app.scholarship.filled_slots - 1)
                    app.scholarship.save()
                send_application_rejected_email(app)
                Notification.objects.create(
                    user=app.student,
                    title="Application Status Update",
                    message=f"Your application for '{app.scholarship.name}' has been reviewed. Please check your dashboard."
                )

            messages.success(request, f"Application status updated to {app.get_status_display()}.")
            return redirect('admin_review_application', pk=pk)
    else:
        form = ApplicationReviewForm(instance=application)

    return render(request, 'core/admin_review_application.html', {
        'application': application,
        'form': form,
        'documents': documents,
        'payment': payment,
    })


@login_required
@admin_required
def admin_scholarships(request):
    scholarships = Scholarship.objects.annotate(app_count=Count('applications')).order_by('-created_at')
    return render(request, 'core/admin_scholarships.html', {'scholarships': scholarships})


@login_required
@admin_required
def admin_scholarship_create(request):
    if request.method == 'POST':
        form = ScholarshipForm(request.POST)
        if form.is_valid():
            scholarship = form.save(commit=False)
            scholarship.created_by = request.user
            scholarship.save()
            messages.success(request, "Scholarship created successfully!")
            return redirect('admin_scholarships')
    else:
        form = ScholarshipForm()
    return render(request, 'core/admin_scholarship_form.html', {'form': form, 'action': 'Create'})


@login_required
@admin_required
def admin_scholarship_edit(request, pk):
    scholarship = get_object_or_404(Scholarship, pk=pk)
    if request.method == 'POST':
        form = ScholarshipForm(request.POST, instance=scholarship)
        if form.is_valid():
            form.save()
            messages.success(request, "Scholarship updated successfully!")
            return redirect('admin_scholarships')
    else:
        form = ScholarshipForm(instance=scholarship)
    return render(request, 'core/admin_scholarship_form.html', {'form': form, 'action': 'Edit', 'scholarship': scholarship})


@login_required
@admin_required
def admin_students(request):
    students = User.objects.filter(role='student').select_related('student_profile').order_by('-created_at')
    search = request.GET.get('search', '')
    if search:
        students = students.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(student_profile__student_id__icontains=search)
        )
    return render(request, 'core/admin_students.html', {'students': students, 'search': search})


@login_required
@admin_required
def admin_student_detail(request, pk):
    student = get_object_or_404(User, pk=pk, role='student')
    applications = Application.objects.filter(student=student).select_related('scholarship')
    try:
        profile = student.student_profile
    except StudentProfile.DoesNotExist:
        profile = None
    return render(request, 'core/admin_student_detail.html', {
        'student': student,
        'profile': profile,
        'applications': applications,
    })


@login_required
@admin_required
def admin_payments(request):
    payments = Payment.objects.select_related('application__student', 'application__scholarship').order_by('-created_at')
    return render(request, 'core/admin_payments.html', {'payments': payments})


@login_required
@admin_required
def admin_payment_update(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            p = form.save(commit=False)
            p.processed_by = request.user
            p.save()
            messages.success(request, "Payment record updated!")
            return redirect('admin_payments')
    else:
        form = PaymentForm(instance=payment)
    return render(request, 'core/admin_payment_form.html', {'form': form, 'payment': payment})


@login_required
@admin_required
def admin_reports(request):
    # Application statistics
    total_apps = Application.objects.count()
    approved_apps = Application.objects.filter(status='approved').count()
    rejected_apps = Application.objects.filter(status='rejected').count()
    pending_apps = Application.objects.filter(status='pending').count()

    # Financial statistics
    total_allocated = Payment.objects.filter(status='processed').aggregate(total=Sum('amount'))['total'] or 0
    pending_payments = Payment.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0

    # Scholarship breakdown
    scholarship_stats = Scholarship.objects.annotate(
        app_count=Count('applications'),
        approved_count=Count('applications', filter=Q(applications__status='approved'))
    ).order_by('-app_count')

    # Monthly applications (last 6 months)
    from django.db.models.functions import TruncMonth
    monthly_apps = Application.objects.annotate(
        month=TruncMonth('submitted_at')
    ).values('month').annotate(count=Count('id')).order_by('-month')[:6]

    return render(request, 'core/admin_reports.html', {
        'total_apps': total_apps,
        'approved_apps': approved_apps,
        'rejected_apps': rejected_apps,
        'pending_apps': pending_apps,
        'total_allocated': total_allocated,
        'pending_payments': pending_payments,
        'scholarship_stats': scholarship_stats,
        'monthly_apps': monthly_apps,
        'approval_rate': round((approved_apps / total_apps * 100) if total_apps > 0 else 0, 1),
    })
