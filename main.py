# -*- coding: utf-8 -*-
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from config import (
    COMPROBANTE1_CONFIG,
    COMPROBANTE4_CONFIG,
    COMPROBANTE_MOVIMIENTO_CONFIG,
    COMPROBANTE_MOVIMIENTO2_CONFIG,
    COMPROBANTE_QR_CONFIG,
    COMPROBANTE_NUEVO_CONFIG,
    COMPROBANTE_ANULADO_CONFIG,  # 
    COMPROBANTE_MOVIMIENTO3_CONFIG,
    MVKEY_CONFIG,  # 
    COMPROBANTE_AHORROS_CONFIG,  # 
    COMPROBANTE_AHORROS2_CONFIG,  # Configuración para corriente
    COMPROBANTE_DAVIPLATA_CONFIG,  # Configuración para daviplata
    COMPROBANTE_BC_NQ_T_CONFIG,  # Configuración para BC a NQ y T
    COMPROBANTE_BC_QR_CONFIG,  # Configuración para BC QR
    COMPROBANTE_NEQUI_BC_CONFIG,  # Configuración para Nequi a BC
    COMPROBANTE_NEQUI_AHORROS_CONFIG,  # Configuración para Nequi Ahorros
    MOVIMIENTO_BC_AHORROS_CONFIG,  #📊 Movimientos Bancolombia
    MOVIMIENTO_BC_CORRIENTE_CONFIG,
    MOVIMIENTO_BC_NEQUI_CONFIG,
    MOVIMIENTO_BC_QR_CONFIG
)
from utils import generar_comprobante, generar_comprobante_nuevo, generar_comprobante_anulado, enmascarar_nombre, generar_comprobante_ahorros, generar_comprobante_daviplata, generar_comprobante_bc_nq_t, generar_comprobante_bc_qr, generar_comprobante_nequi_bc, generar_comprobante_nequi_ahorros, generar_movimiento_bancolombia
from auth_system import AuthSystem
import os
import logging
from datetime import datetime
import pytz
import json

logging.basicConfig(level=logging.DEBUG)

# Configuration
ADMIN_ID = 8237177276  # Admin principal - recibe avisos
OWNER_ID = 7535906226  # Owner - mismos permisos, avisos van al admin principal
ALLOWED_GROUP = -1003136359129  # Grupo permitido para usar el bot

# Admins hardcodeados - NO se pueden agregar mas por comandos
HARDCODED_ADMINS = [ADMIN_ID, OWNER_ID]

# Owner para botones
OWNER_USERNAME = "@sebas992269"

# ID del grupo requerido (debe estar unido si o si)
REQUIRED_GROUP_ID = -1003136359129
REQUIRED_GROUP_LINK = "https://t.me/nequixzonevip"

# Initialize authorization system
auth_system = AuthSystem(ADMIN_ID, ALLOWED_GROUP, OWNER_ID)

user_data_store = {}

# Sistema de modo de fechas manuales
fecha_manual_mode = {}  # {user_id: True/False}

# Sistema de modo de referencias manuales
referencia_manual_mode = {}  # {user_id: True/False}

# Sistema de referencias
REFERENCIAS_FILE = "referencias.json"

def cargar_referencias():
    """Carga las referencias desde el archivo JSON"""
    if os.path.exists(REFERENCIAS_FILE):
        try:
            with open(REFERENCIAS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def guardar_referencias(referencias):
    """Guarda las referencias en el archivo JSON"""
    with open(REFERENCIAS_FILE, 'w', encoding='utf-8') as f:
        json.dump(referencias, f, ensure_ascii=False, indent=2)

async def is_member_of_group(bot, user_id):
    """Verifica si el usuario es miembro del grupo requerido"""
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_GROUP_ID, user_id=user_id)
        print(f"[DEBUG] Usuario {user_id} - Estado en grupo: {member.status}")
        
        # Solo permitir si es miembro activo del grupo
        is_member = member.status in ['member', 'administrator', 'creator']
        
        if not is_member:
            print(f"[ACCESO DENEGADO] Usuario {user_id} - Estado: {member.status}")
        else:
            print(f"[ACCESO PERMITIDO] Usuario {user_id} - Estado: {member.status}")
        
        return is_member
        
    except Exception as e:
        print(f"[ERROR CRÍTICO] No se pudo verificar membresía para usuario {user_id}: {e}")
        print(f"[ACCESO DENEGADO] Por seguridad, se deniega el acceso cuando hay errores")
        
        # SIEMPRE denegar acceso si hay cualquier error
        # Esto obliga a que el bot esté correctamente configurado
        return False

def is_allowed_chat(chat_id, user_id):
    """Verifica si el chat es permitido (privado o grupo autorizado)"""
    # Permitir chats privados (chat_id positivo o igual al user_id)
    if chat_id > 0 or chat_id == user_id:
        return True
    # Permitir solo el grupo específico
    if chat_id == ALLOWED_GROUP:
        return True
    return False

async def send_success_message(update: Update):
    """Envía mensaje de éxito después de generar un comprobante"""
    await update.message.reply_text(
        "✅ **Comprobante generado con éxito**\n\n"
        "Usa /comprobante para generar otro",
        parse_mode='Markdown'
    )

async def notify_main_admin(context: ContextTypes.DEFAULT_TYPE, admin_id: int, admin_name: str, action: str, target_info: str = ""):
    """Envía notificación al administrador principal sobre acciones de otros admins"""
    if admin_id == ADMIN_ID:
        return  # No notificar si es el admin principal quien hace la acción
    
    try:
        # Obtener fecha y hora actual
        now = datetime.now()
        fecha_hora = now.strftime("%d/%m/%Y %H:%M:%S")
        
        message = f"🔔 **Notificación Administrativa**\n\n"
        message += f"👤 **Admin:** {admin_id}\n"
        message += f"📝 **Nombre:** {admin_name or 'Sin nombre'}\n"
        message += f"⚡ **Acción:** {action}\n"
        if target_info:
            message += f"📋 **Detalles:** {target_info}\n"
        message += f"🕐 **Fecha/Hora:** {fecha_hora}"
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=message,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"[ERROR] No se pudo enviar notificación al admin principal: {e}")

