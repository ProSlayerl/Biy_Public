import os
import re
import json
import time
import math
import shutil
import base64
import logging
import sys
import requests
import asyncio
import zipfile
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import RPCError

# =========================
# CONFIGURACIÓN Y LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =========================
# CONFIGURACIÓN SEGURA
# =========================
class Config:
    def __init__(self):
        # Cargar desde variables de entorno o usar valores por defecto
        self.API_ID = int(os.getenv("API_ID", 25512912))
        self.API_HASH = os.getenv("API_HASH", "cfe0fcd0f5b048c1586fb6485a9e9750")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "8551744239:AAG2J_gpBldPcZgLJP4DBKBh7_ctgGGUZ6o")
        self.ADMIN_ID = int(os.getenv("ADMIN_ID", 1461573114))
        
        # Configuración de revistas
        self.REVISTAS = {
            "KIKI_REV": {
                "username": os.getenv("KIKI_USER", "daironvf"),
                "password": os.getenv("KIKI_PASS", "Dairon2005"),
                "submission_id": os.getenv("KIKI_SUB", "3493"),
                "base_url": "https://revcardiologia.sld.cu",
                "contexto": "revcardiologia",
                "nombre": "Revista Cardiología",
                "bitzero": int(os.getenv("KIKI_BITZERO", 1)),
                "encryption_key": os.getenv("KIKI_KEY", "default_key_1")
            },
            "COMED_REV": {
                "username": os.getenv("COMED_USER", "daironvf"),
                "password": os.getenv("COMED_PASS", "Dairon2005#"),
                "submission_id": os.getenv("COMED_SUB", "5529"),
                "base_url": "https://revcocmed.sld.cu",
                "contexto": "cocmed",
                "nombre": "Revista COMED",
                "bitzero": int(os.getenv("COMED_BITZERO", 1)),
                "encryption_key": os.getenv("COMED_KEY", "default_key_2")
            },
            "EMS_REV": {
                "username": os.getenv("EMS_USER", "daironvf"),
                "password": os.getenv("EMS_PASS", "Dairon2005#"),
                "submission_id": os.getenv("EMS_SUB", "5033"),
                "base_url": "https://ems.sld.cu",
                "contexto": "ems",
                "nombre": "Revista EMS",
                "bitzero": int(os.getenv("EMS_BITZERO", 1)),
                "encryption_key": os.getenv("EMS_KEY", "default_key_3")
            }
        }
        
        # Configuración general
        self.ROOT_DIR = os.getenv("ROOT_DIR", "raiz")
        self.CHUNK_SIZE_MB = int(os.getenv("CHUNK_SIZE_MB", 5))
        self.AUTHORIZED_USERS_FILE = "authorized_users.json"
        self.BITZERO_SIGNATURE = os.getenv("BITZERO_SIG", "@bitzero#2024")
        
        # Crear directorio raíz si no existe
        os.makedirs(self.ROOT_DIR, exist_ok=True)

config = Config()

