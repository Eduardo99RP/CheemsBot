# CheemsMusic
Este bot utiliza varias bibliotecas de Python. A continuación se detalla cómo instalarlas.
## 🧪 Versiones disponibles

Este proyecto cuenta con dos versiones:

- Una basada en la librería `discord.py`
- Otra basada en `nextcord`

Actualmente, la versión con **`nextcord`** está más actualizada y es la recomendada, ya que `discord.py` puede presentar errores o problemas de compatibilidad debido a que no se encuentra tan mantenida activamente. Se espera que en el futuro estos problemas sean corregidos por sus desarrolladores.

---


### Versión de python recomendada
- python 3.12.3

## 📦 Paquetes

- **asyncio**: Esta biblioteca está incluida en la biblioteca estándar de Python (Python 3.4 o superior).
- **discord.py o nextcord**: Biblioteca para interactuar con la API de Discord.
- **pytube**: Biblioteca para descargar videos de YouTube.
- **spotipy**: Biblioteca para interactuar con la API de Spotify.
- **python-dotenv**: Biblioteca para cargar variables de entorno desde un archivo `.env`.
- **pynacl**: Proporciona herramientas para realizar operaciones criptográficas, como cifrado, firmas digitales, hashing y otras funciones relacionadas con la seguridad.

## ⚙️ Instalación

Clona este repositorio:

```bash
git clone https://github.com/tu_usuario/cheemsbot.git
cd cheemsbot
```
Asegúrate de tener `pip` instalado y configurado correctamente.

Instala las dependencias:
```sh
pip install -r requirements.txt
```

También es necesario instalar la siguiente herramienta: 

- Para instalar en Debian o ubuntu 
  ```sh
  sudo apt install ffmpeg
  ```
- Para instalar en ArchLinux
  ```sh
  sudo pacman -S ffmpeg
  ```
## Archivo .env
Asegúrate de crear un archivo **.env** en el directorio raíz del proyecto para almacenar tus variables de entorno.
### Ejemplo del archivo .env 
```sh
TOKEN=El_token_del_bot
CLIENT_ID_SP=CLiente_id_de_spotify
CLIENT_SECRECT=Cliente_secreto_spotify
```

## Aviso

Este bot está diseñado para uso personal y sin fines de lucro. No se busca hacer negocio con este proyecto ni generar ingresos a partir de su uso.

**Responsabilidad del Usuario:** El uso de este bot es bajo la responsabilidad de quien lo utiliza. Los desarrolladores no se hacen responsables por cualquier daño o problema que pueda surgir del uso de este software.

**Uso Acorde a las Políticas:** Asegúrate de utilizar este bot de acuerdo con las políticas y términos de servicio de las plataformas y servicios con los que interactúa (por ejemplo, Discord, YouTube, Spotify). No nos hacemos responsables por el uso indebido o violaciones a los términos de servicio de estas plataformas.
