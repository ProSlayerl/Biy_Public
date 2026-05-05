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
# CONFIGURACIÓN SEGURA CON PERSISTENCIA Y MÚLTIPLES ADMINS
# =========================
class Config:
    def __init__(self):
        # Variables de entorno básicas
        self.API_ID = int(os.getenv("API_ID", 25512912))
        self.API_HASH = os.getenv("API_HASH", "cfe0fcd0f5b048c1586fb6485a9e9750")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "8551744239:AAG2J_gpBldPcZgLJP4DBKBh7_ctgGGUZ6o")
        
        # Múltiples administradores (separados por coma)
        admin_ids_str = os.getenv("ADMIN_ID", "1461573114")
        self.ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
        
        # Archivo de configuración de revistas (persistente)
        self.REVISTAS_CONFIG_FILE = "revistas_config.json"
        self.REVISTAS = self._load_revistas_config()
        
        # Configuración general
        self.ROOT_DIR = os.getenv("ROOT_DIR", "raiz")
        self.CHUNK_SIZE_MB = int(os.getenv("CHUNK_SIZE_MB", 5))
        self.AUTHORIZED_USERS_FILE = "authorized_users.json"
        self.BITZERO_SIGNATURE = os.getenv("BITZERO_SIG", "@bitzero#2024")
        
        # Configuración de descargas mejorada
        self.DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", 600))
        self.MAX_DOWNLOAD_ATTEMPTS = int(os.getenv("MAX_DOWNLOAD_ATTEMPTS", 5))
        self.DOWNLOAD_CHUNK_SIZE = int(os.getenv("DOWNLOAD_CHUNK_SIZE", 32768))
        
        # Crear directorio raíz si no existe
        os.makedirs(self.ROOT_DIR, exist_ok=True)

    def _load_revistas_config(self) -> Dict:
        """Carga configuración de revistas desde JSON o variables de entorno"""
        if os.path.exists(self.REVISTAS_CONFIG_FILE):
            try:
                with open(self.REVISTAS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    logger.info("Cargando configuración de revistas desde revistas_config.json")
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando revistas_config.json: {e}")
        
        # Si no existe, crear desde variables de entorno
        logger.info("Creando configuración inicial desde variables de entorno")
        revistas = {
            "KIKI_REV": {
                "username": os.getenv("KIKI_USER", "proslayerrs"),
                "password": os.getenv("KIKI_PASS", "Dairon2005#"),
                "submission_id": os.getenv("KIKI_SUB", "3505"),
                "base_url": "https://revcardiologia.sld.cu",
                "contexto": "revcardiologia",
                "nombre": "Revista Cardiología",
                "bitzero": int(os.getenv("KIKI_BITZERO", 1)),
                "encryption_key": os.getenv("KIKI_KEY", "default_key_1")
            },
            "COMED_REV": {
                "username": os.getenv("COMED_USER", "proslayerrs"),
                "password": os.getenv("COMED_PASS", "Dairon2005#"),
                "submission_id": os.getenv("COMED_SUB", "5577"),
                "base_url": "https://revcocmed.sld.cu",
                "contexto": "cocmed",
                "nombre": "Revista COMED",
                "bitzero": int(os.getenv("COMED_BITZERO", 1)),
                "encryption_key": os.getenv("COMED_KEY", "default_key_2")
            },
            "EMS_REV": {
                "username": os.getenv("EMS_USER", "daironvf"),
                "password": os.getenv("EMS_PASS", "Dairon2005#"),
                "submission_id": os.getenv("EMS_SUB", "5191"),
                "base_url": "https://ems.sld.cu",
                "contexto": "ems",
                "nombre": "Revista EMS",
                "bitzero": int(os.getenv("EMS_BITZERO", 1)),
                "encryption_key": os.getenv("EMS_KEY", "default_key_3")
            }
        }
        self._save_revistas_config(revistas)
        return revistas

    def _save_revistas_config(self, revistas: Dict = None):
        """Guarda la configuración de revistas en JSON"""
        if revistas is None:
            revistas = self.REVISTAS
        try:
            with open(self.REVISTAS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(revistas, f, ensure_ascii=False, indent=2)
            logger.info("Configuración de revistas guardada en revistas_config.json")
        except Exception as e:
            logger.error(f"Error guardando revistas_config.json: {e}")

config = Config()

# =========================
# FUNCIÓN AUXILIAR PARA VERIFICAR ADMIN
# =========================
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

# =========================
# INICIALIZACIÓN DE DIRECTORIOS
# =========================
def initialize_directories():
    """Inicializa todos los directorios necesarios"""
    try:
        os.makedirs(config.ROOT_DIR, exist_ok=True)
        temp_dir = os.path.join(config.ROOT_DIR, "_temp")
        os.makedirs(temp_dir, exist_ok=True)
        logs_dir = os.path.join(config.ROOT_DIR, "_logs")
        os.makedirs(logs_dir, exist_ok=True)
        test_dir = os.path.join(config.ROOT_DIR, "_test_bitzero")
        os.makedirs(test_dir, exist_ok=True)
        
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
# ENCRIPTACIÓN BITZERO - MEJORADA
# =========================
class BitZeroEncoder:
    """Sistema de ofuscación avanzado para archivos"""
    
    PNG_HEADER = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
    
    @staticmethod
    def encode_png(file_path: str, output_path: str) -> bool:
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
    def encode_html(file_path: str, output_path: str, encryption_key: str = None) -> bool:
        try:
            with open(file_path, 'rb') as f:
                original_data = f.read()
            encoded = base64.b64encode(original_data).decode('utf-8')
            
            if encryption_key:
                key_bytes = encryption_key.encode('utf-8')
                encoded_bytes = encoded.encode('utf-8')
                ofuscated = bytearray()
                for i, byte in enumerate(encoded_bytes):
                    ofuscated.append(byte ^ key_bytes[i % len(key_bytes)])
                encoded = base64.b64encode(bytes(ofuscated)).decode('utf-8')
            
            timestamp = int(time.time())
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documento de Datos</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .metadata {{
            background: #e9f7fe;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #2196F3;
        }}
        .data-section {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 Documento de Datos</h1>
        
        <div class="metadata">
            <p><strong>📋 Nombre archivo:</strong> {file_name}</p>
            <p><strong>📊 Tamaño:</strong> {file_size} bytes</p>
            <p><strong>🕐 Timestamp:</strong> {timestamp}</p>
            <p><strong>🔐 Tipo:</strong> BitZero HTML Encoding</p>
        </div>
        
        <div class="data-section" id="data">
            <!-- Datos ofuscados -->
            <div id="encoded-data">{encoded}</div>
            <div id="metadata" data-timestamp="{timestamp}" data-filename="{file_name}" data-size="{file_size}"></div>
        </div>
        
        <div class="content">
            <h2>Información del Documento</h2>
            <p>Este documento contiene datos codificados de forma segura.</p>
            <p>Para extraer los datos originales, use el decodificador BitZero apropiado.</p>
            <p><em>Documento generado automáticamente por el sistema BitZero</em></p>
        </div>
    </div>
    
    <script>
        // Datos de diagnóstico
        console.log("Documento BitZero HTML cargado");
        console.log("Timestamp: {timestamp}");
        console.log("Nombre archivo: {file_name}");
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
    def decode_html(html_path: str, output_path: str, encryption_key: str = None) -> bool:
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            encoded_data_div = soup.find('div', {'id': 'encoded-data'})
            
            if not encoded_data_div:
                for script in soup.find_all('script'):
                    if 'base64' in script.text:
                        import re
                        match = re.search(r'["\']([A-Za-z0-9+/=]+)["\']', script.text)
                        if match:
                            encoded = match.group(1)
                            break
                else:
                    raise ValueError("No se encontraron datos codificados en el HTML")
            else:
                encoded = encoded_data_div.text.strip()
            
            if encryption_key:
                decoded_bytes = base64.b64decode(encoded)
                key_bytes = encryption_key.encode('utf-8')
                restored = bytearray()
                for i, byte in enumerate(decoded_bytes):
                    restored.append(byte ^ key_bytes[i % len(key_bytes)])
                original_data = base64.b64decode(bytes(restored))
            else:
                original_data = base64.b64decode(encoded)
            
            with open(output_path, 'wb') as f:
                f.write(original_data)
            
            logger.info(f"Archivo decodificado desde HTML: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error en decode_html: {e}")
            return False
    
    @staticmethod
    def apply_camouflage(file_path: str, bitzero_mode: int, user_id: int, encryption_key: str = None) -> Optional[str]:
        if bitzero_mode == 0:
            return file_path
        
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1]
        
        if bitzero_mode == 1:
            output_name = f"{file_name}_{user_id}_cache{file_ext}.png"
            output_path = os.path.join(os.path.dirname(file_path), output_name)
            if BitZeroEncoder.encode_png(file_path, output_path):
                return output_path
        
        elif bitzero_mode == 2:
            output_name = f"{file_name}_{user_id}_data{file_ext}.html"
            output_path = os.path.join(os.path.dirname(file_path), output_name)
            if BitZeroEncoder.encode_html(file_path, output_path, encryption_key):
                return output_path
        
        elif bitzero_mode == 3:
            output_name = f"{file_name}_{user_id}_archivo{file_ext}.zip"
            output_path = os.path.join(os.path.dirname(file_path), output_name)
            if BitZeroEncoder.encode_zip(file_path, output_path, encryption_key):
                return output_path
        
        return None
    
    @staticmethod
    def encode_zip(file_path: str, output_path: str, encryption_key: str = None) -> bool:
        try:
            import zipfile
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if encryption_key:
                    zipf.setpassword(encryption_key.encode('utf-8'))
                arcname = f"data_{int(time.time())}.bin"
                zipf.write(file_path, arcname)
            logger.info(f"Archivo codificado como ZIP: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error en encode_zip: {e}")
            return False

# =========================
# GENERADOR DE URLS OFUSCADAS - MEJORADO
# =========================
class URLGenerator:
    """Genera URLs ofuscadas tipo BitZero - MEJORADO"""
    
    @staticmethod
    def encode_key(host: str, user: str, password: str, repo: str, contexto: str, 
                  bitzero_mode: int, timestamp: int = None) -> str:
        if timestamp is None:
            timestamp = int(time.time())
        
        parts = [
            base64.b64encode(host.encode()).decode().replace('=', '#'),
            base64.b64encode(user.encode()).decode().replace('=', '#'),
            base64.b64encode(password.encode()).decode().replace('=', '#'),
            base64.b64encode(repo.encode()).decode().replace('=', '#'),
            base64.b64encode(contexto.encode()).decode().replace('=', '#'),
            base64.b64encode(str(bitzero_mode).encode()).decode().replace('=', '#'),
            base64.b64encode(str(timestamp).encode()).decode().replace('=', '#')
        ]
        return "-".join(parts)
    
    @staticmethod
    def decode_key(encoded_key: str) -> Dict:
        try:
            parts = encoded_key.split("-")
            if len(parts) >= 5:
                decoded = {
                    'host': base64.b64decode(parts[0].replace('#', '=')).decode(),
                    'user': base64.b64decode(parts[1].replace('#', '=')).decode(),
                    'password': base64.b64decode(parts[2].replace('#', '=')).decode(),
                    'repo': base64.b64decode(parts[3].replace('#', '=')).decode(),
                    'contexto': base64.b64decode(parts[4].replace('#', '=')).decode()
                }
                if len(parts) >= 6:
                    decoded['bitzero_mode'] = int(base64.b64decode(parts[5].replace('#', '=')).decode())
                if len(parts) >= 7:
                    decoded['timestamp'] = int(base64.b64decode(parts[6].replace('#', '=')).decode())
                return decoded
            else:
                raise ValueError("Formato de clave inválido")
        except Exception as e:
            logger.error(f"Error decodificando clave: {e}")
            return {}
    
    @staticmethod
    def generate_bitzero_url(host: str, user: str, password: str, repo: str, contexto: str,
                           file_ids: List[str], bitzero_mode: int, 
                           original_name: str, file_size: int, 
                           encryption_key: str = None) -> str:
        token = "-".join(file_ids)
        timestamp = int(time.time())
        key = URLGenerator.encode_key(host, user, password, repo, contexto, bitzero_mode, timestamp)
        safe_name = base64.b64encode(original_name.encode()).decode().replace('=', '_')
        
        verification_hash = ""
        if encryption_key:
            import hashlib
            data_to_hash = f"{original_name}{file_size}{timestamp}{encryption_key}"
            verification_hash = hashlib.md5(data_to_hash.encode()).hexdigest()[:8]
        
        url_parts = [
            f"https://bitzero.techdev.cu",
            f"{file_size}-{repo}",
            token,
            str(bitzero_mode),
            key,
            safe_name
        ]
        
        if verification_hash:
            url_parts.append(verification_hash)
        
        return "/".join(url_parts)
    
    @staticmethod
    def parse_bitzero_url(url: str) -> Optional[Dict]:
        try:
            parts = url.strip().split("/")
            if len(parts) < 6:
                return None
            
            base_url = parts[0] + "//" + parts[2]
            size_repo = parts[3].split("-")
            file_size = int(size_repo[0])
            repo = size_repo[1] if len(size_repo) > 1 else ""
            
            token = parts[4]
            bitzero_mode = int(parts[5])
            encoded_key = parts[6]
            encoded_name = parts[7].replace('_', '=') if len(parts) > 7 else ""
            
            original_name = base64.b64decode(encoded_name).decode() if encoded_name else ""
            key_info = URLGenerator.decode_key(encoded_key)
            
            return {
                'base_url': base_url,
                'file_size': file_size,
                'repo': repo,
                'token': token,
                'bitzero_mode': bitzero_mode,
                'original_name': original_name,
                'key_info': key_info,
                'full_url': url
            }
        except Exception as e:
            logger.error(f"Error parseando URL BitZero: {e}")
            return None

# =========================
# SISTEMA DE USUARIOS AUTORIZADOS
# =========================
class UserManager:
    """Gestor avanzado de usuarios autorizados"""
    
    def __init__(self, users_file: str):
        self.users_file = users_file
        self.users = self._load_users()
    
    def _load_users(self) -> List[Dict]:
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando usuarios: {e}")
                return []
        return []
    
    def _save_users(self) -> bool:
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error guardando usuarios: {e}")
            return False
    
    def is_authorized(self, user_id: int) -> bool:
        if user_id in config.ADMIN_IDS:
            return True
        for user in self.users:
            if user.get('id') == user_id:
                return user.get('active', True)
        return False
    
    def add_user(self, user_id: int, username: str = None, added_by: int = None) -> bool:
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
        original_count = len(self.users)
        self.users = [u for u in self.users if u.get('id') != user_id]
        if len(self.users) < original_count:
            return self._save_users()
        return False
    
    def get_all_users(self) -> List[Dict]:
        return self.users.copy()

user_manager = UserManager(config.AUTHORIZED_USERS_FILE)

# =========================
# CLASE UPLOADER REVISTA (CON BITZERO MEJORADO Y GESTIÓN DE SESIÓN)
# =========================
class RevistaUploader:
    """Uploader mejorado con soporte BitZero completo y gestión de sesión persistente"""
    
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
        self.is_logged_in = False
    
    def login(self) -> bool:
        try:
            login_url = f"{self.base_url}/index.php/{self.contexto}/login"
            resp = self.session.get(login_url, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            csrf_token = None
            csrf_input = soup.find('input', {'name': 'csrfToken'})
            if csrf_input:
                csrf_token = csrf_input.get('value', '')
            
            if not csrf_token:
                for script in soup.find_all('script'):
                    if script.string and 'csrfToken' in script.string:
                        match = re.search(r'csrfToken[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]', script.string)
                        if match:
                            csrf_token = match.group(1)
                            break
            
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
            
            if any(x in resp.text for x in ['Cerrar sesión', 'submissionId=', 'Logout', 'Sign out']):
                logger.info(f"Login exitoso en {self.base_url}")
                self.is_logged_in = True
                return True
            else:
                logger.warning(f"Login fallido en {self.base_url}")
                self.is_logged_in = False
                return False
        except Exception as e:
            logger.error(f"Error en login: {e}")
            self.is_logged_in = False
            return False

    def check_session(self) -> bool:
        try:
            test_url = f"{self.base_url}/index.php/{self.contexto}/submission/wizard/2?submissionId={self.submission_id}"
            resp = self.session.get(test_url, timeout=10, allow_redirects=False)
            if resp.status_code == 302 and 'login' in resp.headers.get('Location', ''):
                return False
            if resp.status_code == 200 and 'submissionId' in resp.text:
                return True
            return False
        except Exception:
            return False

    def ensure_logged_in(self) -> bool:
        if self.is_logged_in and self.check_session():
            return True
        if self.login():
            return True
        return False

    def navigate_to_step_2(self) -> bool:
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
        if self.bitzero_mode == 0:
            return file_path
        
        camouflaged_path = BitZeroEncoder.apply_camouflage(
            file_path, self.bitzero_mode, user_id, self.encryption_key
        )
        
        if camouflaged_path:
            original_size = os.path.getsize(file_path)
            camouflaged_size = os.path.getsize(camouflaged_path)
            ratio = (camouflaged_size / original_size) * 100
            logger.info(
                f"Archivo camuflado: {os.path.basename(file_path)} -> {os.path.basename(camouflaged_path)} "
                f"({original_size/1024:.1f}KB -> {camouflaged_size/1024:.1f}KB, ratio: {ratio:.1f}%)"
            )
            return camouflaged_path
        
        return file_path
    
    def upload_file(self, file_path: str, original_name: str = None, user_id: int = None) -> Optional[Dict]:
        if not os.path.exists(file_path):
            logger.error(f"Archivo no existe: {file_path}")
            return None
        
        if not self.navigate_to_step_2():
            logger.error("No se pudo navegar al paso 2")
            return None
        
        upload_path = self._prepare_file_for_upload(file_path, user_id or 0)
        if not upload_path:
            upload_path = file_path
        
        file_name = original_name if original_name else os.path.basename(file_path)
        if upload_path != file_path:
            file_name = os.path.basename(upload_path)
        
        content_type = self._content_type(file_name)
        
        try:
            with open(upload_path, 'rb') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}")
            return None
        
        headers = {
            'X-Csrf-Token': self.csrf_token,
            'Referer': f"{self.base_url}/index.php/{self.contexto}/submission/wizard/2?submissionId={self.submission_id}",
        }
        
        files = {'file': (file_name, file_content, content_type)}
        data = {
            'name[es_ES]': file_name,
            'fileStage': '2',
            'csrfToken': self.csrf_token
        }
        
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
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        if file_size <= self.chunk_size:
            result = self.upload_file(file_path, user_id=user_id)
            return [result] if result else []
        
        chunks = self._split_file(file_path)
        uploaded_chunks = []
        
        for idx, chunk_info in enumerate(chunks, 1):
            chunk_path = chunk_info['path']
            chunk_name = f"{file_name}.part{idx:03d}"
            
            result = self.upload_file(chunk_path, chunk_name, user_id)
            if result:
                uploaded_chunks.append(result)
                logger.info(f"Chunk {idx}/{len(chunks)} subido: {chunk_name}")
            
            if os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                except:
                    pass
        
        return uploaded_chunks
    
    def _split_file(self, file_path: str) -> List[Dict]:
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
            file_size=file_size,
            encryption_key=self.encryption_key
        )
    
    def get_upload_summary(self) -> Dict:
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
journal_uploaders = {}
admin_states = {}  # Para mantener el estado de edición del panel de control

# =========================
# FUNCIONES AUXILIARES
# =========================
def format_size(size_bytes: int) -> str:
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
# HANDLERS DE COMANDOS (EXISTENTES)
# =========================

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
            "• `/status` - Ver estado del sistema\n"
            "• `/bitzero <revista> <modo>` - Cambiar modo BitZero\n"
            "• `/bitzero_status` - Ver estado BitZero\n"
            "• `/test_bitzero <modo> [archivo]` - Probar codificación\n"
            "• `/control_panel` - Panel de administración (solo admins)\n\n"
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

@app.on_message(filters.command("ls"))
@authorized_only
async def list_files(client, message):
    try:
        if not os.path.exists(config.ROOT_DIR):
            os.makedirs(config.ROOT_DIR, exist_ok=True)
            await message.reply(f"📁 **Directorio creado:** `{config.ROOT_DIR}`\nEl directorio estaba vacío.")
            return
        
        files = []
        total_size = 0
        for item in os.listdir(config.ROOT_DIR):
            item_path = os.path.join(config.ROOT_DIR, item)
            if os.path.isfile(item_path):
                file_size = os.path.getsize(item_path)
                files.append({'name': item, 'path': item_path, 'size': file_size, 'modified': os.path.getmtime(item_path)})
                total_size += file_size
        
        if not files:
            await message.reply(f"📭 **Directorio vacío**\n\n📁 **Directorio:** `{config.ROOT_DIR}`\nEnvía archivos para que aparezcan aquí.")
            return
        
        files.sort(key=lambda x: x['modified'], reverse=True)
        file_list = f"📂 **Archivos en `{config.ROOT_DIR}`**\n\n"
        file_list += f"📊 **Total:** {len(files)} archivos | {total_size/1024/1024:.2f} MB\n\n"
        for i, file_info in enumerate(files[:20], 1):
            size_str = format_size(file_info['size'])
            mod_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(file_info['modified']))
            file_list += f"{i}. **{file_info['name']}**\n   📏 {size_str} | 📅 {mod_time}\n\n"
        if len(files) > 20:
            file_list += f"... y {len(files) - 20} archivos más.\n\n"
        file_list += "💡 **Usa `/rm <número>` para eliminar un archivo.**\n"
        file_list += f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
        await message.reply(file_list)
    except Exception as e:
        logger.error(f"Error en comando /ls: {e}")
        await message.reply(f"❌ **Error al listar archivos**\n\nNo se pudo acceder al directorio.\n**Error:** {str(e)[:100]}")

