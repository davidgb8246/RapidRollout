import subprocess
import hashlib
import hmac
import random
import string
import os
import fnmatch


def generate_random_password(length=50):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

    
def get_user_home(username):
    try:
        result = subprocess.run(
            ['getent', 'passwd', username],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        user_info = result.stdout.decode().strip().split(':')
        home_directory = user_info[5] if len(user_info) > 5 else None
        
        return home_directory
    
    except subprocess.CalledProcessError:
        return None


def run_command_as_user(command: str, target_user: str):
    try:
        result = subprocess.run(
            ["sudo", "-u", target_user, "bash", "-c", command],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # print(f"{command} stdout", result.stdout)
        # print(f"{command} stderr", result.stderr)

        return {
            "success": True,
            "message": result.stdout,
        }
    except subprocess.CalledProcessError as e:
        
        # print(f"{command} stdout", e.stdout)
        # print(f"{command} stderr", e.stderr)

        return {
            "success": False,
            "message": e.stderr,
        }
    

def check_folder_exists(folder_path: str, target_user: str) -> bool:
    result = run_command_as_user(f"test -d {folder_path}", target_user)
    return result["success"]


def check_docker_compose_environment(directory_path: str, target_user: str) -> bool:
    compose_files = None
    try:
        compose_files = fnmatch.filter(os.listdir(directory_path), '*compose*')
    except FileNotFoundError:
        return False

    if not compose_files:
        return False

    for compose_file in compose_files:
        command = f"docker compose -f {os.path.join(directory_path, compose_file)} config"
        result = run_command_as_user(command, target_user)

        if result["success"]:
            return True

    return False


def clone_git_repo_with_ssh_key(key_file_path: str, git_ssh_url: str, target_user: str, target_folder: str, folder_name: str):
    if key_file_path:
        git_ssh_command = f"cd {target_folder} && GIT_SSH_COMMAND='ssh -i {key_file_path} -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' git clone {git_ssh_url} {folder_name}"
    else:
        git_ssh_command = f"cd {target_folder} && GIT_TERMINAL_PROMPT=0 git clone {git_ssh_url} {folder_name}"

    return run_command_as_user(git_ssh_command, target_user)



def verify_github_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.

    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    if not signature_header:
        return False
    
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)


def sys_user_exists(username):
    try:
        subprocess.run(["id", username], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def sys_get_or_create_user(username):
    if not sys_user_exists(username):
        try:
            password = generate_random_password(50)

            subprocess.run(["sudo", "useradd", "-m", username], check=True)
            subprocess.run(["sudo", "chpasswd"], input=f"{username}:{password}", text=True, check=True)
            subprocess.run(["sudo", "usermod", "-s", "/usr/sbin/nologin", username], check=True)
            subprocess.run(["sudo", "usermod", "-aG", "docker", username], check=True)
            
            return True
        except subprocess.CalledProcessError:
            return False
    else:
        return True

def sys_delete_user(username):
    if sys_user_exists(username):
        try:
            subprocess.run(["sudo", "deluser", "--remove-all-files", "--remove-home", username], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    else:
        return False

def store_ssh_key_in_user_home(system_user, ssh_key):
    system_user_home = get_user_home(system_user)
    if system_user_home is None:
        return {
            "success": False,
            "message": "No se pudo obtener el home del usuario.",
        }
    
    ssh_key_file_path = f"{system_user_home}/.ssh/{system_user}-sshKey"

    create_dir_result = run_command_as_user(f"mkdir -p {system_user_home}/.ssh", system_user)
    if not create_dir_result['success']:
        return create_dir_result
    
    result = run_command_as_user(f'echo "{ssh_key}" > {ssh_key_file_path}', system_user)
    result['ssh_key_file_path'] = ssh_key_file_path

    permissions_result = run_command_as_user(f"chmod 600 {ssh_key_file_path}", system_user)
    if not permissions_result['success']:
        return permissions_result

    return result


def delete_ssh_key_in_user_home(system_user):
    system_user_home = get_user_home(system_user)
    if system_user_home is None:
        return {
            "success": False,
            "message": "No se pudo obtener el home del usuario.",
        }

    ssh_key_file_path = f"{system_user_home}/.ssh/{system_user}-sshKey"
    file_check_result = run_command_as_user(f"test -f {ssh_key_file_path}", system_user)
    if not file_check_result['success']:
        return {
            "success": False,
            "message": f"El archivo de clave SSH {ssh_key_file_path} no existe.",
        }

    delete_result = run_command_as_user(f"rm -f {ssh_key_file_path}", system_user)
    if delete_result['success']:
        return {
            "success": True,
            "message": f"Clave SSH eliminada de {ssh_key_file_path}.",
        }
    else:
        return delete_result


def save_private_file_to_sys(private_file) -> dict:
    from management.models import PrivateFile
    private_file: PrivateFile = private_file

    system_user = private_file.project.profile.get_sys_username()
    user_home = get_user_home(system_user)

    if user_home is None:
        return {
            "success": False,
            "message": "No se pudo obtener el home del usuario.",
        }

    # Define file path inside user's home directory
    relative_path = private_file.filepath if private_file.filepath else ""
    full_path = f"{user_home}/{private_file.project.name}/{relative_path}"
    file_full_path = f"{full_path}/{private_file.filename}"

    # Ensure the parent directory exists
    parent_dir = os.path.dirname(full_path)
    create_dir_result = run_command_as_user(f"mkdir -p {parent_dir}", system_user)
    if not create_dir_result['success']:
        return {
            "success": False,
            "message": f"No se pudo crear el directorio: {create_dir_result['message']}",
        }

    # Get decrypted content
    content = private_file.get_content()
    if content is None:
        return {
            "success": False,
            "message": "El archivo no tiene contenido válido.",
        }

    # Save content to file
    escaped_content = content.replace('"', '\\"')  # escape quotes to prevent shell issues
    write_cmd = f'echo "{escaped_content}" > "{file_full_path}"'
    result = run_command_as_user(write_cmd, system_user)
    if not result['success']:
        return {
            "success": False,
            "message": f"No se pudo guardar el archivo: {result['message']}",
        }

    # Set secure permissions
    perm_result = run_command_as_user(f"chmod 600 '{file_full_path}'", system_user)
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
