from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Student
    path('dashboard/', views.dashboard, name='dashboard'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('profile/', views.profile, name='profile'),
    path('scholarships/', views.scholarships_list, name='scholarships_list'),
    path('scholarships/<int:pk>/', views.scholarship_detail, name='scholarship_detail'),
    path('scholarships/<int:pk>/apply/', views.apply_scholarship, name='apply_scholarship'),
    path('applications/', views.my_applications, name='my_applications'),
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('applications/<int:application_id>/documents/', views.upload_documents, name='upload_documents'),
    path('notifications/', views.notifications, name='notifications'),

    # Admin
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/applications/', views.admin_applications, name='admin_applications'),
    path('admin-panel/applications/<int:pk>/review/', views.admin_review_application, name='admin_review_application'),
    path('admin-panel/scholarships/', views.admin_scholarships, name='admin_scholarships'),
    path('admin-panel/scholarships/create/', views.admin_scholarship_create, name='admin_scholarship_create'),
    path('admin-panel/scholarships/<int:pk>/edit/', views.admin_scholarship_edit, name='admin_scholarship_edit'),
    path('admin-panel/students/', views.admin_students, name='admin_students'),
    path('admin-panel/students/<int:pk>/', views.admin_student_detail, name='admin_student_detail'),
    path('admin-panel/payments/', views.admin_payments, name='admin_payments'),
    path('admin-panel/payments/<int:pk>/update/', views.admin_payment_update, name='admin_payment_update'),
    path('admin-panel/reports/', views.admin_reports, name='admin_reports'),
]
