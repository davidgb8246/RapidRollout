# RapidRollout
An application designed to facilitate the automated deployment of containerized applications using Docker Compose.

## Features

- Project management linked to GitHub repositories.
- Historical record of deployments performed, including a basic log history.
- Compatible with environments that use HTTPS and protection via Cloudflare proxy.

## Installation Guide

### Step 1:
As a first step, it is necessary to install the minimum dependencies for the application to function:
```bash
apt update -y
apt install -y python3-venv python3-pip nginx curl
```

Next, we will proceed to install Docker using the official script:
```bash
curl -sSL https://get.docker.com/ | CHANNEL=stable bash
```

> [!NOTE]  
> To run containers without elevated privileges, it is recommended to use Docker in rootless mode with a non-root user.
> 
> Make sure to replace `<nonRootUser>` with a system username that does not have administrative privileges.
>
> ```bash
> sh -eux <<EOF
> # Install newuidmap & newgidmap binaries
> apt-get install -y uidmap
> EOF
>
> sudo -u <nonRootUser> bash -c "dockerd-rootless-setuptool.sh install"
> ```

### Step 2:
Then, the application repository must be cloned into the `/var/www/` directory, or downloaded manually.
```bash
cd /var/www/
git clone https://github.com/davidgb8246/RapidRollout
```

### Step 3:
Once the project is downloaded, create a virtual environment and install the required dependencies.
```bash
cd RapidRollout/

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4:
Configure the `.env` environment variable file by copying the example file and editing the necessary values.
```bash
cp .env.example .env
nano .env
```

Specifically, a random string should be assigned to `SECRET_KEY`, and valid domains should be defined in `ALLOWED_HOSTS`, separated by commas.
```env
DEBUG=False
SECRET_KEY=your-very-secret-key
ALLOWED_HOSTS=rapidrollout.domain.example,rapid-deploy.domain.example
```

### Step 5:
At this point, necessary database migrations will be applied, and a `superuser` will be created.

> [!NOTE]  
> Access to the application is restricted. To use it, a `superuser` must first register the user. Only `superusers` have the ability to grant access.

First, run the migrations, then create the `superuser` by providing the required data.
```bash
python3 manage.py migrate
python3 manage.py createsuperuser
```

### Step 6:
Next, collect the application's static files and set the appropriate permissions for proper operation with Nginx.
```bash
python manage.py collectstatic

chown -R www-data:www-data /var/www/RapidRollout
find /var/www/RapidRollout -type d -exec chmod 755 {} \;
find /var/www/RapidRollout -type f -exec chmod 644 {} \;
chmod +x /var/www/RapidRollout/venv/bin/*
```

### Step 7:
Configure the system service that will keep the application running continuously under the `root` user.
```bash
mv /var/www/RapidRollout/resources/rapidrollout.service /etc/systemd/system/
```

Once the service file is moved to its appropriate location, enable and start it. Finally, check its status to ensure it is running (`Active: active (running)`).
```bash
systemctl daemon-reload
systemctl enable rapidrollout.service
systemctl start rapidrollout.service

systemctl status rapidrollout.service
```

### Step 8:
The next step is to configure Nginx to enforce SSL usage and redirect traffic to the Gunicorn server.

Copy the site configuration file, modify it to reflect the domain and SSL certificate locations, then enable the corresponding site.
```bash
mv /var/www/RapidRollout/resources/rapidrollout-ssl-nginx /etc/nginx/sites-available/rapidrollout
nano /etc/nginx/sites-available/rapidrollout

ln -s /etc/nginx/sites-available/rapidrollout /etc/nginx/sites-enabled/
```

> [!NOTE]  
> Make sure to place the SSL certificates in the paths specified in the Nginx configuration file.

Once configuration is complete, reload the Nginx service to apply the changes.
```bash
nginx -t && systemctl reload nginx
```

### Step 9:
Finally, the application will be available from the previously configured domain and ready for use.

## Contributors ✨
- [davidgb8246](https://github.com/davidgb8246)<br><br>

Copyright (C) 2025