@app.on_message(filters.command("rm"))
@authorized_only
async def remove_file(client, message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply("❌ **Uso:** `/rm <número>`")
            return
        idx = int(parts[1]) - 1
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

@app.on_message(filters.command("deleteall"))
@authorized_only
async def delete_all(client, message):
    try:
        if os.path.exists(config.ROOT_DIR):
            for item in os.listdir(config.ROOT_DIR):
                item_path = os.path.join(config.ROOT_DIR, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path) and not item.startswith('.'):
                    shutil.rmtree(item_path)
        await message.reply("✅ **Todos los archivos han sido eliminados.**")
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("zips"))
@authorized_only
async def set_zip_size(client, message):
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

@app.on_message(filters.command("status"))
@authorized_only
async def status_handler(client, message):
    total_size = 0
    file_count = 0
    if os.path.exists(config.ROOT_DIR):
        for item in os.listdir(config.ROOT_DIR):
            item_path = os.path.join(config.ROOT_DIR, item)
            if os.path.isfile(item_path):
                total_size += os.path.getsize(item_path)
                file_count += 1
    
    users = user_manager.get_all_users()
    active_users = [u for u in users if u.get('active', True)]
    
    status_text = "📊 **Estado del Sistema**\n\n"
    status_text += f"👥 **Usuarios:** {len(active_users)}/{len(users)} activos\n"
    status_text += f"📁 **Archivos locales:** {file_count}\n"
    status_text += f"💾 **Espacio usado:** {total_size / 1024 / 1024:.2f} MB\n"
    status_text += f"📦 **Tamaño partes:** {config.CHUNK_SIZE_MB} MB\n"
    status_text += f"📚 **Revistas configuradas:** {len(config.REVISTAS)}\n\n"
    status_text += "🔧 **Configuración Revistas:**\n"
    for rev_id, rev_data in config.REVISTAS.items():
        bitzero_status = "✅" if rev_data.get('bitzero', 0) > 0 else "❌"
        status_text += f"  • {rev_data['nombre']}: BitZero {bitzero_status} (modo {rev_data.get('bitzero', 0)})\n"
    status_text += f"\n🕐 **Hora servidor:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    status_text += f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
    await message.reply(status_text)

