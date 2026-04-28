from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Custom user model with role-based access."""
    ROLE_STUDENT = 'student'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_ADMIN, 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_student(self):
        return self.role == self.ROLE_STUDENT

    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN or self.is_staff

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"


class StudentProfile(models.Model):
    """Extended student information."""
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    LEVEL_CHOICES = [
        ('certificate', 'Certificate'),
        ('diploma', 'Diploma'),
        ('undergraduate', 'Undergraduate'),
        ('postgraduate', 'Postgraduate'),
        ('phd', 'PhD'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    national_id = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    institution = models.CharField(max_length=200, blank=True)
    faculty = models.CharField(max_length=200, blank=True)
    course = models.CharField(max_length=200, blank=True)
    study_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    year_of_study = models.PositiveIntegerField(null=True, blank=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    guardian_name = models.CharField(max_length=200, blank=True)
    guardian_contact = models.CharField(max_length=20, blank=True)
    annual_family_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    number_of_dependants = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.get_full_name()} ({self.student_id})"


class Scholarship(models.Model):
    """Scholarship and bursary programs."""
    TYPE_SCHOLARSHIP = 'scholarship'
    TYPE_BURSARY = 'bursary'
    TYPE_GRANT = 'grant'
    TYPE_CHOICES = [
        (TYPE_SCHOLARSHIP, 'Scholarship'),
        (TYPE_BURSARY, 'Bursary'),
        (TYPE_GRANT, 'Grant'),
    ]
    STATUS_ACTIVE = 'active'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CLOSED, 'Closed'),
    ]

    name = models.CharField(max_length=300)
    scholarship_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_SCHOLARSHIP)
    description = models.TextField()
    eligibility_criteria = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_slots = models.PositiveIntegerField(default=1)
    filled_slots = models.PositiveIntegerField(default=0)
    application_deadline = models.DateField()
    academic_year = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    min_gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    max_family_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_scholarships')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def available_slots(self):
        return self.total_slots - self.filled_slots

    @property
    def is_open(self):
        return self.status == self.STATUS_ACTIVE and self.application_deadline >= timezone.now().date() and self.available_slots > 0

    def __str__(self):
        return f"{self.name} ({self.academic_year})"


class Application(models.Model):
    """Student scholarship/bursary applications."""
    STATUS_PENDING = 'pending'
    STATUS_UNDER_REVIEW = 'under_review'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_UNDER_REVIEW, 'Under Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    personal_statement = models.TextField()
    financial_need_description = models.TextField()
    academic_achievements = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    review_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'scholarship')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.get_full_name()} -> {self.scholarship.name} [{self.status}]"


class Document(models.Model):
    """Documents uploaded by students for applications."""
    DOC_ID = 'national_id'
    DOC_TRANSCRIPT = 'transcript'
    DOC_INCOME = 'proof_of_income'
    DOC_RECOMMENDATION = 'recommendation'
    DOC_OTHER = 'other'
    DOC_TYPE_CHOICES = [
        (DOC_ID, 'National ID / Passport'),
        (DOC_TRANSCRIPT, 'Academic Transcript'),
        (DOC_INCOME, 'Proof of Income / Financial Need'),
        (DOC_RECOMMENDATION, 'Recommendation Letter'),
        (DOC_OTHER, 'Other'),
    ]

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOC_TYPE_CHOICES)
    file = models.FileField(upload_to='documents/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.application}"


class Payment(models.Model):
    """Fund allocation/payment records for approved applications."""
    STATUS_PENDING = 'pending'
    STATUS_PROCESSED = 'processed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSED, 'Processed'),
        (STATUS_FAILED, 'Failed'),
    ]

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reference_number = models.CharField(max_length=100, unique=True)
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='processed_payments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.reference_number} - {self.application.student.get_full_name()}"


class Notification(models.Model):
    """In-system notifications for students."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
