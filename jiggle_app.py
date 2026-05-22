import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import time
import threading
import random
import os
import sys
import json
import socket
from pynput import mouse, keyboard
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController

import pystray
from PIL import Image, ImageDraw
import urllib.request
import urllib.error
import subprocess

# --- Application Constants & Updater Configuration ---
APP_VERSION = "1.0.1"
GITHUB_RELEASES_URL = "https://api.github.com/repos/khalidghaith/jiggle/releases/latest"

def resource_path(relative_path):
    """ Get absolute path to resource (for read-only assets like icons) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_config_dir():
    """ 
    Get path for writable config directory in AppData.
    """
    app_data = os.getenv('LOCALAPPDATA')
    if not app_data:
        app_data = os.path.expanduser("~") 
        
    config_dir = os.path.join(app_data, "Jiggle")
    
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except OSError:
            pass 
            
    return config_dir

def get_config_path():
    """ Get full path to the config file. """
    return os.path.join(get_config_dir(), "config.json")

def create_fallback_image():
    """Generates a simple colored box icon if icon.ico is missing."""
    width = 64
    height = 64
    color1 = "black"
    color2 = "#A8E6CF" # Pastel green
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 4, height // 4, 3 * width // 4, 3 * width // 4), fill=color2)
    return image

# --- Core Jiggle Logic ---
class JiggleEngine:
    def __init__(self, app_reference, interval=30):
        self.app = app_reference
        self.interval = interval
        self.intensity = 50           
        self._jiggle_active = False
        self._thread = None
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        self.enable_move = True
        self.enable_scroll = True
        self.enable_key = True
        
        self.MAX_STEP = 15    
        self.MIN_SLEEP = 0.5  
        self.MAX_SLEEP = 2.0  

    def set_capabilities(self, move, scroll, key):
        self.enable_move = move
        self.enable_scroll = scroll
        self.enable_key = key

    def start_jiggling(self):
        if self._thread and self._thread.is_alive():
            return False

        if not self._jiggle_active:
            self._jiggle_active = True
            self._thread = threading.Thread(target=self._jiggle_loop, daemon=True)
            self._thread.start()
            return True
        return False

    def stop_jiggling(self):
        self._jiggle_active = False
        return True

    def _jiggle_loop(self):
        try:
            center_x, center_y = self.mouse.position
        except:
            self._jiggle_active = False
            return

        half_intensity = self.intensity / 2

        while self._jiggle_active:
            try:
                allowed_actions = []
                allowed_weights = []
                
                if self.enable_move:
                    allowed_actions.append('move')
                    allowed_weights.append(70) 
                
                if self.enable_scroll:
                    allowed_actions.append('scroll')
                    allowed_weights.append(20)
                    
                if self.enable_key:
                    allowed_actions.append('key')
                    allowed_weights.append(10) 

                if not allowed_actions:
                    time.sleep(1)
                    continue

                action = random.choices(allowed_actions, weights=allowed_weights, k=1)[0]

                self.app.programmatic_move = True
                
                if action == 'move':
                    step_x = random.randint(-self.MAX_STEP, self.MAX_STEP)
                    step_y = random.randint(-self.MAX_STEP, self.MAX_STEP)
                    current_x, current_y = self.mouse.position
                    
                    new_x = current_x + step_x
                    new_y = current_y + step_y
                    
                    # Keep movement constrained around the initial center
                    new_x = max(center_x - half_intensity, min(center_x + half_intensity, new_x))
                    new_y = max(center_y - half_intensity, min(center_y + half_intensity, new_y))
                    
                    self.mouse.position = (new_x, new_y)
                
                elif action == 'scroll':
                    scroll_dir = random.choice([1, -1]) 
                    self.mouse.scroll(0, scroll_dir)
                    
                elif action == 'key':
                    # Simulate a key press/release (e.g., Shift) to prevent idle status
                    self.keyboard.press(Key.shift)
                    self.keyboard.release(Key.shift)

                time.sleep(0.1) # Short delay to ensure action registers
                self.app.programmatic_move = False
                
                # Wait for the next jiggle
                sleep_time = random.uniform(self.MIN_SLEEP, self.MAX_SLEEP)
                time.sleep(sleep_time)

            except Exception as e:
                print(f"Simulation Error: {e}")
                self.app.programmatic_move = False
                self._jiggle_active = False
                break
        
        self.app.programmatic_move = False

# --- GUI Application ---
class JiggleApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Jiggle")
        self.geometry("440x540") 
        self.resizable(False, False)
        
        # --- Config File Setup ---
        self.config_file = get_config_path()

        # --- Icon Setup ---
        self.icon_path = resource_path("icon.ico")
        try:
            if os.path.exists(self.icon_path):
                self.iconbitmap(self.icon_path)
        except Exception as e:
            print(f"Could not load window icon: {e}")

        # -- State Variables --
        self.monitoring_active = False  
        self.last_activity_time = time.time()
        self.programmatic_move = False  
        self.app_running = True 
        self.has_shown_tray_message = False 
        self.saved_settings = {} # Store last saved state
        
        self.engine = JiggleEngine(self, interval=99999) 
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # -- Initialize Variables (Updated Defaults) --
        self.var_threshold = tk.IntVar(value=30)      
        self.var_enable_move = tk.BooleanVar(value=True)
        self.var_enable_scroll = tk.BooleanVar(value=True)
        self.var_enable_key = tk.BooleanVar(value=True)
        self.var_start_minimized = tk.BooleanVar(value=True) 
        self.var_start_monitoring = tk.BooleanVar(value=False) 
        self.var_auto_update = tk.BooleanVar(value=True) 
        self.var_dark_theme = tk.BooleanVar(value=True) # Theme switch

        # Add listeners for changes
        self.var_threshold.trace_add("write", self._on_setting_changed)
        self.var_enable_move.trace_add("write", self._on_setting_changed)
        self.var_enable_scroll.trace_add("write", self._on_setting_changed)
        self.var_enable_key.trace_add("write", self._on_setting_changed)
        self.var_start_minimized.trace_add("write", self._on_setting_changed)
        self.var_start_monitoring.trace_add("write", self._on_setting_changed) 
        self.var_auto_update.trace_add("write", self._on_setting_changed)
        self.var_dark_theme.trace_add("write", self._on_setting_changed)

        # -- Load Settings from JSON --
        self._load_settings()

        self._configure_styles()
        self._create_widgets()
        
        # Check for startup launch flag
        is_startup_launch = "--startup" in sys.argv
        
        # 1. Handle Minimizing
        if is_startup_launch and self.var_start_minimized.get():
            self.withdraw()

        # 2. Handle Auto-Monitoring (only if launched via startup AND setting is enabled)
        if is_startup_launch and self.var_start_monitoring.get():
            self.after(500, self._toggle_monitoring) 
            
        self.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
        
        # Start the system tray thread
        self.tray_thread = threading.Thread(target=self._start_tray_icon, daemon=True)
        self.tray_thread.start()

        # 3. Check for updates automatically on startup
        self.after(1000, self._trigger_auto_update_check)

    def _configure_styles(self):
        # Slate/Charcoal Minimal Palette (Sleek Flat colors, no gradients)
        self.COLOR_BG = ("#F1F2F6", "#1A1D20")
        self.COLOR_CARD = ("#FFFFFF", "#262A2E")
        self.COLOR_BORDER = ("#E2E8F0", "#3E444D")
        self.COLOR_TEXT_PRIMARY = ("#2D3748", "#F1F2F6")
        self.COLOR_TEXT_MUTED = ("#718096", "#A4B0BE")
        
        self.COLOR_GREEN = "#2ED573"
        self.COLOR_GREEN_HOVER = "#26AF5F"
        self.COLOR_RED = "#FF4757"
        self.COLOR_RED_HOVER = "#E03E4D"
        
        self.COLOR_ACCENT = ("#1E90FF", "#3742FA")
        self.COLOR_ACCENT_HOVER = ("#1C82EC", "#2F38D9")
        self.COLOR_DISABLED = ("#E0E0E0", "#3E444D")
        self.COLOR_TEXT_DISABLED = ("#888888", "#5A6577")

        # Configure customtkinter appearance and theme
        ctk.set_appearance_mode("dark" if self.var_dark_theme.get() else "light")
        ctk.set_default_color_theme("blue") 

    def _create_widgets(self):
        # Main container filling the whole window
        self.main_frame = ctk.CTkFrame(self, fg_color=self.COLOR_BG, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)

        # 1. Top Card: Status & Countdown Dashboard
        self.status_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=self.COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=self.COLOR_BORDER
        )
        self.status_card.pack(pady=(15, 10), fill="x", padx=20, ipady=12)

        # Status row: Indicator Light + Status Text
        status_row = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_row.pack(pady=(10, 2))

        # Status Dot
        self.status_dot = ctk.CTkFrame(
            status_row,
            width=14,
            height=14,
            corner_radius=7,
            fg_color="#747D8C" # Start with stopped gray
        )
        self.status_dot.pack(side="left", padx=(0, 8))
        self.status_dot.pack_propagate(False) # Prevent size shrinking

        self.status_label = ctk.CTkLabel(
            status_row,
            text="STOPPED",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.status_label.pack(side="left")

        # Detail text
        self.detail_label = ctk.CTkLabel(
            self.status_card,
            text="Ready to monitor.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.detail_label.pack(pady=(2, 6))

        # 2. Prominent Main Action Button
        self.toggle_button = ctk.CTkButton(
            self.main_frame,
            text="START MONITORING",
            command=self._toggle_monitoring,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            height=46,
            corner_radius=10,
            fg_color=self.COLOR_GREEN,
            hover_color=self.COLOR_GREEN_HOVER,
            text_color="#1A1D20",
            cursor="hand2"
        )
        self.toggle_button.pack(fill="x", padx=20, pady=(5, 15))

        # 3. Bottom Card: Settings panel (Always visible in fixed size)
        self.settings_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=self.COLOR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=self.COLOR_BORDER
        )
        self.settings_card.pack(fill="both", expand=True, padx=20, pady=(0, 20), ipady=10)

        # Settings Card Title + Theme Switcher Row
        header_row = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        header_row.pack(fill="x", padx=15, pady=(12, 10))

        ctk.CTkLabel(
            header_row,
            text="SETTINGS",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.COLOR_TEXT_MUTED
        ).pack(side="left")

        self.theme_switch = ctk.CTkSwitch(
            header_row,
            text="Dark Theme",
            variable=self.var_dark_theme,
            command=self._toggle_theme,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            progress_color=self.COLOR_GREEN,
            cursor="hand2"
        )
        self.theme_switch.pack(side="right")

        # Separator line
        sep = ctk.CTkFrame(self.settings_card, height=1, fg_color=self.COLOR_BORDER)
        sep.pack(fill="x", padx=15, pady=(0, 10))

        # Idle Timeout Setting Row
        timeout_row = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        timeout_row.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(
            timeout_row,
            text="Idle Timeout (seconds):",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.COLOR_TEXT_PRIMARY
        ).pack(side="left")

        self.timeout_entry = ctk.CTkEntry(
            timeout_row,
            textvariable=self.var_threshold,
            width=65,
            height=26,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            corner_radius=6,
            border_width=1,
            border_color=self.COLOR_BORDER,
            fg_color=self.COLOR_BG
        )
        self.timeout_entry.pack(side="right")

        # Two-column Toggles Frame
        toggles_frame = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        toggles_frame.pack(fill="both", expand=True, padx=15, pady=8)

        # Left Column: Simulation Actions
        col_left = ctk.CTkFrame(toggles_frame, fg_color="transparent")
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            col_left,
            text="SIMULATION ACTIONS",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(0, 4))

        cb_style = {
            "font": ctk.CTkFont(family="Segoe UI", size=11),
            "progress_color": self.COLOR_GREEN,
            "cursor": "hand2"
        }

        ctk.CTkSwitch(col_left, text="Mouse Movement", variable=self.var_enable_move, **cb_style).pack(anchor="w", pady=3)
        ctk.CTkSwitch(col_left, text="Page Scroll", variable=self.var_enable_scroll, **cb_style).pack(anchor="w", pady=3)
        ctk.CTkSwitch(col_left, text="Key Press (Shift)", variable=self.var_enable_key, **cb_style).pack(anchor="w", pady=3)

        # Right Column: System Preferences
        col_right = ctk.CTkFrame(toggles_frame, fg_color="transparent")
        col_right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ctk.CTkLabel(
            col_right,
            text="SYSTEM PREFERENCES",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkSwitch(col_right, text="Start Minimized", variable=self.var_start_minimized, **cb_style).pack(anchor="w", pady=3)
        ctk.CTkSwitch(col_right, text="Start on Boot", variable=self.var_start_monitoring, **cb_style).pack(anchor="w", pady=3)
        ctk.CTkSwitch(col_right, text="Auto Updates", variable=self.var_auto_update, **cb_style).pack(anchor="w", pady=3)

        # Action Buttons Row (Check for Updates & Apply Changes)
        btn_row = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(8, 0))

        self.update_btn = ctk.CTkButton(
            btn_row,
            text="Check for Updates",
            command=self._manual_check_updates,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color=self.COLOR_BORDER,
            hover_color=self.COLOR_DISABLED,
            text_color=self.COLOR_TEXT_PRIMARY,
            cursor="hand2"
        )
        self.update_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Apply Button - Initial state is disabled (greyed out)
        self.apply_btn = ctk.CTkButton(
            btn_row,
            text="Apply Changes",
            command=self._apply_settings_inline,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=32,
            fg_color=self.COLOR_DISABLED,
            hover_color=self.COLOR_DISABLED,
            text_color=self.COLOR_TEXT_DISABLED,
            state="disabled",
            cursor="arrow"
        )
        self.apply_btn.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Feedback Label for status messages
        self.feedback_label = ctk.CTkLabel(
            self.settings_card,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_TEXT_MUTED
        )
        self.feedback_label.pack(pady=(4, 0))

    # --- Config / Persistence Logic ---
    def _load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.var_threshold.set(data.get("threshold", 30))
                    self.var_enable_move.set(data.get("move", True))
                    self.var_enable_scroll.set(data.get("scroll", True))
                    self.var_enable_key.set(data.get("key", True))
                    self.var_start_minimized.set(data.get("start_minimized", True))
                    self.var_start_monitoring.set(data.get("start_monitoring", False))
                    self.var_auto_update.set(data.get("auto_update", True))
                    self.var_dark_theme.set(data.get("dark_theme", True))
                    
                    self.engine.set_capabilities(
                        data.get("move", True),
                        data.get("scroll", True),
                        data.get("key", True)
                    )
                    self.idle_threshold = data.get("threshold", 30)
            else:
                self.idle_threshold = 30
        except Exception as e:
            print(f"Error loading config: {e}")
            self.idle_threshold = 30
        
        # Save baseline to check against for button highlighting
        self._update_saved_snapshot()

    def _update_saved_snapshot(self):
        """Update the internal snapshot of saved settings."""
        self.saved_settings = {
            "threshold": self.var_threshold.get(),
            "move": self.var_enable_move.get(),
            "scroll": self.var_enable_scroll.get(),
            "key": self.var_enable_key.get(),
            "start_minimized": self.var_start_minimized.get(),
            "start_monitoring": self.var_start_monitoring.get(),
            "auto_update": self.var_auto_update.get(),
            "dark_theme": self.var_dark_theme.get()
        }
        # Reset button state
        if hasattr(self, 'apply_btn'):
            self.apply_btn.configure(
                fg_color=self.COLOR_DISABLED, 
                text_color=self.COLOR_TEXT_DISABLED, 
                state="disabled",
                cursor="arrow"
            )

    def _on_setting_changed(self, *args):
        """Called whenever a settings variable changes."""
        if not hasattr(self, 'apply_btn'): return
        
        current_state = {
            "threshold": self.var_threshold.get(),
            "move": self.var_enable_move.get(),
            "scroll": self.var_enable_scroll.get(),
            "key": self.var_enable_key.get(),
            "start_minimized": self.var_start_minimized.get(),
            "start_monitoring": self.var_start_monitoring.get(),
            "auto_update": self.var_auto_update.get(),
            "dark_theme": self.var_dark_theme.get()
        }
        
        if current_state != self.saved_settings:
            # Highlight button
            self.apply_btn.configure(
                fg_color=self.COLOR_ACCENT, 
                text_color="#FFFFFF", 
                state="normal",
                cursor="hand2"
            )
        else:
            # Dim button
            self.apply_btn.configure(
                fg_color=self.COLOR_DISABLED, 
                text_color=self.COLOR_TEXT_DISABLED, 
                state="disabled",
                cursor="arrow"
            )

    def _save_settings(self):
        data = {
            "threshold": self.var_threshold.get(),
            "move": self.var_enable_move.get(),
            "scroll": self.var_enable_scroll.get(),
            "key": self.var_enable_key.get(),
            "start_minimized": self.var_start_minimized.get(),
            "start_monitoring": self.var_start_monitoring.get(),
            "auto_update": self.var_auto_update.get(),
            "dark_theme": self.var_dark_theme.get()
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
            # Update baseline
            self._update_saved_snapshot()
        except Exception as e:
            print(f"Error saving config: {e}")

    # --- System Tray Logic ---
    def _start_tray_icon(self):
        try:
            if os.path.exists(self.icon_path):
                image = Image.open(self.icon_path)
            else:
                image = create_fallback_image()
        except Exception:
            image = create_fallback_image()

        menu = pystray.Menu(
            pystray.MenuItem("Show Jiggle Monitor", self._restore_window, default=True),
            pystray.MenuItem("Exit", self._quit_application)
        )

        self.tray_icon = pystray.Icon("Jiggle", image, "Jiggle", menu)
        self.tray_icon.run()

    def _minimize_to_tray(self):
        self.withdraw()
        if not self.has_shown_tray_message:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.notify(
                    "Still running in the background.\nDouble-click to restore.",
                    "Jiggle"
                )
            self.has_shown_tray_message = True
        
    def _restore_window(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, lambda: self.attributes('-topmost', True))
        self.after(0, lambda: self.attributes('-topmost', False))

    def _quit_application(self, icon=None, item=None):
        self.app_running = False
        if icon:
            icon.stop()
        self.after(0, self._perform_shutdown)

    def _perform_shutdown(self):
        self.monitoring_active = False
        self.engine.stop_jiggling()
        self._stop_listeners()
        self.destroy() 

    # --- Core Monitoring Logic ---
    def _monitor_loop(self):
        if not self.app_running: return 
        if not self.monitoring_active: return

        current_time = time.time()
        elapsed = current_time - self.last_activity_time
        remaining = max(0, self.idle_threshold - elapsed)

        is_jiggling = self.engine._jiggle_active

        if is_jiggling:
            self.status_label.configure(text="SIMULATION ACTIVE", text_color=self.COLOR_RED)
            self.status_dot.configure(fg_color=self.COLOR_RED)
            self.detail_label.configure(text="Simulating human-like inputs...")
        else:
            if elapsed > self.idle_threshold:
                self.engine.start_jiggling()
            else:
                self.status_label.configure(text="MONITORING", text_color=self.COLOR_GREEN)
                self.status_dot.configure(fg_color=self.COLOR_GREEN)
                self.detail_label.configure(text=f"Waiting for inactivity... {int(remaining)}s remaining")

        self.after(500, self._monitor_loop)

    def _handle_user_input(self, *args):
        if self.programmatic_move:
            return

        self.last_activity_time = time.time()

        if self.engine._jiggle_active:
            self.after(0, self.engine.stop_jiggling)

    # --- Listeners ---
    def _start_listeners(self):
        if not self.mouse_listener or not self.mouse_listener.running:
            self.mouse_listener = mouse.Listener(
                on_move=lambda x, y: self._handle_user_input(),
                on_click=lambda x, y, button, pressed: self._handle_user_input() if pressed else None,
                on_scroll=lambda x, y, dx, dy: self._handle_user_input() if (dx or dy) else None
            )
            self.mouse_listener.start()

        if not self.keyboard_listener or not self.keyboard_listener.running:
            self.keyboard_listener = keyboard.Listener(
                on_press=lambda key: self._handle_user_input()
            )
            self.keyboard_listener.start()

    def _stop_listeners(self):
        if self.mouse_listener and self.mouse_listener.running:
            self.mouse_listener.stop()
            self.mouse_listener = None
        if self.keyboard_listener and self.keyboard_listener.running:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

    # --- Control Flow ---
    def _toggle_monitoring(self):
        if self.monitoring_active:
            self.monitoring_active = False
            self.engine.stop_jiggling()
            self._stop_listeners()
            
            self.toggle_button.configure(
                text="START MONITORING", 
                fg_color=self.COLOR_GREEN, 
                hover_color=self.COLOR_GREEN_HOVER, 
                text_color="#1A1D20"
            )
            self.status_label.configure(text="STOPPED", text_color=self.COLOR_TEXT_MUTED)
            self.status_dot.configure(fg_color="#747D8C") # Neutral gray
            self.detail_label.configure(text="Monitoring paused.")
        else:
            self.monitoring_active = True
            self.last_activity_time = time.time() 
            self._start_listeners()
            self._monitor_loop() 
            
            self.toggle_button.configure(
                text="STOP MONITORING", 
                fg_color=self.COLOR_RED, 
                hover_color=self.COLOR_RED_HOVER, 
                text_color="#FFFFFF"
            )

    # --- Theme Control ---
    def _toggle_theme(self):
        """Toggle appearance mode between Dark and Light."""
        ctk.set_appearance_mode("dark" if self.var_dark_theme.get() else "light")

    def _apply_settings_inline(self):
        try:
            new_thresh = self.var_threshold.get()
            # Enforce minimum idle time of 5 seconds
            if new_thresh < 5:
                self.feedback_label.configure(text="Error: Minimum timeout is 5 seconds.", text_color=self.COLOR_RED)
                return
            self.idle_threshold = new_thresh
        except:
            self.feedback_label.configure(text="Error: Invalid Timeout", text_color=self.COLOR_RED)
            return
        
        self.engine.set_capabilities(
            move=self.var_enable_move.get(),
            scroll=self.var_enable_scroll.get(),
            key=self.var_enable_key.get()
        )

        self._save_settings()

        self.feedback_label.configure(text="Settings Saved ✓", text_color=self.COLOR_GREEN)
        self.after(2000, lambda: self.feedback_label.configure(text=""))

    # --- Auto-Update System Logic ---
    def _trigger_auto_update_check(self):
        if self.var_auto_update.get():
            threading.Thread(target=self._check_updates_background, args=(True,), daemon=True).start()

    def _manual_check_updates(self):
        self.update_btn.configure(state="disabled", text="Checking...")
        threading.Thread(target=self._check_updates_background, args=(False,), daemon=True).start()

    def _check_updates_background(self, silent=True):
        try:
            req = urllib.request.Request(
                GITHUB_RELEASES_URL,
                headers={'User-Agent': 'Jiggle-Updater'}
            )
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                latest_tag = data.get("tag_name", "v1.0.0")
                latest_version = latest_tag.lstrip('v')
                
                # Check version comparison
                if self._is_newer_version(latest_version, APP_VERSION):
                    # Find executable asset in releases
                    exe_url = None
                    for asset in data.get("assets", []):
                        if asset.get("name") == "Jiggle.exe":
                            exe_url = asset.get("browser_download_url")
                            break
                    
                    if exe_url:
                        self.after(0, lambda: self._prompt_update(latest_tag, exe_url))
                    else:
                        if not silent:
                            self.after(0, lambda: messagebox.showinfo("Check Updates", f"A new version {latest_tag} is available, but no Jiggle.exe asset was found in the release."))
                else:
                     if not silent:
                         self.after(0, lambda: messagebox.showinfo("Check Updates", "You are running the latest version of Jiggle."))
        except Exception as e:
            if not silent:
                self.after(0, lambda: messagebox.showerror("Check Updates", f"Failed to check for updates:\n{e}"))
        finally:
            self.after(0, lambda: self.update_btn.configure(state="normal", text="Check for Updates"))

    def _is_newer_version(self, latest, current):
        try:
            lat_parts = [int(x) for x in latest.split('.')]
            cur_parts = [int(x) for x in current.split('.')]
            while len(lat_parts) < 3: lat_parts.append(0)
            while len(cur_parts) < 3: cur_parts.append(0)
            return lat_parts > cur_parts
        except:
            return latest != current

    def _prompt_update(self, latest_tag, exe_url):
        ans = messagebox.askyesno(
            "Update Available",
            f"A new version of Jiggle ({latest_tag}) is available!\n\nWould you like to download and install it now?\nThe application will restart automatically."
        )
        if ans:
            self.update_btn.configure(state="disabled", text="Updating...")
            threading.Thread(target=self._download_and_install_update, args=(exe_url,), daemon=True).start()

    def _download_and_install_update(self, exe_url):
        try:
            is_frozen = getattr(sys, 'frozen', False)
            current_exe = sys.executable if is_frozen else sys.argv[0]
            exe_dir = os.path.dirname(os.path.abspath(current_exe))
            
            temp_exe = os.path.join(exe_dir, "Jiggle_update.exe")
            
            # Download file
            req = urllib.request.Request(exe_url, headers={'User-Agent': 'Jiggle-Updater'})
            with urllib.request.urlopen(req) as response:
                with open(temp_exe, 'wb') as f:
                    f.write(response.read())
            
            if not is_frozen:
                self.after(0, lambda: messagebox.showinfo("Update Downloaded", f"Successfully downloaded update to:\n{temp_exe}\n(Auto-installer runs only on frozen executables)."))
                return
            
            # Create a detached batch script to replace the locked running executable
            updater_bat = os.path.join(exe_dir, "Jiggle_updater.bat")
            
            bat_content = f"""@echo off