@app.on_message(filters.command("up"))
@authorized_only
async def upload_handler(client, message):
    available_files = []
    if os.path.exists(config.ROOT_DIR):
        for item in os.listdir(config.ROOT_DIR):
            item_path = os.path.join(config.ROOT_DIR, item)
            if os.path.isfile(item_path) and not item.startswith('.') and not item.endswith(('.tmp', '.temp', '.log')):
                available_files.append(item_path)
    
    if not available_files:
        await message.reply("📭 **No hay archivos para subir.**\n\nEnvía archivos al bot primero.")
        return
    
    keyboard = []
    for rev_id, rev_data in config.REVISTAS.items():
        bitzero_status = "✅" if rev_data.get('bitzero', 0) > 0 else "❌"
        keyboard.append([
            InlineKeyboardButton(
                f"{bitzero_status} {rev_data['nombre']} (BitZero: {rev_data.get('bitzero', 0)})",
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

@app.on_message(filters.command("bitzero"))
@authorized_only
async def bitzero_handler(client, message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            await message.reply(
                "❌ **Uso:** `/bitzero <revista> <modo>`\n\n"
                "**Revistas disponibles:**\n"
                + "\n".join([f"  • `{key}` - {data['nombre']}" for key, data in config.REVISTAS.items()])
                + "\n\n**Modos BitZero:**\n"
                "  • `0` - Sin ofuscación\n"
                "  • `1` - Ofuscación PNG\n"
                "  • `2` - Ofuscación HTML\n"
                "  • `3` - Ofuscación ZIP (experimental)\n\n"
                f"👨‍💻 **Ejemplo:** `/bitzero KIKI_REV 2`"
            )
            return
        
        revista_id = parts[1].upper()
        modo = int(parts[2])
        
        if revista_id not in config.REVISTAS:
            await message.reply(f"❌ **Revista no encontrada:** `{revista_id}`\n\nRevistas disponibles: {', '.join(config.REVISTAS.keys())}")
            return
        
        if modo not in [0, 1, 2, 3]:
            await message.reply(f"❌ **Modo inválido:** `{modo}`\n\nModos válidos: 0, 1, 2, 3")
            return
        
        config.REVISTAS[revista_id]['bitzero'] = modo
        config._save_revistas_config()
        
        if revista_id in journal_uploaders:
            journal_uploaders[revista_id].bitzero_mode = modo
        
        modo_nombres = {0: "Sin ofuscación", 1: "Ofuscación PNG", 2: "Ofuscación HTML", 3: "Ofuscación ZIP"}
        await message.reply(
            f"✅ **Modo BitZero actualizado**\n\n"
            f"📚 **Revista:** {config.REVISTAS[revista_id]['nombre']}\n"
            f"🔐 **Nuevo modo:** {modo} ({modo_nombres.get(modo, 'Desconocido')})\n"
            f"🔄 **Próximas subidas** usarán este modo de ofuscación.\n\n"
            f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
        )
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("bitzero_status"))
@authorized_only
async def bitzero_status_handler(client, message):
    try:
        status_text = "🔐 **Estado BitZero por Revista**\n\n"
        for rev_id, rev_data in config.REVISTAS.items():
            modo = rev_data.get('bitzero', 0)
            modo_info = {
                0: "❌ **Desactivado**",
                1: "🖼️ **PNG** (ofuscación básica)",
                2: "🌐 **HTML** (ofuscación avanzada)",
                3: "📦 **ZIP** (experimental)"
            }.get(modo, f"❓ **Modo {modo}**")
            status_text += f"📚 **{rev_data['nombre']}** (`{rev_id}`)\n"
            status_text += f"   🔐 Modo: {modo_info}\n"
            status_text += f"   🔑 Clave: {'✅ Configurada' if rev_data.get('encryption_key') else '❌ No configurada'}\n\n"
        status_text += "💡 **Para cambiar el modo:** `/bitzero <revista> <modo>`\n"
        status_text += "💡 **Modos disponibles:** 0=Sin, 1=PNG, 2=HTML, 3=ZIP\n\n"
        status_text += f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
        await message.reply(status_text)
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("test_bitzero"))
@authorized_only
async def test_bitzero_handler(client, message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply(
                "❌ **Uso:** `/test_bitzero <modo> [archivo_num]`\n\n"
                "**Modos disponibles:**\n"
                "• `1` - Prueba modo PNG\n"
                "• `2` - Prueba modo HTML\n"
                "• `3` - Prueba modo ZIP\n\n"
                "**Ejemplo:** `/test_bitzero 2 1` (prueba modo HTML en el archivo #1)"
            )
            return
        
        modo = int(parts[1])
        archivo_idx = int(parts[2]) - 1 if len(parts) > 2 else 0
        
        files = []
        if os.path.exists(config.ROOT_DIR):
            for item in os.listdir(config.ROOT_DIR):
                item_path = os.path.join(config.ROOT_DIR, item)
                if os.path.isfile(item_path) and not item.startswith('.'):
                    files.append(item_path)
        
        if not files:
            await message.reply("📭 **No hay archivos para probar.**")
            return
        
        if archivo_idx < 0 or archivo_idx >= len(files):
            await message.reply(f"❌ **Índice inválido.** Usa números del 1 al {len(files)}")
            return
        
        file_path = files[archivo_idx]
        file_name = os.path.basename(file_path)
        
        status_msg = await message.reply(
            f"🧪 **Probando BitZero Modo {modo}**\n\n"
            f"📄 **Archivo:** `{file_name}`\n"
            f"💾 **Tamaño:** {os.path.getsize(file_path) / 1024:.2f} KB\n"
            f"⏳ Procesando..."
        )
        
        temp_dir = os.path.join(config.ROOT_DIR, "_test_bitzero")
        os.makedirs(temp_dir, exist_ok=True)
        
        if modo == 1:
            output_path = os.path.join(temp_dir, f"{file_name}.test.png")
            success = BitZeroEncoder.encode_png(file_path, output_path)
            tipo = "PNG"
        elif modo == 2:
            output_path = os.path.join(temp_dir, f"{file_name}.test.html")
            encryption_key = None
            for rev_data in config.REVISTAS.values():
                if rev_data.get('encryption_key'):
                    encryption_key = rev_data['encryption_key']
                    break
            success = BitZeroEncoder.encode_html(file_path, output_path, encryption_key)
            tipo = "HTML"
        elif modo == 3:
            output_path = os.path.join(temp_dir, f"{file_name}.test.zip")
            success = BitZeroEncoder.encode_zip(file_path, output_path)
            tipo = "ZIP"
        else:
            await status_msg.edit_text(f"❌ **Modo inválido:** {modo}")
            return
        
        if success:
            output_size = os.path.getsize(output_path)
            ratio = (output_size / os.path.getsize(file_path)) * 100
            
            await status_msg.edit_text(
                f"✅ **Prueba BitZero completada**\n\n"
                f"📄 **Archivo original:** `{file_name}`\n"
                f"🔧 **Modo probado:** {modo} ({tipo})\n"
                f"📊 **Tamaño original:** {os.path.getsize(file_path) / 1024:.2f} KB\n"
                f"📈 **Tamaño codificado:** {output_size / 1024:.2f} KB\n"
                f"📉 **Ratio:** {ratio:.1f}%\n"
                f"📁 **Archivo de prueba:** `{os.path.basename(output_path)}`\n\n"
                f"💡 **Consejo:** El archivo de prueba se guardó en el directorio temporal.\n\n"
                f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
            )
            
            if output_size < 50 * 1024 * 1024:
                await client.send_document(
                    chat_id=message.chat.id,
                    document=output_path,
                    caption=f"🧪 Archivo de prueba BitZero Modo {modo}"
                )
        else:
            await status_msg.edit_text(f"❌ **Error en la codificación BitZero Modo {modo}**")
        
        await asyncio.sleep(60)
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    except Exception as e:
        logger.error(f"Error en test_bitzero: {e}")
        await message.reply(f"❌ **Error:** {str(e)[:100]}")

# =========================
# COMANDOS DE ADMINISTRADOR (adduser, removeuser, ban, listusers)
# =========================

@app.on_message(filters.command("adduser"))
async def add_user_admin(client, message):
    if not is_admin(message.from_user.id):
        await message.reply("❌ **Solo los administradores pueden usar este comando.**")
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

@app.on_message(filters.command("add"))
async def add_user_alias(client, message):
    await add_user_admin(client, message)

@app.on_message(filters.command("removeuser"))
async def remove_user_admin(client, message):
    if not is_admin(message.from_user.id):
        await message.reply("❌ **Solo los administradores pueden usar este comando.**")
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

@app.on_message(filters.command("ban"))
async def ban_user_alias(client, message):
    await remove_user_admin(client, message)

@app.on_message(filters.command("listusers"))
async def list_users_admin(client, message):
    if not is_admin(message.from_user.id):
        await message.reply("❌ **Solo los administradores pueden usar este comando.**")
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
# NUEVO COMANDO: PANEL DE CONTROL
# =========================

@app.on_message(filters.command("control_panel"))
async def control_panel(client, message):
    if not is_admin(message.from_user.id):
        await message.reply("❌ Solo administradores pueden usar este comando.")
        return

    keyboard = []
    for rev_id, rev_data in config.REVISTAS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"📚 {rev_data['nombre']} (Modo {rev_data.get('bitzero',0)})",
                callback_data=f"cp_edit_{rev_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cerrar", callback_data="cp_close")])

    await message.reply(
        "🔧 **Panel de Control de Revistas**\n\n"
        "Selecciona una revista para editar sus parámetros.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =========================
# HANDLER DE CALLBACKS (incluye los nuevos de control panel)
# =========================

@app.on_callback_query()
async def handle_callback(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    if not user_manager.is_authorized(user_id):
        await callback_query.answer("❌ No autorizado", show_alert=True)
        return

    # --- Callbacks existentes para subida ---
    if data.startswith("upload_select_"):
        revista_id = data.replace("upload_select_", "")
        if revista_id not in config.REVISTAS:
            await callback_query.answer("❌ Revista no encontrada", show_alert=True)
            return
        
        revista = config.REVISTAS[revista_id]
        uploader = journal_uploaders.get(revista_id)
        if not uploader:
            uploader = RevistaUploader(
                username=revista['username'],
                password=revista['password'],
                submission_id=revista['submission_id'],
                base_url=revista['base_url'],
                contexto=revista['contexto'],
                bitzero_mode=revista.get('bitzero', 0),
                encryption_key=revista.get('encryption_key')
            )
            journal_uploaders[revista_id] = uploader
        
        await callback_query.answer(f"Iniciando subida a {revista['nombre']}...")
        await callback_query.message.edit_text(
            f"🚀 **Iniciando Subida**\n\n"
            f"📚 **Revista:** {revista['nombre']}\n"
            f"🔐 **BitZero:** {'Activado' if revista.get('bitzero', 0) > 0 else 'Desactivado'} (Modo {revista.get('bitzero', 0)})\n"
            f"⏳ Conectando..."
        )
        
        await perform_upload_with_bitzero(client, callback_query.message, uploader, revista, user_id)
        return

    elif data == "cancel_action":
        await callback_query.message.edit_text("❌ **Operación cancelada.**")
        await callback_query.answer()
        return

    # --- Nuevos callbacks para panel de control ---
    if data.startswith("cp_edit_"):
        rev_id = data.replace("cp_edit_", "")
        rev_data = config.REVISTAS.get(rev_id)
        if not rev_data:
            await callback_query.answer("Revista no encontrada", show_alert=True)
            return

        keyboard = [
            [InlineKeyboardButton(f"👤 Usuario: {rev_data['username']}", callback_data=f"cp_field_{rev_id}_username")],
            [InlineKeyboardButton(f"🔑 Contraseña: {rev_data['password'][:3]}***", callback_data=f"cp_field_{rev_id}_password")],
            [InlineKeyboardButton(f"🆔 Submission ID: {rev_data['submission_id']}", callback_data=f"cp_field_{rev_id}_submission_id")],
            [InlineKeyboardButton(f"🔐 Modo BitZero: {rev_data.get('bitzero',0)}", callback_data=f"cp_field_{rev_id}_bitzero")],
            [InlineKeyboardButton(f"🔑 Clave Encriptación: {rev_data.get('encryption_key', 'No configurada')[:10]}...", callback_data=f"cp_field_{rev_id}_encryption_key")],
            [InlineKeyboardButton("🧪 Probar conexión", callback_data=f"cp_test_{rev_id}")],
            [InlineKeyboardButton("🔙 Volver", callback_data="cp_back")],
            [InlineKeyboardButton("❌ Cerrar", callback_data="cp_close")]
        ]
        await callback_query.message.edit_text(
            f"**Editando:** {rev_data['nombre']}\n\n"
            "Selecciona el campo que deseas modificar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await callback_query.answer()
        return

    elif data.startswith("cp_field_"):
        parts = data.split("_")
        # formato: cp_field_rev_id_campo
        rev_id = parts[2]
        field = parts[3]
        admin_states[user_id] = {"action": "edit_field", "rev_id": rev_id, "field": field}
        await callback_query.message.edit_text(
            f"✏️ Envía el nuevo valor para **{field}**.\n"
            "Responde con el texto o número correspondiente.\n"
            "Para cancelar, escribe /cancel"
        )
        await callback_query.answer()
        return

    elif data.startswith("cp_test_"):
        rev_id = data.replace("cp_test_", "")
        revista = config.REVISTAS.get(rev_id)
        if not revista:
            await callback_query.answer("Revista no encontrada", show_alert=True)
            return

        await callback_query.answer("Probando conexión...")
        # Crear uploader temporal para probar
        uploader = RevistaUploader(
            username=revista['username'],
            password=revista['password'],
            submission_id=revista['submission_id'],
            base_url=revista['base_url'],
            contexto=revista['contexto'],
            bitzero_mode=revista.get('bitzero',0),
            encryption_key=revista.get('encryption_key')
        )
        if uploader.login():
            await callback_query.message.edit_text("✅ **Conexión exitosa.**")
        else:
            await callback_query.message.edit_text("❌ **Falló la conexión.** Revisa credenciales.")
        return

    elif data == "cp_back":
        # Volver al panel principal
        keyboard = []
        for rev_id, rev_data in config.REVISTAS.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"📚 {rev_data['nombre']} (Modo {rev_data.get('bitzero',0)})",
                    callback_data=f"cp_edit_{rev_id}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Cerrar", callback_data="cp_close")])
        await callback_query.message.edit_text(
            "🔧 **Panel de Control de Revistas**\n\n"
            "Selecciona una revista para editar sus parámetros.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await callback_query.answer()
        return

    elif data == "cp_close":
        await callback_query.message.delete()
        await callback_query.answer("Panel cerrado")
        return

# =========================
# MANEJADOR DE TEXTO PARA RECIBIR NUEVOS VALORES DEL PANEL
# =========================

@app.on_message(filters.text & filters.private)
async def handle_admin_input(client, message):
    user_id = message.from_user.id
    if user_id not in admin_states:
        return

    state = admin_states[user_id]
    if state["action"] == "edit_field":
        rev_id = state["rev_id"]
        field = state["field"]
        new_value = message.text.strip()

        if rev_id not in config.REVISTAS:
            await message.reply("❌ Revista no encontrada.")
            del admin_states[user_id]
            return

        # Validaciones según campo
        if field in ["username", "password", "submission_id", "encryption_key"]:
            config.REVISTAS[rev_id][field] = new_value
        elif field == "bitzero":
            try:
                val = int(new_value)
                if val not in [0, 1, 2, 3]:
                    raise ValueError
                config.REVISTAS[rev_id][field] = val
            except:
                await message.reply("❌ El modo BitZero debe ser 0, 1, 2 o 3. Intenta de nuevo.")
                return
        else:
            await message.reply("❌ Campo no válido.")
            del admin_states[user_id]
            return

        # Guardar en JSON
        config._save_revistas_config()

        # Actualizar uploader en memoria si existe
        if rev_id in journal_uploaders:
            uploader = journal_uploaders[rev_id]
            uploader.username = config.REVISTAS[rev_id]["username"]
            uploader.password = config.REVISTAS[rev_id]["password"]
            uploader.submission_id = config.REVISTAS[rev_id]["submission_id"]
            uploader.bitzero_mode = config.REVISTAS[rev_id].get("bitzero",0)
            uploader.encryption_key = config.REVISTAS[rev_id].get("encryption_key")
            # Forzar relogin si se cambiaron credenciales
            uploader.is_logged_in = False

        await message.reply(f"✅ Campo **{field}** actualizado correctamente.")

        # Volver al panel
        await control_panel(client, message)
        del admin_states[user_id]

# =========================
# HANDLER PARA DESCARGAR ARCHIVOS
# =========================

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
@authorized_only
async def save_received_file(client, message):
    user_id = message.from_user.id
    try:
        os.makedirs(config.ROOT_DIR, exist_ok=True)
        
        file_name = None
        if message.document:
            if message.document.file_name:
                file_name = message.document.file_name
            else:
                file_name = f"document_{message.id}"
                if message.document.mime_type:
                    ext_map = {
                        'application/pdf': '.pdf',
                        'application/zip': '.zip',
                        'text/plain': '.txt',
                        'image/jpeg': '.jpg',
                        'image/png': '.png',
                        'video/mp4': '.mp4',
                        'audio/mpeg': '.mp3',
                    }
                    ext = ext_map.get(message.document.mime_type, '.bin')
                    if not file_name.endswith(ext):
                        file_name += ext
        elif message.video:
            file_name = message.video.file_name or f"video_{message.id}.mp4"
        elif message.audio:
            file_name = message.audio.file_name or f"audio_{message.id}.mp3"
        elif message.photo:
            file_name = f"photo_{message.photo.file_id}.jpg"
        else:
            file_name = f"file_{message.id}.bin"
        
        if file_name:
            file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
        else:
            file_name = f"file_{message.id}.bin"
        
        file_path = os.path.join(config.ROOT_DIR, file_name)
        
        counter = 1
        original_name, extension = os.path.splitext(file_name)
        while os.path.exists(file_path):
            new_name = f"{original_name}_{counter}{extension}"
            file_path = os.path.join(config.ROOT_DIR, new_name)
            counter += 1
        
        status_msg = await message.reply(
            f"📥 **Preparando descarga...**\n\n"
            f"📄 **Nombre:** `{os.path.basename(file_path)}`\n"
            f"⏳ Iniciando descarga..."
        )
        
        last_update_time = time.time()
        last_percent = 0
        update_interval = 2
        
        async def download_progress(current, total):
            nonlocal last_update_time, last_percent
            current_time = time.time()
            percent = (current / total) * 100
            if (current_time - last_update_time >= update_interval or 
                abs(percent - last_percent) >= 5 or 
                current == total):
                try:
                    bar_length = 20
                    filled = int(bar_length * current / total)
                    bar = "█" * filled + "▁" * (bar_length - filled)
                    elapsed_time = current_time - status_msg.date.timestamp()
                    if elapsed_time > 0:
                        speed = (current / 1024 / 1024) / elapsed_time
                        if speed > 0:
                            remaining = (total - current) / (speed * 1024 * 1024)
                            time_str = f"⏱️ {remaining:.0f}s"
                        else:
                            time_str = "⏱️ Calculando..."
                    else:
                        speed = 0
                        time_str = "⏱️ --"
                    
                    await status_msg.edit_text(
                        f"📥 **Descargando archivo...**\n\n"
                        f"📄 **Nombre:** `{os.path.basename(file_path)}`\n"
                        f"📊 **Progreso:** [{bar}] {percent:.1f}%\n"
                        f"💾 **Tamaño:** {current/1024/1024:.1f}MB / {total/1024/1024:.1f}MB\n"
                        f"⚡ **Velocidad:** {speed:.2f}MB/s\n"
                        f"{time_str}\n\n"
                        f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
                    )
                    last_update_time = current_time
                    last_percent = percent
                except Exception as e:
                    logger.debug(f"Error actualizando progreso: {e}")
        
        max_attempts = config.MAX_DOWNLOAD_ATTEMPTS
        attempt = 1
        
        while attempt <= max_attempts:
            try:
                logger.info(f"Intento {attempt}/{max_attempts} de descarga: {file_name}")
                await message.download(
                    file_name=file_path,
                    progress=download_progress,
                    progress_args=(),
                    block=True
                )
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    if file_size > 0:
                        await status_msg.edit_text(
                            f"✅ **Archivo guardado exitosamente**\n\n"
                            f"📄 **Nombre:** `{os.path.basename(file_path)}`\n"
                            f"💾 **Tamaño:** {file_size/1024/1024:.2f} MB\n"
                            f"📁 **Ubicación:** `{config.ROOT_DIR}/`\n"
                            f"🔄 **Intentos:** {attempt}\n\n"
                            f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
                        )
                        logger.info(f"Archivo descargado exitosamente: {file_path} ({file_size} bytes)")
                        return
                    else:
                        logger.warning(f"Archivo descargado con tamaño 0: {file_path}")
                else:
                    logger.error(f"Archivo no encontrado después de descarga: {file_path}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout en intento {attempt} para {file_name}")
                await status_msg.edit_text(
                    f"⚠️ **Timeout en descarga (intento {attempt}/{max_attempts})**\n\n"
                    f"📄 **Nombre:** `{os.path.basename(file_path)}`\n"
                    f"⏳ Reintentando en 5 segundos..."
                )
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error en intento {attempt}: {e}")
                await status_msg.edit_text(
                    f"⚠️ **Error en descarga (intento {attempt}/{max_attempts})**\n\n"
                    f"📄 **Nombre:** `{os.path.basename(file_path)}`\n"
                    f"❌ **Error:** {str(e)[:100]}\n"
                    f"⏳ Reintentando en 5 segundos..."
                )
                await asyncio.sleep(5)
            attempt += 1
        
        await status_msg.edit_text(
            f"❌ **No se pudo descargar el archivo**\n\n"
            f"📄 **Nombre:** `{file_name}`\n"
            f"🔄 **Intentos fallidos:** {max_attempts}\n\n"
            f"**Posibles causas:**\n"
            f"• Problemas de conexión\n"
            f"• Timeout del servidor\n\n"
            f"**💡 Solución:**\n"
            f"1. Verifica tu conexión a internet\n"
            f"2. Intenta enviar el archivo de nuevo\n"
            f"3. Contacta al administrador\n\n"
            f"👨‍💻 **Desarrollador:** @Pro_Slayerr"
        )
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Archivo parcial eliminado: {file_path}")
            except:
                pass
    except Exception as e:
        logger.error(f"Error inesperado en save_received_file: {e}")
        await message.reply(f"❌ **Error inesperado**\n\nNo se pudo procesar el archivo.\n**Error:** {str(e)[:100]}")

# =========================
# FUNCIÓN DE SUBIDA CON BITZERO
# =========================

async def perform_upload_with_bitzero(client, message, uploader, revista, user_id):
    if not uploader.ensure_logged_in():
        await message.edit_text("❌ **Error de autenticación.** No se pudo iniciar sesión en la revista.")
        return
    
    uploader.uploaded_files = []
    
    files_to_upload = []
    if os.path.exists(config.ROOT_DIR):
        for item in os.listdir(config.ROOT_DIR):
            item_path = os.path.join(config.ROOT_DIR, item)
            if os.path.isfile(item_path) and not item.startswith('.') and not item.endswith(('.tmp', '.temp', '.log')):
                files_to_upload.append(item_path)
    
    if not files_to_upload:
        await message.edit_text("📭 **No hay archivos para subir.**")
        return
    
    total_files = len(files_to_upload)
    uploaded_count = 0
    all_uploaded_files = []
    
    for idx, file_path in enumerate(files_to_upload, 1):
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        bitzero_info = ""
        if uploader.bitzero_mode == 1:
            bitzero_info = "🖼️ PNG"
        elif uploader.bitzero_mode == 2:
            bitzero_info = "🌐 HTML"
        elif uploader.bitzero_mode == 3:
            bitzero_info = "📦 ZIP"
        
        await message.edit_text(
            f"📤 **Subiendo Archivo**\n\n"
            f"📂 **Progreso:** {idx}/{total_files}\n"
            f"📄 **Archivo:** {file_name}\n"
            f"💾 **Tamaño:** {file_size / 1024 / 1024:.2f} MB\n"
            f"🔐 **BitZero:** {bitzero_info if uploader.bitzero_mode > 0 else '❌'}\n"
            f"⏳ Procesando..."
        )
        
        if file_size > uploader.chunk_size:
            uploaded_files = uploader.upload_chunked_file(file_path, user_id)
        else:
            result = uploader.upload_file(file_path, user_id=user_id)
            uploaded_files = [result] if result else []
        
        if uploaded_files:
            uploaded_count += 1
            all_uploaded_files.extend(uploaded_files)
            await message.edit_text(
                f"✅ **Archivo Subido**\n\n"
                f"📂 **Progreso:** {idx}/{total_files}\n"
                f"📄 **Archivo:** {file_name}\n"
                f"🔗 **Partes:** {len(uploaded_files)}\n"
                f"⏳ Continuando..."
            )
        else:
            await message.edit_text(
                f"⚠️ **Error Subiendo**\n\n"
                f"📄 **Archivo:** {file_name}\n"
                f"❌ No se pudo subir este archivo.\n"
                f"⏳ Continuando con el siguiente..."
            )
        await asyncio.sleep(1)
    
    if not all_uploaded_files:
        await message.edit_text("❌ **Subida Fallida**\n\nNo se pudo subir ningún archivo.\nVerifica permisos y conexión.")
        return
    
    bitzero_url = ""
    if uploader.bitzero_mode > 0 and all_uploaded_files and files_to_upload:
        original_name = os.path.basename(files_to_upload[0])
        total_size = sum(f['size'] for f in all_uploaded_files)
        bitzero_url = uploader.generate_bitzero_url(original_name, total_size)
    
    result_text = f"✅ **Subida Completada**\n\n"
    result_text += f"📚 **Revista:** {revista['nombre']}\n"
    result_text += f"📦 **Archivos procesados:** {uploaded_count}/{total_files}\n"
    result_text += f"🔗 **Partes subidas:** {len(all_uploaded_files)}\n"
    
    if uploader.bitzero_mode > 0:
        bitzero_details = {
            0: "Sin ofuscación",
            1: "Ofuscación PNG (archivo camuflado como imagen)",
            2: "Ofuscación HTML (archivo en base64 dentro de HTML)",
            3: "Ofuscación ZIP (archivo comprimido con contraseña)"
        }.get(uploader.bitzero_mode, "Modo desconocido")
        result_text += f"🔐 **BitZero:** ✅ Activado (Modo {uploader.bitzero_mode})\n"
        result_text += f"📋 **Tipo:** {bitzero_details}\n"
        if uploader.encryption_key:
            result_text += f"🔑 **Encriptación:** ✅ Clave configurada\n"
    else:
        result_text += f"🔐 **BitZero:** ❌ Desactivado\n"
    result_text += "\n"
    
    if bitzero_url:
        result_text += f"🔗 **URL BitZero (ofuscada):**\n`{bitzero_url}`\n\n"
        result_text += "📥 **Para descargar usa:**\n"
        result_text += "```bash\npython3 bitzero.py \"URL\"\n```\n"
        result_text += "🔧 **Modo requerido:** "
        if uploader.bitzero_mode == 1:
            result_text += "PNG Decoder\n"
        elif uploader.bitzero_mode == 2:
            result_text += "HTML Decoder\n"
        elif uploader.bitzero_mode == 3:
            result_text += "ZIP Decoder (con contraseña)\n"
    
    result_text += f"\n👨‍💻 **Desarrollador:** @Pro_Slayerr"
    await message.edit_text(result_text)

# =========================
# INICIALIZACIÓN DEL BOT
# =========================

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🚀 Iniciando Bot de Revistas con BitZero MEJORADO")
    
    if not initialize_directories():
        logger.error("✗ No se pudieron inicializar los directorios. Saliendo...")
        sys.exit(1)
    
    logger.info("Iniciando sesión en todas las revistas...")
    for rev_id, rev_data in config.REVISTAS.items():
        uploader = RevistaUploader(
            username=rev_data['username'],
            password=rev_data['password'],
            submission_id=rev_data['submission_id'],
            base_url=rev_data['base_url'],
            contexto=rev_data['contexto'],
            bitzero_mode=rev_data.get('bitzero', 0),
            encryption_key=rev_data.get('encryption_key')
        )
        if uploader.login():
            logger.info(f"✅ Pre-login exitoso para {rev_data['nombre']}")
        else:
            logger.error(f"❌ Pre-login fallido para {rev_data['nombre']}")
        journal_uploaders[rev_id] = uploader
    
    logger.info(f"📚 Revistas configuradas: {len(config.REVISTAS)}")
    logger.info(f"💾 Tamaño de partes: {config.CHUNK_SIZE_MB} MB")
    logger.info(f"⏱️ Timeout descarga: {config.DOWNLOAD_TIMEOUT}s")
    logger.info(f"🔄 Intentos descarga: {config.MAX_DOWNLOAD_ATTEMPTS}")
    logger.info(f"👑 Administradores: {config.ADMIN_IDS}")
    logger.info(f"📁 Directorio raíz: {config.ROOT_DIR}")
    logger.info("=" * 50)
    
    for rev_id, rev_data in config.REVISTAS.items():
        bitzero_status = "Activado" if rev_data.get('bitzero', 0) > 0 else "Desactivado"
        logger.info(f"   • {rev_data['nombre']}: BitZero {bitzero_status} (modo {rev_data.get('bitzero', 0)})")
    
    logger.info("✅ Bot listo. Esperando comandos...")
    app.run()