# =========================
# INICIALIZACIÓN DE DIRECTORIOS
# =========================
def initialize_directories():
    """Inicializa todos los directorios necesarios"""
    try:
        # Directorio raíz principal
        os.makedirs(config.ROOT_DIR, exist_ok=True)
        logger.info(f"Directorio raíz creado/verificado: {config.ROOT_DIR}")
        
        # Directorio temporal para procesamiento
        temp_dir = os.path.join(config.ROOT_DIR, "_temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Directorio para logs de usuario
        logs_dir = os.path.join(config.ROOT_DIR, "_logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Verificar permisos de escritura
        test_file = os.path.join(config.ROOT_DIR, ".write_test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        
        logger.info("✓ Directorios inicializados correctamente")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error inicializando directorios: {e}")
        return False

# =========================
# ENCRIPTACIÓN BITZERO
# =========================
class BitZeroEncoder:
    """Sistema de ofuscación avanzado para archivos"""
    
    # PNG de 1x1 pixel (cabecera camuflaje)
    PNG_HEADER = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
    
    @staticmethod
    def encode_png(file_path: str, output_path: str) -> bool:
        """Codifica un archivo dentro de un PNG falso"""
        try:
            with open(file_path, 'rb') as f:
                original_data = f.read()
            
            with open(output_path, 'wb') as f:
                f.write(BitZeroEncoder.PNG_HEADER + original_data)
            
            logger.info(f"Archivo codificado como PNG: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error en encode_png: {e}")
            return False
    
    @staticmethod
    def encode_html(file_path: str, output_path: str) -> bool:
        """Codifica un archivo en base64 dentro de HTML"""
        try:
            with open(file_path, 'rb') as f:
                original_data = f.read()
            
            # Codificar en base64
            encoded = base64.b64encode(original_data).decode('utf-8')
            
            # Crear HTML con datos ocultos
            html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Document</title>
</head>
<body>
    <div style="display:none;" id="data">{encoded}</div>
    <script>
        // Documento generado
        console.log("Document loaded");
    </script>
</body>
</html>"""
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Archivo codificado como HTML: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error en encode_html: {e}")
            return False
    
    @staticmethod
    def apply_camouflage(file_path: str, bitzero_mode: int, user_id: int) -> Optional[str]:
        """Aplica camuflaje según el modo bitzero"""
        if bitzero_mode == 0:
            return file_path
        
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1]
        
        if bitzero_mode == 1:
            # Modo PNG
            output_name = f"{file_name}_{user_id}_cache{file_ext}.png"
            output_path = os.path.join(os.path.dirname(file_path), output_name)
            if BitZeroEncoder.encode_png(file_path, output_path):
                return output_path
        
        elif bitzero_mode == 2:
            # Modo HTML
            output_name = f"{file_name}_{user_id}_data{file_ext}.html"
            output_path = os.path.join(os.path.dirname(file_path), output_name)
            if BitZeroEncoder.encode_html(file_path, output_path):
                return output_path
        
        return None

# =========================
# GENERADOR DE URLS OFUSCADAS
# =========================
class URLGenerator:
    """Genera URLs ofuscadas tipo BitZero"""
    
    @staticmethod
    def encode_key(host: str, user: str, password: str, repo: str, contexto: str) -> str:
        """Codifica credenciales en formato seguro incluyendo contexto"""
        parts = [
            base64.b64encode(host.encode()).decode().replace('=', '#'),
            base64.b64encode(user.encode()).decode().replace('=', '#'),
            base64.b64encode(password.encode()).decode().replace('=', '#'),
            base64.b64encode(repo.encode()).decode().replace('=', '#'),
            base64.b64encode(contexto.encode()).decode().replace('=', '#')
        ]
        return "-".join(parts)
    
    @staticmethod
    def generate_bitzero_url(host: str, user: str, password: str, repo: str, contexto: str,
                           file_ids: List[str], bitzero_mode: int, 
                           original_name: str, file_size: int) -> str:
        """Genera URL ofuscada estilo BitZero"""
        token = "-".join(file_ids)
        key = URLGenerator.encode_key(host, user, password, repo, contexto)
        safe_name = base64.b64encode(original_name.encode()).decode().replace('=', '_')
        
        url_parts = [
            f"https://bitzero.techdev.cu",
            f"{file_size}-{repo}",
            token,
            str(bitzero_mode),
            key,
            safe_name
        ]
        
        return "/".join(url_parts)

# =========================
# SISTEMA DE USUARIOS AUTORIZADOS
# =========================
class UserManager:
    """Gestor avanzado de usuarios autorizados"""
    
    def __init__(self, users_file: str):
        self.users_file = users_file
        self.users = self._load_users()
    
    def _load_users(self) -> List[Dict]:
        """Carga usuarios desde archivo JSON"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando usuarios: {e}")
                return []
        return []
    
    def _save_users(self) -> bool:
        """Guarda usuarios en archivo JSON"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error guardando usuarios: {e}")
            return False
    
    def is_authorized(self, user_id: int) -> bool:
        """Verifica si usuario está autorizado"""
        if user_id == config.ADMIN_ID:
            return True
        
        for user in self.users:
            if user.get('id') == user_id:
                return user.get('active', True)
        return False
    
    def add_user(self, user_id: int, username: str = None, 
                 added_by: int = None) -> bool:
        """Agrega un nuevo usuario autorizado"""
        if self.is_authorized(user_id):
            return False
        
        new_user = {
            'id': user_id,
            'username': username,
            'added_by': added_by,
            'added_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'active': True,
            'last_access': None
        }
        
        self.users.append(new_user)
        return self._save_users()
    
    def remove_user(self, user_id: int) -> bool:
        """Elimina un usuario autorizado"""
        original_count = len(self.users)
        self.users = [u for u in self.users if u.get('id') != user_id]
        
        if len(self.users) < original_count:
            return self._save_users()
        return False
    
    def get_all_users(self) -> List[Dict]:
        """Obtiene lista de todos los usuarios"""
        return self.users.copy()

user_manager = UserManager(config.AUTHORIZED_USERS_FILE)

# =========================
# CLASE UPLOADER REVISTA (CON BITZERO)
# =========================
class RevistaUploader:
    """Uploader mejorado con soporte BitZero"""
    
    def __init__(self, username: str, password: str, submission_id: str, 
                 base_url: str, contexto: str, bitzero_mode: int = 0, 
                 encryption_key: str = None):
        self.base_url = base_url
        self.contexto = contexto
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        self.csrf_token = None
        self.submission_id = str(submission_id).strip()
        self.chunk_size = config.CHUNK_SIZE_MB * 1024 * 1024
        self.username = username
        self.password = password
        self.bitzero_mode = bitzero_mode
        self.encryption_key = encryption_key
        self.uploaded_files = []
    
    def login(self) -> bool:
        """Inicia sesión en la revista"""
        try:
            login_url = f"{self.base_url}/index.php/{self.contexto}/login"
            resp = self.session.get(login_url, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extraer token CSRF de múltiples formas
            csrf_token = None
            
            # Método 1: Buscar en input hidden
            csrf_input = soup.find('input', {'name': 'csrfToken'})
            if csrf_input:
                csrf_token = csrf_input.get('value', '')
            
            # Método 2: Buscar en scripts
            if not csrf_token:
                for script in soup.find_all('script'):
                    if script.string and 'csrfToken' in script.string:
                        match = re.search(r'csrfToken[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]', script.string)
                        if match:
                            csrf_token = match.group(1)
                            break
            
            # Método 3: Buscar en meta tags
            if not csrf_token:
                meta_tag = soup.find('meta', {'name': 'csrf-token'})
                if meta_tag:
                    csrf_token = meta_tag.get('content', '')
            
            if not csrf_token:
                logger.warning("No se encontró token CSRF, intentando continuar...")
                csrf_token = "temp_token"
            
            self.csrf_token = csrf_token
            
            data = {
                'csrfToken': csrf_token,
                'username': self.username,
                'password': self.password,
                'remember': '1',
                'source': '',
            }
            
            post_url = f"{self.base_url}/index.php/{self.contexto}/login/signIn"
            resp = self.session.post(post_url, data=data, timeout=30)
            
            # Verificar login exitoso de múltiples formas
            if any(x in resp.text for x in ['Cerrar sesión', 'submissionId=', 'Logout', 'Sign out']):
                logger.info(f"Login exitoso en {self.base_url}")
                return True
            else:
                logger.warning(f"Login fallido en {self.base_url}")
                logger.debug(f"Respuesta login: {resp.text[:500]}")
                return False
                
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return False
    
    def navigate_to_step_2(self) -> bool:
        """Navega al paso 2 del wizard de envío"""
        if not self.submission_id:
            return False
        
        step2_url = f"{self.base_url}/index.php/{self.contexto}/submission/wizard/2?submissionId={self.submission_id}#step-2"
        resp = self.session.get(step2_url, timeout=30)
        
        if "step-2" not in resp.url and "submission/wizard" not in resp.url:
            logger.warning(f"No se pudo navegar al paso 2. URL actual: {resp.url}")
            return False
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrfToken'})
        if csrf_input:
            self.csrf_token = csrf_input.get('value', '')
        
        return True
    
    def _prepare_file_for_upload(self, file_path: str, user_id: int) -> Optional[str]:
        """Prepara archivo aplicando camuflaje si es necesario"""
        if self.bitzero_mode == 0:
            return file_path
        
        camouflaged_path = BitZeroEncoder.apply_camouflage(
            file_path, self.bitzero_mode, user_id
        )
        
        if camouflaged_path:
            logger.info(f"Archivo camuflado: {os.path.basename(file_path)} -> {os.path.basename(camouflaged_path)}")
            return camouflaged_path
        
        return file_path
    
    def upload_file(self, file_path: str, original_name: str = None, 
                   user_id: int = None) -> Optional[Dict]:
        """Sube un archivo a la revista"""
        if not os.path.exists(file_path):
            logger.error(f"Archivo no existe: {file_path}")
            return None
        
        if not self.navigate_to_step_2():
            logger.error("No se pudo navegar al paso 2")
            return None
        
        # Preparar archivo
        upload_path = self._prepare_file_for_upload(file_path, user_id or 0)
        if not upload_path:
            upload_path = file_path
        
        file_name = original_name if original_name else os.path.basename(file_path)
        if upload_path != file_path:
            file_name = os.path.basename(upload_path)
        
        # Determinar content-type
        content_type = self._content_type(file_name)
        
        # Leer archivo
        try:
            with open(upload_path, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}")
            return None
        
        # Configurar headers
        headers = {
            'X-Csrf-Token': self.csrf_token,
            'Referer': f"{self.base_url}/index.php/{self.contexto}/submission/wizard/2?submissionId={self.submission_id}",
        }
        
        # Preparar datos para upload
        files = {'file': (file_name, file_content, content_type)}
        data = {
            'name[es_ES]': file_name,
            'fileStage': '2',
            'csrfToken': self.csrf_token
        }
        
        # URL de la API
        api_url = f"{self.base_url}/index.php/{self.contexto}/api/v1/submissions/{self.submission_id}/files"
        
        try:
            resp = self.session.post(api_url, files=files, data=data, headers=headers, timeout=60)
            
            if resp.status_code == 200:
                result = resp.json()
                if result.get('id'):
                    file_id = result.get("id")
                    
                    download_url = f"{self.base_url}/$$$call$$$/api/file/file-api/download-file?submissionFileId={file_id}&submissionId={self.submission_id}&stageId=1"
                    
                    file_info = {
                        "id": file_id,
                        "name": result.get("name", {}).get("es_ES", file_name) if isinstance(result.get("name"), dict) else result.get("name", file_name),
                        "url": download_url,
                        "size": os.path.getsize(upload_path),
                        "original_name": original_name or os.path.basename(file_path)
                    }
                    
                    self.uploaded_files.append(file_info)
                    logger.info(f"Archivo subido exitosamente: {file_name} (ID: {file_id})")
                    
                    # Limpiar archivo camuflado temporal
                    if upload_path != file_path and os.path.exists(upload_path):
                        try:
                            os.remove(upload_path)
                        except:
                            pass
                    
                    return file_info
                else:
                    logger.warning(f"Respuesta JSON no contiene ID: {result}")
            else:
                logger.warning(f"Error en upload: {resp.status_code} - {resp.text[:200]}")
            return None
            
        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            return None
    
    def upload_chunked_file(self, file_path: str, user_id: int) -> List[Dict]:
        """Sube un archivo dividido en chunks"""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        if file_size <= self.chunk_size:
            result = self.upload_file(file_path, user_id=user_id)
            return [result] if result else []
        
        # Dividir archivo en chunks
        chunks = self._split_file(file_path)
        uploaded_chunks = []
        
        for idx, chunk_info in enumerate(chunks, 1):
            chunk_path = chunk_info['path']
            chunk_name = f"{file_name}.part{idx:03d}"
            
            result = self.upload_file(chunk_path, chunk_name, user_id)
            if result:
                uploaded_chunks.append(result)
                logger.info(f"Chunk {idx}/{len(chunks)} subido: {chunk_name}")
            
            # Limpiar chunk temporal
            if os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                except:
                    pass
        
        return uploaded_chunks
    
    def _split_file(self, file_path: str) -> List[Dict]:
        """Divide un archivo en chunks"""
        chunks = []
        file_name = os.path.basename(file_path)
        
        with open(file_path, 'rb') as f:
            chunk_num = 1
            while True:
                chunk_data = f.read(self.chunk_size)
                if not chunk_data:
                    break
                
                chunk_filename = f"{file_name}.part{chunk_num:03d}"
                chunk_path = os.path.join(os.path.dirname(file_path), chunk_filename)
                
                with open(chunk_path, 'wb') as chunk_file:
                    chunk_file.write(chunk_data)
                
                chunks.append({
                    'path': chunk_path,
                    'name': chunk_filename,
                    'size': len(chunk_data),
                    'number': chunk_num
                })
                
                chunk_num += 1
        
        return chunks
    
    def _content_type(self, filename: str) -> str:
        """Determina el content-type del archivo"""
        name = filename.lower()
        extensions = {
            '.pdf': 'application/pdf',
            '.zip': 'application/zip',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.html': 'text/html',
            '.txt': 'text/plain',
            '.7z': 'application/x-7z-compressed',
            '.rar': 'application/x-rar-compressed'
        }
        
        for ext, content_type in extensions.items():
            if name.endswith(ext):
                return content_type
        
        return 'application/octet-stream'
    
    def generate_bitzero_url(self, original_name: str, file_size: int) -> str:
        """Genera URL ofuscada BitZero para los archivos subidos"""
        if not self.uploaded_files:
            return ""
        
        file_ids = [str(f['id']) for f in self.uploaded_files]
        
        return URLGenerator.generate_bitzero_url(
            host=self.base_url,
            user=self.username,
            password=self.password,
            repo=self.submission_id,
            contexto=self.contexto,
            file_ids=file_ids,
            bitzero_mode=self.bitzero_mode,
            original_name=original_name,
            file_size=file_size
        )
    
    def get_upload_summary(self) -> Dict:
        """Obtiene resumen de la subida"""
        total_size = sum(f['size'] for f in self.uploaded_files)
        
        return {
            'total_files': len(self.uploaded_files),
            'total_size': total_size,
            'file_ids': [f['id'] for f in self.uploaded_files],
            'original_names': [f.get('original_name', '') for f in self.uploaded_files]
        }

# =========================
# INICIALIZAR BOT
# =========================
app = Client("revista_bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)

# Variables globales
active_uploads = {}

# =========================
# FUNCIONES AUXILIARES
# =========================
def format_size(size_bytes: int) -> str:
    """Formatea el tamaño del archivo de manera legible"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

# =========================
# DECORADOR PARA VERIFICAR USUARIOS
# =========================
def authorized_only(func):
    """Decorador para verificar si el usuario está autorizado"""
    async def wrapper(client, message):
        user_id = message.from_user.id
        
        if not user_manager.is_authorized(user_id):
            await message.reply(
                "❌ **Acceso Denegado**\n\n"
                "No tienes permisos para usar este bot.\n"
                "Contacta al administrador para solicitar acceso.\n\n"
                f"📋 **Tu ID:** `{user_id}`\n"
                f"👨‍💻 **Soporte:** @Pro_Slayerr"
            )
            return
        
        return await func(client, message)
    
    return wrapper

# =========================
# FUNCIÓN DE DESCARGA MEJORADA
# =========================
async def download_file_enhanced(client, message, media_type, media_obj, file_path, status_msg):
    """Función mejorada para descargar archivos de cualquier tipo"""
    try:
        # Configurar parámetros específicos según el tipo de archivo
        download_params = {
            'file_name': file_path,
            'block': True,
            'progress': None  # Desactivamos progreso interno para manejar manualmente
        }
        
        # Para archivos grandes, usar descarga directa sin progreso
        file_size = 0
        if hasattr(media_obj, 'file_size'):
            file_size = media_obj.file_size or 0
        
        start_time = time.time()
        downloaded_bytes = 0
        
        # Función de progreso personalizada
        async def progress_callback(current, total):
            nonlocal downloaded_bytes
            downloaded_bytes = current
            
            if total == 0:
                return
                
            now = time.time()
            elapsed = now - start_time
            
            # Actualizar cada 3 segundos o al completar
            if elapsed > 0 and (current == total or int(elapsed) % 3 == 0):
                percent = (current / total) * 100
                speed = current / elapsed if elapsed > 0 else 0
                
                # Crear barra de progreso
                bar_length = 20
                filled = int(bar_length * percent / 100)
                bar = "█" * filled + "▁" * (bar_length - filled)
                
                # Calcular tiempo restante
                if current > 0 and speed > 0:
                    remaining = (total - current) / speed
                    if remaining < 60:
                        remaining_str = f"{remaining:.0f}s"
                    elif remaining < 3600:
                        remaining_str = f"{remaining/60:.1f}m"
                    else:
                        remaining_str = f"{remaining/3600:.1f}h"
                else:
                    remaining_str = "--"
                
                try:
                    await status_msg.edit_text(
                        f"📥 **Descargando...**\n\n"
                        f"📄 **Archivo:** `{os.path.basename(file_path)}`\n"
                        f"📊 **Progreso:** [{bar}] {percent:.1f}%\n"
                        f"💾 **Descargado:** {current/1024/1024:.2f} MB / {total/1024/1024:.2f} MB\n"
                        f"⚡ **Velocidad:** {speed/1024/1024:.2f} MB/s\n"
                        f"⏱️ **Tiempo restante:** {remaining_str}"
                    )
                except:
                    pass  # Ignorar errores de edición
        
        # MÉTODO 1: Usar download_media con timeout extendido
        try:
            logger.info(f"Método 1: Descargando {media_type} a {file_path}")
            
            # Para archivos grandes, usar descarga sin callback de progreso
            if file_size > 50 * 1024 * 1024:  # Más de 50MB
                await client.download_media(
                    message=message,
                    file_name=file_path,
                    block=True
                )
            else:
                await client.download_media(
                    message=message,
                    file_name=file_path,
                    progress=progress_callback,
                    block=True
                )
            
            # Verificar descarga
            if os.path.exists(file_path):
                actual_size = os.path.getsize(file_path)
                if actual_size > 0:
                    return True, actual_size
                
            # Si llegamos aquí, el archivo está vacío o no existe
            logger.warning(f"Método 1 falló: Archivo vacío o inexistente")
            return False, 0
            
        except Exception as e1:
            logger.warning(f"Método 1 falló: {str(e1)[:100]}")
            
            # MÉTODO 2: Descarga manual usando get_file
            try:
                logger.info("Intentando Método 2: Descarga manual")
                
                # Obtener file_id del objeto multimedia
                if hasattr(media_obj, 'file_id'):
                    file_id = media_obj.file_id
                else:
                    # Para fotos, obtener el file_id de la foto de mayor calidad
                    if media_type == 'photo' and message.photo:
                        file_id = message.photo[-1].file_id
                    else:
                        return False, 0
                
                # Obtener información del archivo
                file_info = await client.get_file(file_id)
                if not file_info or not hasattr(file_info, 'file_path'):
                    return False, 0
                
                # Crear directorio si no existe
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Descargar usando download_file
                await client.download_file(
                    file_info.file_path,
                    file_path
                )
                
                # Verificar descarga
                if os.path.exists(file_path):
                    actual_size = os.path.getsize(file_path)
                    if actual_size > 0:
                        return True, actual_size
                
                return False, 0
                
            except Exception as e2:
                logger.error(f"Método 2 falló: {str(e2)[:100]}")
                return False, 0
                
    except Exception as e:
        logger.error(f"Error en download_file_enhanced: {e}")
        return False, 0

# =========================
# HANDLER PARA DESCARGAR ARCHIVOS
# =========================
@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
@authorized_only
async def handle_file_download(client, message):
    """Guarda archivos recibidos en el directorio raíz"""
    try:
        user_id = message.from_user.id
        user_dir = config.ROOT_DIR  # Guardamos directamente en raíz, no en subdirectorio
        
        # Crear directorio si no existe
        os.makedirs(user_dir, exist_ok=True)
        
        # Determinar tipo de archivo y nombre
        if message.document:
            file_obj = message.document
            # Usar el nombre real del archivo o generar uno
            if message.document.file_name:
                file_name = message.document.file_name
            else:
                # Detectar tipo por mime type para APKs y otros
                mime_type = message.document.mime_type or ""
                if "apk" in mime_type or message.document.file_name and message.document.file_name.endswith('.apk'):
                    file_name = f"app_{message.document.file_id}.apk"
                elif "zip" in mime_type:
                    file_name = f"archive_{message.document.file_id}.zip"
                elif "pdf" in mime_type:
                    file_name = f"document_{message.document.file_id}.pdf"
                else:
                    file_name = f"file_{message.document.file_id}.bin"
                    
        elif message.video:
            file_obj = message.video
            file_name = message.video.file_name or f"video_{message.video.file_id}.mp4"
        elif message.audio:
            file_obj = message.audio
            file_name = message.audio.file_name or f"audio_{message.audio.file_id}.mp3"
        elif message.photo:
            file_obj = message.photo[-1]  # Foto de mayor calidad
            file_name = f"photo_{message.photo.file_id}.jpg"
        else:
            return
        
        # Limpiar nombre de caracteres inválidos
        file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
        
        # Ruta completa del archivo
        file_path = os.path.join(user_dir, file_name)
        
        # Si ya existe, agregar número
        counter = 1
        original_name, ext = os.path.splitext(file_name)
        while os.path.exists(file_path):
            file_name = f"{original_name}_{counter}{ext}"
            file_path = os.path.join(user_dir, file_name)
            counter += 1
        
        # Obtener tamaño del archivo
        file_size = 0
        if hasattr(file_obj, 'file_size'):
            file_size = file_obj.file_size or 0
        
        # Mensaje de estado inicial
        status_msg = await message.reply(f"📥 **Descargando...**\n\n`{file_name}`\n\n📦 Tamaño: {file_size/1024/1024:.2f} MB\n\n⏳ Preparando...")
        
        # Variable para el progreso
        last_update = time.time()
        
        # Función de callback para el progreso
        async def progress_callback(current, total):
            nonlocal last_update
            now = time.time()
            
            # Actualizar cada 2 segundos o cuando haya cambios significativos
            if now - last_update >= 2 or current == total:
                try:
                    percent = current * 100 / total if total > 0 else 0
                    
                    # Crear barra de progreso visual
                    bar_length = 20
                    filled = int(bar_length * percent / 100)
                    bar = "█" * filled + "▁" * (bar_length - filled)
                    
                    # Calcular velocidad
                    elapsed = now - status_msg.date.timestamp() if hasattr(status_msg, 'date') and status_msg.date else now - time.time() + 2
                    speed = (current / 1024 / 1024) / (elapsed + 0.001)
                    
                    # Calcular tiempo restante
                    if current > 0 and speed > 0:
                        remaining = (total - current) / (current / elapsed)
                        if remaining < 60:
                            remaining_str = f"{remaining:.0f}s"
                        elif remaining < 3600:
                            remaining_str = f"{remaining/60:.1f}m"
                        else:
                            remaining_str = f"{remaining/3600:.1f}h"
                    else:
                        remaining_str = "--"
                    
                    await status_msg.edit_text(
                        f"📥 **Descargando...**\n\n"
                        f"📄 **Archivo:** `{file_name}`\n"
                        f"📊 **Progreso:** [{bar}] {percent:.1f}%\n"
                        f"💾 **Descargado:** {current/1024/1024:.2f} MB / {total/1024/1024:.2f} MB\n"
                        f"⚡ **Velocidad:** {speed:.2f} MB/s\n"
                        f"⏱️ **Tiempo restante:** {remaining_str}\n\n"
                        f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
                    )
                    last_update = now
                except Exception as e:
                    logger.debug(f"Error actualizando progreso: {e}")
        
        # Descargar el archivo
        try:
            await client.download_media(
                message=message,
                file_name=file_path,
                progress=progress_callback
            )
            
            # Verificar que se descargó correctamente
            if os.path.exists(file_path):
                actual_size = os.path.getsize(file_path)
                
                # Mensaje final
                elapsed = time.time() - status_msg.date.timestamp() if hasattr(status_msg, 'date') and status_msg.date else 0
                avg_speed = actual_size / elapsed / 1024 / 1024 if elapsed > 0 else 0
                
                # Determinar icono según tipo de archivo
                icon = "📄"
                if file_name.lower().endswith(('.apk', '.exe', '.msi')):
                    icon = "📱"
                elif file_name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    icon = "🎬"
                elif file_name.lower().endswith(('.mp3', '.wav', '.flac')):
                    icon = "🎵"
                elif file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    icon = "🖼️"
                elif file_name.lower().endswith(('.zip', '.rar', '.7z', '.tar')):
                    icon = "📦"
                
                await status_msg.edit_text(
                    f"{icon} **¡Descarga completada!**\n\n"
                    f"📄 **Archivo:** `{file_name}`\n"
                    f"📦 **Tamaño:** {actual_size/1024/1024:.2f} MB\n"
                    f"⚡ **Velocidad promedio:** {avg_speed:.2f} MB/s\n"
                    f"⏱️ **Tiempo total:** {elapsed:.1f}s\n"
                    f"📁 **Guardado en:** `{config.ROOT_DIR}`\n\n"
                    f"✅ **Listo para subir a revistas**\n"
                    f"Usa `/ls` para ver todos los archivos\n"
                    f"Usa `/up` para subir a una revista\n\n"
                    f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
                )
                
                logger.info(f"✅ Archivo descargado: {file_path} ({actual_size} bytes)")
            else:
                await status_msg.edit_text(
                    f"❌ **Error en la descarga**\n\n"
                    f"No se pudo guardar el archivo `{file_name}`.\n"
                    f"Intenta nuevamente o verifica el espacio disponible."
                )
                
        except Exception as download_error:
            logger.error(f"Error descargando archivo: {download_error}")
            
            # Limpiar archivo parcial si existe
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            
            await status_msg.edit_text(
                f"❌ **Error en la descarga**\n\n"
                f"Archivo: `{file_name}`\n"
                f"Error: {str(download_error)[:100]}\n\n"
                f"⚠️ **Posibles causas:**\n"
                f"• Archivo demasiado grande\n"
                f"• Problemas de conexión\n"
                f"• Tiempo de espera agotado\n\n"
                f"👨‍💻 **Soporte:** @Pro_Slayerr"
            )
    
    except Exception as e:
        logger.error(f"Error en handle_file_download: {e}", exc_info=True)
        try:
            await message.reply(f"❌ **Error procesando archivo:** {str(e)[:100]}")
        except:
            pass 
            
# =========================
# HANDLERS DE COMANDOS
# =========================

# Comando /start
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = message.from_user.id
    
    if user_manager.is_authorized(user_id):
        rev_list = "\n".join([f"  • **{key}**: {data['nombre']} (BitZero: {data.get('bitzero', 0)})" 
                             for key, data in config.REVISTAS.items()])
        
        await message.reply(
            f"👋 **Bienvenido, {message.from_user.first_name}!**\n\n"
            "✅ **Estás autorizado para usar este bot.**\n\n"
            f"📚 **Revistas Disponibles:**\n{rev_list}\n\n"
            "🔧 **Comandos Disponibles:**\n"
            "• `/ls` - Ver archivos locales\n"
            "• `/rm <num>` - Eliminar archivo local\n"
            "• `/deleteall` - Limpiar todos los archivos\n"
            "• `/up` - Subir archivos a revista\n"
            "• `/clear_rev` - Limpiar archivos de revista\n"
            "• `/zips <tamaño>` - Cambiar tamaño de partes\n"
            "• `/status` - Ver estado del sistema\n\n"
            f"💾 **Directorio:** `{config.ROOT_DIR}`\n"
            f"📦 **Tamaño partes:** {config.CHUNK_SIZE_MB} MB\n\n"
            f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
        )
    else:
        await message.reply(
            "🔒 **Bot Privado**\n\n"
            "Este bot es de uso restringido.\n"
            "Para solicitar acceso, contacta al administrador:\n\n"
            f"👨‍💻 @Pro_Slayerr\n\n"
            f"📋 **Tu ID:** `{user_id}`"
        )

# Comando /ls
@app.on_message(filters.command("ls"))
@authorized_only
async def list_files(client, message):
    """Lista archivos en el directorio raíz"""
    try:
        if not os.path.exists(config.ROOT_DIR):
            os.makedirs(config.ROOT_DIR, exist_ok=True)
            await message.reply(
                f"📁 **Directorio creado:** `{config.ROOT_DIR}`\n"
                f"El directorio estaba vacío."
            )
            return
        
        files = []
        total_size = 0
        
        for item in os.listdir(config.ROOT_DIR):
            item_path = os.path.join(config.ROOT_DIR, item)
            if os.path.isfile(item_path):
                file_size = os.path.getsize(item_path)
                files.append({
                    'name': item,
                    'path': item_path,
                    'size': file_size,
                    'modified': os.path.getmtime(item_path)
                })
                total_size += file_size
        
        if not files:
            await message.reply(
                f"📭 **Directorio vacío**\n\n"
                f"📁 **Directorio:** `{config.ROOT_DIR}`\n"
                f"Envía archivos para que aparezcan aquí."
            )
            return
        
        # Ordenar archivos por fecha de modificación
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        # Crear lista formateada
        file_list = f"📂 **Archivos en `{config.ROOT_DIR}`**\n\n"
        file_list += f"📊 **Total:** {len(files)} archivos | {total_size/1024/1024:.2f} MB\n\n"
        
        for i, file_info in enumerate(files[:20], 1):
            size_str = format_size(file_info['size'])
            mod_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(file_info['modified']))
            file_list += f"{i}. **{file_info['name']}**\n"
            file_list += f"   📏 {size_str} | 📅 {mod_time}\n\n"
        
        if len(files) > 20:
            file_list += f"... y {len(files) - 20} archivos más.\n\n"
        
        file_list += "💡 **Usa `/rm <número>` para eliminar un archivo.**\n"
        file_list += f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
        
        await message.reply(file_list)
        
    except Exception as e:
        logger.error(f"Error en comando /ls: {e}")
        await message.reply(
            f"❌ **Error al listar archivos**\n\n"
            f"No se pudo acceder al directorio.\n"
            f"**Error:** {str(e)[:100]}"
        )

# Comando /rm
@app.on_message(filters.command("rm"))
@authorized_only
async def remove_file(client, message):
    """Elimina un archivo local"""
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply("❌ **Uso:** `/rm <número>`")
            return
        
        idx = int(parts[1]) - 1
        
        # Listar archivos
        files = []
        for item in os.listdir(config.ROOT_DIR):
            item_path = os.path.join(config.ROOT_DIR, item)
            if os.path.isfile(item_path):
                files.append(item_path)
        
        files.sort()
        
        if 0 <= idx < len(files):
            target = files[idx]
            file_name = os.path.basename(target)
            os.remove(target)
            await message.reply(f"✅ **Eliminado:** `{file_name}`")
        else:
            await message.reply(f"❌ **Índice inválido.** Usa números del 1 al {len(files)}")
            
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

# Comando /deleteall
@app.on_message(filters.command("deleteall"))
@authorized_only
async def delete_all(client, message):
    """Elimina todos los archivos locales"""
    try:
        if os.path.exists(config.ROOT_DIR):
            # Eliminar todos los archivos pero mantener el directorio
            for item in os.listdir(config.ROOT_DIR):
                item_path = os.path.join(config.ROOT_DIR, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path) and not item.startswith('.'):
                    shutil.rmtree(item_path)
        
        await message.reply("✅ **Todos los archivos han sido eliminados.**")
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

# Comando /zips
@app.on_message(filters.command("zips"))
@authorized_only
async def set_zip_size(client, message):
    """Cambia el tamaño de las partes"""
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply("❌ **Uso:** `/zips <tamaño_MB>`")
            return
        
        new_size = int(parts[1])
        if not 1 <= new_size <= 100:
            await message.reply("❌ **El tamaño debe estar entre 1 y 100 MB.**")
            return
        
        config.CHUNK_SIZE_MB = new_size
        await message.reply(f"✅ **Tamaño de partes cambiado a {new_size} MB.**")
        
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

# Comando /status
@app.on_message(filters.command("status"))
@authorized_only
async def status_handler(client, message):
    """Muestra estado del sistema"""
    user_id = message.from_user.id
    
    # Calcular uso de disco
    total_size = 0
    file_count = 0
    if os.path.exists(config.ROOT_DIR):
        for item in os.listdir(config.ROOT_DIR):
            item_path = os.path.join(config.ROOT_DIR, item)
            if os.path.isfile(item_path):
                total_size += os.path.getsize(item_path)
                file_count += 1
    
    # Información de usuarios
    users = user_manager.get_all_users()
    active_users = [u for u in users if u.get('active', True)]
    
    status_text = "📊 **Estado del Sistema**\n\n"
    status_text += f"👥 **Usuarios:** {len(active_users)}/{len(users)} activos\n"
    status_text += f"📁 **Archivos locales:** {file_count}\n"
    status_text += f"💾 **Espacio usado:** {total_size / 1024 / 1024:.2f} MB\n"
    status_text += f"📦 **Tamaño partes:** {config.CHUNK_SIZE_MB} MB\n"
    status_text += f"📚 **Revistas configuradas:** {len(config.REVISTAS)}\n\n"
    
    # Información de revistas
    status_text += "🔧 **Configuración Revistas:**\n"
    for rev_id, rev_data in config.REVISTAS.items():
        bitzero_status = "✅" if rev_data.get('bitzero', 0) > 0 else "❌"
        status_text += f"  • {rev_data['nombre']}: BitZero {bitzero_status}\n"
    
    status_text += f"\n🕐 **Hora servidor:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    status_text += f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
    
    await message.reply(status_text)

# Comando /up
@app.on_message(filters.command("up"))
@authorized_only
async def upload_handler(client, message):
    """Muestra menú para seleccionar revista y subir archivos"""
    
    # Verificar archivos disponibles
    available_files = []
    if os.path.exists(config.ROOT_DIR):
        for item in os.listdir(config.ROOT_DIR):
            item_path = os.path.join(config.ROOT_DIR, item)
            if os.path.isfile(item_path):
                # Excluir archivos temporales y de sistema
                if not item.startswith('.') and not item.endswith(('.tmp', '.temp', '.log')):
                    available_files.append(item_path)
    
    if not available_files:
        await message.reply("📭 **No hay archivos para subir.**\n\n"
                          "Envía archivos al bot primero.")
        return
    
    # Crear botones para cada revista
    keyboard = []
    for rev_id, rev_data in config.REVISTAS.items():
        bitzero_status = "✅" if rev_data.get('bitzero', 0) > 0 else "❌"
        keyboard.append([
            InlineKeyboardButton(
                f"{bitzero_status} {rev_data['nombre']}",
                callback_data=f"upload_select_{rev_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_action")])
    
    await message.reply(
        f"📦 **Selecciona Revista Destino**\n\n"
        f"📂 **Archivos listos:** {len(available_files)}\n"
        f"💾 **Tamaño partes:** {config.CHUNK_SIZE_MB} MB\n\n"
        "✅ = BitZero activado\n"
        "❌ = BitZero desactivado\n\n"
        "👇 **Elige una revista:**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# CALLBACK HANDLER
# =========================
@app.on_callback_query()
async def handle_callback(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if not user_manager.is_authorized(user_id):
        await callback_query.answer("❌ No autorizado", show_alert=True)
        return
    
    if data.startswith("upload_select_"):
        revista_id = data.replace("upload_select_", "")
        
        if revista_id not in config.REVISTAS:
            await callback_query.answer("❌ Revista no encontrada", show_alert=True)
            return
        
        revista = config.REVISTAS[revista_id]
        
        # Crear uploader
        uploader = RevistaUploader(
            username=revista['username'],
            password=revista['password'],
            submission_id=revista['submission_id'],
            base_url=revista['base_url'],
            contexto=revista['contexto'],
            bitzero_mode=revista.get('bitzero', 0),
            encryption_key=revista.get('encryption_key')
        )
        
        await callback_query.answer(f"Iniciando subida a {revista['nombre']}...")
        await callback_query.message.edit_text(
            f"🚀 **Iniciando Subida**\n\n"
            f"📚 **Revista:** {revista['nombre']}\n"
            f"🔐 **BitZero:** {'Activado' if revista.get('bitzero', 0) > 0 else 'Desactivado'}\n"
            f"⏳ Conectando..."
        )
        
        # Realizar subida
        await perform_upload_with_bitzero(client, callback_query.message, uploader, revista, user_id)
        
    elif data == "cancel_action":
        await callback_query.message.edit_text("❌ **Operación cancelada.**")
        await callback_query.answer()

# =========================
# FUNCIÓN DE SUBIDA CON BITZERO
# =========================
async def perform_upload_with_bitzero(client, message, uploader, revista, user_id):
    """Realiza el proceso completo de subida con BitZero"""
    
    # Paso 1: Login
    status_msg = await message.edit_text(
        f"🔐 **Iniciando Sesión**\n\n"
        f"📚 {revista['nombre']}\n"
        f"👤 {uploader.username}\n"
        f"⏳ Conectando al servidor..."
    )
    
    if not uploader.login():
        await status_msg.edit_text(
            f"❌ **Error de Conexión**\n\n"
            f"No se pudo conectar a {revista['nombre']}.\n"
            f"Verifica las credenciales y conexión."
        )
        return
    
    await status_msg.edit_text(
        f"✅ **Conexión Exitosa**\n\n"
        f"📋 **Submission ID:** {uploader.submission_id}\n"
        f"🔐 **BitZero:** {'✅ Activado' if uploader.bitzero_mode > 0 else '❌ Desactivado'}\n"
        f"⏳ Preparando archivos..."
    )
    
    # Paso 2: Obtener archivos
    files_to_upload = []
    if os.path.exists(config.ROOT_DIR):
        for item in os.listdir(config.ROOT_DIR):
            item_path = os.path.join(config.ROOT_DIR, item)
            if os.path.isfile(item_path):
                # Excluir archivos temporales y de sistema
                if not item.startswith('.') and not item.endswith(('.tmp', '.temp', '.log')):
                    files_to_upload.append(item_path)
    
    if not files_to_upload:
        await status_msg.edit_text("📭 **No hay archivos para subir.**")
        return
    
    total_files = len(files_to_upload)
    uploaded_count = 0
    all_uploaded_files = []
    
    # Paso 3: Subir cada archivo
    for idx, file_path in enumerate(files_to_upload, 1):
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        await status_msg.edit_text(
            f"📤 **Subiendo Archivo**\n\n"
            f"📂 **Progreso:** {idx}/{total_files}\n"
            f"📄 **Archivo:** {file_name}\n"
            f"💾 **Tamaño:** {file_size / 1024 / 1024:.2f} MB\n"
            f"🔐 **BitZero:** {'✅' if uploader.bitzero_mode > 0 else '❌'}\n"
            f"⏳ Procesando..."
        )
        
        # Subir archivo (con chunks si es necesario)
        if file_size > uploader.chunk_size:
            uploaded_files = uploader.upload_chunked_file(file_path, user_id)
        else:
            result = uploader.upload_file(file_path, user_id=user_id)
            uploaded_files = [result] if result else []
        
        if uploaded_files:
            uploaded_count += 1
            all_uploaded_files.extend(uploaded_files)
            
            await status_msg.edit_text(
                f"✅ **Archivo Subido**\n\n"
                f"📂 **Progreso:** {idx}/{total_files}\n"
                f"📄 **Archivo:** {file_name}\n"
                f"🔗 **Partes:** {len(uploaded_files)}\n"
                f"⏳ Continuando..."
            )
        else:
            await status_msg.edit_text(
                f"⚠️ **Error Subiendo**\n\n"
                f"📄 **Archivo:** {file_name}\n"
                f"❌ No se pudo subir este archivo.\n"
                f"⏳ Continuando con el siguiente..."
            )
        
        await asyncio.sleep(1)
    
    # Paso 4: Generar resultados
    if not all_uploaded_files:
        await status_msg.edit_text(
            f"❌ **Subida Fallida**\n\n"
            f"No se pudo subir ningún archivo.\n"
            f"Verifica permisos y conexión."
        )
        return
    
    # Generar URL BitZero si está activado
    bitzero_url = ""
    if uploader.bitzero_mode > 0 and all_uploaded_files and files_to_upload:
        original_name = os.path.basename(files_to_upload[0])
        total_size = sum(f['size'] for f in all_uploaded_files)
        
        bitzero_url = uploader.generate_bitzero_url(
            original_name=original_name,
            file_size=total_size
        )
    
    # Generar URLs directas
    direct_urls = []
    for file_info in all_uploaded_files:
        direct_urls.append(file_info['url'])
    
    # Paso 5: Mostrar resultados
    result_text = f"✅ **Subida Completada**\n\n"
    result_text += f"📚 **Revista:** {revista['nombre']}\n"
    result_text += f"📦 **Archivos procesados:** {uploaded_count}/{total_files}\n"
    result_text += f"🔗 **Partes subidas:** {len(all_uploaded_files)}\n"
    result_text += f"🔐 **BitZero:** {'✅ Activado' if uploader.bitzero_mode > 0 else '❌ Desactivado'}\n\n"
    
    if bitzero_url:
        result_text += f"🔗 **URL BitZero (ofuscada):**\n`{bitzero_url}`\n\n"
        result_text += "📥 **Para descargar usa:**\n"
        result_text += "```bash\npython3 bitzero.py \"URL\"\n```\n"
    
    if direct_urls:
        result_text += f"🔗 **URLs Directas ({len(direct_urls)}):**\n"
        for i, url in enumerate(direct_urls[:5], 1):
            result_text += f"{i}. `{url}`\n"
        
        if len(direct_urls) > 5:
            result_text += f"... y {len(direct_urls) - 5} más\n"
    
    result_text += f"\n👨‍💻 **Desarrollador:** @Pro_Slayerr"
    
    await status_msg.edit_text(result_text)
    
    # Enviar URLs largas en archivo si es necesario
    if len(direct_urls) > 10:
        urls_file = f"urls_{int(time.time())}.txt"
        with open(urls_file, 'w', encoding='utf-8') as f:
            for url in direct_urls:
                f.write(url + "\n")
        
        await client.send_document(
            chat_id=message.chat.id,
            document=urls_file,
            caption=f"📋 URLs completas ({len(direct_urls)} en total)"
        )
        
        os.remove(urls_file)

# =========================
# COMANDOS DE ADMINISTRADOR
# =========================

# Comando /adduser
@app.on_message(filters.command("adduser"))
async def add_user_admin(client, message):
    """Añade un usuario autorizado (solo admin)"""
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("❌ **Solo el administrador puede usar este comando.**")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply("❌ **Uso:** `/adduser <user_id> [@username]`")
            return
        
        target_id = int(parts[1])
        target_username = parts[2] if len(parts) > 2 else None
        
        if user_manager.add_user(target_id, target_username, message.from_user.id):
            await message.reply(
                f"✅ **Usuario añadido exitosamente.**\n\n"
                f"👤 **ID:** `{target_id}`\n"
                f"📛 **Usuario:** @{target_username if target_username else 'N/A'}\n"
                f"📅 **Fecha:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            await message.reply(f"❌ **El usuario `{target_id}` ya está autorizado.**")
            
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

# Comando /removeuser
@app.on_message(filters.command("removeuser"))
async def remove_user_admin(client, message):
    """Elimina un usuario autorizado (solo admin)"""
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("❌ **Solo el administrador puede usar este comando.**")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply("❌ **Uso:** `/removeuser <user_id>`")
            return
        
        target_id = int(parts[1])
        
        if user_manager.remove_user(target_id):
            await message.reply(f"✅ **Usuario `{target_id}` eliminado.**")
        else:
            await message.reply(f"❌ **El usuario `{target_id}` no existe.**")
            
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

# Comando /listusers
@app.on_message(filters.command("listusers"))
async def list_users_admin(client, message):
    """Lista todos los usuarios autorizados (solo admin)"""
    if message.from_user.id != config.ADMIN_ID:
        await message.reply("❌ **Solo el administrador puede usar este comando.**")
        return
    
    users = user_manager.get_all_users()
    
    if not users:
        await message.reply("📭 **No hay usuarios autorizados.**")
        return
    
    user_list = ""
    for i, user in enumerate(users, 1):
        status = "✅" if user.get('active', True) else "❌"
        user_list += (
            f"{i}. **ID:** `{user['id']}`\n"
            f"   **Usuario:** @{user.get('username', 'N/A')}\n"
            f"   **Estado:** {status}\n"
            f"   **Agregado:** {user.get('added_date', 'N/A')}\n\n"
        )
    
    await message.reply(f"👥 **Usuarios Autorizados ({len(users)}):**\n\n{user_list}")

# =========================
# INICIALIZACIÓN DEL BOT
# =========================
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🚀 Iniciando Bot de Revistas con BitZero")
    
    # Inicializar directorios
    if not initialize_directories():
        logger.error("✗ No se pudieron inicializar los directorios. Saliendo...")
        sys.exit(1)
    
    logger.info(f"📚 Revistas configuradas: {len(config.REVISTAS)}")
    logger.info(f"💾 Tamaño de partes: {config.CHUNK_SIZE_MB} MB")
    logger.info(f"👑 Administrador: {config.ADMIN_ID}")
    logger.info(f"📁 Directorio raíz: {config.ROOT_DIR}")
    logger.info("=" * 50)
    
    # Mostrar información de revistas
    for rev_id, rev_data in config.REVISTAS.items():
        bitzero_status = "Activado" if rev_data.get('bitzero', 0) > 0 else "Desactivado"
        logger.info(f"   • {rev_data['nombre']}: BitZero {bitzero_status}")
    
    logger.info("✅ Bot listo. Esperando comandos...")
    
    app.run()