async def start_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Función que redirige a los usuarios que usan /start al comando correcto"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si el chat es permitido
    if not is_allowed_chat(chat_id, user_id):
        await update.message.reply_text("🚫 GRUPO NO PERMITIDO")
        return
    
    keyboard = [
        [InlineKeyboardButton("Owner", url="https://t.me/sebas992269")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎉 Bienvenido al generador de comprobantes\n\n"
        "� Adm inistradores autorizados:\n"
        "Haz clic en el botón para contactar\n\n"
        "📋 Comandos disponibles:\n"
        "/comprobante - Iniciar el bot\n"
        "/fechas - Activar/desactivar fechas manuales\n"
        "/refes - Activar/desactivar referencias manuales\n"
        "/horarios - Ver horarios gratis\n"
        "/precios - Ver planes premium\n\n"
        "👉 Usa /comprobante para empezar",
        reply_markup=reply_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si el chat es permitido
    if not is_allowed_chat(chat_id, user_id):
        await update.message.reply_text("🚫 GRUPO NO PERMITIDO")
        return
    user = update.effective_user
    
    # Verificar primero si está baneado
    if auth_system.is_banned(user_id):
        await update.message.reply_text("❌ Estás baneado")
        return
    
    # Verificar membresia del grupo
    if not await is_member_of_group(context.bot, user_id):
        keyboard = [[InlineKeyboardButton("🔗 Unirse al Grupo", url=REQUIRED_GROUP_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **Acceso Denegado**\n\n"
            "Tienes que unirte a nuestro grupo oficial para poder usar el bot\n\n"
            "👇 Haz clic en el botón para unirte:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    # Check authorization y auto-registrar si es necesario
    if not auth_system.can_use_bot(user_id, chat_id):
        if not auth_system.gratis_mode:
            keyboard = [
                [InlineKeyboardButton("👑 Owner", url="https://t.me/sebas992269")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🔴 **Bot en Modo OFF**\n\n"
                "El bot está fuera del horario gratuito\n\n"
                "💰 **¿Necesitas usarlo ahora?**\n"
                "Contacta con el owner:\n\n"
                "✨ Pueden activarte el acceso premium",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
    else:
        # En modo gratis, los usuarios pueden usar el bot sin ser agregados a la lista
        pass
    
    # Crear teclado personalizado con botones organizados
    keyboard = [
        [KeyboardButton("Nequi"), KeyboardButton("Daviplata")],
        [KeyboardButton("Nequi QR"), KeyboardButton("Bre B"), KeyboardButton("Anulado")],
        [KeyboardButton("Ahorros"), KeyboardButton("Corriente")],
        [KeyboardButton("BC a NQ"), KeyboardButton("BC QR")],
        [KeyboardButton("Nequi Corriente"), KeyboardButton("Nequi Ahorros")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        "📱 Selecciona el botón del comprobante que quieres generar",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    user = update.effective_user
    
    # Verificar si el chat es permitido
    if not is_allowed_chat(chat_id, user_id):
        await update.message.reply_text("🚫 GRUPO NO PERMITIDO")
        return

    # En modo gratis, los usuarios pueden usar el bot sin registro automático
    if auth_system.gratis_mode and not auth_system.is_authorized(user_id):
        pass

    # Mapeo de botones del teclado a tipos de comprobante
    button_mapping = {
        "Nequi": "comprobante1",
        "Transfiya": "comprobante4", 
        "Daviplata": "comprobante_daviplata",
        "Nequi QR": "comprobante_qr",
        "Bre B": "comprobante_nuevo",
        "Anulado": "comprobante_anulado",
        "Ahorros": "comprobante_ahorros",
        "Corriente": "comprobante_corriente",
        "BC a NQ": "comprobante_bc_nq_t",
        "BC QR": "comprobante_bc_qr",
        "Nequi Corriente": "comprobante_nequi_bc",
        "Nequi Ahorros": "comprobante_nequi_ahorros"
    }

    # Si el mensaje es uno de los botones del teclado, verificar baneos
    if text in button_mapping and user_id not in user_data_store:
        # Verificar si el bot está apagado
        if not auth_system.can_use_bot(user_id, chat_id):
            if not auth_system.gratis_mode:
                keyboard = [
                    [InlineKeyboardButton("Owner", url="https://t.me/sebas992269")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "🔴 **Bot en Modo OFF**\n\n"
                    "El bot está fuera del horario gratuito\n\n"
                    "💰 **¿Necesitas usarlo ahora?**\n"
                    "Contacta con el owner:\n\n"
                    "✨ Pueden activarte el acceso premium",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
        
        # Verificar si está baneado solo cuando intenta usar el bot
        if auth_system.is_banned(user_id):
            await update.message.reply_text("❌ Estás baneado de nuestros servicios, si crees que es un error contacta con el owner")
            return
        
        # Verificar membresia del grupo
        if not await is_member_of_group(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("Unirse al Grupo", url=REQUIRED_GROUP_LINK)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🚫 **Acceso Denegado**\n\n"
                "Tienes que unirte a nuestro grupo oficial para poder usar el bot\n\n"
                "👇 Haz clic en el botón para unirte:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
            
        tipo = button_mapping[text]
        user_data_store[user_id] = {"step": 0, "tipo": tipo}

        prompts = {
            "comprobante1": "📝 ¿Nombre de la víctima?",
            "comprobante4": "📱 ¿Número a transferir?",
            "movimiento": "📝 ¿Nombre de la víctima?",
            "movimiento2": "📝 ¿Nombre de la víctima?",
            "comprobante_qr": "🏪 ¿Nombre del negocio?",
            "comprobante_nuevo": "📝 ¿Nombre de la víctima?",
            "comprobante_anulado": "📝 ¿Nombre de la víctima?",  
            "comprobante_corriente": "📝 ¿Nombre de la víctima?",  
            "comprobante_daviplata": "📝 ¿Nombre de la víctima?",  
            "comprobante_ahorros": "📝 ¿Nombre de la víctima?",  
            "comprobante_bc_nq_t": "📱 ¿Número de teléfono?",
            "comprobante_bc_qr": "📋 ¿Descripción del QR?",
            "comprobante_nequi_bc": "📝 ¿Nombre?"
        }

        await update.message.reply_text(prompts.get(tipo, "📋 Inicia ingresando los datos:"))
        return

    if user_id not in user_data_store:
        return

    # Verificar baneos cuando el usuario está completando datos del bot
    if auth_system.is_banned(user_id):
        await update.message.reply_text("❌ Estás baneado de nuestros servicios, si crees que es un error contacta a algún administrador")
        return

    data = user_data_store[user_id]
    tipo = data["tipo"]
    step = data["step"]

    # --- NEQUI ---
    if tipo == "comprobante1":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text("📱 Ingresa el número de teléfono")
        elif step == 1:
            # Validar número de teléfono
            if not text.isdigit() or len(text) != 10 or not text.startswith('3'):
                await update.message.reply_text("⚠️ El número tiene que empezar en 3 y tener exactamente 10 dígitos\nEjemplo: 3012223855")
                return
            data["telefono"] = text
            data["step"] = 2
            await update.message.reply_text("💰 Ingresa el valor")
        elif step == 2:
            if not text.replace("-", "", 1).isdigit():
                await update.message.reply_text("⚠️ El valor debe ser numérico")
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text("⚠️ El valor mínimo es $1,000. Intenta de nuevo")
                return
            data["valor"] = valor
            
            # Verificar si el modo de referencia manual está activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text("🔢 Ingresa la referencia\n\nEjemplo: M12345678")
                return
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text("📅 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return
            
            output_path = generar_comprobante(data, COMPROBANTE1_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅")
            os.remove(output_path)

            # movimiento negativo
            data_mov = data.copy()
            data_mov["nombre"] = data["nombre"].upper()
            data_mov["valor"] = -abs(data["valor"])
            output_path_mov = generar_comprobante(data_mov, COMPROBANTE_MOVIMIENTO_CONFIG)
            with open(output_path_mov, "rb") as f:
                await update.message.reply_document(document=f, caption="📊")
            os.remove(output_path_mov)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE1_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅")
            os.remove(output_path)

            # movimiento negativo
            data_mov = data.copy()
            data_mov["nombre"] = data["nombre"].upper()
            data_mov["valor"] = -abs(data["valor"])
            output_path_mov = generar_comprobante(data_mov, COMPROBANTE_MOVIMIENTO_CONFIG)
            with open(output_path_mov, "rb") as f:
                await update.message.reply_document(document=f, caption="📊")
            os.remove(output_path_mov)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text("📅 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return
            
            output_path = generar_comprobante(data, COMPROBANTE1_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅")
            os.remove(output_path)

            # movimiento negativo
            data_mov = data.copy()
            data_mov["nombre"] = data["nombre"].upper()
            data_mov["valor"] = -abs(data["valor"])
            output_path_mov = generar_comprobante(data_mov, COMPROBANTE_MOVIMIENTO_CONFIG)
            with open(output_path_mov, "rb") as f:
                await update.message.reply_document(document=f, caption="📊")
            os.remove(output_path_mov)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual después de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE1_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅")
            os.remove(output_path)

            # movimiento negativo
            data_mov = data.copy()
            data_mov["nombre"] = data["nombre"].upper()
            data_mov["valor"] = -abs(data["valor"])
            output_path_mov = generar_comprobante(data_mov, COMPROBANTE_MOVIMIENTO_CONFIG)
            with open(output_path_mov, "rb") as f:
                await update.message.reply_document(document=f, caption="📊")
            os.remove(output_path_mov)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- TRANSFIYA ---
    elif tipo == "comprobante4":
        if step == 0:
            # Validar número de teléfono
            if not text.isdigit() or len(text) != 10 or not text.startswith('3'):
                await update.message.reply_text("⚠️ El número tiene que empezar en 3 y tener exactamente 10 dígitos\nEjemplo: 3012223855")
                return
            data["telefono"] = text
            data["step"] = 1
            await update.message.reply_text("💰 Digite el valor")
        elif step == 1:
            if not text.replace("-", "", 1).isdigit():
                await update.message.reply_text("⚠️ El valor debe ser numérico")
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text("⚠️ El valor mínimo es $1,000. Intenta de nuevo")
                return
            data["valor"] = valor
            
            # Verificar si el modo de referencia manual está activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text("🔢 Ingresa la referencia\n\nEjemplo: M12345678")
                return
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 2
                await update.message.reply_text("📅 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return
            
            output_path = generar_comprobante(data, COMPROBANTE4_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅")
            os.remove(output_path)

            # movimiento negativo
            data_mov2 = {
                "telefono": data["telefono"],
                "valor": -abs(data["valor"]),
                "nombre": data["telefono"],
            }
            output_path_mov2 = generar_comprobante(data_mov2, COMPROBANTE_MOVIMIENTO2_CONFIG)
            with open(output_path_mov2, "rb") as f:
                await update.message.reply_document(document=f, caption="📊")
            os.remove(output_path_mov2)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 2:
            # Procesar fecha manual para Transfiya
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE4_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅")
            os.remove(output_path)

            # movimiento negativo
            data_mov2 = {
                "telefono": data["telefono"],
                "valor": -abs(data["valor"]),
                "nombre": data["telefono"],
            }
            output_path_mov2 = generar_comprobante(data_mov2, COMPROBANTE_MOVIMIENTO2_CONFIG)
            with open(output_path_mov2, "rb") as f:
                await update.message.reply_document(document=f, caption="📊")
            os.remove(output_path_mov2)
            
            # Enviar mensaje de éxito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para Transfiya
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual está activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text("📅 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return
            
            output_path = generar_comprobante(data, COMPROBANTE4_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅")
            os.remove(output_path)

            data_mov2 = {
                "telefono": data["telefono"],
                "valor": -abs(data["valor"]),
                "nombre": data["telefono"],
            }
            output_path_mov2 = generar_comprobante(data_mov2, COMPROBANTE_MOVIMIENTO2_CONFIG)
            with open(output_path_mov2, "rb") as f:
                await update.message.reply_document(document=f, caption="📊")
            os.remove(output_path_mov2)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual después de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE4_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅")
            os.remove(output_path)

            data_mov2 = {
                "telefono": data["telefono"],
                "valor": -abs(data["valor"]),
                "nombre": data["telefono"],
            }
            output_path_mov2 = generar_comprobante(data_mov2, COMPROBANTE_MOVIMIENTO2_CONFIG)
            with open(output_path_mov2, "rb") as f:
                await update.message.reply_document(document=f, caption="📊")
            os.remove(output_path_mov2)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- MOVIMIENTOS ---
    elif tipo in ["movimiento", "movimiento2"]:
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text("💰 Ingresa el valor")
        elif step == 1:
            if not text.isdigit():
                await update.message.reply_text("⚠️ El valor debe ser numérico")
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text("⚠️ El valor mínimo es $1,000. Intenta de nuevo")
                return
            data["valor"] = valor

            cfg = COMPROBANTE_MOVIMIENTO_CONFIG if tipo == "movimiento" else COMPROBANTE_MOVIMIENTO2_CONFIG
            output_path = generar_comprobante(data, cfg)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE QR ---
    elif tipo == "comprobante_qr":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 1:
            if not text.replace("-", "", 1).isdigit():
                await update.message.reply_text(" El valor debe ser numrico ")
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text(" El valor mnimo es $1,000. Intenta de nuevo ")
                return
            data["valor"] = valor

            # Verificar si el modo de referencia manual est activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text("📝 Ingresa la referencia\n\nEjemplo: M12345678")
                return

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 2
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return

            output_path = generar_comprobante(data, COMPROBANTE_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            #📊 Movimiento adicional con plantilla 3
            data_mov_qr = {
                "nombre": data["nombre"].upper(),
                "valor": -abs(data["valor"])
            }
            output_path_movqr = generar_comprobante(data_mov_qr, COMPROBANTE_MOVIMIENTO3_CONFIG)
            with open(output_path_movqr, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movqr)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 2:
            # Procesar fecha manual para QR
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            #📊 Movimiento adicional con plantilla 3
            data_mov_qr = {
                "nombre": data["nombre"].upper(),
                "valor": -abs(data["valor"])
            }
            output_path_movqr = generar_comprobante(data_mov_qr, COMPROBANTE_MOVIMIENTO3_CONFIG)
            with open(output_path_movqr, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movqr)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para QR
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return

            output_path = generar_comprobante(data, COMPROBANTE_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov_qr = {
                "nombre": data["nombre"].upper(),
                "valor": -abs(data["valor"])
            }
            output_path_movqr = generar_comprobante(data_mov_qr, COMPROBANTE_MOVIMIENTO3_CONFIG)
            with open(output_path_movqr, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movqr)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual despus de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante(data, COMPROBANTE_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov_qr = {
                "nombre": data["nombre"].upper(),
                "valor": -abs(data["valor"])
            }
            output_path_movqr = generar_comprobante(data_mov_qr, COMPROBANTE_MOVIMIENTO3_CONFIG)
            with open(output_path_movqr, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movqr)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE NUEVO (LLAVES) ---
    elif tipo == "comprobante_nuevo":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 1:
            val_txt = text.replace(".", "").replace(",", ".")
            try:
                valor = float(val_txt)
                if valor < 1000:
                    await update.message.reply_text(" El valor mnimo es $1,000. Intenta de nuevo ")
                    return
                data["valor"] = valor
            except ValueError:
                await update.message.reply_text(" El valor debe ser numrico. Intenta de nuevo ")
                return
            data["step"] = 2
            await update.message.reply_text(" Ingresa la llave ")
        elif step == 2:
            data["llave"] = text
            data["step"] = 3
            await update.message.reply_text(" Ingresa el banco ")
        elif step == 3:
            data["banco"] = text
            data["step"] = 4
            await update.message.reply_text("📱 Ingresa el número de quien envía")
        elif step == 4:
            # Validar número de teléfono del que envía
            if not text.isdigit() or len(text) != 10 or not text.startswith('3'):
                await update.message.reply_text("⚠️ El número tiene que empezar en 3 y tener exactamente 10 dígitos\nEjemplo: 3012223855")
                return
            data["numero_envia"] = text

            # Verificar si el modo de referencia manual est activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text("📝 Ingresa la referencia\n\nEjemplo: M12345678")
                return

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 5
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return

            #  Generar comprobante principal
            output_path = generar_comprobante_nuevo(data, COMPROBANTE_NUEVO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            #  Generar movimiento automático con MVKEY (enmascarado)
            data_mov_llaves = {
                "nombre": enmascarar_nombre(data["nombre"]),  
                "valor": -abs(float(data["valor"]))
            }
            output_path_movllaves = generar_comprobante(data_mov_llaves, MVKEY_CONFIG)
            with open(output_path_movllaves, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movllaves)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 5:
            # Procesar fecha manual para comprobante NUEVO
            data["fecha_manual"] = text
            
            #  Generar comprobante principal
            output_path = generar_comprobante_nuevo(data, COMPROBANTE_NUEVO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            #  Generar movimiento automático con MVKEY (enmascarado)
            data_mov_llaves = {
                "nombre": enmascarar_nombre(data["nombre"]),  
                "valor": -abs(float(data["valor"]))
            }
            output_path_movllaves = generar_comprobante(data_mov_llaves, MVKEY_CONFIG)
            with open(output_path_movllaves, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movllaves)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para Bre B
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return

            output_path = generar_comprobante_nuevo(data, COMPROBANTE_NUEVO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov_llaves = {
                "nombre": enmascarar_nombre(data["nombre"]),  
                "valor": -abs(float(data["valor"]))
            }
            output_path_movllaves = generar_comprobante(data_mov_llaves, MVKEY_CONFIG)
            with open(output_path_movllaves, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movllaves)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual despus de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante_nuevo(data, COMPROBANTE_NUEVO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path)

            data_mov_llaves = {
                "nombre": enmascarar_nombre(data["nombre"]),  
                "valor": -abs(float(data["valor"]))
            }
            output_path_movllaves = generar_comprobante(data_mov_llaves, MVKEY_CONFIG)
            with open(output_path_movllaves, "rb") as f:
                await update.message.reply_document(document=f, caption=" ")
            os.remove(output_path_movllaves)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE❌ ANULADO ---
    elif tipo == "comprobante_anulado":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 1:
            if not text.replace("-", "", 1).isdigit():
                await update.message.reply_text(" El valor debe ser numrico ")
                return
            valor = int(text)
            if valor < 1000:
                await update.message.reply_text(" El valor mnimo es $1,000. Intenta de nuevo ")
                return
            data["valor"] = valor

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 2
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return

            output_path = generar_comprobante_anulado(data, COMPROBANTE_ANULADO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="❌ ANULADO")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 2:
            # Procesar fecha manual para❌ ANULADO
            data["fecha_manual"] = text
            
            output_path = generar_comprobante_anulado(data, COMPROBANTE_ANULADO_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="❌ ANULADO")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE AHORROS ---
    elif tipo == "comprobante_ahorros":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text("🏦 Ingresa el número de cuenta")
        elif step == 1:
            # Validar que tenga 11 dígitos
            digitos = "".join(ch for ch in text if ch.isdigit())
            if len(digitos) != 11:
                await update.message.reply_text("⚠️ El número de cuenta debe tener exactamente 11 dígitos\nEjemplo: 12345678912")
                return
            data["numero_cuenta"] = text
            data["step"] = 2
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 2:
            # Validar valor numrico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(" El valor debe ser numrico ")
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(" El valor mnimo es $1,000. Intenta de nuevo ")
                return
            data["valor"] = valor

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 Sept 2025 - 01:23 p. m.")
                return

            # Generar comprobante
            output_path = generar_comprobante_ahorros(data, COMPROBANTE_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Ahorros")
            os.remove(output_path)
            
            # MOVIMIENTO DESACTIVADO
            # data_mov_ahorros = {
            #     "valor": data["valor"],
            #     "nombre": data["nombre"]
            # }
            # output_path_mov = generar_movimiento_bancolombia(data_mov_ahorros, MOVIMIENTO_BC_AHORROS_CONFIG)
            # with open(output_path_mov, "rb") as f:
            #     await update.message.reply_document(document=f, caption="📊 Movimiento Ahorros")
            # os.remove(output_path_mov)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual para Ahorros
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_ahorros(data, COMPROBANTE_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Ahorros")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE CORRIENTE ---
    elif tipo == "comprobante_corriente":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text("🏦 Ingresa el número de cuenta")
        elif step == 1:
            # Validar que tenga 11 dígitos
            digitos = "".join(ch for ch in text if ch.isdigit())
            if len(digitos) != 11:
                await update.message.reply_text("⚠️ El número de cuenta debe tener exactamente 11 dígitos\nEjemplo: 12345678912")
                return
            data["numero_cuenta"] = text
            data["step"] = 2
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 2:
            # Validar valor numrico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(" El valor debe ser numrico ")
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(" El valor mnimo es $1,000. Intenta de nuevo ")
                return
            data["valor"] = valor

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 Sept 2025 - 01:23 p. m.")
                return

            # Generar comprobante
            output_path = generar_comprobante_ahorros(data, COMPROBANTE_AHORROS2_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante de Corriente")
            os.remove(output_path)
            
            # MOVIMIENTO DESACTIVADO
            # data_mov_corriente = {
            #     "valor": data["valor"],
            #     "nombre": data["nombre"]
            # }
            # output_path_mov = generar_movimiento_bancolombia(data_mov_corriente, MOVIMIENTO_BC_CORRIENTE_CONFIG)
            # with open(output_path_mov, "rb") as f:
            #     await update.message.reply_document(document=f, caption="📊 Movimiento Corriente")
            # os.remove(output_path_mov)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual para Corriente
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_ahorros(data, COMPROBANTE_AHORROS2_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante de Corriente")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE DAVIPLATA ---
    elif tipo == "comprobante_daviplata":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 1:
            # Validar valor numrico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(" El valor debe ser numrico ")
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(" El valor mnimo es $1,000. Intenta de nuevo ")
                return
            data["valor"] = valor
            data["step"] = 2
            await update.message.reply_text(" Ingresa los 4 dígitos de la cuenta que envia ")
        elif step == 2:
            # Validar cuenta que recibe (4 dígitos)
            if not text.isdigit() or len(text) != 4:
                await update.message.reply_text(" Deben ser exactamente 4 dígitos numricos ")
                return
            data["recibe"] = text
            data["step"] = 3
            await update.message.reply_text(" Ingresa los 4 dígitos de la cuenta que recibe ")
        elif step == 3:
            # Validar cuenta que enva (4 dígitos)
            if not text.isdigit() or len(text) != 4:
                await update.message.reply_text(" Deben ser exactamente 4 dígitos numricos ")
                return
            data["envia"] = text

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 4
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06/12/2025 - 02:30 PM")
                return

            # Generar comprobante
            output_path = generar_comprobante_daviplata(data, COMPROBANTE_DAVIPLATA_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Daviplata")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 4:
            # Procesar fecha manual para Daviplata
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_daviplata(data, COMPROBANTE_DAVIPLATA_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Daviplata")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE BC A NQ Y T ---
    elif tipo == "comprobante_bc_nq_t":
        if step == 0:
            # Validar número de teléfono
            if not text.isdigit() or len(text) != 10 or not text.startswith('3'):
                await update.message.reply_text("⚠️ El número tiene que empezar en 3 y tener exactamente 10 dígitos\nEjemplo: 3012223855")
                return
            data["telefono"] = text
            data["step"] = 1
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 1:
            # Validar valor numrico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(" El valor debe ser numrico ")
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(" El valor mnimo es $1,000. Intenta de nuevo ")
                return
            data["valor"] = valor

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 2
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 Sept 2025 - 01:23 p. m.")
                return

            # Generar comprobante
            output_path = generar_comprobante_bc_nq_t(data, COMPROBANTE_BC_NQ_T_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante BC a NQ")
            os.remove(output_path)
            
            # MOVIMIENTO DESACTIVADO
            # data_mov_nequi = {
            #     "valor": data["valor"],
            #     "nombre": data.get("telefono", "NEQUI")
            # }
            # output_path_mov = generar_movimiento_bancolombia(data_mov_nequi, MOVIMIENTO_BC_NEQUI_CONFIG)
            # with open(output_path_mov, "rb") as f:
            #     await update.message.reply_document(document=f, caption="📊 Movimiento BC a Nequi")
            # os.remove(output_path_mov)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 2:
            # Procesar fecha manual para BC a NQ
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_bc_nq_t(data, COMPROBANTE_BC_NQ_T_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante BC a NQ")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE BC QR ---
    elif tipo == "comprobante_bc_qr":
        if step == 0:
            data["descripcion_qr"] = text  # Descripcin del QR
            data["step"] = 1
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 1:
            data["valor"] = text  # Valor
            data["step"] = 2
            await update.message.reply_text(" Ingresa el nombre ")
        elif step == 2:
            data["nombre"] = text  # Nombre completo
            data["step"] = 3
            await update.message.reply_text("🏦 Ingresa el número de cuenta")
        elif step == 3:
            # Guardar número de cuenta
            data["numero_cuenta"] = text

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 4
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 07 oct. 2025 - 02:34 a. m.")
                return

            # Generar comprobante
            output_path = generar_comprobante_bc_qr(data, COMPROBANTE_BC_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante BC QR")
            os.remove(output_path)
            
            # MOVIMIENTO DESACTIVADO
            # data_mov_qr = {
            #     "valor": data["valor"],
            #     "nombre": data.get("punto_venta", "QR")
            # }
            # output_path_mov = generar_movimiento_bancolombia(data_mov_qr, MOVIMIENTO_BC_QR_CONFIG)
            # with open(output_path_mov, "rb") as f:
            #     await update.message.reply_document(document=f, caption="📊 Movimiento BC QR")
            # os.remove(output_path_mov)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 4:
            # Procesar fecha manual para BC QR
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_bc_qr(data, COMPROBANTE_BC_QR_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante BC QR")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE NEQUI A BC ---
    elif tipo == "comprobante_nequi_bc":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 1:
            # Validar valor numrico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(" El valor debe ser numrico ")
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(" El valor mnimo es $1,000. Intenta de nuevo ")
                return
            data["valor"] = valor
            data["step"] = 2
            await update.message.reply_text("🏦 Ingresa el número de cuenta")
        elif step == 2:
            # Validar que tenga 11 dígitos
            digitos = "".join(ch for ch in text if ch.isdigit())
            if len(digitos) != 11:
                await update.message.reply_text("⚠️ El número de cuenta debe tener exactamente 11 dígitos\nEjemplo: 12345678912")
                return
            data["numero_cuenta"] = text

            # Verificar si el modo de referencia manual est activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text("📝 Ingresa la referencia\n\nEjemplo: M12345678")
                return

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return

            # Generar comprobante
            output_path = generar_comprobante_nequi_bc(data, COMPROBANTE_NEQUI_BC_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Nequi Corriente")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual para Nequi a BC
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_nequi_bc(data, COMPROBANTE_NEQUI_BC_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Nequi Corriente")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para Nequi Corriente
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return

            output_path = generar_comprobante_nequi_bc(data, COMPROBANTE_NEQUI_BC_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Nequi Corriente")
            os.remove(output_path)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual despus de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante_nequi_bc(data, COMPROBANTE_NEQUI_BC_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Nequi Corriente")
            os.remove(output_path)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- COMPROBANTE NEQUI AHORROS ---
    elif tipo == "comprobante_nequi_ahorros":
        if step == 0:
            data["nombre"] = text
            data["step"] = 1
            await update.message.reply_text(" Ingresa el valor ")
        elif step == 1:
            # Validar valor numrico
            valor_limpio = text.replace(".", "").replace(",", "").replace(" ", "")
            if not valor_limpio.isdigit():
                await update.message.reply_text(" El valor debe ser numrico ")
                return
            valor = int(valor_limpio)
            if valor < 1000:
                await update.message.reply_text(" El valor mnimo es $1,000. Intenta de nuevo ")
                return
            data["valor"] = valor
            data["step"] = 2
            await update.message.reply_text("🏦 Ingresa el número de cuenta")
        elif step == 2:
            # Validar que tenga 11 dígitos
            digitos = "".join(ch for ch in text if ch.isdigit())
            if len(digitos) != 11:
                await update.message.reply_text("⚠️ El número de cuenta debe tener exactamente 11 dígitos\nEjemplo: 12345678912")
                return
            data["numero_cuenta"] = text

            # Verificar si el modo de referencia manual est activado
            if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
                data["step"] = 10
                await update.message.reply_text("📝 Ingresa la referencia\n\nEjemplo: M12345678")
                return

            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 3
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return

            # Generar comprobante
            output_path = generar_comprobante_nequi_ahorros(data, COMPROBANTE_NEQUI_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Nequi Ahorros")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 3:
            # Procesar fecha manual para Nequi Ahorros
            data["fecha_manual"] = text
            
            # Generar comprobante
            output_path = generar_comprobante_nequi_ahorros(data, COMPROBANTE_NEQUI_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Nequi Ahorros")
            os.remove(output_path)
            
            # Enviar mensaje de xito
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 10:
            # Procesar referencia manual para Nequi Ahorros
            data["referencia_manual"] = text
            
            # Verificar si el modo de fecha manual est activado
            if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
                data["step"] = 11
                await update.message.reply_text("📝 Ingresa la fecha\n\nEjemplo: 06 de diciembre de 2025 a las 02:30 p. m.")
                return

            output_path = generar_comprobante_nequi_ahorros(data, COMPROBANTE_NEQUI_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Nequi Ahorros")
            os.remove(output_path)
            
            await send_success_message(update)
            del user_data_store[user_id]
        elif step == 11:
            # Procesar fecha manual despus de referencia manual
            data["fecha_manual"] = text
            
            output_path = generar_comprobante_nequi_ahorros(data, COMPROBANTE_NEQUI_AHORROS_CONFIG)
            with open(output_path, "rb") as f:
                await update.message.reply_document(document=f, caption="✅ Comprobante Nequi Ahorros")
            os.remove(output_path)
            
            await send_success_message(update)
            del user_data_store[user_id]

    # --- AGREGAR USUARIO (ADMIN) ---
    elif tipo == "agregar_usuario":
        if step == 0:
            # Validar que sea un ID numrico
            if not text.isdigit():
                await update.message.reply_text("❌ El ID debe ser numrico. Intenta de nuevo:")
                return
            data["target_user_id"] = int(text)
            data["step"] = 1
            await update.message.reply_text("📝 Ingresa el nombre del usuario:")
        elif step == 1:
            data["nombre"] = text
            data["step"] = 2
            await update.message.reply_text("📝 Ingresa la fecha de vencimiento:\n(Ejemplo: lunes 12 de octubre de 2025)")
        elif step == 2:
            try:
                data["fecha_vencimiento"] = text
                
                # Agregar usuario al sistema
                auth_system.add_user(data["target_user_id"], data["nombre"])
                
                # Obtener fecha actual
                now = datetime.now(pytz.timezone("America/Bogota"))
                fecha_agregado = now.strftime("%d/%m/%Y %H:%M:%S")
                
                # Escapar caracteres especiales de Markdown en los datos del usuario
                nombre_escaped = data['nombre'].replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                fecha_venc_escaped = data['fecha_vencimiento'].replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                admin_name_escaped = data['admin_name'].replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                
                # Mensaje de confirmacin para quien agreg
                mensaje_confirmacion = (
                    "✅ **Usuario Agregado Exitosamente**\n\n"
                    f"🆔 **ID:** `{data['target_user_id']}`\n"
                    f"👤 **Nombre:** {nombre_escaped}\n"
                    f"📅 **Fecha de vencimiento:** {fecha_venc_escaped}\n"
                    f"📅 **Agregado el:** {fecha_agregado}\n"
                    f"📋📅 **Agregado por:** {admin_name_escaped}"
                )
                
                await update.message.reply_text(mensaje_confirmacion, parse_mode='Markdown')
                
                # Notificar al admin supremo si no es l quien agreg
                if user_id != ADMIN_ID:
                    mensaje_admin = (
                        "📋 **Nuevo Usuario Agregado**\n\n"
                        f"🆔 **ID:** `{data['target_user_id']}`\n"
                        f"👤 **Nombre:** {nombre_escaped}\n"
                        f"📅 **Vence:** {fecha_venc_escaped}\n"
                        f"📅 **Agregado:** {fecha_agregado}\n"
                        f"📋�� **Por:** {admin_name_escaped} (`{user_id}`)"
                    )
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=mensaje_admin,
                        parse_mode='Markdown'
                    )
                
                logging.debug(f"[ADMIN] {user_id} agreg usuario {data['target_user_id']} ({data['nombre']}) - Vence: {data['fecha_vencimiento']}")
                del user_data_store[user_id]
            except Exception as e:
                logging.error(f"Error al agregar usuario: {e}")
                await update.message.reply_text(f"❌ Error al agregar usuario: {str(e)}")
                del user_data_store[user_id]

# ================= ADMIN COMMANDS =================
async def gratis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("comando solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if chat_id != ALLOWED_GROUP and chat_id != user_id:
        await update.message.reply_text(
            "🚫 **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
        return
    
    auth_system.set_gratis_mode(True)
    await update.message.reply_text(
        "✅ **Modo Gratis ACTIVADO**\n\n"
        "📋 Todos los usuarios pueden usar el bot ahora\n"
        "📋 Sin restricciones de horario",
        parse_mode='Markdown'
    )
    print(f"[ADMIN] {user_id} activó modo gratis en chat {chat_id}")
    await notify_main_admin(context, user_id, update.effective_user.first_name, "Activó modo gratis")

async def off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if chat_id != ALLOWED_GROUP and chat_id != user_id:
        await update.message.reply_text(
            "🚫 **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
        return
    
    auth_system.set_gratis_mode(False)
    await update.message.reply_text(
        "🔄 **Modo Gratis DESACTIVADO**\n\n"
        "📋 Solo usuarios autorizados pueden usar el bot\n"
        "🕐 Horario restringido activado",
        parse_mode='Markdown'
    )
    print(f"[ADMIN] {user_id} desactivó modo gratis en chat {chat_id}")
    await notify_main_admin(context, user_id, update.effective_user.first_name, "Desactivó modo gratis")

async def agregar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("❌ Comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if chat_id != ALLOWED_GROUP and chat_id != user_id:
        await update.message.reply_text(
            "🚫 **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
        return
    
    # Iniciar proceso interactivo
    user_data_store[user_id] = {
        "step": 0, 
        "tipo": "agregar_usuario",
        "admin_name": update.effective_user.first_name or "Admin"
    }
    await update.message.reply_text("📝 Ingresa el ID del usuario:")

async def eliminar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("❌ Comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if chat_id != ALLOWED_GROUP and chat_id != user_id:
        await update.message.reply_text("🚫 Validación incorrecta.")
        return
    
    if not context.args:
        await update.message.reply_text(" Uso: /eliminar <id_usuario>")
        return
    
    try:
        target_user_id = int(context.args[0])
        if auth_system.remove_user(target_user_id):
            await update.message.reply_text(f" Usuario {target_user_id} desautorizado.")
        else:
            await update.message.reply_text(f" Usuario {target_user_id} no estaba autorizado.")
        logging.debug(f"[ADMIN] {user_id} elimin usuario {target_user_id} en chat {chat_id}")
        await notify_main_admin(context, user_id, update.effective_user.first_name, "Elimin usuario", str(target_user_id))
    except ValueError:
        await update.message.reply_text(" ID de usuario invlido.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if chat_id != ALLOWED_GROUP and chat_id != user_id:
        await update.message.reply_text(
            "🚫 **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
    
    stats = auth_system.get_stats()
    authorized_users = auth_system.get_authorized_users()
    banned_users = auth_system.get_banned_users()
    admin_users = auth_system.get_admin_users()
    
    message = f" **Estadsticas del Bot**\n\n"
    message += f" Usuarios autorizados: {stats['total_authorized']}\n"
    message += f" Usuarios baneados: {stats['total_banned']}\n"
    message += f" Administradores: {stats['total_admins']}\n"
    message += f" Modo gratis: {'Activado' if stats['gratis_mode'] else 'Desactivado'}\n"
    message += f" Grupo permitido: {stats['allowed_group']}\n\n"
    
    # Mostrar administradores
    message += " **Administradores:**\n"
    message += f"  {auth_system.admin_id} - Administrador Principal\n"
    if admin_users:
        for uid in admin_users:
            user_name = authorized_users.get(uid, f"Usuario_{uid}")
            message += f"  {uid} - {user_name}\n"
    
    if authorized_users:
        message += "\n **Usuarios autorizados:**\n"
        for uid, nombre in authorized_users.items():
            if uid != auth_system.admin_id and uid not in admin_users:
                message += f"   {uid} - {nombre}\n"
    else:
        message += "\n No hay usuarios autorizados.\n"
    
    if banned_users:
        message += "\n **Usuarios baneados:**\n"
        for uid in banned_users:
            message += f"   {uid}\n"
    
    await update.message.reply_text(message)

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if chat_id != ALLOWED_GROUP and chat_id != user_id:
        await update.message.reply_text(
            "🚫 **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
        return
    
    if not context.args:
        await update.message.reply_text(" Uso: /ban <id_usuario>")
        return
    
    try:
        target_user_id = int(context.args[0])
        auth_system.ban_user(target_user_id)
        await update.message.reply_text(f" Usuario {target_user_id} baneado.")
        logging.debug(f"[ADMIN] {user_id} bane usuario {target_user_id} en chat {chat_id}")
        await notify_main_admin(context, user_id, update.effective_user.first_name, "Bane usuario", str(target_user_id))
    except ValueError:
        await update.message.reply_text(" ID de usuario invlido.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("comando disponible solo para administradores.")
        return
    
    # Verificar si es el grupo permitido o chat privado con admin
    if chat_id != ALLOWED_GROUP and chat_id != user_id:
        await update.message.reply_text(
            "🚫 **Acceso Denegado**\n\n"
            "Este comando solo puede ser usado por administradores autorizados",
            parse_mode='Markdown'
        )
        return
    
    if not context.args:
        await update.message.reply_text(" Uso: /unban <id_usuario>")
        return
    
    try:
        target_user_id = int(context.args[0])
        if auth_system.unban_user(target_user_id):
            await update.message.reply_text(f" Usuario {target_user_id} desbaneado.")
        else:
            await update.message.reply_text(f" Usuario {target_user_id} no estaba baneado.")
        logging.debug(f"[ADMIN] {user_id} desbane usuario {target_user_id} en chat {chat_id}")
        await notify_main_admin(context, user_id, update.effective_user.first_name, "Desbane usuario", str(target_user_id))
    except ValueError:
        await update.message.reply_text(" ID de usuario invlido.")

async def verificar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para verificar el estado de membresia del usuario"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si el chat es permitido
    if not is_allowed_chat(chat_id, user_id):
        await update.message.reply_text("🚫 GRUPO NO PERMITIDO")
        return
    
    # Intentar verificar membresia
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_GROUP_ID, user_id=user_id)
        status = member.status
        
        status_emoji = {
            'creator': '👑',
            'administrator': '⭐',
            'member': '✅',
            'restricted': '⚠️',
            'left': '❌',
            'kicked': '🚫'
        }
        
        emoji = status_emoji.get(status, '❓')
        
        message = f"**Estado de Verificacion** {emoji}\n\n"
        message += f"Tu ID: `{user_id}` 👤\n"
        message += f"Grupo ID: `{REQUIRED_GROUP_ID}` 📋\n"
        message += f"Estado: **{status.upper()}** 📊\n\n"
        
        if status in ['member', 'administrator', 'creator', 'restricted']:
            message += "**Tienes acceso al bot** ✅"
        else:
            message += "**No tienes acceso al bot** ❌\n"
            message += f"Unete aqui: {REQUIRED_GROUP_LINK} 👉"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = str(e)
        
        message = "**ERROR DE CONFIGURACION** ⚠️\n\n"
        
        if "bot is not a member" in error_msg.lower() or "chat not found" in error_msg.lower():
            message += "**El bot NO esta en el grupo** 🚫\n\n"
            message += "**IMPORTANTE:** El bot debe estar en el grupo para funcionar ⚠️\n\n"
            message += "**Pasos para solucionarlo:** 🔧\n"
            message += "1. Agrega el bot al grupo\n"
            message += "2. Hazlo administrador del grupo\n"
            message += "3. Reinicia el bot\n\n"
            message += "**Mientras tanto, NADIE puede usar el bot** ❌"
        elif "forbidden" in error_msg.lower():
            message += "**El bot no tiene permisos de administrador** 🚫\n\n"
            message += "**IMPORTANTE:** El bot necesita ser admin ⚠️\n\n"
            message += "**Solucion:** 🔧\n"
            message += "1. Ve a la configuracion del grupo\n"
            message += "2. Busca al bot en la lista de miembros\n"
            message += "3. Hazlo administrador\n\n"
            message += "**Mientras tanto, NADIE puede usar el bot** ❌"
        else:
            message += f"**Error tecnico:** `{error_msg}` 🔴\n\n"
            message += "**El bot no puede verificar miembros** ❌\n"
            message += "Contacta al owner: 📞"
        
        keyboard = [
            [InlineKeyboardButton("Owner", url="https://t.me/sebas992269")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def precios_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra info de contacto"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si el chat es permitido
    if not is_allowed_chat(chat_id, user_id):
        await update.message.reply_text("🚫 GRUPO NO PERMITIDO")
        return
    
    keyboard = [
        [InlineKeyboardButton("Owner", url="https://t.me/sebas992269")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "**Contacta al owner para mas informacion:** 📞",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def horarios_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los horarios del servicio gratuito"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si el chat es permitido
    if not is_allowed_chat(chat_id, user_id):
        await update.message.reply_text("🚫 GRUPO NO PERMITIDO")
        return
    
    await update.message.reply_text(
        "**HORARIOS DE SERVICIO** ⏰\n\n"
        "**Horarios GRATIS:** 📅\n\n"
        "**Manana:** 🌅\n"
        "9:00 AM - 11:00 AM\n\n"
        "**Tarde:** 🌇\n"
        "12:00 PM - 3:00 PM\n\n"
        "──────────\n\n"
        "**Usuarios VIP:** 💎\n"
        "Acceso 24/7 sin restricciones ✅\n\n"
        "Usa /precios para contactar 📞",
        parse_mode='Markdown'
    )

async def cancelar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si el chat es permitido
    if not is_allowed_chat(chat_id, user_id):
        await update.message.reply_text("🚫 GRUPO NO PERMITIDO")
        return
    
    # Verificar primero si está baneado
    if auth_system.is_banned(user_id):
        await update.message.reply_text("❌ Estás baneado de nuestros servicios, si crees que es un error contacta al owner")
        return
    
    # Check authorization
    if not auth_system.can_use_bot(user_id, chat_id):
        if not auth_system.gratis_mode:
            keyboard = [
                [InlineKeyboardButton("Owner", url="https://t.me/sebas992269")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🔴 **Bot en Modo OFF**\n\n"
                "El bot está fuera del horario gratuito 🕒\n\n"
                "💰 **¿Necesitas usarlo ahora?**\n"
                "Contacta con el owner:\n\n"
                "✨ Pueden activarte el acceso premium",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
    
    # Check if user has an active order
    if user_id in user_data_store:
        # Get the type of order being cancelled
        tipo = user_data_store[user_id].get("tipo", "orden")
        
        # Remove user data to cancel the order
        del user_data_store[user_id]
        
        # Send confirmation message
        await update.message.reply_text("Se cancelo la operacion ✅")
    else:
        # No active order to cancel
        await update.message.reply_text("No tienes acciones activas, usa /comprobante para iniciar una 📋")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para fotos - actualmente no se usa"""
    pass

async def refe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda una foto como referencia cuando se responde a ella"""
    user_id = update.effective_user.id
    
    # Verificar si es admin
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("❌ Este comando solo est disponible para administradores.")
        return
    
    # Verificar si est respondiendo a un mensaje
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Debes responder a una foto con /refe para guardarla como referencia.")
        return
    
    # Verificar si el mensaje tiene una foto
    replied_message = update.message.reply_to_message
    if not replied_message.photo:
        await update.message.reply_text("❌ El mensaje debe contener una foto.")
        return
    
    try:
        # Obtener la foto de mayor calidad
        photo = replied_message.photo[-1]
        file_id = photo.file_id
        
        # Obtener informacin adicional
        admin_name = update.effective_user.first_name or "Admin"
        now = datetime.now(pytz.timezone("America/Bogota"))
        fecha = now.strftime("%d/%m/%Y %H:%M:%S")
        
        # Cargar referencias existentes
        referencias = cargar_referencias()
        
        # Agregar nueva referencia
        nueva_referencia = {
            "file_id": file_id,
            "guardado_por": admin_name,
            "user_id": user_id,
            "fecha": fecha,
            "numero": len(referencias) + 1
        }
        
        referencias.append(nueva_referencia)
        guardar_referencias(referencias)
        
        await update.message.reply_text(
            f"✅ **Referencia guardada**\n\n"
            f"📋 **Número:** #{nueva_referencia['numero']}\n"
            f"👤 **Guardado por:** {admin_name}\n"
            f"📅 **Fecha:** {fecha}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"Error al guardar referencia: {e}")
        await update.message.reply_text(f"❌ Error al guardar referencia: {str(e)}")

async def referencias_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra todas las referencias guardadas"""
    user_id = update.effective_user.id
    
    # Verificar si es admin
    if not auth_system.is_admin(user_id):
        await update.message.reply_text("❌ Este comando solo est disponible para administradores.")
        return
    
    try:
        referencias = cargar_referencias()
        
        if not referencias:
            await update.message.reply_text("📭 No hay referencias guardadas an.")
            return
        
        # Enviar las primeras 5 referencias
        await enviar_referencias_paginadas(update, context, referencias, 0)
        
    except Exception as e:
        logging.error(f"Error al mostrar referencias: {e}")
        await update.message.reply_text(f"❌ Error al mostrar referencias: {str(e)}")

async def enviar_referencias_paginadas(update_or_query, context: ContextTypes.DEFAULT_TYPE, referencias, offset):
    """Enva referencias en grupos de 5"""
    # Determinar si es un update o un callback_query
    if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query is not None:
        query = update_or_query.callback_query
        chat_id = query.message.chat_id
        is_callback = True
    else:
        chat_id = update_or_query.effective_chat.id
        is_callback = False
    
    total = len(referencias)
    fin = min(offset + 5, total)
    referencias_a_enviar = referencias[offset:fin]
    
    # Lista para guardar los message_ids de las fotos enviadas
    message_ids = []
    
    # Enviar cada referencia como foto (sin compresin usando send_document)
    for ref in referencias_a_enviar:
        caption = (
            f"📋 **Referencia #{ref['numero']}**\n"
            f"📋 Guardado por: {ref['guardado_por']}\n"
            f"📋 Fecha: {ref['fecha']}"
        )
        
        try:
            # Primero obtener el archivo
            file = await context.bot.get_file(ref['file_id'])
            # Descargar el archivo
            file_path = await file.download_to_drive()
            
            # Enviar como documento para evitar compresin
            with open(file_path, 'rb') as photo_file:
                msg = await context.bot.send_document(
                    chat_id=chat_id,
                    document=photo_file,
                    caption=caption,
                    parse_mode='Markdown',
                    filename=f"referencia_{ref['numero']}.jpg"
                )
            message_ids.append(msg.message_id)
            
            # Eliminar archivo temporal
            try:
                os.remove(file_path)
            except:
                pass
                
        except Exception as e:
            logging.error(f"Error al enviar referencia #{ref['numero']}: {e}")
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Error al enviar referencia #{ref['numero']}: {str(e)}"
            )
            message_ids.append(msg.message_id)
    
    # Si hay ms referencias, mostrar botn
    if fin < total:
        keyboard = [[InlineKeyboardButton(
            f"➡️ Enviar las siguientes 5 ({fin + 1}-{min(fin + 5, total)} de {total})",
            callback_data=f"ref_next_{fin}_{','.join(map(str, message_ids))}"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="👇 Presiona el botn para ver ms referencias:",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Todas las referencias han sido enviadas."
        )

async def referencias_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el callback de paginacin de referencias"""
    query = update.callback_query
    await query.answer()
    
    # Extraer datos del callback
    data_parts = query.data.split('_')
    offset = int(data_parts[2])
    message_ids_str = data_parts[3]
    message_ids = [int(mid) for mid in message_ids_str.split(',')]
    
    # Borrar mensajes anteriores
    for msg_id in message_ids:
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=msg_id
            )
        except Exception as e:
            logging.error(f"Error al borrar mensaje {msg_id}: {e}")
    
    # Borrar el mensaje del botn
    try:
        await query.message.delete()
    except:
        pass
    
    # Cargar referencias y enviar las siguientes
    referencias = cargar_referencias()
    await enviar_referencias_paginadas(update, context, referencias, offset)

async def apk_precios_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra info de contacto cuando presionan el botón"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Owner", url="https://t.me/sebas992269")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        "📞 **Contacta al owner para más información:**",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def fechas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa/desactiva el modo de fechas manuales"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si el chat es permitido
    if not is_allowed_chat(chat_id, user_id):
        await update.message.reply_text("🚫 GRUPO NO PERMITIDO")
        return
    
    # Verificar si está baneado
    if auth_system.is_banned(user_id):
        await update.message.reply_text("❌ Estás baneado de nuestros servicios")
        return
    
    # Verificar autorización
    if not auth_system.can_use_bot(user_id, chat_id):
        await update.message.reply_text("🚫 No tienes acceso al bot")
        return
    
    # Alternar modo de fechas manuales
    if user_id in fecha_manual_mode and fecha_manual_mode[user_id]:
        fecha_manual_mode[user_id] = False
        await update.message.reply_text(
            "🔄 **Modo Fecha Automática ACTIVADO**\n\n"
            "✅ Los comprobantes usarán la fecha actual automáticamente",
            parse_mode='Markdown'
        )
    else:
        fecha_manual_mode[user_id] = True
        await update.message.reply_text(
            "🔄 **Modo Fecha Manual ACTIVADO**\n\n"
            "✅ Ahora el bot te pedirá la fecha para cada comprobante\n"
            "📋 Puedes escribir la fecha como: lunes 2 2023, martes 15 enero 2024, etc.\n\n"
            "📋 Usa /fechas nuevamente para volver al modo automático",
            parse_mode='Markdown'
        )

async def refes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa/desactiva el modo de referencias manuales"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Verificar si el chat es permitido
    if not is_allowed_chat(chat_id, user_id):
        await update.message.reply_text("🚫 GRUPO NO PERMITIDO")
        return
    
    # Verificar si está baneado
    if auth_system.is_banned(user_id):
        await update.message.reply_text("❌ Estás baneado de nuestros servicios")
        return
    
    # Verificar autorización
    if not auth_system.can_use_bot(user_id, chat_id):
        await update.message.reply_text("🚫 No tienes acceso al bot")
        return
    
    # Alternar modo de referencias manuales
    if user_id in referencia_manual_mode and referencia_manual_mode[user_id]:
        referencia_manual_mode[user_id] = False
        await update.message.reply_text(
            "🔄 **Modo Referencia Automática ACTIVADO**\n\n"
            "✅ Los comprobantes generarán la referencia automáticamente",
            parse_mode='Markdown'
        )
    else:
        referencia_manual_mode[user_id] = True
        await update.message.reply_text(
            "🔄 **Modo Referencia Manual ACTIVADO**\n\n"
            "✅ Ahora el bot te pedirá la referencia para los comprobantes que la usan\n"
            "📋 Formato: M + 8 dígitos (Ejemplo: M12345678)\n\n"
            "📋 Usa /refes nuevamente para volver al modo automático",
            parse_mode='Markdown'
        )

def main():
    app = Application.builder().token("8290898091:AAHkCRcfKCMvJVe16FbAhcwYpTFaEUmKdAI").build()
    

    app.add_handler(CommandHandler("comprobante", start))
    app.add_handler(CommandHandler("start", start_redirect))
    app.add_handler(CommandHandler("fechas", fechas_command))
    app.add_handler(CommandHandler("refes", refes_command))
    app.add_handler(CommandHandler("precios", precios_command))
    app.add_handler(CommandHandler("horarios", horarios_command))
    app.add_handler(CommandHandler("gratis", gratis_command))
    app.add_handler(CommandHandler("off", off_command))
    app.add_handler(CommandHandler("agregar", agregar_command))
    app.add_handler(CommandHandler("eliminar", eliminar_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("cancelar", cancelar_command))
    app.add_handler(CommandHandler("verificar", verificar_command))
    app.add_handler(CommandHandler("refe", refe_command))
    app.add_handler(CommandHandler("referencias", referencias_command))
    app.add_handler(CallbackQueryHandler(apk_precios_callback, pattern="^apk_precios$"))
    app.add_handler(CallbackQueryHandler(referencias_callback, pattern="^ref_next_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
