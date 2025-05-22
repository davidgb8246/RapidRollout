# RapidRollout
Una aplicación diseñada para facilitar el despliegue automatizado de aplicaciones contenerizadas mediante Docker Compose.

## Características

- Gestión de proyectos vinculados a repositorios de GitHub.
- Registro histórico de despliegues realizados, incluyendo un historial de logs básico.
- Compatible con entornos que utilizan HTTPS y protección mediante proxy de Cloudflare.

## Guía de Instalación

### Paso 1:
Como primer paso, es necesario instalar las dependencias mínimas para el funcionamiento de la aplicación:
```bash
apt update -y
apt install -y python3-venv python3-pip nginx curl
```

A continuación, procederemos a instalar Docker utilizando el script oficial:
```bash
curl -sSL https://get.docker.com/ | CHANNEL=stable bash
```

> [!NOTE]  
> Para ejecutar contenedores sin privilegios elevados, se recomienda utilizar el modo rootless de Docker con un usuario sin privilegios de root.
> 
> Asegúrese de reemplazar `<usuarioNoRoot>` por un nombre de usuario del sistema que no tenga privilegios administrativos.
>
> ```bash
> sh -eux <<EOF
> # Install newuidmap & newgidmap binaries
> apt-get install -y uidmap
> EOF
>
> sudo -u <usuarioNoRoot> bash -c "dockerd-rootless-setuptool.sh install"
> ```
> 

### Paso 2:
Después, se debe clonar el repositorio de la aplicación en el directorio `/var/www/`, o bien descargarlo manualmente.
```bash
cd /var/www/
git clone https://github.com/davidgb8246/RapidRollout
```

### Paso 3:
Una vez descargado el proyecto, se procederá a la creación de un entorno virtual y la instalación de las dependencias requeridas.
```bash
cd RapidRollout/

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 4:
Se debe configurar el archivo de variables de entorno `.env`, copiando el archivo de ejemplo y editando los valores necesarios.
```bash
cp .env.example .env
nano .env
```

Específicamente, deberá asignarse una cadena aleatoria a `SECRET_KEY` y definir los dominios válidos en `ALLOWED_HOSTS`, separados por comas.
```env
DEBUG=False
SECRET_KEY=your-very-secret-key
ALLOWED_HOSTS=rapidrollout.domain.example,rapid-deploy.domain.example
```

### Paso 5:
En este punto, se aplicarán las migraciones necesarias a la base de datos y se creará un `superusuario`.

> [!NOTE]  
> El acceso a la aplicación está restringido. Para poder utilizarla, un `superusuario` debe registrar previamente al usuario. Solo los `superusuarios` tienen la capacidad de conceder acceso.

Primero se ejecutan las migraciones, y posteriormente se genera el `superusuario` proporcionando los datos requeridos.
```bash
python3 manage.py migrate
python3 manage.py createsuperuser
```

### Paso 6:
A continuación, se recopilarán los archivos estáticos de la aplicación y se establecerán los permisos adecuados para su correcto funcionamiento con Nginx.
```bash
python manage.py collectstatic

chown -R www-data:www-data /var/www/RapidRollout
find /var/www/RapidRollout -type d -exec chmod 755 {} \;
find /var/www/RapidRollout -type f -exec chmod 644 {} \;
chmod +x /var/www/RapidRollout/venv/bin/*
```

### Paso 7:
Se configurará el servicio del sistema que permitirá mantener la aplicación en ejecución de forma continua bajo el usuario `root`.
```bash
mv /var/www/RapidRollout/resources/rapidrollout.service /etc/systemd/system/
```

Una vez movido el archivo del servicio a su ubicación correspondiente, se procederá a su habilitación y puesta en marcha. Finalmente, se verifica su estado para asegurar que se encuentra en ejecución (`Active: active (running)`).
```bash
systemctl daemon-reload
systemctl enable rapidrollout.service
systemctl start rapidrollout.service

systemctl status rapidrollout.service
```

### Paso 8:
El siguiente paso consiste en la configuración de Nginx para forzar el uso de SSL y redirigir el tráfico hacia el servidor Gunicorn.

Se copiará el archivo de configuración del sitio, se modificará para reflejar el dominio y la ubicación de los certificados SSL, y luego se habilitará el sitio correspondiente.
```bash
mv /var/www/RapidRollout/resources/rapidrollout-ssl-nginx /etc/nginx/sites-available/rapidrollout
nano /etc/nginx/sites-available/rapidrollout

ln -s /etc/nginx/sites-available/rapidrollout /etc/nginx/sites-enabled/
```

> [!NOTE]  
> Asegúrese de colocar los certificados SSL en las rutas especificadas dentro del archivo de configuración de Nginx.

Una vez completada la configuración, se recargará el servicio de Nginx para aplicar los cambios.
```bash
nginx -t && systemctl reload nginx
```

### Paso 9:
Finalmente, la aplicación estará disponible desde el dominio configurado previamente, y estará lista para su uso.

## Colaboradores ✨
- [davidgb8246](https://github.com/davidgb8246)<br><br>

Copyright (C) 2025
