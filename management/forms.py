from django.contrib.auth.models import User
from django import forms
from management.models import *



class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'is_staff', 'is_active']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class ProjectForm(forms.ModelForm):
    ssh_private_key = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text="Paste your private SSH key (leave blank to keep existing)"
    )

    class Meta:
        model = Project
        fields = ['repository_url', 'ssh_private_key']

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
        widget=forms.Textarea,
        required=False,
        help_text="Paste your private SSH key (leave blank to keep existing)"
    )

    class Meta:
        model = Project
        fields = ['repository_url', 'ssh_private_key']

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
        widget=forms.Textarea(attrs={'placeholder': 'Enter file content here...'}),
        required=False,
        label="Content"
    )

    class Meta:
        model = PrivateFile
        fields = ['filename', 'filepath', 'plain_content']
        widgets = {
            'filename': forms.TextInput(attrs={'placeholder': 'e.g., config.json'}),
            'filepath': forms.TextInput(attrs={'placeholder': 'e.g., /app/config/'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            content = self.instance.get_content()
            self.fields['plain_content'].initial = content

    def clean_filepath(self):
        filepath = self.cleaned_data.get('filepath')
        if not filepath:
            return ''
        
        filepath = filepath.strip()
        if not filepath.endswith('/'):
            filepath += '/'
            
        return filepath

    def save(self, commit=True):
        instance = super().save(commit=False)
        content = self.cleaned_data.get('plain_content')
        if content:
            instance.set_content(content, commit=False)
        if commit:
            instance.save()
        return instance
