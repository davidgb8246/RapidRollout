import json
import threading

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action

from management.models import PrivateFile, Project, Deployment
from api.utils import delete_ssh_key_in_user_home, verify_github_signature, clone_git_repo_with_ssh_key, check_docker_compose_environment, check_folder_exists, sys_get_or_create_user, run_command_as_user, get_user_home, store_ssh_key_in_user_home


class GithubViewSet(viewsets.ViewSet):
    def get_permissions(self):
        return [AllowAny()]
        
    
    def githubPingEvent(self, data):
        project: Project = data.get('project', None)
        project.set_name(data['repository'].get('name', None))
        project.set_as_initialized()

        return Response({
            'data': None,
            'errors': None,
            'status': 'GITHUB_PING_EVENT_RECEIVED',
        }, status=status.HTTP_200_OK)
    

    def deploy_tasks(self, vars: dict):
        project: Project = vars['project']
        deployment: Deployment = vars['deployment']
        is_compose_project = vars['is_compose_project']
        project_folder = vars['project_folder']
        delete_key_command = vars['store_key_command']
        project_clone_url = vars['project_clone_url']
        system_user = vars['system_user']
        user_home = vars['user_home']
        project_name = vars['project_name']


        ssh_key_file_path = delete_key_command.get('ssh_key_file_path', None)
        clone_repo_command = clone_git_repo_with_ssh_key(ssh_key_file_path, project_clone_url, system_user, user_home, project_name)
        if not clone_repo_command['success']:
            deployment.set_status("failed")
            deployment.add_status_message("There was a problem downloading the remote repository.")
            deployment.add_status_message(clone_repo_command['message'])

            return Response({
                'data': None,
                'errors': [{'field': 'repository', 'message': 'There was a problem downloading the remote repository.'}],
                'status': 'REPOSITORY_CLONE_FAILED',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        priv_files_failed = False
        if project.has_private_files():
            priv_files: list[PrivateFile] = project.get_private_files()
            
            for file in priv_files:
                save_file_command = file.save_to_sys()
                if not save_file_command['success']:
                    if not priv_files_failed:
                        deployment.set_status("failed")
                        priv_files_failed = True
        
                    deployment.add_status_message(f"There was a problem saving the private file with ID: {file.id}.")
        
        if priv_files_failed:
            return Response({
                'data': None,
                'errors': [{'field': 'private_files', 'message': 'There was a problem loading the private files into the system.'}],
                'status': 'PRIVATE_FILES_LOAD_FAILED',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if project.has_ssh_key():
            delete_key_command = delete_ssh_key_in_user_home(system_user)
            if not delete_key_command['success']:
                deployment.set_status("failed")
                deployment.add_status_message("There was a problem deleting the SSH key from the system.")

                return Response({
                    'data': None,
                    'errors': [{'field': 'ssh_key', 'message': 'There was a problem deleting the SSH key from the system.'}],
                    'status': 'SSH_KEY_LOAD_FAILED',
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if is_compose_project is None:
            is_compose_project = check_docker_compose_environment(project_folder, system_user)

        if is_compose_project:
            command = run_command_as_user(f"cd {project_folder} && docker compose up -d --build", system_user)
            if not command['success']:
                deployment.set_status("failed")
                deployment.add_status_message("There was a problem starting the Docker Compose environment.")

                return Response({
                    'data': None,
                    'errors': [{'field': 'compose', 'message': 'There was a problem starting the Docker Compose environment.'}],
                    'status': 'DOCKER_COMPOSE_UP_FAILED',
                }, status=status.HTTP_400_BAD_REQUEST)
            
        exec_files_failed = False
        if project.has_private_files(PrivateFile.FileType.AFTER_START_SCRIPT):
            files: list[PrivateFile] = project.private_files.filter(file_type=PrivateFile.FileType.AFTER_START_SCRIPT)
            for file in files:
                result = file.execute(action="PROJECT_DEPLOY", deployment_id=str(deployment.id))
                if not result['success']:
                    if not exec_files_failed:
                        deployment.set_status("failed")
                        exec_files_failed = True
                    
                    deployment.add_status_message(f"There was a problem running the script with ID: {file.id}.")
        
        if exec_files_failed:
            return Response({
                'data': None,
                'errors': [{'field': 'after_scripts_files', 'message': 'There was a problem running the project\'s post-build scripts.'}],
                'status': 'AFTER_SCRIPTS_FILES_EXECUTE_FAILED',
            }, status=status.HTTP_400_BAD_REQUEST)
            
        deployment.set_status("completed")
        return Response({
            'data': None,
            'errors': None,
            'status': 'GITHUB_PUSH_EVENT_COMPLETED',
        }, status=status.HTTP_200_OK)



    def githubPushEvent(self, data):
        project: Project = data.get('project', None)
        commit_data = data.get('head_commit', {})
        deployment: Deployment = Deployment.objects.create(
            project=project,
            commit_url=commit_data.get("url", None),
            commit_id=commit_data.get("id", None)
        )
        project_name = project.name
        project_owner = project.profile
        project_clone_url = None
        is_compose_project = None

        if project_name is None:
            project.set_name(data['repository'].get('name', None))
            project_name = project.name
            project.set_as_initialized()

        system_user = project_owner.get_sys_username()
        if not sys_get_or_create_user(system_user):
            deployment.set_status("failed")
            deployment.add_status_message("There was a problem creating the user in the system.")

            return Response({
                'data': None,
                'errors': [{'field': 'system_user', 'message': 'There was a problem creating the user in the system.'}],
                'status': 'USER_CREATION_FAILED',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user_home = get_user_home(system_user)
        project_folder = f"{user_home}/{project_name}"
        store_key_command = {}

        if project.has_ssh_key():
            project_clone_url = data['repository'].get('ssh_url', None)
            ssh_key = project.get_ssh_key()
            
            store_key_command = store_ssh_key_in_user_home(system_user, ssh_key)
            if not store_key_command['success']:
                deployment.set_status("failed")
                deployment.add_status_message("There was a problem temporarily saving the SSH key in the system.")

                return Response({
                    'data': None,
                    'errors': [{'field': 'ssh_key', 'message': 'There was a problem temporarily saving the SSH key in the system.'}],
                    'status': 'SSH_KEY_LOAD_FAILED',
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            project_clone_url = data['repository'].get('clone_url', None)

        variables = {
            "project": project,
            "deployment": deployment,
            "is_compose_project": is_compose_project,
            "project_folder": project_folder,
            "store_key_command": store_key_command,
            "project_clone_url": project_clone_url,
            "system_user": system_user, 
            "user_home": user_home, 
            "project_name": project_name,
        }

        project_exists = check_folder_exists(project_folder, system_user)
        if project_exists:
            errors = []
            is_compose_project = check_docker_compose_environment(project_folder, system_user)

            if is_compose_project:
                command = run_command_as_user(f"cd {project_folder} && docker compose down", system_user)
                if not command['success']:
                    errors.append({'field': 'docker_compose_shutdown', 'message': command['message']})

            command = run_command_as_user(f"rm -rf {project_folder}", system_user)
            if not command['success']:
                errors = [*errors, {'field': 'project_folder', 'message': 'There was a problem deleting the old version of the project.'}]
                deployment.set_status("failed")
                deployment.add_status_message("\n".join([error['message'] for error in errors]))

                return Response({
                'data': None,
                'errors': errors,
                'status': 'DELETE_OLD_PROJECT_VERSION_FAILED',
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        # Continua de manera asincrona la ejecución normal.
        thread = threading.Thread(target=self.deploy_tasks, args=(variables,))
        thread.start()

        if not project_exists:
            return Response({
                'data': {
                    "message": "It seems this is the first time deploying the project, so it will take a while. Check the deployment panel for more information."
                },
                'errors': None,
                'status': 'PROJECT_DEPLOYEMENT_FIRST_BEGIN',
            }, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({
                'data': {
                    "message": "We have received the code update. Check the deployment panel for more information."
                },
                'errors': None,
                'status': 'PROJECT_DEPLOYEMENT_BEGIN',
            }, status=status.HTTP_202_ACCEPTED)
        

    @action(detail=False, methods=['post'])
    def githubUpdate(self, request):
        github_event = request.headers.get('X-GitHub-Event')
        supported_events = {
            'ping': self.githubPingEvent,
            'push': self.githubPushEvent,
        }

        if not github_event in supported_events.keys():
            return Response({
                'data': None,
                'errors': [{'field': 'github_event', 'message': 'Unsupported event.'}],
                'status': 'GITHUB_EVENT_NOT_SUPPORTED',
            }, status=status.HTTP_202_ACCEPTED)
        
        raw_body = request.body
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response({
                'data': None,
                'errors': [{'field': 'body', 'message': 'Invalid JSON payload.'}],
                'status': 'INVALID_PAYLOAD',
            }, status=status.HTTP_400_BAD_REQUEST)

        repo_url = payload.get("repository", {}).get("html_url")
        project = Project.objects.filter(repository_url=repo_url).first()

        if not project:
            return Response({
            'data': None,
            'errors': [{'field': 'html_url', 'message': 'This project is not registered in the deployment service.'}],
            'status': 'PROJECT_NOT_REGISTERED',
            }, status=status.HTTP_404_NOT_FOUND)
        
        signature_header = request.headers.get('X-Hub-Signature-256')
        secret_token = project.get_secret()

        if not verify_github_signature(request.body, secret_token, signature_header):
            return Response({
                'data': None,
                'errors': [{'field': 'signature', 'message': 'Invalid signature. Make sure the configured \'secret\' is the same as in the code repository settings.'}],
                'status': 'SIGNATURE_VERIFICATION_FAILED',
            }, status=status.HTTP_403_FORBIDDEN)

        payload['project'] = project

        return supported_events[github_event](payload)


    @action(detail=False, methods=['post'])
    def addDeploymentStatusMessage(self, request):
        request_secret = request.data.get("secret", None)
        deployment_id = request.data.get("deployment_id", None)
        message = request.data.get("message", None)

        if not deployment_id or not message or not request_secret:
            errors = []
            if not request_secret: errors.append({'field': 'request_secret', 'message': 'The "request_secret" field is required.'})
            if not deployment_id: errors.append({'field': 'deployment_id', 'message': 'The "deployment_id" field is required.'})
            if not message: errors.append({'field': 'message', 'message': 'The "message" field is required.'})

            return Response({
                'data': None,
                'errors': errors,
                'status': 'MISSING_REQUIRED_FIELDS',
            }, status=status.HTTP_400_BAD_REQUEST)

        deployment = Deployment.objects.filter(id=deployment_id).first()
        if not deployment:
            return Response({
            'data': None,
            'errors': [{'field': 'deployment', 'message': 'That deployment is not registered in the deployment service.'}],
            'status': 'DEPLOYMENT_NOT_REGISTERED',
            }, status=status.HTTP_404_NOT_FOUND)
        
        project: Project = deployment.project
        if not project.check_secret(request_secret):
            return Response({
                'data': None,
                'errors': [{'field': 'secret', 'message': 'The secret key is incorrect.'}],
                'status': 'AUTHENTICATION_FAILED',
            }, status=status.HTTP_403_FORBIDDEN)

        deployment.add_status_message(message)

        return Response({
            'data': None,
            'errors': None,
            'status': 'STATUS_MESSAGE_CREATED',
        }, status=status.HTTP_201_CREATED)
