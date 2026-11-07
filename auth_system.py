import json
import os
from typing import Dict, List, Set

class AuthSystem:
    def __init__(self, admin_id: int, allowed_group: int, owner_id: int = None):
        self.admin_id = admin_id  # Admin principal - recibe avisos
        self.owner_id = owner_id if owner_id else admin_id  # Owner - mismos permisos
        self.allowed_group = allowed_group
        self.authorized_users: Dict[int, str] = {}  # {user_id: nombre}
        self.banned_users: Set[int] = set()
        self.gratis_mode = False  # Default: only authorized users can use
        
        # Load existing data
        self.load_data()
    
    def load_data(self):
        """Load authorization data from file"""
        try:
            if os.path.exists('auth_data.json'):
                print(f"[AUTH] Cargando datos desde auth_data.json...")
                with open('auth_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"[AUTH] Datos cargados: {data}")
                    
                    # Migrar datos antiguos si existen
                    if 'authorized_users' in data and isinstance(data['authorized_users'], list):
                        # Convertir lista antigua a diccionario
                        self.authorized_users = {int(user_id): f"Usuario_{user_id}" for user_id in data['authorized_users']}
                        print(f"[AUTH] Migrados usuarios de lista a diccionario: {self.authorized_users}")
                    elif 'authorized_users' in data and isinstance(data['authorized_users'], dict):
                        # Asegurar que las claves sean enteros
                        self.authorized_users = {int(k): v for k, v in data['authorized_users'].items()}
                        print(f"[AUTH] Usuarios cargados como diccionario: {self.authorized_users}")
                    else:
                        self.authorized_users = {}
                        print("[AUTH] No se encontraron usuarios autorizados")
                    
                    self.banned_users = set(int(uid) for uid in data.get('banned_users', []))
                    self.gratis_mode = data.get('gratis_mode', False)
                    
                    print(f"[AUTH] Estado final - Usuarios: {len(self.authorized_users)}, Baneados: {len(self.banned_users)}, Gratis: {self.gratis_mode}")
            else:
                print("[AUTH] No existe auth_data.json, iniciando con datos vacíos")
                self.authorized_users = {}
                self.banned_users = set()
                self.gratis_mode = False
        except Exception as e:
            print(f"[AUTH] Error cargando datos: {e}")
            self.authorized_users = {}
            self.banned_users = set()
            self.gratis_mode = False
    
    def save_data(self):
        """Save authorization data to file"""
        try:
            data = {
                'authorized_users': {str(k): v for k, v in self.authorized_users.items()},
                'banned_users': list(self.banned_users),
                'gratis_mode': self.gratis_mode
            }
            with open('auth_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[AUTH] Datos guardados exitosamente: {len(self.authorized_users)} usuarios")
        except Exception as e:
            print(f"[AUTH] Error guardando datos: {e}")
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin (principal o owner) - SOLO hardcodeados"""
        return user_id == self.admin_id or user_id == self.owner_id
    
    def is_main_admin(self, user_id: int) -> bool:
        """Check if user is the main admin"""
        return user_id == self.admin_id
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is the owner"""
        return user_id == self.owner_id
    
    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return user_id in self.authorized_users
    
    def is_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        return user_id in self.banned_users

    def can_use_bot(self, user_id: int, chat_id: int, is_private: bool | None = None) -> bool:
        """
        Determina si un usuario puede usar el bot basado en el modo actual
        """
        user_id = int(user_id)
        chat_id = int(chat_id)
        
        if self.is_banned(user_id):
            return False
            
        if is_private is None:
            try:
                is_private = chat_id > 0
            except Exception:
                is_private = False

        if self.gratis_mode:
            return True

        return self.is_authorized(user_id) or self.is_admin(user_id)
    
    def add_user(self, user_id: int, nombre: str = None) -> bool:
        """Add user to authorized list with optional name"""
        if nombre is None:
            nombre = f"Usuario_{user_id}"
        self.authorized_users[user_id] = nombre
        self.save_data()
        return True
    
    def remove_user(self, user_id: int) -> bool:
        """Remove user from authorized list"""
        if user_id in self.authorized_users:
            del self.authorized_users[user_id]
            self.save_data()
            return True
        return False
    
    def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        self.banned_users.add(user_id)
        self.save_data()
        return True
    
    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        if user_id in self.banned_users:
            self.banned_users.remove(user_id)
            self.save_data()
            return True
        return False
    
    def set_gratis_mode(self, enabled: bool):
        """Enable/disable gratis mode"""
        self.gratis_mode = enabled
        self.save_data()
    
    def get_authorized_users(self) -> Dict[int, str]:
        """Get dictionary of authorized users with names"""
        return self.authorized_users.copy()
    
    def get_banned_users(self) -> List[int]:
        """Get list of banned users"""
        return list(self.banned_users)
    
    def get_stats(self) -> Dict:
        """Get authorization statistics"""
        return {
            'total_authorized': len(self.authorized_users),
            'total_banned': len(self.banned_users),
            'total_admins': 2,  # Solo los 2 hardcodeados
            'gratis_mode': self.gratis_mode,
            'allowed_group': self.allowed_group
        }
