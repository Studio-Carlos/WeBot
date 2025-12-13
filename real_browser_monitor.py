#!/usr/bin/env python3
"""
Ticket Monitor v4 - Background Edition
=======================================
- Runs in BACKGROUND - doesn't steal focus
- Verbose logs with ticket counts
- Test notification at startup
- Smart Cloudflare handling (45s wait)
"""

import time
import random
import subprocess
import re
import requests
from datetime import datetime
import os

# =============================================================================
# CONFIGURATION
# =============================================================================

TARGET_URL = "https://www.passetonbillet.fr/events/383424"
NTFY_TOPIC = "billet_nantes_tracy_777"

MIN_SLEEP = 12
MAX_SLEEP = 20
PAGE_LOAD_WAIT = 4
CLOUDFLARE_WAIT = 45  # seconds to wait when Cloudflare detected

SCREENSHOT_DIR = "/Users/Carlos/Documents/Cursor/Webot/screenshots"


# =============================================================================
# NOTIFICATIONS
# =============================================================================

def send_mobile_notification(title: str, message: str, priority: str = "default") -> bool:
    try:
        clean_title = title.encode('ascii', 'ignore').decode('ascii').strip() or "Ticket Alert"
        response = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={"Title": clean_title, "Priority": priority, "Tags": "ticket"},
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  ⚠️  ntfy failed: {e}")
        return False


def send_desktop_notification(title: str, message: str) -> bool:
    try:
        script = f'display notification "{message}" with title "{title}" sound name "Glass"'
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return True
    except:
        return False


def play_alert_sound():
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], capture_output=True)
    except:
        pass


def send_test_notification():
    """Send a test notification at startup to verify the system works."""
    print("  📱 Sending test notification...")
    success = send_mobile_notification(
        "Ticket Monitor Started",
        f"Monitoring {TARGET_URL}\nYou will be notified when tickets appear!",
        priority="low"
    )
    if success:
        print("  ✅ Test notification sent! Check your phone.")
    else:
        print("  ❌ Test notification FAILED - check ntfy topic")
    return success


