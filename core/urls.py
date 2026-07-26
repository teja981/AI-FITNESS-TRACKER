from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('email-verify/<str:token>/', views.email_verify, name='email_verify'),
    path('email-pending/', views.email_pending, name='email_pending'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('macro-summary/', views.macro_summary_view, name='macro_summary'),
    path('login/', views.login_view, name='login'),
    path("dashboard/", views.dashboard, name="dashboard"),
    path('logout/', views.logout_view, name='logout'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('api/ask-bot/', views.chatbot_api, name='chatbot_api'),
    path('start-journey/', views.start_journey, name='start_journey'),
    path('profile/<str:username>/', views.profile_settings_view, name='profile_settings'),
    path('generate-plan/', views.generate_plan_view, name='generate_plan'),
    path('resend/', views.resend_otp, name='resend_otp_url_name'), 
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url='/password-reset/done/'
        ),
        name='password_reset'
    ),

    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/password-reset-complete/'
        ),
        name='password_reset_confirm'
    ),

    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]
