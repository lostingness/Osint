#!/usr/bin/env python3
"""
OSINT Telegram Bot - Railway.com Compatible Version
Deploy with: main.py + requirements.txt + Procfile
"""

import os
import logging
import requests
import tempfile
import threading
import json
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ApplicationBuilder
)
from telegram.constants import ParseMode

# ====================== CONFIGURATION ======================
# REPLACE THESE WITH YOUR ACTUAL VALUES
TELEGRAM_BOT_TOKEN = "8329681179:AAG1GONFFmEDRYH-MQwCw7REVugNXEAjZEQ"
ADMIN_USER_IDS = [20022466, 8488687671]  # Add more admin IDs as needed

# For Railway webhooks (auto-generated)
WEBHOOK_URL = os.environ.get("RAILWAY_STATIC_URL", "") + "/webhook"
PORT = int(os.environ.get("PORT", 5000))

# API Endpoints
TG_INFO_API = "https://my.lostingness.site/tgn.php?value={}"
UNIVERSAL_API = "https://my.lostingness.site/infox.php?type={}"

# Flask app
app = Flask(__name__)

# ====================== HELPER FUNCTIONS ======================
def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_USER_IDS

def fetch_telegram_info(user_id: str):
    """Fetch Telegram information using User ID only"""
    try:
        # Validate numeric input
        if not str(user_id).isdigit():
            return {"success": False, "error": "Invalid input. Telegram User ID must be numeric."}
        
        url = TG_INFO_API.format(user_id)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        return {"success": False, "error": f"API Error: {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def fetch_universal_info(query: str):
    """Fetch information from Universal API"""
    try:
        query = str(query).strip()
        url = UNIVERSAL_API.format(query)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # Handle different response formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                return []
        return []
    except Exception as e:
        print(f"Universal API Error: {e}")
        return []

def format_telegram_info(data: dict) -> str:
    """Format Telegram API response with emojis"""
    if not data.get("success"):
        return "❌ *No information found for this Telegram ID*\n\nPlease check the ID and try again."
    
    user = data
    account = data.get("account_info", {})
    phone = data.get("phone_info", {})
    
    formatted = "🔍 *TELEGRAM INFORMATION*\n"
    formatted += "═" * 35 + "\n\n"
    
    # Basic Info
    formatted += "👤 *Basic Information:*\n"
    formatted += f"   • 🆔 ID: `{user.get('user_id', 'N/A')}`\n"
    formatted += f"   • 📛 Name: {account.get('first_name', 'N/A')}\n"
    if account.get('last_name'):
        formatted += f"   • 📛 Last Name: {account.get('last_name')}\n"
    formatted += f"   • 🤖 Bot: {'✅ Yes' if account.get('is_bot') else '❌ No'}\n"
    formatted += f"   • 🟢 Active: {'✅ Yes' if account.get('is_active') else '❌ No'}\n\n"
    
    # Phone Info
    if phone:
        formatted += "📱 *Phone Information:*\n"
        formatted += f"   • 🌍 Country: {phone.get('country', 'N/A')}\n"
        formatted += f"   • 📞 Number: `{phone.get('full_number', 'N/A')}`\n\n"
    
    # Activity Info
    formatted += "📊 *Activity Statistics:*\n"
    formatted += f"   • 💬 Total Messages: {account.get('total_messages', 0):,}\n"
    formatted += f"   • 👥 Total Groups: {account.get('total_groups', 0)}\n"
    formatted += f"   • 💬 Group Messages: {account.get('messages_in_groups', 0)}\n"
    formatted += f"   • 👑 Admin Groups: {account.get('admin_in_groups', 0)}\n"
    formatted += f"   • 🔄 Usernames Used: {account.get('usernames_count', 0)}\n"
    formatted += f"   • 📛 Names Used: {account.get('names_count', 0)}\n\n"
    
    # Dates
    if account.get('first_message_date'):
        first_date = account['first_message_date'].replace('T', ' ').replace('Z', '')
        formatted += f"   • 🕐 First Message: `{first_date}`\n"
    if account.get('last_message_date'):
        last_date = account['last_message_date'].replace('T', ' ').replace('Z', '')
        formatted += f"   • 🕐 Last Message: `{last_date}`\n"
    
    formatted += "\n" + "═" * 35 + "\n"
    formatted += "⚡ *Powered by @phenion*"
    
    return formatted

def create_universal_txt_file(data_list: list, query: str):
    """Create .txt file with Universal Info results"""
    if not data_list:
        return None
    
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.txt', 
            delete=False, 
            encoding='utf-8'
        )
        
        # Write header
        temp_file.write("=" * 60 + "\n")
        temp_file.write("🌐 UNIVERSAL INFORMATION LOOKUP RESULTS\n")
        temp_file.write("=" * 60 + "\n\n")
        temp_file.write(f"Search Query: {query}\n")
        temp_file.write(f"Search Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        temp_file.write(f"Total Results: {len(data_list)}\n")
        temp_file.write("=" * 60 + "\n\n")
        
        # Write each result
        for i, data in enumerate(data_list, 1):
            temp_file.write(f"📄 RESULT {i} of {len(data_list)}\n")
            temp_file.write("-" * 40 + "\n\n")
            
            temp_file.write("👤 PERSONAL INFORMATION:\n")
            if data.get('name'):
                temp_file.write(f"   • Full Name: {data['name']}\n")
            if data.get('father_name'):
                temp_file.write(f"   • Father's Name: {data['father_name']}\n")
            if data.get('id_number'):
                temp_file.write(f"   • ID Number: {data['id_number']}\n")
            
            temp_file.write("\n📱 CONTACT DETAILS:\n")
            if data.get('mobile'):
                temp_file.write(f"   • Mobile: {data['mobile']}\n")
            if data.get('alt_mobile'):
                temp_file.write(f"   • Alt Mobile: {data['alt_mobile']}\n")
            if data.get('email'):
                temp_file.write(f"   • Email: {data['email']}\n")
            if data.get('circle'):
                temp_file.write(f"   • Operator: {data['circle']}\n")
            
            if data.get('address'):
                temp_file.write("\n🏠 ADDRESS:\n")
                address_parts = data['address'].split('!')
                for part in address_parts:
                    if part.strip():
                        temp_file.write(f"   • {part.strip()}\n")
            
            temp_file.write("\n" + "=" * 40 + "\n\n")
        
        # Write footer
        temp_file.write("=" * 60 + "\n")
        temp_file.write("🔐 This information is confidential\n")
        temp_file.write("⚡ Powered by @phenion\n")
        temp_file.write("=" * 60 + "\n")
        
        temp_file.close()
        return temp_file.name
    except Exception as e:
        print(f"Error creating text file: {e}")
        return None

# ====================== TELEGRAM BOT HANDLERS ======================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("📞 Contact Admin", url="https://t.me/phenion")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""
🚫 *ACCESS DENIED*

This bot is for authorized personnel only.

📞 *Contact Admin:* @phenion

🔑 *Your User ID:* `{user_id}`

_If you are an admin, add your ID to the bot configuration._
        """
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return
    
    # Admin user - show main menu
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu with options"""
    user_id = update.effective_user.id
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("🔍 Telegram Info", callback_data="tg_info")],
        [InlineKeyboardButton("🌐 Universal Info", callback_data="universal_info")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = f"""
✨ *Welcome to OSINT Bot* ✨

👤 *User:* {update.effective_user.first_name or 'Admin'}
🆔 *ID:* `{user_id}`
🎯 *Status:* ✅ **ADMIN ACCESS**
📊 *Access:* 🔓 **UNLIMITED**

*Select an option below:*
    """
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                welcome_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                welcome_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    except Exception as e:
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Admin access required!", show_alert=True)
        return
    
    if query.data == "tg_info":
        await query.edit_message_text(
            "📱 *Telegram Information Lookup*\n\n"
            "Please send me a Telegram User ID (numeric only).\n"
            "Example: `8190291080`\n\n"
            "⚠️ *Note:*\n"
            "• Only User ID is accepted\n"
            "• No usernames or phone numbers\n"
            "• Input must be numeric",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['waiting_for'] = 'tg_info'
        
    elif query.data == "universal_info":
        await query.edit_message_text(
            "🌐 *Universal Information Lookup*\n\n"
            "Please send me:\n"
            "• 📱 Mobile Number\n"
            "• 📧 Email Address\n"
            "• 🆔 Aadhaar Number\n\n"
            "Example: `8200704994` or `example@email.com`\n\n"
            "📝 *Note:* Results will be sent as .txt file",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['waiting_for'] = 'universal_info'
        
    elif query.data == "help":
        help_message = """
❓ *Help & Instructions*

🔍 *Telegram Info:*
   • Enter Telegram User ID (numeric only)
   • No usernames or phone numbers
   • Example: `8190291080`

🌐 *Universal Info:*
   • Enter Mobile Number, Email, or Aadhaar
   • Results sent as .txt file
   • Example: `8200704994` or `example@email.com`

⚙️ *Admin Features:*
   • Unlimited queries
   • Direct API access
   • .txt file export

⚠️ *Important:*
   • This bot is for authorized use only
   • Respect privacy laws
   • Keep information secure

👑 *Bot Owner:* @phenion
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    elif query.data == "back_to_menu":
        await show_main_menu(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages"""
    user_id = update.effective_user.id
    
    # Check if user is admin
    if not is_admin(user_id):
        await update.message.reply_text(
            "🚫 *Access Denied*\n\n"
            "This bot is for authorized personnel only.\n"
            "Contact @phenion for access.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message_text = update.message.text.strip()
    
    if 'waiting_for' not in context.user_data:
        # Show main menu if no action is expected
        keyboard = [[InlineKeyboardButton("📋 Main Menu", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Please use the buttons to select an option.",
            reply_markup=reply_markup
        )
        return
    
    # Show processing message
    processing_msg = await update.message.reply_text("🔄 *Processing your request...*")
    
    try:
        if context.user_data['waiting_for'] == 'tg_info':
            # Validate: Only numeric input allowed (Telegram User ID)
            if not message_text.isdigit():
                await processing_msg.edit_text(
                    "❌ *Invalid Input*\n\n"
                    "Please enter a valid Telegram User ID (numeric only).\n"
                    "Example: `8190291080`\n\n"
                    "⚠️ Do not enter:\n"
                    "• Usernames (like @username)\n"
                    "• Phone numbers (like +919876543210)\n"
                    "• Non-numeric characters",
                    parse_mode=ParseMode.MARKDOWN
                )
                context.user_data.pop('waiting_for', None)
                return
            
            # Fetch data
            data = fetch_telegram_info(message_text)
            
            if data.get("success"):
                formatted = format_telegram_info(data)
                
                # Check message length (Telegram limit: 4096 chars)
                if len(formatted) > 4000:
                    # Split message if too long
                    parts = [formatted[i:i+4000] for i in range(0, len(formatted), 4000)]
                    for i, part in enumerate(parts):
                        if i == 0:
                            await processing_msg.edit_text(part, parse_mode=ParseMode.MARKDOWN)
                        else:
                            await update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
                else:
                    await processing_msg.edit_text(
                        formatted,
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await processing_msg.edit_text(
                    f"❌ *No information found*\n\n"
                    f"Could not find information for User ID: `{message_text}`\n\n"
                    f"Possible reasons:\n"
                    f"• Invalid User ID\n"
                    f"• Account is private\n"
                    f"• API temporarily unavailable",
                    parse_mode=ParseMode.MARKDOWN
                )
        
        elif context.user_data['waiting_for'] == 'universal_info':
            # Fetch data
            data = fetch_universal_info(message_text)
            
            if data:
                # Create .txt file
                txt_file_path = create_universal_txt_file(data, message_text)
                
                if txt_file_path:
                    # Get file size
                    file_size = os.path.getsize(txt_file_path)
                    
                    # Send file
                    with open(txt_file_path, 'rb') as file:
                        await processing_msg.delete()  # Delete processing message
                        
                        await update.message.reply_document(
                            document=file,
                            filename=f"universal_info_{message_text}.txt",
                            caption=f"🌐 *Universal Information Results*\n\n"
                                   f"🔍 Query: `{message_text}`\n"
                                   f"📄 Results: {len(data)}\n"
                                   f"📦 File Size: {file_size:,} bytes\n\n"
                                   f"📝 *Open file to view detailed information*",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    
                    # Clean up temp file
                    os.unlink(txt_file_path)
                else:
                    await processing_msg.edit_text(
                        "❌ *Error creating file*\n\n"
                        "Could not create .txt file for results.",
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await processing_msg.edit_text(
                    f"❌ *No information found*\n\n"
                    f"Could not find information for: `{message_text}`\n\n"
                    f"Try different search terms.",
                    parse_mode=ParseMode.MARKDOWN
                )
    
    except Exception as e:
        error_msg = str(e)[:200]  # Limit error message length
        await processing_msg.edit_text(
            f"❌ *Error occurred*\n\n"
            f"Error: `{error_msg}`\n\n"
            f"Please try again later.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Clear waiting state
    context.user_data.pop('waiting_for', None)
    
    # Show back to menu button
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ *Query Completed*\n\nWhat would you like to do next?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin management command"""
    user_id = update.effective_user.id
    
    # Only allow existing admins
    if not is_admin(user_id):
        await update.message.reply_text(
            "🚫 *Access Denied*\n\n"
            "This command is for admins only.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check if command has arguments
    if context.args:
        action = context.args[0].lower()
        
        if action == "list":
            # List all admin IDs
            admin_list = "\n".join([f"• `{admin_id}`" for admin_id in ADMIN_USER_IDS])
            message = f"""
👑 *Current Admin IDs* 👑

{admin_list}

Total Admins: {len(ADMIN_USER_IDS)}

To add new admin, edit ADMIN_USER_IDS list in main.py.
            """
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        
        elif action == "count":
            # Count admins
            await update.message.reply_text(
                f"👑 Total Admins: `{len(ADMIN_USER_IDS)}`",
                parse_mode=ParseMode.MARKDOWN
            )
        
        elif action == "check":
            # Check specific ID
            if len(context.args) > 1:
                check_id = context.args[1]
                if check_id.isdigit():
                    is_admin_user = int(check_id) in ADMIN_USER_IDS
                    status = "✅ ADMIN" if is_admin_user else "❌ NOT ADMIN"
                    await update.message.reply_text(
                        f"User ID `{check_id}`: {status}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text(
                        "Invalid ID. Please provide numeric user ID.",
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.message.reply_text(
                    "Please provide user ID to check.\n"
                    "Usage: `/admin check USER_ID`",
                    parse_mode=ParseMode.MARKDOWN
                )
    else:
        # Show admin help
        help_text = f"""
👑 *Admin Management Commands*

`/admin list` - List all admin IDs
`/admin count` - Show total admin count
`/admin check USER_ID` - Check if user is admin

📝 *Current Bot Info:*
• Bot Token: `{TELEGRAM_BOT_TOKEN[:10]}...{TELEGRAM_BOT_TOKEN[-10:]}`
• Total Admins: `{len(ADMIN_USER_IDS)}`
• Bot Status: ✅ **RUNNING**
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# ====================== FLASK ROUTES FOR RAILWAY ======================
@app.route('/')
def home():
    """Root endpoint for Railway health checks"""
    return jsonify({
        "status": "online",
        "service": "Telegram OSINT Bot",
        "admin_count": len(ADMIN_USER_IDS),
        "message": "Bot is running on Railway"
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram (if using webhooks instead of polling)"""
    try:
        # Parse the request
        update_data = request.get_json()
        if update_data:
            # Create update object
            update = Update.de_json(update_data, application.bot)
            # Process update asynchronously
            application.create_task(
                application.process_update(update)
            )
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 400

# ====================== BOT SETUP FUNCTION ======================
def setup_bot():
    """Setup and run the Telegram bot"""
    global application
    
    # Create bot application
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("="*50)
    print("🤖 OSINT BOT - RAILWAY VERSION")
    print("="*50)
    print(f"✅ Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...{TELEGRAM_BOT_TOKEN[-10:]}")
    print(f"✅ Admin IDs: {ADMIN_USER_IDS}")
    print(f"✅ Total Admins: {len(ADMIN_USER_IDS)}")
    print("✅ Features:")
    print("   • 📱 Telegram User ID Lookup")
    print("   • 🌐 Universal Info (.txt file output)")
    print("   • 🔐 Admin-Only Access")
    print("   • 🚂 Railway Compatible")
    print("="*50)
    
    # Check if we should use webhooks or polling
    if WEBHOOK_URL and WEBHOOK_URL != "/webhook":
        # Use webhooks (for production on Railway)
        print(f"🌐 Setting up webhook: {WEBHOOK_URL}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
        )
    else:
        # Use polling (for local testing or if no webhook URL)
        print("🔄 Using polling mode...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )

# ====================== MAIN EXECUTION ======================
if __name__ == "__main__":
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=setup_bot, daemon=True)
    bot_thread.start()
    
    print(f"🌐 Starting Flask server on port {PORT}...")
    print("📱 Bot is ready! Use /start in Telegram")
    print("⚡ Press Ctrl+C to stop\n")
    
    # Start Flask app
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)