title Jiggle Updater
echo Waiting for Jiggle to exit...
:loop
tasklist | find /i "Jiggle.exe" > nul
if %errorlevel% equ 0 (
    timeout /t 1 /nobreak > nul
    goto loop
)

echo Replacing Jiggle.exe...
del "{current_exe}"
ren "{temp_exe}" "Jiggle.exe"

if exist "{temp_exe}" (
    echo Error: Permission denied. Trying with administrator rights...
    powershell -Command "Start-Process cmd -ArgumentList '/c del \\"{current_exe}\\" & ren \\"{temp_exe}\\" \\"Jiggle.exe\\" & start \\"\\" \\"{current_exe}\\"' -Verb RunAs"
    goto end
)

echo Starting Jiggle...
start "" "{current_exe}"

:end
del "%~f0"
exit
"""
            with open(updater_bat, "w") as f:
                f.write(bat_content)
                
            subprocess.Popen([updater_bat], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.after(0, self._quit_application)
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Update Error", f"Failed to install update:\n{e}"))
        finally:
            self.after(0, lambda: self.update_btn.configure(state="normal", text="Check for Updates"))

# --- SINGLE INSTANCE LOGIC (SOCKET BASED) ---
SINGLE_INSTANCE_PORT = 65432 # Port to listen on

def check_single_instance():
    """
    Returns the server socket if this is the first instance.
    If another instance is running, sends 'SHOW' and returns None.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Try to bind to localhost port
        s.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        s.listen(1)
        return s 
    except OSError:
        # Port is in use, another instance exists
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', SINGLE_INSTANCE_PORT))
            client.sendall(b"SHOW")
            client.close()
        except:
            pass # Failed to signal, maybe zombie process
        return None

def listen_for_instances(server_socket, app_instance):
    """Background thread to listen for second instances trying to start."""
    while True:
        try:
            conn, addr = server_socket.accept()
            data = conn.recv(1024)
            if b"SHOW" in data:
                # Trigger window restore on main thread
                app_instance.after(0, app_instance._restore_window)
            conn.close()
        except:
            break

if __name__ == "__main__":
    # Check for existing instance
    server_sock = check_single_instance()
    
    if server_sock:
        # We are the main instance
        try:
            app = JiggleApp()
            
            # Start listener thread
            listener = threading.Thread(target=listen_for_instances, args=(server_sock, app), daemon=True)
            listener.start()
            
            app.mainloop()
        except ImportError:
             # Dependency fallback
             import tkinter.messagebox
             root = tk.Tk()
             root.withdraw()
             tkinter.messagebox.showerror("Missing Dependency", "Please install dependencies:\npip install pynput pystray Pillow")
             root.destroy()
        finally:
            server_sock.close()
    else:
        # Another instance is running; we sent the signal and now exit.
        sys.exit(0)