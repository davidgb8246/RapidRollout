# RapidRollout
Una aplicación diseñada para facilitar el despliegue automatizado de aplicaciones contenerizadas mediante Docker Compose.

## Características

- Gestión de proyectos vinculados a repositorios de GitHub.
- Registro histórico de despliegues realizados, incluyendo un historial de logs básico.
- Compatible con entornos que utilizan HTTPS y protección mediante proxy de Cloudflare.

## Guía de Uso
Haga [clic aquí](https://github.com/davidgb8246/RapidRollout/wiki) para acceder a la guía de uso de la aplicación.

## Guía de Instalación

### Paso 1:
Como primer paso, es necesario instalar las dependencias mínimas para el funcionamiento de la aplicación:
```bash
apt update -y
apt install -y python3-venv python3-pip python3-dev \
    mariadb-server default-libmysqlclient-dev nginx \
    curl git pkg-config build-essential
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

...
```
> [!NOTE]  
> Por favor, complete la configuración del archivo `.env` agregando los campos necesarios que no se detallaron en la sección anterior, asegurándose de incluir toda la información requerida para el correcto funcionamiento del entorno del proyecto.

### Paso 5:
Una vez configurado el proyecto, es necesario crear la base de datos y el usuario correspondiente en el Sistema de Gestión de Bases de Datos (SGBD).
A continuación, se detallan los pasos para realizar esta configuración utilizando MariaDB:

Acceder al cliente de MariaDB como usuario root:
```bash
mariadb -u root -p
```

Ejecutar los siguientes comandos SQL para crear la base de datos, el usuario y asignar los privilegios:

```sql
CREATE DATABASE your_db_name;
CREATE USER 'your_db_user'@'127.0.0.1' IDENTIFIED BY 'your_db_password';
GRANT ALL PRIVILEGES ON your_db_name.* TO 'your_db_user'@'127.0.0.1' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EXIT;
```

> [!NOTE]  
> Reemplace `your_db_name`, `your_db_user` y `your_db_password` con los valores correspondientes a su entorno de desarrollo.

### Paso 6:
En este punto, se aplicarán las migraciones necesarias a la base de datos y se creará un `superusuario`.

> [!NOTE]  
> El acceso a la aplicación está restringido. Para poder utilizarla, un `superusuario` debe registrar previamente al usuario. Solo los `superusuarios` tienen la capacidad de conceder acceso.

Primero se ejecutan las migraciones, y posteriormente se genera el `superusuario` proporcionando los datos requeridos.
```bash
python3 manage.py migrate
python3 manage.py createsuperuser
```

### Paso 7:
A continuación, se recopilarán los archivos estáticos de la aplicación y se establecerán los permisos adecuados para su correcto funcionamiento con Nginx.
```bash
python manage.py collectstatic

chown -R www-data:www-data /var/www/RapidRollout
find /var/www/RapidRollout -type d -exec chmod 755 {} \;
find /var/www/RapidRollout -type f -exec chmod 644 {} \;
chmod +x /var/www/RapidRollout/venv/bin/*
```

### Paso 8:
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

### Paso 9:
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

### Paso 10:
Finalmente, la aplicación estará disponible desde el dominio configurado previamente, y estará lista para su uso.

## 👥 Contribuyentes

### Autor
- **[davidgb8246](https://github.com/davidgb8246)** – Creador y desarrollador principal de RapidRollout

### Cómo contribuir
¡Las contribuciones son bienvenidas! Para colaborar, por favor haz un fork del repositorio, realiza tus cambios y envía un pull request.  
Asegúrate de que tus contribuciones cumplan con los requisitos de licencia y atribución.

---

## 📄 Licencia

Este proyecto está licenciado bajo la **Licencia Pública General Affero de GNU versión 3.0 (AGPLv3)** con Términos Adicionales.  
Consulta el archivo [LICENSE](./LICENSE) para conocer los términos legales completos, incluyendo las condiciones adicionales conforme a la Sección 7 de la AGPLv3.
