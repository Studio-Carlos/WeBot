#!/usr/bin/env python3
"""
Ticket Monitor Bot
==================
Monitors a ticket resale page and sends notifications when tickets become available.

Usage:
    python main.py

Requirements:
    pip install playwright requests plyer
    playwright install chromium
"""

import time
import random
import subprocess
import re
from datetime import datetime

import requests
from playwright.sync_api import sync_playwright


# =============================================================================
# CONFIGURATION - Edit these values as needed
# =============================================================================

# Target URL to monitor
TARGET_URL = "https://www.ticketswap.fr/festival-tickets/radio-meuh-circus-festival-2026-la-clusaz-la-clusaz-2026-04-02-CVWqcs977h1jNpTpHXNbR/thursday-tickets/5442855"

# ntfy.sh topic for mobile notifications (change to your own topic)
NTFY_TOPIC = "billet_nantes_tracy_777"

# Check interval range (seconds) - randomized to avoid detection
# DOUBLED to be less aggressive (was 9-17)
MIN_SLEEP = 18
MAX_SLEEP = 34

# Warmup time (seconds) - wait for manual Cloudflare bypass + login
WARMUP_TIME = 120  # 2 minutes

# Alert loop interval when tickets found (seconds)
ALERT_INTERVAL = 5

# Browser settings
HEADLESS = False  # Set to False to see the browser window

# Realistic User-Agent for macOS Safari
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.1 Safari/605.1.15"
)


# =============================================================================
# NOTIFICATION FUNCTIONS
# =============================================================================

def send_mobile_notification(title: str, message: str) -> bool:
    """
    Send a push notification to mobile via ntfy.sh.
    
    Args:
        title: Notification title
        message: Notification body
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Remove emojis from title for header compatibility
        clean_title = title.encode('ascii', 'ignore').decode('ascii').strip()
        if not clean_title:
            clean_title = "Ticket Alert"
        
        response = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": clean_title,
                "Priority": "urgent",
                "Tags": "ticket,rotating_light"
            },
            timeout=10
        )
        response.raise_for_status()
        print(f"  📱 Mobile notification sent!")
        return True
    except requests.RequestException as e:
        print(f"  ⚠️  Mobile notification failed: {e}")
        return False


def send_desktop_notification(title: str, message: str) -> bool:
    """
    Send a native macOS desktop notification via osascript.
    
    Args:
        title: Notification title
        message: Notification body
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Use AppleScript for native macOS notifications (no dependencies)
        script = f'''
        display notification "{message}" with title "{title}" sound name "Glass"
        '''
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True
        )
        print(f"  🖥️  Desktop notification sent!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Desktop notification failed: {e}")
        return False
    except Exception as e:
        print(f"  ⚠️  Desktop notification failed: {e}")
        return False


