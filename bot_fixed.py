import os
import asyncio
import logging
from datetime import datetime
from typing import Set
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from telegram.constants import ParseMode
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

# Import our fixed modules
from database.connection import get_db_manager, get_db_session
from services.admin_service import get_admin_service
from services.user_service import get_user_service
from utils.validators import validate_instagram_link, extract_shortcode_from_url, validate_email, validate_usdt_address
from utils.helpers import paginate_list, format_views, calculate_payout
from apify_client import get_apify_client

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = set(map(int, ADMIN_IDS_STR.split(","))) if ADMIN_IDS_STR.strip() else set()
PORT = int(os.getenv("PORT", 8000))
LOG_GROUP_ID_STR = os.getenv("LOG_GROUP_ID", "0")
LOG_GROUP_ID = int(LOG_GROUP_ID_STR) if LOG_GROUP_ID_STR.isdigit() else None
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Validate required environment variables
if not all([TOKEN, DATABASE_URL, APIFY_TOKEN]):
    print("❌ BOT_TOKEN, DATABASE_URL, and APIFY_TOKEN must be set in .env")
    exit(1)

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# FastAPI health check
app_fastapi = FastAPI()

@app_fastapi.get("/")
async def root():
    return {"message": "Bot is running 🚀"}

@app_fastapi.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

