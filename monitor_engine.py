
import time
import random
import subprocess
import re
import requests
import threading
from datetime import datetime
import os

class TicketMonitorEngine:
    """
    Background engine for monitoring tickets using Arc browser.
    Runs in a separate thread and communicates via callbacks.
    """
    def __init__(self, update_callback=None, status_callback=None):
        self.running = False
        self.paused = False
        self.update_callback = update_callback  # For log messages
        self.status_callback = status_callback  # For status updates (Running, Paused, Cloudflare)
        
        # Default Configuration
        self.target_url = "https://www.ticketswap.fr/festival-tickets/radio-meuh-circus-festival-2026-la-clusaz-la-clusaz-2026-04-02-CVWqcs977h1jNpTpHXNbR/thursday-tickets/5442855"
        self.ntfy_topic = "billet_nantes_tracy_777"
        self.min_sleep = 18
        self.max_sleep = 32
        self.page_load_wait = 4
        self.screenshot_dir = "/Users/Carlos/Documents/Cursor/Webot/screenshots"

    def log(self, message):
        if self.update_callback:
            self.update_callback(message)
        else:
            print(message)

    def set_status(self, status):
        if self.status_callback:
            self.status_callback(status)

    def start(self):
        if not self.running:
            self.running = True
            self.paused = False
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            self.log("🚀 Monitor Engine Started")
            self.set_status("Running")
            
            # Send test notification at startup
            test_title = "Webot Monitor Started"
            test_message = f"Monitoring started for TicketSwap"
            self.send_notification(test_title, test_message, priority="low")
            self.send_desktop_notification(test_title, test_message)
            self.log("🔔 Test notifications sent!")

    def stop(self):
        self.running = False
        self.log("🛑 Monitor Engine Stopping...")
        self.set_status("Stopped")

    def pause(self):
        self.paused = True
        self.log("⏸️  Paused")
        self.set_status("Paused")

    def resume(self):
        self.paused = False
        self.log("▶️  Resumed")
        self.set_status("Running")

    def send_notification(self, title, message, priority="default"):
        try:
            clean_title = title.encode('ascii', 'ignore').decode('ascii').strip() or "Ticket Alert"
            requests.post(
                f"https://ntfy.sh/{self.ntfy_topic}",
                data=message.encode("utf-8"),
                headers={"Title": clean_title, "Priority": priority, "Tags": "ticket"},
                timeout=10
            )
            return True
        except Exception as e:
            self.log(f"⚠️ Notification failed: {e}")
            return False

    def send_desktop_notification(self, title, message):
        try:
            script = f'display notification "{message}" with title "{title}" sound name "Glass"'
            subprocess.run(["osascript", "-e", script], capture_output=True)
        except:
            pass
            
    def play_sound(self):
        try:
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], capture_output=True)
        except:
            pass

    def open_arc_background(self):
        script = f'''
        tell application "Arc"
            if (count of windows) = 0 then
                make new window
            end if
            tell front window
                make new tab with properties {{URL:"{self.target_url}"}}
            end tell
        end tell
        '''
        subprocess.run(["osascript", "-e", script], capture_output=True)
        self.log("🌐 Arc browser opened (background)")

    def refresh_and_read(self):
        script = f'''
        tell application "Arc"
            tell front window
                tell active tab
                    execute javascript "location.reload()"
                    delay {self.page_load_wait}
                    return execute javascript "document.body.innerText"
                end tell
            end tell
        end tell
        '''
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=30)
            return result.stdout.strip()
        except Exception as e:
            # self.log(f"⚠️ Read error: {e}") 
            return ""

    def take_screenshot(self):
        os.makedirs(self.screenshot_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.screenshot_dir, f"tickets_{timestamp}.png")
        subprocess.run(["screencapture", "-x", filepath], capture_output=True)
        self.log(f"📸 Screenshot saved: {os.path.basename(filepath)}")
        return filepath

    def check_for_tickets(self, text):
        if not text or len(text) < 100:
            return False, 0, "Page empty/loading"
            
        lower = text.lower()
        if "checking your browser" in lower or "just a moment" in lower or "verify you are human" in lower:
            return False, 0, "CLOUDFLARE"
            
        # TicketSwap Specific: "X disponibles"
        # Using a flexible regex that skips potential whitespace
        ts_match = re.search(r'(\d+)\s*disponibles?', text, re.IGNORECASE)
        
        if ts_match:
            count = int(ts_match.group(1))
            if count > 0:
                return True, count, f"🚨 {count} TicketSwap tickets found!"
            else:
                # If 0 disponibles, also double check for "Aucun billet disponible"
                if "aucun billet disponible" in lower:
                    return False, 0, "0 disponibles (Confirmed)"
                return False, 0, "0 disponibles"

        # General fallbacks
        matches = re.findall(r'(\d+)\s*Billets?', text, re.IGNORECASE)
        total = sum(int(m) for m in matches)
        if total > 0:
            return True, total, f"{total} tickets found!"
            
        if "Acheter" in text or "Ajouter au panier" in text:
            # Only trigger if NOT followed by "Vendu" or similar indicators
            if "aucun billet disponible" not in lower:
                return True, 1, "Buy button detected!"
            
        return False, 0, "No tickets found"

    def _run_loop(self):
        self.open_arc_background()
        
        check_count = 0
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
                
            check_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # self.log(f"[{check_count}] Refreshing...")
            text = self.refresh_and_read()
            found, count, status = self.check_for_tickets(text)
            
            if status == "CLOUDFLARE":
                self.log(f"🚫 CLOUDFLARE DETECTED!")
                self.set_status("Start Cloudflare Check")
                self.log("⏳ Pausing 45s for manual check...")
                time.sleep(45)
                continue
                
            elif found:
                self.log(f"🚨 {status}")
                self.take_screenshot()
                self.send_notification("TICKETS FOUND!", f"{status}\n{self.target_url}", "urgent")
                self.send_desktop_notification("TICKETS FOUND!", f"{status}")
                self.play_sound()
                
                self.log("⏸️ Pausing 3 mins...")
                self.set_status("Cooldown")
                time.sleep(180)
                self.set_status("Running")
                
            else:
                self.log(f"[{timestamp}] {status}")
            
            sleep_time = random.uniform(self.min_sleep, self.max_sleep)
            time.sleep(sleep_time)
