from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django import forms
from management.models import *



class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'is_superuser', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
            'email': forms.EmailInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An user with that email already exists.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_staff = user.is_superuser

        if commit:
            user.save()
        return user


class EditUserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
        help_text="Leave blank to keep the current password."
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'is_superuser', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out', 'readonly': 'readonly'}),
            'email': forms.EmailInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip()

        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("An user with that email already exists.")

        return email

    def save(self, commit=True):
        if self.instance.pk:
            original_password = User.objects.values_list('password', flat=True).get(pk=self.instance.pk)
        else:
            original_password = None

        user = super().save(commit=False)

        user.username = self.instance.username
        user.is_staff = user.is_superuser

        new_pw = self.cleaned_data.get('password')
        if new_pw and new_pw.strip():
            user.password = make_password(new_pw)
        else:
            user.password = original_password or user.password

        if commit:
            user.save()
        return user


class EmailUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out',
                'placeholder': 'Enter new email',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip()

        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("An user with that email already exists.")

        return email

    def save(self, commit=True):
        user = self.instance
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class ProjectForm(forms.ModelForm):
    ssh_private_key = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
        required=False,
        help_text="Paste your private SSH key (leave blank to keep existing)"
    )

    class Meta:
        model = Project
        fields = ['repository_url', 'ssh_private_key']
        widgets = {
            'repository_url': forms.TextInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
        }

    def clean_repository_url(self):
        url = self.cleaned_data['repository_url'].strip()
        url = url.rstrip('/')

        if Project.objects.filter(repository_url=url).exists():
            raise forms.ValidationError("A project with this repository URL already exists.")

        return url

    def save(self, commit=True):
        instance = super().save(commit=False)
        ssh_key = self.cleaned_data.get('ssh_private_key')
        if ssh_key:
            instance.store_ssh_key(ssh_key)
        if commit:
            instance.save()
        return instance


class ProjectEditForm(forms.ModelForm):
    ssh_private_key = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
        required=False,
        help_text="Paste your private SSH key (leave blank to keep existing)",
        label="SSH Private key"
    )

    class Meta:
        model = Project
        fields = ['repository_url', 'ssh_private_key']
        widgets = {
            'repository_url': forms.TextInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
        }

    def clean_repository_url(self):
        url = self.cleaned_data['repository_url'].strip()
        url = url.rstrip('/')

        qs = Project.objects.filter(repository_url=url)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("A project with this repository URL already exists.")

        return url

    def save(self, commit=True):
        instance = super().save(commit=False)
        ssh_key = self.cleaned_data.get('ssh_private_key')
        if ssh_key:
            instance.store_ssh_key(ssh_key)
        if commit:
            instance.save()
        return instance
    

class PrivateFileForm(forms.ModelForm):
    plain_content = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out', 'placeholder': 'Enter file content here...', 'style': 'height: 20dvh;'}),
        required=False,
        label="Content"
    )

    file_type = forms.ChoiceField(
        choices=PrivateFile.FileType.choices,
        widget=forms.Select(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out'}),
        label="File Type",
        required=True,
    )

    class Meta:
        model = PrivateFile
        fields = ['filename', 'filepath', 'plain_content', 'fileperms', 'file_type']
        widgets = {
            'filename': forms.TextInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out', 'placeholder': 'e.g., config.json'}),
            'filepath': forms.TextInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out', 'placeholder': 'e.g., /app/config/'}),
            'fileperms': forms.TextInput(attrs={'class': 'order-2 w-full px-4 py-2 border border-[#444] text-[#f1f1f1] focus:border-[#5c7cfa] focus:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-within:border-[#5c7cfa] focus-within:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] focus-visible:border-[#5c7cfa] focus-visible:[box-shadow:0_0_0_0.2rem_rgba(92,124,250,0.25)] rounded-[8px] bg-[#3a3b3c] focus:bg-[#27292a] text-[20px] placeholder-[#a0a0a0] outline-none transition-all duration-200 ease-in-out', 'placeholder': 'e.g., 600'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            content = self.instance.get_content()
            self.fields['plain_content'].initial = content
            self.fields['file_type'].initial = self.instance.file_type

    def clean_filepath(self):
        filepath = self.cleaned_data.get('filepath')
        if not filepath:
            return ''
        
        filepath = filepath.strip()
        if not filepath.endswith('/'):
            filepath += '/'
            
        return filepath

    def clean_fileperms(self):
        fileperms = self.cleaned_data.get('fileperms')
        if not fileperms.isdigit() or len(fileperms) != 3 or not all(c in '01234567' for c in fileperms):
            raise forms.ValidationError("Enter a valid 3-digit Unix file permission (e.g., 644, 600).")
        return fileperms

    def save(self, commit=True):
        instance = super().save(commit=False)
        content = self.cleaned_data.get('plain_content')
        if content:
            instance.set_content(content, commit=False)
        instance.file_type = self.cleaned_data.get('file_type')
        if commit:
            instance.save()
        return instance