async def start_health_check_server():
    """Start the health check server"""
    config = uvicorn.Config(app_fastapi, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

# Initialize services
admin_service = get_admin_service(ADMIN_IDS)
user_service = get_user_service()

def debug_handler(fn):
    """Decorator for debugging and error handling"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if LOG_GROUP_ID and update.message:
            user = update.effective_user
            name = user.full_name
            handle = f"@{user.username}" if user.username else ""
            text = update.message.text or ""
            try:
                await context.bot.send_message(LOG_GROUP_ID, f"{name} {handle}: {text}")
            except Exception as e:
                logger.error(f"Failed to send log message: {e}")
        
        try:
            # Check if user is banned
            if update.effective_user:
                is_banned = await user_service.is_banned(update.effective_user.id)
                if is_banned:
                    await update.message.reply_text("❌ You are banned from using this bot.")
                    return
            
            return await fn(update, context)
        except Exception as e:
            logger.exception("Handler error")
            if update.message:
                await update.message.reply_text(f"⚠️ An error occurred: {str(e)}")
            raise
    return wrapper

@debug_handler
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - register user and show help"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Create user account if it doesn't exist
    user_created = await user_service.create_user(user_id, username)
    
    if user_created:
        welcome_msg = f"🎉 Welcome to Instagram Reel Tracker Bot, {username}!\n\n"
        welcome_msg += "✅ Your account has been created successfully!\n\n"
    else:
        welcome_msg = f"👋 Welcome back, {username}!\n\n"
    
    # Show help text
    help_text = """🤖 <b>Instagram Reel Tracker Bot</b>

📋 <b>Available Commands:</b>
• <code>/submit &lt;url&gt;</code> - Submit Instagram reel URLs for tracking
• <code>/profile</code> - View your profile and statistics  
• <code>/addusdt &lt;address&gt;</code> - Add USDT ERC20 payment address
• <code>/addpaypal &lt;email&gt;</code> - Add PayPal payment email
• <code>/addupi &lt;address&gt;</code> - Add UPI payment address
• <code>/addaccount &lt;instagram_handle&gt;</code> - Request to link Instagram account

💡 <b>Getting Started:</b>
1. Add at least one payment method (USDT, PayPal, or UPI)
2. Request to link your Instagram account with <code>/addaccount</code>
3. Wait for admin approval
4. Start submitting reels with <code>/submit</code>

📊 <b>Features:</b>
• Track Instagram reel views, likes, and comments
• Automatic view updates
• Detailed statistics and analytics
• Secure payment processing

❓ Need help? Contact an admin for support."""

    if await admin_service.is_admin(user_id):
        help_text += """

🔧 <b>Admin Commands:</b>
• <code>/userstats</code> - View user statistics
• <code>/currentaccounts</code> - View linked accounts
• <code>/banuser &lt;user_id&gt;</code> - Ban a user
• <code>/unban &lt;user_id&gt;</code> - Unban a user
• <code>/broadcast &lt;message&gt;</code> - Send message to all users
• <code>/forceupdate</code> - Force update all reel views
• <code>/addadmin &lt;user_id&gt;</code> - Add admin
• <code>/removeadmin &lt;user_id&gt;</code> - Remove admin
• <code>/review &lt;user_id&gt;</code> - Review account requests"""

    await update.message.reply_text(welcome_msg + help_text, parse_mode=ParseMode.HTML)

@debug_handler
async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reel submission with improved error handling"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    try:
        # Get user data
        user_data = await user_service.get_user(user_id)
        if not user_data:
            await update.message.reply_text("❌ You need to register first. Use /start to begin.")
            return
        
        # Check if user is approved (or if user is admin)
        is_user_admin = await admin_service.is_admin(user_id)
        if not user_data["approved"] and not is_user_admin:
            await update.message.reply_text("❌ Your account is pending approval. Please wait for admin approval.")
            return
        
        # Check cooldown
        if user_data["last_submission"]:
            time_since_last = datetime.now() - user_data["last_submission"]
            cooldown_minutes = 5  # 5 minute cooldown
            if time_since_last.total_seconds() < cooldown_minutes * 60:
                remaining = cooldown_minutes * 60 - time_since_last.total_seconds()
                await update.message.reply_text(f"⏰ Please wait {int(remaining/60)} minutes and {int(remaining%60)} seconds before submitting again.")
                return
        
        # Get the message text
        message_text = update.message.text.strip()
        if not message_text or message_text == '/submit':
            await update.message.reply_text("📝 Please provide Instagram reel URLs after the /submit command.\n\nExample: `/submit https://instagram.com/reel/ABC123/`")
            return
        
        # Extract URLs from message
        urls = []
        
        # Remove the /submit command and get the rest
        if message_text.startswith('/submit'):
            url_part = message_text[7:].strip()  # Remove '/submit' and whitespace
            if url_part:
                # Split by whitespace to handle multiple URLs
                potential_urls = url_part.split()
                for url in potential_urls:
                    url = url.strip()
                    if url:
                        # Clean up the URL
                        if 'instagram.com' in url or url.startswith('http'):
                            urls.append(url)
                        elif len(url) > 5:  # Assume it's a shortcode
                            urls.append(f"https://www.instagram.com/reel/{url}/")
        
        if not urls:
            await update.message.reply_text("❌ No valid Instagram URLs found. Please provide valid Instagram reel URLs.")
            return
        
        # Validate URLs and check for duplicates
        valid_urls = []
        invalid_urls = []
        duplicate_urls = []
        
        async with await get_db_session() as session:
            for url in urls:
                if validate_instagram_link(url):
                    # Extract shortcode and check if it already exists
                    shortcode = extract_shortcode_from_url(url)
                    if shortcode:
                        from sqlalchemy import text
                        existing = await session.execute(
                            text("SELECT 1 FROM reels WHERE shortcode = :sc"),
                            {"sc": shortcode}
                        )
                        if existing.fetchone():
                            duplicate_urls.append(url)
                        else:
                            valid_urls.append(url)
                    else:
                        invalid_urls.append(url)
                else:
                    invalid_urls.append(url)
        
        if not valid_urls:
            error_msg = "❌ No valid new Instagram reel URLs found."
            if duplicate_urls:
                error_msg += f"\n\n🔄 {len(duplicate_urls)} URL(s) already exist in database."
            if invalid_urls:
                error_msg += f"\n\n❌ {len(invalid_urls)} invalid URL(s) were skipped."
            await update.message.reply_text(error_msg)
            return
        
        # Process the valid URLs (simplified for this example)
        processing_msg = await update.message.reply_text(f"🔄 Processing {len(valid_urls)} reel(s)...")
        
        try:
            # Create Apify task for scraping
            apify_client = get_apify_client()
            task_id = await apify_client.create_scraping_task(valid_urls, "single")
            
            await processing_msg.edit_text(f"📋 Task created: {task_id}\n🔄 Processing {len(valid_urls)} reel(s)...")
            
            # Get results
            result = await apify_client.get_task_results(task_id, wait=True, timeout=300)
            
            if result["status"] != "completed":
                raise Exception(f"Task failed: {result.get('task_info', {}).get('error', 'Unknown error')}")
            
            # Process results and add to database
            successful_reels = []
            failed_reels = []
            
            async with await get_db_session() as session:
                from sqlalchemy import text
                try:
                    for item in result.get("results", []):
                        if item.get("success", False):
                            url = item.get("url")
                            shortcode = extract_shortcode_from_url(url)
                            
                            if shortcode:
                                # Insert new reel entry
                                await session.execute(
                                    text("""
                                        INSERT INTO reels (user_id, shortcode, url, username, views, likes, comments, caption, media_url, submitted_at, last_updated)
                                        VALUES (:user_id, :shortcode, :url, :username, :views, :likes, :comments, :caption, :media_url, :submitted_at, :last_updated)
                                    """),
                                    {
                                        "user_id": user_id,
                                        "shortcode": shortcode,
                                        "url": url,
                                        "username": item.get("username", ""),
                                        "views": item.get("views", 0),
                                        "likes": item.get("likes", 0),
                                        "comments": item.get("comments", 0),
                                        "caption": item.get("caption", "")[:500],  # Limit caption length
                                        "media_url": item.get("media_url", ""),
                                        "submitted_at": datetime.now(),
                                        "last_updated": datetime.now()
                                    }
                                )
                                
                                successful_reels.append({
                                    "shortcode": shortcode,
                                    "username": item.get("username", ""),
                                    "views": item.get("views", 0)
                                })
                        else:
                            failed_reels.append({"url": item.get("url", "unknown"), "error": item.get("error", "Unknown error")})
                    
                    # Update user statistics
                    if successful_reels:
                        new_total_views = user_data["total_views"] + sum(reel["views"] for reel in successful_reels)
                        new_total_reels = user_data["total_reels"] + len(successful_reels)
                        new_used_slots = user_data["used_slots"] + len(successful_reels)
                        
                        await user_service.update_user_stats(
                            user_id, 
                            total_views=new_total_views,
                            total_reels=new_total_reels,
                            used_slots=new_used_slots
                        )
                    
                    await session.commit()
                    
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Database error in submit: {str(e)}")
                    raise Exception(f"Database error: {str(e)}")
            
            # Send results to user
            if successful_reels:
                result_text = f"✅ Successfully added {len(successful_reels)} reel(s):\n\n"
                for reel in successful_reels[:5]:  # Show first 5
                    result_text += f"📊 @{reel['username']} - {reel['views']:,} views\n"
                
                if len(successful_reels) > 5:
                    result_text += f"\n... and {len(successful_reels) - 5} more reels"
                
                new_total_views = user_data["total_views"] + sum(reel["views"] for reel in successful_reels)
                new_total_reels = user_data["total_reels"] + len(successful_reels)
                
                result_text += f"\n\n📈 Your total: {new_total_reels} reels, {new_total_views:,} views"
                
                await processing_msg.edit_text(result_text)
            
            if failed_reels:
                error_text = f"❌ {len(failed_reels)} reel(s) could not be processed:\n\n"
                for fail in failed_reels[:3]:  # Show first 3 failures
                    error_text += f"• {fail['url'][:50]}...\n  └ {fail['error']}\n\n"
                
                if len(failed_reels) > 3:
                    error_text += f"... and {len(failed_reels) - 3} more issues"
                
                await update.message.reply_text(error_text)
            
        except Exception as e:
            logger.error(f"Error in submit task processing: {str(e)}")
            await processing_msg.edit_text("❌ An error occurred while processing your reels. Please try again later.")
            
    except Exception as e:
        logger.error(f"Error in submit command: {str(e)}")
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

@debug_handler
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile with statistics"""
    user_id = update.effective_user.id
    
    try:
        user_data = await user_service.get_user(user_id)
        if not user_data:
            await update.message.reply_text("❌ User not found. Use /start to register.")
            return
        
        # Get payment details
        async with await get_db_session() as session:
            from sqlalchemy import text
            payment_result = await session.execute(
                text("SELECT usdt_address, paypal_email, upi_address FROM payment_details WHERE user_id = :u"),
                {"u": user_id}
            )
            payment_data = payment_result.fetchone()
            
            # Get linked accounts
            accounts_result = await session.execute(
                text("SELECT insta_handle FROM allowed_accounts WHERE user_id = :u"),
                {"u": user_id}
            )
            accounts = [row[0] for row in accounts_result.fetchall()]
        
        # Build profile message
        payout = calculate_payout(user_data["total_views"])
        
        msg = [
            "👤 <b>Your Profile</b>",
            f"• Total Views: <b>{user_data['total_views']:,}</b>",
            f"• Total Reels: <b>{user_data['total_reels']}</b>",
            f"• Slots Used: <b>{user_data['used_slots']}/{user_data['max_slots']}</b>",
            f"• Payable Amount: <b>${payout:.2f}</b>",
            f"• Account Status: <b>{'Approved' if user_data['approved'] else 'Pending'}</b>",
            "",
            "📸 <b>Linked Accounts:</b>"
        ]
        
        if accounts:
            msg.extend([f"• @{account}" for account in accounts])
        else:
            msg.append("• No accounts linked")
        
        msg.append("\n💳 <b>Payment Methods:</b>")
        
        if payment_data:
            usdt, paypal, upi = payment_data
            if usdt:
                msg.append(f"• USDT: <code>{usdt}</code>")
            if paypal:
                msg.append(f"• PayPal: <code>{paypal}</code>")
            if upi:
                msg.append(f"• UPI: <code>{upi}</code>")
            
            if not any([usdt, paypal, upi]):
                msg.append("• No payment methods added")
        else:
            msg.append("• No payment methods added")
        
        await update.message.reply_text("\n".join(msg), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Error in profile command: {str(e)}")
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

@debug_handler
async def addaccount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request to link an Instagram account"""
    if not context.args:
        return await update.message.reply_text(
            "❗ Please provide your Instagram handle.\n"
            "Usage: /addaccount <@handle>\n"
            "Example: /addaccount johndoe"
        )
    
    handle = context.args[0].lstrip("@")
    user_id = update.effective_user.id
    
    async with await get_db_session() as session:
        from sqlalchemy import text
        
        # Check if user already has 15 linked accounts
        account_count = (await session.execute(
            text("SELECT COUNT(*) FROM allowed_accounts WHERE user_id = :u"),
            {"u": user_id}
        )).scalar() or 0
        
        if account_count >= 15:
            return await update.message.reply_text(
                "❌ You have reached the maximum limit of 15 Instagram accounts.\n"
                "Please remove some accounts using /removeaccount before adding new ones."
            )
        
        # Check if this handle is already linked
        existing_handle = (await session.execute(
            text("SELECT 1 FROM allowed_accounts WHERE user_id = :u AND insta_handle = :h"),
            {"u": user_id, "h": handle}
        )).fetchone()
        
        if existing_handle:
            return await update.message.reply_text(f"❌ You have already linked @{handle}")
        
        # Check number of pending requests
        pending_count = (await session.execute(
            text("SELECT COUNT(*) FROM account_requests WHERE user_id = :u AND status = 'pending'"),
            {"u": user_id}
        )).scalar() or 0
        
        if pending_count >= 5:
            return await update.message.reply_text(
                "❌ You have reached the maximum limit of 5 pending requests.\n"
                "Please wait for admin approval of your existing requests before adding more."
            )
        
        # Check if there's already a pending request for this handle
        pending = (await session.execute(
            text("""
                SELECT 1 FROM account_requests 
                WHERE user_id = :u AND insta_handle = :h AND status = 'pending'
            """),
            {"u": user_id, "h": handle}
        )).fetchone()
        
        if pending:
            return await update.message.reply_text(
                f"❌ You already have a pending request for @{handle}.\n"
                "Please wait for admin approval."
            )
        
        # Create new request
        await session.execute(
            text("""
                INSERT INTO account_requests (user_id, insta_handle)
                VALUES (:u, :h)
            """),
            {"u": user_id, "h": handle}
        )
        await session.commit()
        
        # Notify admins
        admin_notifications_sent = 0
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"🔔 <b>New Account Link Request</b>\n\n"
                    f"👤 <b>User:</b> {update.effective_user.full_name}\n"
                    f"📱 <b>Username:</b> @{update.effective_user.username or 'None'}\n"
                    f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                    f"📸 <b>Instagram:</b> @{handle}\n"
                    f"📊 <b>Current Accounts:</b> {account_count}/15\n"
                    f"⏳ <b>Pending Requests:</b> {pending_count + 1}/5\n\n"
                    f"🔧 <b>Action Required:</b>\n"
                    f"Use <code>/review {user_id}</code> to approve/reject",
                    parse_mode=ParseMode.HTML
                )
                admin_notifications_sent += 1
                logger.info(f"✅ Admin notification sent to {admin_id}")
            except Exception as e:
                logger.error(f"❌ Failed to notify admin {admin_id}: {e}")
        
        # Log admin notification status
        if admin_notifications_sent == 0:
            logger.warning(f"⚠️ No admin notifications were sent for user {user_id} account request")
        else:
            logger.info(f"✅ {admin_notifications_sent} admin(s) notified about account request from user {user_id}")
        
        await update.message.reply_text(
            f"✅ Your request to link @{handle} has been submitted.\n"
            f"📊 Current accounts: {account_count}/15\n"
            f"⏳ Pending requests: {pending_count + 1}/5\n"
            f"📧 {admin_notifications_sent} admin(s) notified\n"
            "Please wait for admin approval."
        )

@debug_handler
async def addusdt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add USDT ERC20 address"""
    if not context.args:
        return await update.message.reply_text(
            "❗ Please provide your USDT ERC20 address.\n"
            "Usage: /addusdt <your usdt erc20 address>\n"
            "Example: /addusdt 0x1234567890abcdef1234567890abcdef12345678"
        )
    
    usdt_address = " ".join(context.args).strip()
    user_id = update.effective_user.id
    
    # Validate USDT address
    if not validate_usdt_address(usdt_address):
        return await update.message.reply_text("❌ Invalid USDT ERC20 address format")
    
    try:
        async with await get_db_session() as session:
            from sqlalchemy import text
            
            # Check if user exists
            user = (await session.execute(
                text("SELECT 1 FROM users WHERE user_id = :u"),
                {"u": user_id}
            )).fetchone()
            
            if not user:
                await user_service.create_user(user_id, update.effective_user.username)
            
            # Check if payment details exist
            existing = (await session.execute(
                text("SELECT id FROM payment_details WHERE user_id = :u"),
                {"u": user_id}
            )).fetchone()
            
            if existing:
                # Update USDT address
                await session.execute(
                    text("UPDATE payment_details SET usdt_address = :a WHERE user_id = :u"),
                    {"a": usdt_address, "u": user_id}
                )
                await update.message.reply_text(
                    f"✅ Updated USDT address:\n<code>{usdt_address}</code>",
                    parse_mode=ParseMode.HTML
                )
            else:
                # Insert new payment details with USDT
                await session.execute(
                    text("""
                        INSERT INTO payment_details (user_id, usdt_address)
                        VALUES (:u, :a)
                    """),
                    {"u": user_id, "a": usdt_address}
                )
                await update.message.reply_text(
                    f"✅ Added USDT address:\n<code>{usdt_address}</code>",
                    parse_mode=ParseMode.HTML
                )
            
            await session.commit()
            
    except Exception as e:
        logger.error(f"Error in addusdt: {str(e)}")
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

@debug_handler
async def addpaypal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add PayPal email"""
    if not context.args:
        return await update.message.reply_text(
            "❗ Please provide your PayPal email.\n"
            "Usage: /addpaypal <your paypal email>\n"
            "Example: /addpaypal john@example.com"
        )
    
    paypal_email = " ".join(context.args).strip()
    user_id = update.effective_user.id
    
    # Validate email
    if not validate_email(paypal_email):
        return await update.message.reply_text("❌ Invalid PayPal email format")
    
    try:
        async with await get_db_session() as session:
            from sqlalchemy import text
            
            # Check if user exists
            user = (await session.execute(
                text("SELECT 1 FROM users WHERE user_id = :u"),
                {"u": user_id}
            )).fetchone()
            
            if not user:
                await user_service.create_user(user_id, update.effective_user.username)
            
            # Check if payment details exist
            existing = (await session.execute(
                text("SELECT id FROM payment_details WHERE user_id = :u"),
                {"u": user_id}
            )).fetchone()
            
            if existing:
                # Update PayPal email
                await session.execute(
                    text("UPDATE payment_details SET paypal_email = :e WHERE user_id = :u"),
                    {"e": paypal_email, "u": user_id}
                )
                await update.message.reply_text(
                    f"✅ Updated PayPal email:\n<code>{paypal_email}</code>",
                    parse_mode=ParseMode.HTML
                )
            else:
                # Insert new payment details with PayPal
                await session.execute(
                    text("""
                        INSERT INTO payment_details (user_id, paypal_email)
                        VALUES (:u, :e)
                    """),
                    {"u": user_id, "e": paypal_email}
                )
                await update.message.reply_text(
                    f"✅ Added PayPal email:\n<code>{paypal_email}</code>",
                    parse_mode=ParseMode.HTML
                )
            
            await session.commit()
            
    except Exception as e:
        logger.error(f"Error in addpaypal: {str(e)}")
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

@debug_handler
async def addupi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add UPI address"""
    if not context.args:
        return await update.message.reply_text(
            "❗ Please provide your UPI address.\n"
            "Usage: /addupi <your upi address>\n"
            "Example: /addupi username@upi"
        )
    
    upi_address = " ".join(context.args).strip()
    user_id = update.effective_user.id
    
    # Basic validation
    if not upi_address or len(upi_address) < 3:
        return await update.message.reply_text("❌ Invalid UPI address")
    
    try:
        async with await get_db_session() as session:
            from sqlalchemy import text
            
            # Check if user exists
            user = (await session.execute(
                text("SELECT 1 FROM users WHERE user_id = :u"),
                {"u": user_id}
            )).fetchone()
            
            if not user:
                await user_service.create_user(user_id, update.effective_user.username)
            
            # Check if payment details exist
            existing = (await session.execute(
                text("SELECT id FROM payment_details WHERE user_id = :u"),
                {"u": user_id}
            )).fetchone()
            
            if existing:
                # Update UPI address
                await session.execute(
                    text("UPDATE payment_details SET upi_address = :a WHERE user_id = :u"),
                    {"a": upi_address, "u": user_id}
                )
                await update.message.reply_text(
                    f"✅ Updated UPI address:\n<code>{upi_address}</code>",
                    parse_mode=ParseMode.HTML
                )
            else:
                # Insert new payment details with UPI
                await session.execute(
                    text("""
                        INSERT INTO payment_details (user_id, upi_address)
                        VALUES (:u, :a)
                    """),
                    {"u": user_id, "a": upi_address}
                )
                await update.message.reply_text(
                    f"✅ Added UPI address:\n<code>{upi_address}</code>",
                    parse_mode=ParseMode.HTML
                )
            
            await session.commit()
            
    except Exception as e:
        logger.error(f"Error in addupi: {str(e)}")
        await update.message.reply_text(f"❌ An error occurred: {str(e)}")

async def run_bot():
    """Main bot runner"""
    try:
        # Initialize database
        db_manager = get_db_manager()
        await db_manager.init_database()
        
        # Start health check server
        asyncio.create_task(start_health_check_server())
        
        # Create bot application
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(CommandHandler("submit", submit))
        app.add_handler(CommandHandler("profile", profile))
        app.add_handler(CommandHandler("addaccount", addaccount))
        app.add_handler(CommandHandler("addusdt", addusdt))
        app.add_handler(CommandHandler("addpaypal", addpaypal))
        app.add_handler(CommandHandler("addupi", addupi))
        
        # Start bot
        logger.info("🚀 Starting bot...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        
        # Keep running
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        raise
    finally:
        # Cleanup
        try:
            await app.stop()
            await app.shutdown()
            
            # Close database connection
            db_manager = get_db_manager()
            await db_manager.close()
            
            # Close Apify client
            apify_client = get_apify_client()
            await apify_client.close()
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_bot())