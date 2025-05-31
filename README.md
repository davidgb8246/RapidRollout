# RapidRollout
An application designed to facilitate the automated deployment of containerized applications using Docker Compose.

## Features

- Project management linked to GitHub repositories.
- Historical record of deployments performed, including a basic log history.
- Compatible with environments that use HTTPS and protection via Cloudflare proxy.

## Future Improvements

- Improve the logging system.
- Add pagination and search functionality to the project and user listings.

## Installation Guide

### Step 1:
As a first step, it is necessary to install the minimum dependencies for the application to function:
```bash
apt update -y
apt install -y python3-venv python3-pip python3-dev nginx mariadb-server curl git libmysqlclient-dev pkg-config
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

Specifically, a random string must be assigned to `SECRET_KEY` and the valid domains defined in `ALLOWED_HOSTS`, separated by commas.
```env
DEBUG=False
SECRET_KEY=your-very-secret-key
ALLOWED_HOSTS=rapidrollout.domain.example,rapid-deploy.domain.example

...
```
> [!NOTE]  
> Please complete the configuration of the `.env` file by adding the necessary fields that were not detailed in the previous section, making sure to include all the required information for the proper functioning of the project environment.

### Step 5:
Once the project is configured, it is necessary to create the database and the corresponding user in the Database Management System (DBMS).
Below are the steps to perform this setup using MariaDB:

Access the MariaDB client as the root user:
```bash
mariadb -u root -p
```

Run the following SQL commands to create the database, the user, and assign the privileges:

```sql
CREATE DATABASE your_db_name;
CREATE USER 'your_db_user'@'127.0.0.1' IDENTIFIED BY 'your_db_password';
GRANT ALL PRIVILEGES ON your_db_name.* TO 'your_db_user'@'127.0.0.1' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EXIT;
```

> [!NOTE]  
> Replace `your_db_name`, `your_db_user`, and `your_db_password` with the values corresponding to your development environment.

### Step 6:
At this point, necessary database migrations will be applied, and a `superuser` will be created.

> [!NOTE]  
> Access to the application is restricted. To use it, a `superuser` must first register the user. Only `superusers` have the ability to grant access.

First, run the migrations, then create the `superuser` by providing the required data.
```bash
python3 manage.py migrate
python3 manage.py createsuperuser
```

### Step 7:
Next, collect the application's static files and set the appropriate permissions for proper operation with Nginx.
```bash
python manage.py collectstatic

chown -R www-data:www-data /var/www/RapidRollout
find /var/www/RapidRollout -type d -exec chmod 755 {} \;
find /var/www/RapidRollout -type f -exec chmod 644 {} \;
chmod +x /var/www/RapidRollout/venv/bin/*
```

### Step 8:
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

### Step 9:
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

### Step 10:
Finally, the application will be available from the previously configured domain and ready for use.

## Contributors ✨
- [davidgb8246](https://github.com/davidgb8246)<br><br>

Copyright (C) 2025
