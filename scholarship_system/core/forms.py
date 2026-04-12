from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, StudentProfile, Application, Document, Scholarship, Payment


class StudentRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=20, required=False)
    student_id = forms.CharField(max_length=20, required=True, label='Student ID')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.ROLE_STUDENT
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                student_id=self.cleaned_data['student_id']
            )
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            'student_id', 'date_of_birth', 'gender', 'national_id',
            'address', 'institution', 'faculty', 'course',
            'study_level', 'year_of_study', 'gpa',
            'guardian_name', 'guardian_contact',
            'annual_family_income', 'number_of_dependants',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['personal_statement', 'financial_need_description', 'academic_achievements']
        widgets = {
            'personal_statement': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe yourself and why you deserve this scholarship...'}),
            'financial_need_description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe your financial situation and need...'}),
            'academic_achievements': forms.Textarea(attrs={'rows': 4, 'placeholder': 'List your academic achievements, awards, etc...'}),
        }


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['document_type', 'file']

    def save(self, commit=True):
        doc = super().save(commit=False)
        doc.original_filename = self.cleaned_data['file'].name
        if commit:
            doc.save()
        return doc


class ScholarshipForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = [
            'name', 'scholarship_type', 'description', 'eligibility_criteria',
            'amount', 'total_slots', 'application_deadline', 'academic_year',
            'status', 'min_gpa', 'max_family_income',
        ]
        widgets = {
            'application_deadline': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'eligibility_criteria': forms.Textarea(attrs={'rows': 4}),
        }


class ApplicationReviewForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['status', 'review_notes']
        widgets = {
            'review_notes': forms.Textarea(attrs={'rows': 4}),
        }


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'reference_number', 'payment_date', 'notes', 'status']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']
