from django.contrib import admin
from management.models import UserProfile, Project, Deployment, DeploymentStatusMessage, PrivateFile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user',)
    search_fields = ('user__username',)
    readonly_fields = ('id',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'name', 'repository_url', 'initialized', 'has_secret', 'has_ssh_key', 'has_private_files')
    search_fields = ('name', 'repository_url', 'profile__user__username')
    list_filter = ('initialized',)
    readonly_fields = ('id', 'encrypted_secret', 'encrypted_ssh_key')

    def has_secret(self, obj):
        return obj.has_secret()
    has_secret.boolean = True

    def has_ssh_key(self, obj):
        return obj.has_ssh_key()
    has_ssh_key.boolean = True

    def has_private_files(self, obj):
        return obj.has_private_files()
    has_private_files.boolean = True


@admin.register(Deployment)
class DeploymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'commit_id', 'status', 'created_at', 'updated_at')
    search_fields = ('commit_id', 'project__name')
    list_filter = ('status', 'created_at')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(DeploymentStatusMessage)
class DeploymentStatusMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'deployment', 'timestamp', 'short_message')
    search_fields = ('deployment__commit_id', 'message')
    list_filter = ('timestamp',)
    readonly_fields = ('id', 'timestamp')

    def short_message(self, obj):
        return obj.message[:75] + ('...' if len(obj.message) > 75 else '')
    short_message.short_description = 'Message'


@admin.register(PrivateFile)
class PrivateFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'filename', 'filepath', 'created_at', 'updated_at')
    search_fields = ('filename', 'filepath', 'project__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'content')

