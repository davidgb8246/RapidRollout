import secrets
import os
import json
import shlex

from typing import Literal
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from cryptography.fernet import InvalidToken
from uuid import uuid4

from api.utils import run_command_as_user, check_docker_compose_environment, check_folder_exists, get_user_home



class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    def __str__(self):
        return self.user.username

    @classmethod
    def create_for_user(cls, user: User):
        return cls.objects.create(user=user)

    def get_sys_username(self) -> str:
        return f"{self.user.username}-{str(self.id).split('-')[0]}"
    

class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='projects')

    name = models.CharField(max_length=255, blank=True, null=True)
    repository_url = models.URLField(max_length=255)

    encrypted_secret = models.BinaryField(blank=True, null=True)
    encrypted_ssh_key = models.BinaryField(blank=True, null=True)

    initialized = models.BooleanField(default=False)

    class Meta:
        unique_together = ('profile', 'repository_url')

    def set_name(self, name):
        self.name = name
        self.save()

    def is_initialized(self):
        return self.initialized

    def set_as_initialized(self):
        self.initialized = True
        self.save()

    def generate_secret(self):
        raw_secret = secrets.token_urlsafe(32)
        self.encrypted_secret = settings.FERNET.encrypt(raw_secret.encode('utf-8'))
        self.save()
        return raw_secret

    def get_secret(self) -> str | None:
        if not self.encrypted_secret:
            return None
        try:
            return settings.FERNET.decrypt(self.encrypted_secret).decode('utf-8')
        except InvalidToken:
            return None

    def reset_secret(self):
        return self.generate_secret()

    def delete_secret(self):
        self.encrypted_secret = None
        self.save()

    def has_secret(self):
        return bool(self.encrypted_secret)

    def check_secret(self, raw_secret: str) -> bool:
        """Use this if you want to compare against the decrypted version (less secure than hashing)."""
        decrypted = self.get_secret()
        return decrypted == raw_secret

    def store_ssh_key(self, plain_ssh_key: str, commit: bool = False):
        self.encrypted_ssh_key = settings.FERNET.encrypt(plain_ssh_key.encode('utf-8').replace(b'\x0d', b'\x0a'))
        if commit:
            self.save()

    def get_ssh_key(self) -> str | None:
        if not self.encrypted_ssh_key:
            return None
        try:
            return settings.FERNET.decrypt(self.encrypted_ssh_key).decode('utf-8')
        except InvalidToken:
            return None

    def delete_ssh_key(self):
        self.encrypted_ssh_key = None
        self.save()

    def has_ssh_key(self):
        return bool(self.encrypted_ssh_key)
    
    def has_private_files(self, file_type: str | None = None) -> bool:
        qs = self.private_files.all()
        if file_type:
            qs = qs.filter(file_type=file_type)
        return qs.exists()

    def get_private_files(self, file_type: str | None = None):
        qs = self.private_files.all()
        if file_type:
            qs = qs.filter(file_type=file_type)
        return qs.order_by('-updated_at')

    def get_project_dir(self) -> str:
        return f"{get_user_home(self.profile.get_sys_username())}/{self.name}/"
    
    def reboot_project(self, rebuild: bool = False) -> bool:
        project_dir = self.get_project_dir()
        system_user = self.profile.get_sys_username()

        if not check_docker_compose_environment(project_dir, system_user):
            return False
        
        if rebuild:
            if self.has_private_files():
                priv_files_failed = False
                priv_files: list[PrivateFile] = self.get_private_files()
                
                for file in priv_files:
                    save_file_command = file.save_to_sys()
                    if not save_file_command['success']:
                        if not priv_files_failed:
                            priv_files_failed = True
            
                if priv_files_failed:
                    return False
        
        reboot_command = run_command_as_user(f"cd {project_dir} && docker compose down && docker compose up -d {'--build' if rebuild else ''}", system_user)
        if not reboot_command['success']:
            return False
        
        if self.has_private_files(PrivateFile.FileType.AFTER_START_SCRIPT):
            exec_files_failed = False
                
            files: list[PrivateFile] = self.private_files.filter(file_type=PrivateFile.FileType.AFTER_START_SCRIPT)
            method_action = "PROJECT_REBUILD" if rebuild else "PROJECT_REBOOT"

            for file in files:
                result = file.execute(action=method_action)
                if not result['success']:
                    exec_files_failed = True

            if exec_files_failed:
                return False
            
        return True

    
    def delete(self, *args, **kwargs):
        self.before_delete_cleanup()
        super().delete(*args, **kwargs)

    def before_delete_cleanup(self):
        project_name = self.name
        project_owner = self.profile

        system_user = project_owner.get_sys_username()
        user_home = get_user_home(system_user)
        project_folder = f"{user_home}/{project_name}"

        if check_folder_exists(project_folder, system_user):
            errors = []
            is_compose_project = check_docker_compose_environment(project_folder, system_user)

            if is_compose_project:
                command = run_command_as_user(f"cd {project_folder} && docker compose down -v", system_user)
                if not command['success']:
                    errors.append({'field': 'docker_compose_shutdown', 'message': command['message']})

            command = run_command_as_user(f"rm -rf {project_folder}", system_user)
            if not command['success']:
                errors = [*errors, {'field': 'project_folder', 'message': 'Hubo un problema al borrar la antigua versión del proyecto.'}]

                return {
                    'data': None,
                    'errors': errors,
                    'status': 'DELETE_OLD_PROJECT_VERSION_FAILED',
                }
            
        return {
            'data': None,
            'errors': None,
            'status': 'DELETE_OLD_PROJECT_VERSION_SUCCESS',
        } 


    def __str__(self):
        return f"Project for {self.profile.user.username} - {self.repository_url}"


