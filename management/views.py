from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Case, When, Value, IntegerField
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import modelformset_factory
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect
from django.contrib.auth.models import User

from api.utils import check_docker_compose_environment, get_user_home
from management.forms import EditUserForm, EmailUpdateForm, UserCreateForm, ProjectEditForm, ProjectForm, PrivateFileForm
from management.models import Project, UserProfile, PrivateFile
from management.serializers import DeploymentSerializer



@login_required
def dashboard(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    form = PasswordChangeForm(user=user)
    email_form = EmailUpdateForm(instance=user)

    if request.method == 'POST':
        if 'update_password' in request.POST:
            form = PasswordChangeForm(user=user, data=request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been updated successfully.", extra_tags='password')
                return redirect('dashboard')
            else:
                messages.error(request, "There was an error changing the password.", extra_tags='password')

        elif 'update_email' in request.POST:
            email_form = EmailUpdateForm(request.POST, instance=user)
            if email_form.is_valid():
                email_form.save()
                messages.success(request, "Your email was updated successfully.", extra_tags='email')
                return redirect('dashboard')
            else:
                messages.error(request, "There was an error updating your email.", extra_tags='email')

    all_messages = messages.get_messages(request)
    email_messages = [m for m in all_messages if 'email' in m.extra_tags]
    password_messages = [m for m in all_messages if 'password' in m.extra_tags]

    return render(request, 'management/dashboard.html', {
        'form': form,
        'email_form': email_form,
        'user': user,
        'profile': profile,
        'email_messages': email_messages,
        'password_messages': password_messages,
    })


@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users = User.objects.all()
    return render(request, 'management/users/user_list.html', {'users': users})


@user_passes_test(lambda u: u.is_superuser)
def create_user(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('user_list')
    else:
        form = UserCreateForm()
    return render(request, 'management/users/create_user.html', {'form': form})


@user_passes_test(lambda u: u.is_superuser)
def edit_user(request, profile_id):
    profile = get_object_or_404(UserProfile, id=profile_id)
    user = profile.user

    if request.method == 'POST':
        form = EditUserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
        form = EditUserForm(instance=user)

    return render(request, 'management/users/edit_user.html', {'form': form, 'user_obj': user})


@user_passes_test(lambda u: u.is_superuser)
def delete_user(request, user_id):
    profile = get_object_or_404(UserProfile, pk=user_id)
    profile.user.delete()
    return redirect('user_list')


@login_required
def project_list(request):
    profile = request.user.profile
    projects = profile.projects.all()
    return render(request, 'management/projects/project_list.html', {'projects': projects})


@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project: Project = form.save(commit=False)
            project.profile = request.user.profile

            try:
                secret = project.generate_secret()  # This will hash + assign secret
                project.save()  # Save after everything is set
            except IntegrityError:
                form.add_error('repository_url', 'You already have a project with this repository URL.')
                return render(request, 'management/projects/create_project.html', {'form': form})

            return render(request, 'management/projects/show_secret.html', {'secret': secret})
    else:
        form = ProjectForm()
    return render(request, 'management/projects/create_project.html', {'form': form})


@login_required
def edit_project(request, project_id):
    project: Project = get_object_or_404(Project, id=project_id, profile__user=request.user)
    if not project.is_initialized():
        return render(request, 'management/projects/uninitialized_project.html', { "project": project })

    system_user = project.profile.get_sys_username()
    project_dir = project.get_project_dir()
    deployments_data = DeploymentSerializer(project.deployments.all().order_by('-created_at')[:5], many=True).data

    PrivateFileFormSet = modelformset_factory(PrivateFile, form=PrivateFileForm, extra=1, can_delete=True)
    importance_cases = [
        When(file_type=ft, then=Value(level))
        for ft, level in PrivateFile.FILE_TYPE_IMPORTANCE.items()
    ]
    queryset = project.private_files.annotate(
        importance=Case(
            *importance_cases,
            default=Value(99),
            output_field=IntegerField()
        )
    ).order_by('importance', 'filename')

    saved_successfully = False
    reboot_successfully = None
    rebuild_successfully = None
    private_files_saved_successfully = None
    is_docker_compose_project = check_docker_compose_environment(project_dir, system_user)

    if request.method == 'POST':
        form = ProjectEditForm(request.POST, instance=project)
        formset = PrivateFileFormSet(request.POST, queryset=queryset)

        if 'reboot_project' in request.POST:
            reboot_successfully = project.reboot_project()
            
        elif 'rebuild_project' in request.POST:
            rebuild_successfully = project.reboot_project(True)
            
        elif 'save_private_files' in request.POST:
            private_files_saved_successfully = True

            for file in project.get_private_files():
                if not file.save_to_sys()['success']:
                    private_files_saved_successfully = False

        elif form.is_valid() and formset.is_valid():
            form.save()

            private_files = formset.save(commit=False)
            for pf in private_files:
                pf.project = project
                pf.save()

            for obj in formset.deleted_objects:
                obj.delete()

            saved_successfully = True
            queryset = project.private_files.annotate(
                importance=Case(
                    *importance_cases,
                    default=Value(99),
                    output_field=IntegerField()
                )
            ).order_by('importance', 'filename')
            formset = PrivateFileFormSet(queryset=queryset)

    form = ProjectEditForm(instance=project, initial={'ssh_private_key': ''})
    formset = PrivateFileFormSet(queryset=queryset)

    return render(request, 'management/projects/edit_project.html', {
        'form': form,
        'formset': formset,
        'project': project,
        'deployments_data': deployments_data,
        'action_executed': (reboot_successfully is not None) or (rebuild_successfully is not None) or (private_files_saved_successfully is not None),
        'saved_successfully': saved_successfully,
        'reboot_successfully': reboot_successfully,
        'rebuild_successfully': rebuild_successfully,
        'private_files_saved_successfully': private_files_saved_successfully,
        'is_docker_compose_project': is_docker_compose_project,
    })


@login_required
def reset_project_secret(request, project_id):
    project = get_object_or_404(Project, id=project_id, profile=request.user.profile)
    secret = project.reset_secret()
    next_url = request.GET.get('next') or request.POST.get('next')
    return render(request, 'management/projects/show_secret.html', {'secret': secret, 'next': next_url, 'nextTxt': 'Back to project details'})


@login_required
def delete_project_secret(request, project_id):
    project = get_object_or_404(Project, id=project_id, profile=request.user.profile)
    project.delete_secret()
    return redirect('edit_project', project_id=project.id)


@login_required
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, profile=request.user.profile)
    project.delete()
    return redirect('project_list')