def play_alert_sound() -> None:
    """
    Play the macOS system alert sound using afplay.
    Uses the built-in Glass sound for maximum attention.
    """
    try:
        # Use macOS built-in sound
        subprocess.run(
            ["afplay", "/System/Library/Sounds/Glass.aiff"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError:
        # Fallback to terminal bell
        print("\a", end="", flush=True)
    except FileNotFoundError:
        print("\a", end="", flush=True)


def trigger_all_alerts() -> None:
    """
    Trigger all notification channels at once.
    Called when tickets are detected.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    title = "🎟️ TICKETS AVAILABLE!"
    message = f"Tickets detected at {timestamp}!\n{TARGET_URL}"
    
    print(f"\n{'='*60}")
    print(f"🚨 TICKETS FOUND! - {timestamp}")
    print(f"{'='*60}")
    
    send_mobile_notification(title, message)
    send_desktop_notification(title, message)
    play_alert_sound()


# =============================================================================
# PAGE CHECKING LOGIC
# =============================================================================

def check_for_cloudflare_block(page) -> bool:
    """
    Detect if the page is blocked by Cloudflare or other bot detection.
    
    Args:
        page: Playwright page object
    
    Returns:
        True if blocked, False otherwise
    """
    # Get page content for analysis
    page_content = page.content().lower()
    page_title = page.title().lower()
    
    # Check for Cloudflare challenge elements first (most reliable)
    # Note: data-cf-beacon is just analytics, NOT a block indicator
    cf_selectors = [
        "#cf-challenge-running",
        "#challenge-running", 
        ".cf-browser-verification",
        "#cf-wrapper",
        "#challenge-form",
        "#cf-please-wait"
    ]
    
    for selector in cf_selectors:
        try:
            if page.locator(selector).count() > 0:
                print(f"  🔍 DEBUG: Cloudflare selector found: {selector}")
                return True
        except:
            pass
    
    # Check page title for block indicators
    block_titles = [
        "just a moment",
        "attention required",
        "access denied",
        "checking your browser"
    ]
    
    for title_check in block_titles:
        if title_check in page_title:
            print(f"  🔍 DEBUG: Blocked title found: '{title_check}' in '{page_title}'")
            return True
    
    # Check if main content is missing (common when blocked)
    # If the page has very little content, it might be a challenge page
    try:
        body_text = page.locator("body").inner_text()
        if len(body_text.strip()) < 100:
            # Very short page content might indicate a challenge
            if "verify" in page_content or "checking" in page_content:
                print(f"  🔍 DEBUG: Short page content detected ({len(body_text.strip())} chars)")
                return True
    except:
        pass
    
    return False


def send_block_notification() -> None:
    """
    Send notification when blocked by Cloudflare/bot detection.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    title = "⚠️ BOT BLOCKED!"
    message = f"Cloudflare/bot detection triggered at {timestamp}. Manual intervention may be needed."
    
    print(f"\n{'='*60}")
    print(f"🚫 BLOCKED BY CLOUDFLARE/BOT DETECTION - {timestamp}")
    print(f"{'='*60}")
    
    send_mobile_notification(title, message)
    send_desktop_notification(title, message)
    play_alert_sound()


def check_for_tickets(page) -> tuple[bool, bool]:
    """
    Check if tickets are available on the page.
    
    Logic:
        - Check for TicketSwap specific "X disponibles" text
        - If count > 0, tickets are available
        - Also check for fallback purchase buttons
    
    Args:
        page: Playwright page object
    
    Returns:
        Tuple of (tickets_available, is_blocked)
    """
    # First check for Cloudflare/bot block
    if check_for_cloudflare_block(page):
        return (False, True)
    
    page_text = page.locator("body").inner_text()
    lower_text = page_text.lower()
    
    # 1. TicketSwap Specific Check: "X disponibles"
    # Note: Scrape shows "0disponibles" or "1disponible", so regex is flexible
    ts_match = re.search(r'(\d+)\s*disponibles?', page_text, re.IGNORECASE)
    if ts_match:
        count = int(ts_match.group(1))
        if count > 0:
            print(f"  ✅ TicketSwap: {count} ticket(s) AVAILABLE!")
            return (True, False)
        else:
            print(f"  ❌ TicketSwap: {count} disponibles (Aucun billet)")
            return (False, False)

    # 2. Check for purchase buttons (fallback)
    buy_button = page.locator("text=Acheter")
    add_to_cart = page.locator("text=Ajouter au panier")
    
    if buy_button.count() > 0 or add_to_cart.count() > 0:
        # Avoid false positives if "Aucun billet" is also present
        if "aucun billet disponible" not in lower_text:
            print("  ✅ Purchase button found!")
            return (True, False)
    
    # 3. Text-based fallback "X Billets"
    ticket_pattern = re.compile(r'(\d+)\s*Billet', re.IGNORECASE)
    matches = ticket_pattern.findall(page_text)
    
    for count in matches:
        if int(count) > 0:
            print(f"  ✅ Found {count} ticket(s) matching 'Billet' pattern")
            return (True, False)
    
    # No tickets found
    print(f"  ❌ No availability found")
    return (False, False)


# =============================================================================
# MAIN MONITORING LOOP
# =============================================================================

def run_monitor() -> None:
    """
    Main function that runs the infinite monitoring loop.
    """
    print("\n" + "="*60)
    print("🎟️  TICKET MONITOR BOT")
    print("="*60)
    print(f"📍 URL: {TARGET_URL}")
    print(f"📱 ntfy topic: {NTFY_TOPIC}")
    print(f"⏱️  Check interval: {MIN_SLEEP}-{MAX_SLEEP}s")
    print(f"👁️  Headless: {HEADLESS}")
    print("="*60 + "\n")
    
    # Send test notification at startup
    print("🔔 Sending test notification...")
    test_title = "Ticket Monitor Started"
    test_message = f"Monitoring started for {TARGET_URL}"
    send_mobile_notification(test_title, test_message)
    send_desktop_notification(test_title, test_message)
    print("✅ Test notification sent! Check ntfy and macOS notifications.\n")
    with sync_playwright() as p:
        # Use WebKit (Safari) instead of Chrome - much better for Cloudflare bypass!
        user_data_dir = "/Users/Carlos/Documents/Cursor/Webot/browser_profile"
        
        print("🍎 Using WebKit (Safari) for better Cloudflare bypass...")
        print(f"   Profile location: {user_data_dir}")
        
        # Launch WebKit with persistent context (stores cookies)
        context = p.webkit.launch_persistent_context(
            user_data_dir,
            headless=HEADLESS,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            viewport={"width": 1440, "height": 900},
            locale="fr-FR",
            timezone_id="Europe/Paris",
            ignore_https_errors=True,
        )
        
        # Get the first page or create one
        if context.pages:
            page = context.pages[0]
        else:
            page = context.new_page()
        
        check_count = 0
        
        # =====================================================================
        # WARMUP PHASE: Let user manually pass Cloudflare and login
        # =====================================================================
        print("\n" + "="*60)
        print("⏳ WARMUP PHASE - Opening browser...")
        print("="*60)
        print("")
        print("👉 1. Wait for the page to load")
        print("👉 2. Click on the Cloudflare checkbox if prompted")
        print("👉 3. Login if needed")
        print("👉 4. Make sure the ticket page is visible and loaded")
        print("")
        print("="*60)
        
        # Navigate to page first
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        
        print("\n✅ Browser opened! Complete the steps above.")
        print("")
        input("🚀 Press ENTER when you're ready to start monitoring...")
        
        print("\n" + "="*60)
        print("🤖 MONITORING ACTIVE - Bot is now in control!")
        print("="*60 + "\n")
        
        # =====================================================================
        # MONITORING LOOP: Reload and check for tickets
        # =====================================================================
        while True:
            check_count += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                # Reload page (not full navigate, to keep session/cookies)
                print(f"[{check_count}] {timestamp} - Refreshing page...")
                page.reload(wait_until="domcontentloaded", timeout=30000)
                
                # Wait a bit for dynamic content to load
                page.wait_for_timeout(3000)
                
                # Check for tickets
                tickets_found, is_blocked = check_for_tickets(page)
                
                if is_blocked:
                    # Blocked by Cloudflare/bot detection
                    send_block_notification()
                elif tickets_found:
                    # TICKETS FOUND! Loop alerts until user stops
                    while True:
                        trigger_all_alerts()
                        print(f"\n⏳ Next alert in {ALERT_INTERVAL}s... (Ctrl+C to stop)")
                        time.sleep(ALERT_INTERVAL)
                else:
                    # No tickets yet
                    print(f"  ❌ No tickets available - Waiting list is active")
                
            except KeyboardInterrupt:
                raise  # Re-raise to exit cleanly
                
            except Exception as e:
                print(f"  ⚠️  Error during check: {type(e).__name__}: {e}")
                print("  🔄 Will retry on next iteration...")
            
            # Random sleep to avoid detection
            sleep_time = random.uniform(MIN_SLEEP, MAX_SLEEP)
            print(f"  💤 Sleeping for {sleep_time:.1f}s...\n")
            time.sleep(sleep_time)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        run_monitor()
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped by user. Goodbye!")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        raise