def trigger_ticket_alert(ticket_count: int):
    """Full alert when tickets are found."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    print(f"\n{'='*60}")
    print(f"🚨🚨🚨 {ticket_count} TICKET(S) AVAILABLE! - {timestamp} 🚨🚨🚨")
    print(f"{'='*60}")
    
    send_mobile_notification(
        f"{ticket_count} TICKETS AVAILABLE!",
        f"GO NOW: {TARGET_URL}",
        priority="urgent"
    )
    send_desktop_notification(
        f"{ticket_count} TICKETS!",
        f"Go to passetonbillet NOW!"
    )
    play_alert_sound()


# =============================================================================
# BACKGROUND BROWSER CONTROL (no focus stealing!)
# =============================================================================

def open_arc_background():
    """Open Arc browser in background."""
    script = f'''
    tell application "Arc"
        if (count of windows) = 0 then
            make new window
        end if
        tell front window
            make new tab with properties {{URL:"{TARGET_URL}"}}
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", script], capture_output=True)
    print("  ✅ Arc opened (background)")


def refresh_and_get_text_background() -> str:
    """
    Refresh and get page text from Arc WITHOUT activating it.
    """
    script = f'''
    tell application "Arc"
        tell front window
            tell active tab
                set tabURL to URL
                -- Reload by executing JavaScript
                execute javascript "location.reload()"
                delay {PAGE_LOAD_WAIT}
                -- Get page text
                set pageText to execute javascript "document.body.innerText"
                return pageText
            end tell
        end tell
    end tell
    '''
    
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip()
    except:
        return ""


def take_screenshot() -> str:
    """Take screenshot of Safari window."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(SCREENSHOT_DIR, f"tickets_{timestamp}.png")
    
    # Capture Safari window without activating
    script = '''
    tell application "Safari"
        set winID to id of front window
    end tell
    return winID
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    
    # Use screencapture
    subprocess.run(["screencapture", "-x", filepath], capture_output=True)
    print(f"  📸 Screenshot: {filepath}")
    return filepath


# =============================================================================
# TICKET DETECTION (verbose)
# =============================================================================

def check_for_tickets(page_text: str) -> tuple[bool, int, str]:
    """
    Check for tickets.
    Returns: (tickets_available, ticket_count, status_message)
    """
    if not page_text or len(page_text.strip()) < 50:
        return (False, 0, "Page empty - may still be loading")
    
    # Check for Cloudflare FIRST
    lower_text = page_text.lower()
    if "checking your browser" in lower_text or "just a moment" in lower_text or "verify you are human" in lower_text:
        return (False, 0, "CLOUDFLARE")
    
    # Look for "X Billets" pattern
    billets_pattern = re.compile(r'(\d+)\s*Billets?', re.IGNORECASE)
    matches = billets_pattern.findall(page_text)
    
    total_tickets = 0
    if matches:
        for count_str in matches:
            total_tickets += int(count_str)
        
        if total_tickets > 0:
            return (True, total_tickets, f"{total_tickets} ticket(s) available!")
        else:
            return (False, 0, "0 tickets")
    
    # Check for buy buttons
    if "Acheter" in page_text or "Ajouter au panier" in page_text:
        return (True, 1, "Purchase button found!")
    
    return (False, 0, "No ticket info found")


# =============================================================================
# MAIN
# =============================================================================

def run_monitor():
    print("\n" + "="*60)
    print("🎟️  TICKET MONITOR v4 (Background Edition)")
    print("="*60)
    print(f"📍 {TARGET_URL}")
    print(f"📱 {NTFY_TOPIC}")
    print(f"⏱️  Check every {MIN_SLEEP}-{MAX_SLEEP}s")
    print("="*60)
    
    # Test notification system
    print("\n🔔 Testing notification system...")
    send_test_notification()
    
    # Open Safari (background)
    print("\n🌐 Opening Arc in background...")
    open_arc_background()
    
    print("\n" + "="*60)
    print("👆 IMPORTANT - DO THIS NOW:")
    print("   1. Switch to Arc (Cmd+Tab)")
    print("   2. Pass Cloudflare if needed")
    print("   3. Wait for ticket page to load")
    print("   4. Come back here and press ENTER")
    print("="*60)
    print("")
    input("🚀 Press ENTER when ready...")
    
    print("\n" + "="*60)
    print("🤖 MONITORING IN BACKGROUND")
    print("   You can keep using your computer!")
    print("   Ctrl+C to stop")
    print("="*60 + "\n")
    
    check_count = 0
    
    while True:
        check_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        try:
            # Refresh in background
            page_text = refresh_and_get_text_background()
            
            # Check tickets
            tickets_found, ticket_count, status = check_for_tickets(page_text)
            
            # Verbose log
            if "CLOUDFLARE" in status:
                print(f"[{check_count}] {timestamp} | 🚫 CLOUDFLARE - waiting {CLOUDFLARE_WAIT}s for you to click...")
                time.sleep(CLOUDFLARE_WAIT)
                continue
            elif tickets_found:
                print(f"[{check_count}] {timestamp} | 🎟️  {ticket_count} TICKETS!")
                take_screenshot()
                trigger_ticket_alert(ticket_count)
                
                print(f"  ⏸️  Pausing 3 minutes...")
                time.sleep(180)
                print(f"  ▶️  Resuming...")
            else:
                print(f"[{check_count}] {timestamp} | ❌ {status}")
            
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[{check_count}] {timestamp} | ⚠️  Error: {e}")
        
        sleep_time = random.uniform(MIN_SLEEP, MAX_SLEEP)
        time.sleep(sleep_time)


if __name__ == "__main__":
    try:
        run_monitor()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped.")
