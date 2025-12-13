
import customtkinter as ctk
import threading
from monitor_engine import TicketMonitorEngine
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TicketMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Webot")
        self.geometry("600x650")
        
        # Engine
        self.engine = TicketMonitorEngine(
            update_callback=self.log_message,
            status_callback=self.update_status
        )

        # -- UI LAYOUT --
        
        # Header
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(fill="x", padx=20, pady=20)
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="TICKET MONITOR", font=("Arial", 24, "bold"))
        self.title_label.pack(side="left", padx=10)
        
        self.status_label = ctk.CTkLabel(self.header_frame, text="STOPPED", text_color="gray", font=("Arial", 14, "bold"))
        self.status_label.pack(side="right", padx=10)

        # Configuration
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.pack(fill="x", padx=20, pady=10)
        
        # URL
        ctk.CTkLabel(self.config_frame, text="Target URL:").pack(anchor="w", padx=10, pady=(10,0))
        self.url_entry = ctk.CTkEntry(self.config_frame, width=500)
        self.url_entry.insert(0, self.engine.target_url)
        self.url_entry.pack(fill="x", padx=10, pady=(0,10))
        
        # Ntfy
        ctk.CTkLabel(self.config_frame, text="Ntfy Topic:").pack(anchor="w", padx=10)
        self.ntfy_entry = ctk.CTkEntry(self.config_frame)
        self.ntfy_entry.insert(0, self.engine.ntfy_topic)
        self.ntfy_entry.pack(fill="x", padx=10, pady=(0,10))
        
        # Delays
        delay_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        delay_frame.pack(fill="x", padx=10, pady=10)
        
        self.min_sleep_var = ctk.DoubleVar(value=self.engine.min_sleep)
        self.max_sleep_var = ctk.DoubleVar(value=self.engine.max_sleep)
        
        ctk.CTkLabel(delay_frame, text="Min Delay (s):").pack(side="left")
        ctk.CTkEntry(delay_frame, width=50, textvariable=self.min_sleep_var).pack(side="left", padx=5)
        
        ctk.CTkLabel(delay_frame, text="Max Delay (s):").pack(side="left", padx=(20,0))
        ctk.CTkEntry(delay_frame, width=50, textvariable=self.max_sleep_var).pack(side="left", padx=5)

        # Controls
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_start = ctk.CTkButton(self.controls_frame, text="START MONITOR", command=self.start_monitor, fg_color="green", font=("Arial", 14, "bold"))
        self.btn_start.pack(side="left", expand=True, fill="x", padx=5)
        
        self.btn_pause = ctk.CTkButton(self.controls_frame, text="PAUSE", command=self.pause_monitor, fg_color="orange", state="disabled")
        self.btn_pause.pack(side="left", expand=True, fill="x", padx=5)
        
        self.btn_stop = ctk.CTkButton(self.controls_frame, text="STOP", command=self.stop_monitor, fg_color="red", state="disabled")
        self.btn_stop.pack(side="left", expand=True, fill="x", padx=5)
        
        # Test Notification
        self.btn_test = ctk.CTkButton(self, text="Test Notification", command=self.test_notify, fg_color="gray")
        self.btn_test.pack(pady=5)

        # Logs
        self.log_box = ctk.CTkTextbox(self, height=200)
        self.log_box.pack(fill="both", expand=True, padx=20, pady=20)
        self.log_message("System ready. Configure and press START.")

    def log_message(self, message):
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")

    def update_status(self, status):
        self.status_label.configure(text=status.upper())
        if status == "Running":
            self.status_label.configure(text_color="green")
        elif status == "Paused" or "Cloudflare" in status:
            self.status_label.configure(text_color="orange")
        else:
            self.status_label.configure(text_color="gray")

    def start_monitor(self):
        # Update engine settings from UI
        self.engine.target_url = self.url_entry.get()
        self.engine.ntfy_topic = self.ntfy_entry.get()
        self.engine.min_sleep = self.min_sleep_var.get()
        self.engine.max_sleep = self.max_sleep_var.get()
        
        self.engine.start()
        
        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal")
        self.btn_stop.configure(state="normal")
        self.url_entry.configure(state="disabled")

    def stop_monitor(self):
        self.engine.stop()
        
        self.btn_start.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="PAUSE")
        self.btn_stop.configure(state="disabled")
        self.url_entry.configure(state="normal")

    def pause_monitor(self):
        if self.engine.paused:
            self.engine.resume()
            self.btn_pause.configure(text="PAUSE")
        else:
            self.engine.pause()
            self.btn_pause.configure(text="RESUME")

    def test_notify(self):
        self.log_message("Sending test notification...")
        # Use a thread so it doesn't freeze UI
        threading.Thread(target=lambda: self.engine.send_notification("Test", "This is a test notification from the GUI")).start()

if __name__ == "__main__":
    app = TicketMonitorApp()
    app.mainloop()
