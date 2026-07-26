from django import forms
from .models import UserProfile # Assuming UserProfile model exists
from django.contrib.auth.models import User

class SignupForm(forms.ModelForm):
    VERIFICATION_CHOICES = [
        ('mobile', 'Mobile OTP'),
        ('email', 'Email Verification'),
    ]

    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'}),
        label=""
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'form-control'}),
        label=""
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}),
        label=""
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}),
        label=""
    )

    mobile = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Phone Number', 'class': 'form-control'}),
        label=""
    )

    verification_method = forms.ChoiceField(
        choices=VERIFICATION_CHOICES,
        widget=forms.RadioSelect,
        label="Choose Verification Method"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        method = cleaned_data.get('verification_method')
        mobile = cleaned_data.get('mobile')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords don't match.")

        if method == 'mobile' and not mobile:
            self.add_error('mobile', 'Mobile number is required for OTP verification.')
        if method == 'email' and not cleaned_data.get('email'):
            self.add_error('email', 'Email is required for email verification.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()

            user_profile = user.profile
            user_profile.mobile = self.cleaned_data.get('mobile')
            user_profile.verification_method = self.cleaned_data.get('verification_method')
            user_profile.save()

        return user

class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6, label="Enter OTP", widget=forms.TextInput(attrs={'placeholder': 'Enter OTP', 'class': 'form-control'}))

def send_otp_sms(recipient_number, otp_code):
    """
    Sends an OTP via Twilio SMS.
    Returns True on success, False on failure.
    """
    if not recipient_number:
        logger.error("Recipient number is missing for OTP SMS.")
        return False
        
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Twilio API call
        message = client.messages.create(
            to=recipient_number,
            from_=TWILIO_PHONE_NUMBER,
            body=f"Your Fitness app verification code (OTP) is: {otp_code}"
        )
        print(f"Twilio SMS sent successfully. Message SID: {message.sid}")
        return True
    except Exception as e:
        logger.error("Failed to send OTP via Twilio: %s", e)
        return False
class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}))

class MultiStepRegistrationForm(forms.Form):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    GOAL_CHOICES = [
        ('cut', 'Cut (Fat Loss)'),
        ('bulk', 'Bulk (Muscle Gain)'),
        ('recomposition', 'Body Recomposition'),
        ('abs', 'Get Six Pack Abs'),
    ]

    name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Name', 'class': 'form-control'}))
    gender = forms.ChoiceField(choices=GENDER_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    height = forms.FloatField(widget=forms.NumberInput(attrs={'placeholder': 'Height (cm/inches)', 'class': 'form-control'}), help_text="In centimeters or inches")
    weight = forms.FloatField(widget=forms.NumberInput(attrs={'placeholder': 'Weight (kg/lbs)', 'class': 'form-control'}), help_text="In kilograms or pounds")
    target_weight = forms.FloatField(widget=forms.NumberInput(attrs={'placeholder': 'Target Weight', 'class': 'form-control'}), help_text="Target body weight")
    goal = forms.ChoiceField(choices=GOAL_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = '__all__'


# ✅ OTP Verification Form
class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6, label="Enter OTP", widget=forms.TextInput(attrs={'placeholder': 'Enter OTP', 'class': 'form-control'}))


# 🔓 Login Form
class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}))


# 🧍 Multi-step Profile Form
class MultiStepRegistrationForm(forms.Form):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    GOAL_CHOICES = [
        ('cut', 'Cut (Fat Loss)'),
        ('bulk', 'Bulk (Muscle Gain)'),
        ('recomposition', 'Body Recomposition'),
        ('abs', 'Get Six Pack Abs'),
    ]

    name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Name', 'class': 'form-control'}))
    gender = forms.ChoiceField(choices=GENDER_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    height = forms.FloatField(widget=forms.NumberInput(attrs={'placeholder': 'Height (cm/inches)', 'class': 'form-control'}), help_text="In centimeters or inches")
    weight = forms.FloatField(widget=forms.NumberInput(attrs={'placeholder': 'Weight (kg/lbs)', 'class': 'form-control'}), help_text="In kilograms or pounds")
    target_weight = forms.FloatField(widget=forms.NumberInput(attrs={'placeholder': 'Target Weight', 'class': 'form-control'}), help_text="Target body weight")
    goal = forms.ChoiceField(choices=GOAL_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))


# ✅ UserProfile Model Form
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = '__all__'
        # Add widgets for all fields if this form is used for editing, etc.
        # Example:
        # widgets = {
        #     'username': forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'}),
        #     'email': forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'form-control'}),
        #     # ... and so on for other fields
        # }