class Deployment(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='deployments')

    commit_id = models.CharField(max_length=40, blank=True, null=True)
    commit_url = models.URLField(max_length=255)

    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        default='in_progress'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Deployment {self.commit_id} for {self.project.name} - {self.get_status_display()}"

    def add_status_message(self, message: str):
        DeploymentStatusMessage.objects.create(deployment=self, message=message)

    def set_status(self, new_status: Literal['in_progress', 'completed', 'failed']) -> None:
        if new_status not in dict(self.STATUS_CHOICES):
            raise ValueError(f"Invalid status: {new_status}. Must be one of {list(dict(self.STATUS_CHOICES).keys())}")
        
        self.status = new_status
        self.save()


class DeploymentStatusMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    deployment = models.ForeignKey(Deployment, on_delete=models.CASCADE, related_name='status_messages')

    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Status message for {self.deployment.commit_id} at {self.timestamp}: {self.message}"
    

class PrivateFile(models.Model):
    class FileType(models.TextChoices):
        DEFAULT = 'DEFAULT', 'Default File type'
        ENV = 'ENV', 'ENV File type'
        AFTER_START_SCRIPT = 'AFTER_START_SCRIPT', 'After Start Script File type'

    FILE_TYPE_IMPORTANCE = {
        FileType.AFTER_START_SCRIPT: 1,
        FileType.ENV: 2,
        FileType.DEFAULT: 3,
    }

    EXECUTABLE_FILE_TYPES = {
        FileType.AFTER_START_SCRIPT
    }

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='private_files')

    content = models.BinaryField(blank=True, null=True)
    filename = models.CharField(max_length=255)
    filepath = models.CharField(max_length=1024, blank=True, null=True)
    fileperms = models.CharField(max_length=3, default="600")

    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        default=FileType.DEFAULT,
        help_text="Type of the private file"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_executable(self) -> bool:
        return self.file_type in self.EXECUTABLE_FILE_TYPES

    def get_importance_level(self) -> int:
        return self.FILE_TYPE_IMPORTANCE.get(self.file_type, 99)

    def set_content(self, plain_content: str, commit: bool = False):
        self.content = settings.FERNET.encrypt(plain_content.encode('utf-8').replace(b'\r', b''))
        if commit:
            self.save()

    def get_content(self) -> str | None:
        if not self.content:
            return None
        try:
            return settings.FERNET.decrypt(self.content).decode('utf-8')
        except InvalidToken:
            return None

    def reset_content(self):
        self.content = None
        self.save()

    def get_full_path_info(self) -> dict:
        relative_path = self.filepath if isinstance(self.filepath, str) else ""
        has_placeholder = relative_path.startswith(":root:")
        user_home = get_user_home(self.project.profile.get_sys_username())

        if user_home is None:
            return {
                "success": False,
                "message": "No se pudo obtener el home del usuario.",
            }

        full_path = (
            f"{user_home}/{self.project.name}/{relative_path}"
            if not has_placeholder
            else relative_path.replace(":root:", "", 1)
        )
        file_full_path = f"{full_path.rstrip('/')}/{self.filename}"

        return {
            "success": True,
            'has_placeholder': has_placeholder,
            'file_name': self.filename,
            'full_path': full_path,
            'file_full_path': file_full_path,
        }

    def save_to_sys(self) -> dict:
        system_user = self.project.profile.get_sys_username()
        user_home = get_user_home(system_user)

        if user_home is None:
            return {
                "success": False,
                "message": "No se pudo obtener el home del usuario.",
            }

        # Define file path inside user's home directory
        file_path_data = self.get_full_path_info()
        if not file_path_data['success']:
            return {
                "success": False,
                "message": f"No se pudo obtener la ruta del fichero: {file_path_data['message']}",
            }
        
        full_path = file_path_data['full_path']
        file_full_path = file_path_data['file_full_path']
        has_placeholder = file_path_data['has_placeholder']

        # Ensure the parent directory exists
        parent_dir = os.path.dirname(full_path)
        create_dir_result = run_command_as_user(f"mkdir -p {parent_dir}", system_user if not has_placeholder else "root")
        if not create_dir_result['success']:
            return {
                "success": False,
                "message": f"No se pudo crear el directorio: {create_dir_result['message']}",
            }

        # Get decrypted content
        content = self.get_content()
        if content is None:
            return {
                "success": False,
                "message": "El archivo no tiene contenido válido.",
            }

        # Save content to file using here-document to prevent variable expansion
        write_cmd = f"""cat << 'EOF' > "{file_full_path}"
{content}
EOF"""
        result = run_command_as_user(write_cmd, system_user if not has_placeholder else "root")
        if not result['success']:
            return {
                "success": False,
                "message": f"No se pudo guardar el archivo: {result['message']}",
            }

        # Set secure permissions
        perm_result = run_command_as_user(f"chmod {self.fileperms} '{file_full_path}'", system_user if not has_placeholder else "root")
        if not perm_result['success']:
            return {
                "success": False,
                "message": f"No se pudieron asignar permisos: {perm_result['message']}",
            }

        return {
            "success": True,
            "message": f"Archivo guardado correctamente en {full_path}",
            "path": full_path,
        }
    

    def execute(self, **kwargs) -> dict:
        if not self.is_executable():
            return {
                "success": False,
                "message": f"El tipo de fichero {self.file_type} no es un ejecutable."
            }

        file_data = self.get_full_path_info()
        if not file_data['success']:
            return {
                "success": False,
                "message": file_data['message'],
            }

        system_user = self.project.profile.get_sys_username()
        kwargs['user'] = system_user if not kwargs.get('user', None) else kwargs['user']

        kwargs_json = json.dumps(kwargs)
        safe_json_arg = shlex.quote(kwargs_json)
        
        script_path = file_data['full_path']
        script_full_path = file_data['file_full_path']
        command = f"cd {script_path} && bash {script_full_path} {safe_json_arg}"

        return run_command_as_user(command, "root")


    def __str__(self):
        return f"PrivateFile {self.filename} ({self.file_type}) for Project {self.project.name}"
