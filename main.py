import os
import shutil
import mysql.connector  # MySQL Driver
from dotenv import load_dotenv
from kivy.app import App
import psutil
from kivy.uix.checkbox import CheckBox
from kivy.uix.dropdown import DropDown
from kivy.uix.floatlayout import FloatLayout
from fpdf import FPDF
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivy.animation import Animation  # Import Animation
from kivy.uix.image import Image
from kivy.graphics import Ellipse
import random
import pygame
import sys
import mysql.connector
import os
import webview # Import webview to display web contents
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle
from kivy import Config
from kivy.resources import resource_find
import re
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.graphics import Color, Line
from datetime import datetime
import pytz
from kivy.uix.spinner import Spinner
from functools import partial
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.properties import BooleanProperty
from kivy.uix.label import Label
from kivy.properties import NumericProperty
from tkinter import Tk, filedialog



def resource_path(relative_path):
    """ Get absolute path to resource, works for development and for PyInstaller. """
    try:
        base_path = sys._MEIPASS  # Set by PyInstaller
    except AttributeError:
        base_path = os.path.abspath(".")

    full_path = os.path.join(base_path, relative_path)
    if not os.path.exists(full_path):
        print(f"[ERROR] Resource NOT FOUND: {full_path}")
    else:
        print(f"[FOUND] Resource: {full_path}")
    return full_path


img_path = resource_find(resource_path('positions/tank.png'))


medal_files = [
    resource_path('positions/1st-prize.png'),
    resource_path('positions/2nd-place.png'),
    resource_path('positions/3rd-place.png')
]


Config.set('graphics', 'multisamples', '0')  # Disable multisampling
Config.set('graphics', 'backend', 'angle_sdl2')

if getattr(sys, 'frozen', False):
    dotenv_path = os.path.join(sys._MEIPASS, '.env')
else:
    dotenv_path = '.env'

# Load environment variables
load_dotenv(dotenv_path=dotenv_path)
DB_HOST = os.getenv("DB_HOST")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "defaultdb")
DB_PORT = os.getenv("DB_PORT")  # DB_PORT as string



try:
    # Safely convert DB_PORT to integer with a fallback default
    port = int(DB_PORT) if DB_PORT else 16308
except ValueError:
    print("Invalid DB_PORT value. Falling back to default port 3306.")
    port = 16308



class ConfirmationPopup(Popup):
    def __init__(self, title, message, on_confirm, on_cancel, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.7, 0.4)  # You can adjust size
        self.auto_dismiss = False

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        layout.add_widget(Label(text=message))

        button_layout = BoxLayout(size_hint_y=0.3, spacing=10)
        yes_button = Button(text="Yes", on_release=lambda *args: self._confirm(on_confirm))
        no_button = Button(text="No", on_release=lambda *args: self._cancel(on_cancel))

        button_layout.add_widget(yes_button)
        button_layout.add_widget(no_button)

        layout.add_widget(button_layout)

        self.add_widget(layout)

    def _confirm(self, on_confirm):
        self.dismiss()
        if on_confirm:
            on_confirm()

    def _cancel(self, on_cancel):
        self.dismiss()
        if on_cancel:
            on_cancel()




class RotatableLabel(Label):
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(angle=self.update_transform)

    def update_transform(self, instance, value):
        self.canvas.before.clear()
        with self.canvas.before:
            from kivy.graphics import PushMatrix, Rotate, PopMatrix
            PushMatrix()
            self._rotation = Rotate(
                angle=self.angle,
                origin=self.center
            )

    def on_size(self, *args):
        # Recalculate rotation origin when size changes
        if hasattr(self, '_rotation'):
            self._rotation.origin = self.center



class HoverButton(Button):
    hovered = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(HoverButton, self).__init__(**kwargs)
        self.register_event_type('on_enter')  # Register event
        self.register_event_type('on_leave')  # Register event
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, *args):
        if not self.get_root_window():
            return
        pos = args[1]
        inside = self.collide_point(*self.to_widget(*pos))
        if self.hovered != inside:
            self.hovered = inside
            if inside:
                self.dispatch('on_enter')
            else:
                self.dispatch('on_leave')

    def on_enter(self, *args):
        Animation(background_color=(0.7, 0.7, 1, 1), duration=0.2).start(self)  # Light blue glow

    def on_leave(self, *args):
        Animation(background_color=(1, 1, 1, 1), duration=0.2).start(self)  # Back to normal



class CountdownWidget(BoxLayout):
    countdown_text = StringProperty()
    progress = NumericProperty(0)

    def __init__(self, target_datetime, target_timezone,conn, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.progress_circle = None
        self.glow_event = None
        self.bind(size=self.on_size)
        self.target_timezone = pytz.timezone(target_timezone)
        self.conn = conn

        self.target_datetime = datetime.strptime(target_datetime, "%Y-%m-%d %H:%M:%S")
        self.target_datetime = self.target_timezone.localize(self.target_datetime)
        self.total_seconds = int((self.target_datetime - datetime.now(self.target_timezone)).total_seconds())

        self.label = Label(font_size=40, bold=True, color=(1, 1, 1, 1))  # Start with white color
        self.add_widget(self.label)

        with self.canvas.after:
            Color(0.2, 0.6, 0.9, 1)
            self.progress_circle = Line(circle=(self.center_x, self.center_y, 100, 0, 0), width=4)

        Clock.schedule_interval(self.update_countdown, 1)
        Clock.schedule_interval(self.check_for_update, 10)  # Schedule checking AFTER everything is set up

    def update_countdown(self, dt):
        # Check if a countdown target is set
        if not self.target_datetime or self.target_datetime <= datetime.now(self.target_timezone):
            self.label.text = "NO MAYHEM SCHEDULED"
            return  # Stop further processing

        now = datetime.now(self.target_timezone)
        remaining = self.target_datetime - now
        seconds = int(remaining.total_seconds())

        if seconds < 0:
            self.label.text = "MAYHEM STARTED!"

            if not self.glow_event:
                self.glow_event = Clock.schedule_interval(self.animate_glow, 0.5)
            return False  # Stop the countdown clock

        # Update label with remaining time
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        self.label.text = f"{days}d {hours:02}h {minutes:02}m {seconds:02}s"

        # Animate progress circle
        self.total_seconds = int((self.target_datetime - datetime.now(self.target_timezone)).total_seconds())
        percent = (self.total_seconds - int(
            remaining.total_seconds())) / self.total_seconds if self.total_seconds > 0 else 0
        if self.progress_circle:
            circle_x, circle_y, circle_radius = self.center_x, self.center_y, min(self.width, self.height) / 3
            self.progress_circle.circle = (circle_x, circle_y, circle_radius, 0, 360 * percent)

    def get_countdown_target(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT countdown_to FROM countdown WHERE id = 1")
            result = cursor.fetchone()
            cursor.close()
            if result and result[0]:
                return result[0]
            return None
        except Exception as e:
            print(f"Database error while fetching countdown target: {e}")
            return None

    def check_for_update(self, dt):
        new_target_str = self.get_countdown_target()

        if new_target_str:
            if isinstance(new_target_str, str):
                new_target_dt = datetime.strptime(new_target_str, "%Y-%m-%d %H:%M:%S")
            else:
                new_target_dt = new_target_str  # Already a datetime object

            new_target_dt = self.target_timezone.localize(new_target_dt)

            if new_target_dt != self.target_datetime:
                print("Countdown target updated!")
                self.start_countdown(new_target_dt)

    def animate_glow(self, dt):
        r, g, b, a = self.label.color
        if r > 0.9:
            self.label.color = (0.6, 0, 0, 1)  # Darker red
        else:
            self.label.color = (1, 0, 0, 1)  # Bright red

    def on_size(self, *args):
        if hasattr(self, 'progress_circle') and self.progress_circle:
            self.progress_circle.pos = self.pos
            self.progress_circle.size = self.size



    def start_countdown(self, target_datetime):
        if isinstance(target_datetime, str):
            target_datetime = datetime.strptime(target_datetime, "%Y-%m-%d %H:%M:%S")

        # Only localize if it’s naive (has no timezone)
        if target_datetime.tzinfo is None or target_datetime.tzinfo.utcoffset(target_datetime) is None:
            self.target_datetime = self.target_timezone.localize(target_datetime)
        else:
            self.target_datetime = target_datetime

        now = datetime.now(self.target_timezone)
        self.total_seconds = max((self.target_datetime - now).total_seconds(), 1)

        self.label.text = "Starting countdown..."
        self.label.color = (1, 1, 1, 1)  # Reset color to white

        if self.glow_event:
            self.glow_event.cancel()
            self.glow_event = None

        Clock.unschedule(self.update_countdown)
        Clock.schedule_interval(self.update_countdown, 1)


class YouTubeVideoPlayer(FloatLayout):

    def set_video_id(self, new_video_id):
        self.video_id = new_video_id
        print(f"Video ID updated to: {new_video_id}")



    def play_video(self, instance, touch):
        if instance.collide_point(*touch.pos):
            # Pause the background music
            pygame.mixer.music.pause()
            webview.create_window('YouTube Video', f'https://www.youtube.com/watch?v={self.video_id}')
            webview.start()  # Start the webview
            print(f"Thumbnail clicked: {self.video_id}")  # Temporary log to check clicks

            if hasattr(self, 'youtube_player'):
                self.youtube_player.set_video_id(self.video_id)
            # Change the music control button to indicate pause

            resource_path('positions/play.png')
            play_icon_path = resource_path('positions/play.png')
            if play_icon_path:
                self.music_control_button.background_normal = play_icon_path
                self.music_control_button.background_down = play_icon_path
            else:
                fallback_path = 'positions/pause.png'  # Point to an existing image
                self.music_control_button.background_normal = fallback_path
                self.music_control_button.background_down = fallback_path



    def __init__(self, video_id, thumbnail_path, music_control_button, **kwargs):
        super().__init__(**kwargs)
        self.video_id = video_id
        self.music_control_button = music_control_button  # Store the reference to the music control button


        # Use the downloaded thumbnail image
        self.thumbnail = Image(source=thumbnail_path, size_hint=(None, None), size=(300, 180))
        self.thumbnail.bind(on_touch_down=self.play_video)

        # Set the position of the thumbnail
        self.thumbnail.pos_hint = {'center_x': 0.98, 'center_y': 1.15}  # Center the thumbnail

        # Add the thumbnail to the layout
        self.add_widget(self.thumbnail)


def play_video(self, instance, touch):
    if instance.collide_point(*touch.pos):
        webview.create_window('YouTube Video', f'https://www.youtube.com/watch?v={self.video_id}')
        webview.start()  # Start the webview
        print(f"Thumbnail clicked: {self.video_id}")  # Temporary log to check clicks


class TransparentGridLayout(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 0.6)  # Transparent background (RGBA)
            self.rect = Rectangle(size=self.size, pos=self.pos)

    def on_size(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos

    def on_pos(self, *args):
        self.rect.pos = self.pos


class MovingGIF(FloatLayout):
    def __init__(self, gif_source, start_x, start_y, end_x, duration, **kwargs):
        super().__init__(**kwargs)
        self.gif_source = gif_source
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.duration = duration

        self.gif_image = Image(source=self.gif_source, size_hint=(None, None), size=(100, 100))  # Adjust size as needed
        self.add_widget(self.gif_image)

        self.animate_gif()

    def animate_gif(self):
        self.gif_image.pos = (self.start_x, self.start_y)
        animation = Animation(x=self.end_x, duration=self.duration)
        animation.bind(on_complete=self.remove_gif)
        animation.start(self.gif_image)

    def remove_gif(self, *args):
        self.parent.remove_widget(self)  # Remove the GIF from the parent layout

class Splash:
    def __init__(self, canvas, pos):
        self.canvas = canvas
        self.size = random.uniform(5, 10)
        self.x, self.y = pos
        self.lifetime = 0.5
        with self.canvas:
            self.ellipse = Ellipse(pos=(self.x - self.size / 2, self.y - self.size / 2), size=(self.size, self.size))
        Clock.schedule_once(self.expire, self.lifetime)

    def expire(self, dt):
        self.canvas.remove(self.ellipse)


class Snowflake:
    class FlakeParticle:
        def __init__(self, canvas, x, y, size):
            self.canvas = canvas
            self.x = x
            self.y = y
            self.size = size * 0.4

            self.vx = random.uniform(-0.5, 0.5)
            self.vy = random.uniform(0.5, 1.5)
            self.alpha = random.uniform(0.3, 0.6)

            with self.canvas:
                self.color_instruction = Color(1, 1, 1, self.alpha)  # pure white
                self.ellipse = Ellipse(pos=(self.x, self.y), size=(self.size, self.size))

        def update(self, parent_x, parent_y):
            self.x += self.vx
            self.y += self.vy
            self.alpha -= 0.005

            if self.alpha <= 0:
                self.x = parent_x + random.uniform(-8, 8)
                self.y = parent_y + random.uniform(-8, 8)
                self.vx = random.uniform(-0.5, 0.5)
                self.vy = random.uniform(0.5, 1.5)
                self.alpha = random.uniform(0.3, 0.6)

            self.ellipse.pos = (self.x, self.y)
            self.color_instruction.a = self.alpha

    def __init__(self, canvas, width):
        self.canvas = canvas
        self.size = random.uniform(6, 10)
        self.x = random.uniform(0, width)
        self.y = random.uniform(0, Window.height)
        self.speed = random.uniform(1, 2)

        self.particles = []

        with self.canvas:
            Color(1, 1, 1, 0.9)
            self.ellipse = Ellipse(pos=(self.x, self.y), size=(self.size, self.size))

        for _ in range(6):  # slightly fewer than fireball for soft glow
            particle = self.FlakeParticle(self.canvas, self.x, self.y, self.size)
            self.particles.append(particle)

        Clock.schedule_interval(self.update, 1 / 60)

    def update(self, dt):
        self.y -= self.speed
        if self.y < 0:
            self.y = Window.height
            self.x = random.uniform(0, Window.width)

        self.ellipse.pos = (self.x, self.y)

        for particle in self.particles:
            particle.update(self.x, self.y)



class Fireball:
    class FlameParticle:
        def __init__(self, canvas, x, y, size):
            self.canvas = canvas
            self.x = x
            self.y = y
            self.size = size * 0.4

            self.vx = random.uniform(-1, 1)
            self.vy = random.uniform(1, 3)
            self.alpha = random.uniform(0.5, 0.8)

            with self.canvas:
                self.color_instruction = Color(1, random.uniform(0.5, 0.2), 0, self.alpha)
                self.ellipse = Ellipse(pos=(self.x, self.y), size=(self.size, self.size))

        def update(self, parent_x, parent_y):
            self.x += self.vx
            self.y += self.vy
            self.alpha -= 0.01

            if self.alpha <= 0:
                # Respawn near parent fireball
                self.x = parent_x + random.uniform(-10, 10)
                self.y = parent_y + random.uniform(-10, 10)
                self.vx = random.uniform(-1, 1)
                self.vy = random.uniform(1, 3)
                self.alpha = random.uniform(0.5, 0.8)

            # Update position and alpha
            self.ellipse.pos = (self.x, self.y)
            self.color_instruction.a = self.alpha

    def __init__(self, canvas, width):
        self.canvas = canvas
        self.size = random.uniform(8, 12)
        self.x = random.uniform(0, width)
        self.y = random.uniform(Window.height, Window.height + 300)
        self.speed = random.uniform(1, 2)

        self.flame_particles = []

        with self.canvas:
            # Main core of fireball
            Color(1, random.uniform(0.2, 0), 0, 1)
            self.ellipse = Ellipse(pos=(self.x, self.y), size=(self.size, self.size))

        # Create multiple flame particles around it
        for _ in range(8):
            particle = self.FlameParticle(self.canvas, self.x, self.y, self.size)
            self.flame_particles.append(particle)

        Clock.schedule_interval(self.update, 1 / 60)

    def update(self, dt):
        self.y -= self.speed

        if self.y < 0:
            self.y = Window.height + random.uniform(0, 300)
            self.x = random.uniform(0, Window.width)

        # Move main fireball
        self.ellipse.pos = (self.x, self.y)

        # Update flame particles
        for particle in self.flame_particles:
            particle.update(self.x, self.y)



class Player:
    def __init__(self, name, level, kills, flags_captured, time_played, xp,skill_rating=0.0):

        self.name = name
        self.level = level
        self.kills = kills
        self.flags_captured = flags_captured
        self.time_played = time_played
        self.xp = xp
        self.skill_rating = float(skill_rating)


def style_button(button):
    button.background_color = (0.1, 0.5, 0.8, 1)
    button.color = (1, 1, 1, 1)


def get_tier(rating):
    if rating < 21:
        return "Bronze"
    elif rating < 41:
        return "Silver"
    elif rating < 61:
        return "Gold"
    elif rating < 81:
        return "Platinum"
    elif rating < 101:
        return "Diamond"
    elif rating < 121:
        return "Master"
    elif rating < 141:
        return "Grandmaster"
    elif rating < 201:
        return "Challenger"
    else:
        return "Legend"  # For ratings above Challenger



class SkillRatingApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shadow_rect = None
        self.music_control_button = None
        self.music_selection_button = None
        self.match_result = None
        self.center_y = None
        self.center_x = None
        self.target_datetime = None
        self.glow_event = None
        self.progress_circle = None
       # self.label = None
        self.no_mayhem_checkbox = None
        self.mayham_label = None
        self.countdown_widget = None
        self.flag_image_paths = None
        self.generate_inputs_button = None
        self.player_inputs_layout = None
        self.blue_team_size_input = None
        self.blue_team_size_input_box = None
        self.red_team_size_input_box = None
        self.game_number_input_box = None
        self.red_team_size_input = None
        self.game_number_input = None
        self.xp = None
        self.kills = None
        self.time_played = None
        self.skill_rating = None
        self.flags_captured = None
        self.conn = None
        self.create_db()
        self.players = []
        self.music_playing = True
        self.video_player = None  # Initialize video_player reference
        self.previous_input = None

     # Add an instance variable to store player stats
        self.player_stats = {}

        self.persistent_music_folder = os.path.join(os.path.expanduser("~"), "Documents", "MyApp", "music")
        os.makedirs(self.persistent_music_folder, exist_ok=True)

    def ensure_music_folder_exists(self):
        try:
            if not os.path.exists(self.persistent_music_folder):
                os.makedirs(self.persistent_music_folder)
                print(f"Recreated missing folder: {self.persistent_music_folder}")
        except Exception as e:
            print(f"Failed to create music folder: {e}")



    def check_disk_space(self, path, required_space):
        """
        Check if the specified path has enough disk space.
        """
        try:
            # Check free space using psutil
            disk_usage = psutil.disk_usage(path)
            free_space = disk_usage.free
            if free_space >= required_space:
                return True
            else:
                return False
        except Exception as e:
            print(f"Error checking disk space: {e}")
            return False

    def save_file_with_fallback(self, file_path, file_data, required_space):
        """
        Try saving the file to the Documents folder, fallback to Desktop if not enough space.
        """
        primary_location = os.path.expanduser('~/Documents')
        secondary_location = os.path.expanduser('~/Desktop')

        # Check space in primary location
        if self.check_disk_space(primary_location, required_space):
            try:
                with open(os.path.join(primary_location, file_path), 'w') as f:
                    f.write(file_data)
                print(f"File saved to {primary_location}")
                return True
            except Exception as e:
                print(f"Error saving file to primary location: {e}")
                return False
        else:
            # Try saving to secondary location
            if self.check_disk_space(secondary_location, required_space):
                try:
                    with open(os.path.join(secondary_location, file_path), 'w') as f:
                        f.write(file_data)
                    print(f"File saved to {secondary_location}")
                    return True
                except Exception as e:
                    print(f"Error saving file to secondary location: {e}")
                    return False
            else:
                # Inform the user if both locations have insufficient space
                self.show_no_space_popup()
                return False

    def show_no_space_popup(self):
        """
        Show a popup informing the user that there's no space available.
        """
        content = Label(text="There is not enough space in both Documents and Desktop.")
        close_btn = Button(text="Close")
        close_btn.bind(on_release=lambda x: content.parent.dismiss())
        popup = Popup(title="Error", content=content, size_hint=(None, None), size=(400, 200))
        popup.open()

    def on_start(self):
        try:
            self.retry_check_app_version()
        except Exception as e:
            print(f"[ERROR] Startup error: {e}")
            self.show_no_connection_popup()  #

    def retry_check_app_version(self):
        try:
            self.check_app_version(APP_VERSION="1.0.0")
        except Exception as e:
            print(f"Retry version check failed: {e}")
            self.show_no_connection_popup()

    def check_app_version(self, APP_VERSION="1.0.0"):
        try:
            if getattr(sys, 'frozen', False):
                dotenv_path = os.path.join(sys._MEIPASS, '.env')
            else:
                dotenv_path = '.env'
            load_dotenv(dotenv_path)

            DB_HOST = os.getenv("DB_HOST")
            DB_USERNAME = os.getenv("DB_USERNAME")
            DB_PASSWORD = os.getenv("DB_PASSWORD")
            DB_NAME = os.getenv("DB_NAME", "defaultdb")
            DB_PORT = int(os.getenv("DB_PORT", 16308))

            self.conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USERNAME,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=DB_PORT
            )
            print("[DB] Connection established successfully.")

            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM app_version_control ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()

            if result:
                min_required = result['minimum_required_version']
                latest = result['latest_version']
                force_update = result['force_update']
                update_message = result['update_message']

                if self.compare_versions(APP_VERSION, min_required) < 0:
                    self.show_force_update_popup(update_message)
                elif self.compare_versions(APP_VERSION, latest) < 0:
                    if force_update:
                        self.show_force_update_popup(update_message)
                    else:
                        self.show_optional_update_popup(update_message)

            cursor.close()

        except Exception as e:
            print(f"[ERROR] DB connection failed: {e}")
            self.conn = None
            raise  # Optional: let the build() method handle this

    def compare_versions(self, v1, v2):
        def normalize(v):
            return [int(x) for x in v.split(".")]
        return (normalize(v1) > normalize(v2)) - (normalize(v1) < normalize(v2))

    def show_force_update_popup(self, message):
        # This is the small box inside the full-screen modal
        inner_layout = BoxLayout(orientation='vertical', padding=20, spacing=20,
                                 size_hint=(None, None), size=(400, 300))
        inner_layout.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        inner_layout.add_widget(Label(text=message, halign='center'))

        close_button = Button(text='Exit App', size_hint_y=None, height=40)
        inner_layout.add_widget(close_button)

        # FloatLayout allows absolute positioning of the inner popup box
        root_layout = FloatLayout()
        root_layout.add_widget(inner_layout)

        popup = Popup(
            title='',
            content=root_layout,
            size_hint=(1, 1),
            size=(Window.width, Window.height),
            auto_dismiss=False,
            background='atlas://data/images/defaulttheme/modalview-background',
            background_color=(0, 0, 0, 0.8),  # Dark translucent background
            separator_height=0
        )

        close_button.bind(on_press=lambda x: self.exit_app())
        popup.open()

    def show_optional_update_popup(self, message):
        layout = BoxLayout(orientation='vertical', padding=30, spacing=10)
        layout.add_widget(Label(text=message))

        ok_button = Button(text='Continue', size_hint_y=None, height=40)
        layout.add_widget(ok_button)

        popup = Popup(title='Update Available', content=layout,
                      size_hint=(None, None), size=(400, 300))

        ok_button.bind(on_press=popup.dismiss)
        popup.open()

    def exit_app(self):
        App.get_running_app().stop()
        sys.exit()

    def show_no_connection_popup(self, error_message = "disconnected"):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        label = Label(
            text=f"Database connection failed:\n{error_message}\n\nPlease check your internet connection.",
            halign='center'
        )
        layout.add_widget(label)

        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=20)
        retry_button = Button(text="Retry")
        exit_button = Button(text="Exit")
        buttons_layout.add_widget(retry_button)
        buttons_layout.add_widget(exit_button)
        layout.add_widget(buttons_layout)

        # Only create and assign the popup once
        if not hasattr(self, 'popup') or self.popup is None:
            self.popup = Popup(
                title="Connection Error",
                content=layout,
                size_hint=(None, None),
                size=(400, 300),
                auto_dismiss=False
            )
            # Store label for updating messages on retry failure
            self.popup_label = label
        else:
            # If popup exists, just update the message
            self.popup_label.text = f"Database connection failed:\n{error_message}\n\nPlease check your internet connection."

        retry_button.bind(on_press=self.try_again_connection)
        exit_button.bind(on_press=self.exit_app)

        self.popup.open()

    def try_again_connection(self, *args):
        print("[INFO] Retrying database connection...")
        try:
            self.check_app_version(APP_VERSION="1.0.0")
            if self.conn:
                print("[INFO] Reconnection successful.")
                self.popup.dismiss()
                # Rebuild the UI and replace app root widget to reflect updates
                new_main_layout = self.build()
                app_instance = App.get_running_app()

                # Check if the root widget is set
                if app_instance.root is not None:
                    # Clear existing widgets
                    for child in app_instance.root.children[:]:  # Use a copy of the list
                        app_instance.root.remove_widget(child)
                    app_instance.root.add_widget(new_main_layout)  # Add the new layout
                else:
                    print("[ERROR] Root widget is None. Setting new root widget.")
                    app_instance.root = new_main_layout  # Set the new layout as root
            else:
                print("[ERROR] Connection still not available.")
                self.show_no_connection_popup()  # Show a popup to inform the user
        except Exception as e:
            print(f"[ERROR] Retry failed: {e}")
            self.show_no_connection_popup()  # Show a popup to inform the user

    def rebuild_ui(self):
        # Clear existing widgets
        self.main_layout.clear_widgets()

        # Rebuild the UI components
        self.build()

    def create_db(self):
        try:

            if getattr(sys, 'frozen', False):
                dotenv_path = os.path.join(sys._MEIPASS, '.env')
            else:
                dotenv_path = '.env'

            # Using a default for DB_PORT if the environment variable is not set
            port = os.getenv("DB_PORT", 16308)


            # Get environment variables
            DB_HOST = os.getenv("DB_HOST")
            DB_USERNAME = os.getenv("DB_USERNAME")
            DB_PASSWORD = os.getenv("DB_PASSWORD")
            DB_NAME = os.getenv("DB_NAME", "defaultdb")
            DB_PORT = os.getenv("DB_PORT",
                                "16308")  # Defaults to a string # Example of connecting to the database using these variables
            self.conn = mysql.connector.connect(host=DB_HOST, user=DB_USERNAME, password=DB_PASSWORD, database=DB_NAME,
                                                port=int(DB_PORT),  # Convert port to integer ssl_disabled=False
                                                )


            self.conn.autocommit = True
            cursor = self.conn.cursor()
            print("connected to db!")


            # Create player_skill_rating table if it doesn't exist
            cursor.execute('''
             CREATE TABLE IF NOT EXISTS overall_player_skill_rating (
               id INT AUTO_INCREMENT PRIMARY KEY,
               player_name VARCHAR(255) NOT NULL UNIQUE,
               kills INT NOT NULL  DEFAULT 0,
               xp INT NOT NULL  DEFAULT 0,
               flags_captured INT NOT NULL DEFAULT 0,
               last_updated_player_level INT NOT NULL  DEFAULT 0,
               total_matches INT NOT NULL DEFAULT 0,
               final_skill_rating FLOAT NOT NULL  DEFAULT 0,
               overall_win_ratio FLOAT NOT NULL DEFAULT 0,
               red_team_win_rate FLOAT NOT NULL DEFAULT 0, 
               blue_team_win_rate FLOAT NOT NULL DEFAULT 0, 
               KPG INT NOT NULL  DEFAULT 0,
               FPG INT NOT NULL  DEFAULT 0,
               XPG INT NOT NULL  DEFAULT 0,
               country_flag VARCHAR(255) DEFAULT 'default.png'      
                           )
                       ''')

            # Create commentary_games_details table if it doesn't exist
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS commentary_games_details (
                               game_id INT AUTO_INCREMENT PRIMARY KEY,
                               game_date DATETIME NOT NULL,
                               total_players INT NOT NULL,
                               winning_team VARCHAR(50),
                               total_kills INT DEFAULT 0,
                               total_flags_captured INT DEFAULT 0
                           )
                       ''')

            cursor.execute('''
                       CREATE TABLE IF NOT EXISTS commentary_games_video(
                           id INT AUTO_INCREMENT PRIMARY KEY,
                           video_id VARCHAR(255) NOT NULL,
                           thumbnail_path VARCHAR(255) NOT NULL

                       )''')

            cursor.execute('''
                               CREATE TABLE IF NOT EXISTS matches ( 
                               match_number INT PRIMARY KEY,
                               match_date DATE
                       )''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_credentials (
                    id INTEGER PRIMARY KEY,
                    password TEXT NOT NULL        
                   )''')


            cursor.execute('''
              CREATE TABLE IF NOT EXISTS countdown (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  countdown_to DATETIME NOT NULL
                    )''')

            cursor.execute('''
              CREATE TABLE IF NOT EXISTS player_skill_rating (
    id INT AUTO_INCREMENT PRIMARY KEY,
    final_team VARCHAR(50) DEFAULT 'Unknown',  -- Using one definition and a default value
    player_name VARCHAR(255) NOT NULL,
    kills INT NOT NULL DEFAULT 0,
    xp INT NOT NULL DEFAULT 0,  -- Changed to INT for experience points
    flags_captured INT NOT NULL DEFAULT 0,
    player_level INT NOT NULL DEFAULT 0,
    skill_rating FLOAT NOT NULL DEFAULT 0,
    match_number INT,
    outcome VARCHAR(255) NOT NULL DEFAULT 'Unknown',
    FOREIGN KEY (match_number) REFERENCES matches(match_number),
    UNIQUE (player_name, match_number)  -- Allows sets of players per match
                )
            ''')

            # ✅ NEW: App Version Control Table
            cursor.execute('''
                       CREATE TABLE IF NOT EXISTS app_version_control (
                           id INT AUTO_INCREMENT PRIMARY KEY,
                           minimum_required_version VARCHAR(10),
                           latest_version VARCHAR(10),
                           force_update BOOLEAN DEFAULT FALSE,
                           update_message TEXT
                       )
                   ''')

            cursor.close()

        except mysql.connector.Error as err:
            print("Error connecting to the database:", err)
            self.conn = None
        except Exception as e:
            print("An error occurred:", e)
            self.conn = None

    if getattr(sys, 'frozen', False):
        music_path = resource_path('music/background_music.mp3')
    else:
        music_path = 'music/background_music.mp3'
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(music_path)  # Load music from the correct path
        pygame.mixer.music.set_volume(0.5)
        print("Pygame mixer initialized.")
    except Exception as e:
        print(f"Error initializing Pygame mixer: {e}")

    def create_snowflakes(self):
        self.snowflakes = []
        for _ in range(30):
            snowflake = Snowflake(self.main_layout.canvas, Window.width)
            self.snowflakes.append(snowflake)

    def fetch_top_players(self):
        if self.conn is None:
            print("Database connection is not established. Cannot fetch top players.")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                   SELECT player_name, 
                          final_skill_rating,
                          COALESCE(kills, 0) AS kills,
                          COALESCE(flags_captured, 0) AS flags_captured,
                          COALESCE(country_flag, 'flags/default.png') AS country_flag
                   FROM overall_player_skill_rating
                   ORDER BY final_skill_rating DESC
                   LIMIT 3
               ''')
            results = cursor.fetchall()
            print("Fetched results:", results)  # Debugging line
            self.top_players_container.clear_widgets()

            for idx, row in enumerate(results):
                print(f"Row data: {row}")  # Debugging output
                medal_path = resource_path(['positions/1st-prize.png',
                                            'positions/2nd-place.png',
                                            'positions/3rd-place.png'][idx])

                player_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
                medal_image = Image(source=medal_path, size_hint=(None, 1), width=30)
                player_layout.add_widget(medal_image)

                stats_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)

                player_name = row[0]
                truncated_name = (player_name[:15] + '...') if len(player_name) > 15 else player_name
                player_name_label = Label(text=truncated_name, size_hint_y=None, height=40, color=(1, 0.84, 1, 1))
                stats_layout.add_widget(player_name_label)

                country_flag_filename = row[4]
                country_flag_path = resource_path(f'flags/{country_flag_filename}')

                if not os.path.exists(country_flag_path):
                    print(f"[WARNING] Country flag not found: {country_flag_path}. Falling back to default.")
                    country_flag_path = resource_path('flags/default.png')

                country_flag_image = Image(source=country_flag_path, size_hint=(None, None), size=(30, 30))
                stats_layout.add_widget(country_flag_image)

                total_kills = int(row[2])
                total_flags = int(row[3])
                skill_rating = float(row[1])  # Ensure this is the correct index

                print(f"Skill rating for {player_name}: {skill_rating}")  # Debug specific skill rating

                skill_label = Label(text=f"Rating: {skill_rating:.2f}", size_hint_y=None, height=40,
                                    color=(1, 1, 1, 1))
                kills_label = Label(text=f"Kills: {total_kills}", size_hint_y=None, height=40, color=(1, 1, 1, 1))
                flags_label = Label(text=f"Flags: {total_flags}", size_hint_y=None, height=40, color=(1, 1, 1, 1))

                print(skill_rating, "line 886")
                self.animate_count_up(skill_label, skill_rating)
                self.animate_count_up(kills_label, total_kills)
                self.animate_count_up(flags_label, total_flags)

                stats_layout.add_widget(kills_label)
                stats_layout.add_widget(flags_label)
                stats_layout.add_widget(skill_label)
                player_layout.add_widget(stats_layout)
                self.top_players_container.add_widget(player_layout)

        except mysql.connector.Error as err:
            print(f"Error occurred: {err}")
            self.show_popup("Error", str(err))






    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

    def build(self):
        try:
            self.check_app_version(APP_VERSION="1.0.0")
        except Exception as e:
            print(f"Startup error: {e}")
            Clock.schedule_once(lambda dt: self.show_no_connection_popup(), 0)
            return FloatLayout()  # Avoid proceeding with a broken DB connection

        if self.conn is None:
            print("[FATAL] No DB connection available. Cannot proceed.")
            return FloatLayout()  # Return an empty layout or a loading screen

        print("Building the main layout.")
        self.main_layout = FloatLayout()

        self.title_gif = Image(
            source=resource_path('positions/title.gif'),
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(None, None),
            size=(600, 200)
        )
        self.title_gif.pos = (320, 780)
        self.main_layout.add_widget(self.title_gif)

        pygame.mixer.music.play(-1)  # Start playing music when the app is built

        self.music_control_button = Button(size_hint=(None, None), size=(80, 80))
        self.music_control_button.pos = (20, 860)
        self.update_button_image()  # Set initial button image
        self.music_control_button.bind(on_press=self.toggle_music)
        self.main_layout.add_widget(self.music_control_button)

        self.music_selection_button = Button(
            background_normal=resource_path('music/music.png'),
            background_down=resource_path('music/music.png'),
            size_hint=(None, None),
            pos=(30, 750),
            background_color=(0.7, 0.4, 0.9, 1),  # Light rainbowish purple
            color=(1, 1, 1, 1)  # White text
        )

        self.music_selection_button.bind(on_press=self.open_music_selection)
        self.music_selection_button.bind(on_press=self.on_button_press)
        self.music_selection_button.bind(on_release=self.on_button_release)
        self.main_layout.add_widget(self.music_selection_button)

        # Create snowflakes
        self.create_snowflakes()

        self.fireballs = []
        for _ in range(10):  # How many fireballs you want
            fireball = Fireball(self.main_layout.canvas, Window.width)
            self.fireballs.append(fireball)

        # Add background image at the bottom of the screen
        self.background_image = Image(
          #  source=resource_path('positions/tank.png'),
            source=img_path,
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, None),  # Full width, height to be defined
            size=(Window.width, 900),  # Set a fixed height for the background image
            pos_hint={'x': 0, 'y': 0}  # Positioning it at the bottom
        )
        self.main_layout.add_widget(self.background_image)

        # Create an overlay layout for all UI components
        overlay = BoxLayout(orientation='vertical', size_hint=(1, None), height=00)  # Use fixed height for overlay



        # Create header section
        self.create_header()

        self.mayham_label = RotatableLabel(
            text=" METAL MAYHEM",
            color=(0.0, 1.0, 0.0, 1.0),
            font_size='25sp',
            pos_hint={'x': 0.2, 'y': 0.87},
            size_hint=(None, None),
            font_name=resource_path('fonts/DancingScript.ttf')
        )

        # Add it to the main layout
        self.main_layout.add_widget(self.mayham_label)



        self.achievement_label = RotatableLabel(
            text=" Top Achievements",
            color=(0.0, 1.0, 0.0, 1.0),
            font_size='25sp',
            pos_hint={'x': 0.83, 'y': 0.57},
            size_hint=(None, None),
            font_name=resource_path('fonts/DancingScript.ttf')
        )

        # Add it to the main layout
        self.main_layout.add_widget(self.achievement_label)

        self.show_animated_stats()






        self.create_db()

        self.countdown_widget = CountdownWidget(
            target_datetime="2025-05-05 23:59:59",
            target_timezone='America/New_York',
            size_hint=(None, None),
            size=(250, 50),
            pos_hint={'x': 0.65, 'top': 0.95},
            conn = self.conn
        )
        self.main_layout.add_widget(self.countdown_widget)

        new_target = self.get_countdown_target()
        if new_target:
            self.countdown_widget.start_countdown(new_target)


        # Add refresh button with GIF
        self.refresh_button = self.create_refresh_button()
        overlay.add_widget(self.refresh_button)

        # Create and add input screen
        self.input_layout = self.create_input_screen()
        overlay.add_widget(self.input_layout)

        # Top players layout
        self.top_players_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=170,
            padding=[80, 0, 0, 0]
        )

        # Top players label
        self.top_players_label = Label(
            text="Top 3 Players",
            size_hint_y=None,
            height=30,
            bold=True,
            color=(0.0, 1.0, 0.0, 1.0),
            size_hint_x=None,
            width=180
        )
        self.top_players_label.font_size = 24
      #  self.top_players_label.font_name =  resource_path(os.path.join("fonts", "DancingScript.ttf"))
        self.top_players_layout.add_widget(self.top_players_label)

        # Add glowing animation to top players label
        # Add glowing animation to top players label
        self.animate_glow(self.top_players_label)

        # Add glowing animation to mayhem label as well
        self.start_breathing_glow(self.mayham_label)


        # Spacer below the label
        spacer = Label(size_hint_y=None, height=10)
        self.top_players_layout.add_widget(spacer)

        # Add container for top players
        self.top_players_container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.top_players_container.bind(minimum_height=self.top_players_container.setter('height'))
        if self.conn is not None:
            self.fetch_top_players()
        else:
            print("Database connection was not established. Cannot fetch top players.")
        self.top_players_layout.add_widget(self.top_players_container)

        overlay.add_widget(self.top_players_layout)

        # Buttons layout
        self.button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height='60dp',
            spacing=10,
            padding=[10, 10, 10, 10]
        )

        # Create buttons
        self.create_players_button = Button(text='Admin Panel', size_hint_x=None, width=150)
      #  self.create_players_button.bind(on_press=self.open_create_player_popup)
        self.create_players_button.bind(
            on_press=lambda instance: self.prompt_admin_password(lambda: self.open_create_player_popup(instance)))
        style_button(self.create_players_button)
        self.button_layout.add_widget(self.create_players_button)

        self.submit_button = Button(text='Submit', size_hint_x=None, width=150, disabled=True)
        self.submit_button.bind(on_press=self.calculate_skill_rating)
        style_button(self.submit_button)
        self.button_layout.add_widget(self.submit_button)

        self.export_button = Button(text='Export Data', size_hint_x=None, width=150, disabled=True)
        self.export_button.bind(on_press=self.export_data)
        style_button(self.export_button)
        self.button_layout.add_widget(self.export_button)

        self.download_pdf_button = Button(
            text='Download Leaderboard as PDF',
            size_hint_x=None,
            width=260,
            disabled=False
        )
        self.download_pdf_button.bind(on_press=self.export_leaderboard_to_pdf)
        style_button(self.download_pdf_button)
        self.button_layout.add_widget(self.download_pdf_button)

        self.performance_leaderboard_button = Button(
            text='Performance\nLeaderboard',
            size_hint_x=None,
            width=150,
            disabled=False
        )
        self.performance_leaderboard_button.bind(on_press=self.show_leaderboard)
        style_button(self.performance_leaderboard_button)
        self.button_layout.add_widget(self.performance_leaderboard_button)

        self.statistical_leaderboard_button = Button(
            text='Statistical\nLeaderboard',
            size_hint_x=None,
            width=150,
            disabled=False
        )
        self.statistical_leaderboard_button.bind(on_press=self.show_statistical_leaderboard)
        style_button(self.statistical_leaderboard_button)
        self.button_layout.add_widget(self.statistical_leaderboard_button)

        self.stats_button = Button(text='My Stats', size_hint_x=None, width=150, disabled=False)
        self.stats_button.bind(on_press=self.request_player_name)
        style_button(self.stats_button)
        self.button_layout.add_widget(self.stats_button)

        overlay.add_widget(self.button_layout)

        # Add the overlay to the main layout
        self.main_layout.add_widget(overlay)

        # Create animation layout
        self.animation_layout = FloatLayout(size=Window.size)  # Dedicated layout for animations
        self.main_layout.add_widget(self.animation_layout)

        # Perform initial calculations for totals
        self.calculate_totals()

        video_id, thumbnail_path = self.fetch_video_data()

        if not hasattr(self, 'video_player_layout'):
            self.video_player_layout = FloatLayout(size_hint=(0.12, 0.5))

        thumbnail_path = resource_find(resource_path("positions/default_thumbnail.jpg"))
        if video_id and thumbnail_path:
            self.video_player = YouTubeVideoPlayer(video_id, thumbnail_path, self.music_control_button)
        else:
            fallback_thumbnail = resource_find(resource_path("positions/default_thumbnail.jpg"))
            self.video_player = YouTubeVideoPlayer(video_id, fallback_thumbnail,self.music_control_button)
        print("Thumbnail path:", resource_path("positions/default_thumbnail.jpg"))

        if self.video_player not in self.video_player_layout.children:
            self.video_player_layout.add_widget(self.video_player)

        if hasattr(self, 'refresh_button') and self.refresh_button in self.main_layout.children:
            self.main_layout.remove_widget(self.refresh_button)

        self.refresh_button = Button(
            background_normal=resource_path('positions/refresh.png'),
            background_down=resource_path('positions/refresh.png'),
            size_hint=(None, None),
            size=(50, 50),
            pos_hint={'center_x': 0.120, 'center_y': 0.45}
        )
        self.refresh_button.bind(on_press=self.animate_refresh)
        self.refresh_button.bind(on_press=self.on_button_press)
        self.refresh_button.bind(on_release=self.on_button_release)

        self.main_layout.add_widget(self.refresh_button)

        self.main_layout.add_widget(self.video_player_layout)

        # Create Home button
        self.home_button = Button(
            background_normal=resource_path('positions/home.png'),
            background_down=resource_path('positions/home.png'),
            size_hint=(None, None),
            size=(85, 85),
            pos_hint={'right': 1, 'top': 0.99}
        )

        print(self.main_layout.children)
        self.home_button.bind(on_press=self.go_to_home)  # Bind button press to the method
        self.home_button.bind(on_press=self.on_button_press)
        self.home_button.bind(on_release=self.on_button_release)
        self.main_layout.add_widget(self.home_button)  # Add the button to the main layout
        print(self.main_layout.children)

        return self.main_layout

    def get_highest_stats_sentences(self):
        cursor = self.conn.cursor()

        # Highest kills
        cursor.execute("SELECT player_name, kills FROM player_skill_rating ORDER BY kills DESC LIMIT 1")
        kill_row = cursor.fetchone()
        kill_sentence = ""
        if kill_row:
            kill_sentence = (
                f"             {kill_row[0]}\n\n"
                "         has scored the highest \n\n"
                "      kill count in a match and \n\n"
                f"             it is {kill_row[1]}."
            )

        # Highest flags captured
        cursor.execute(
            "SELECT player_name, flags_captured FROM player_skill_rating ORDER BY flags_captured DESC LIMIT 1")
        flag_row = cursor.fetchone()
        flag_sentence = ""
        if flag_row:
            flag_sentence = (
                f"             {flag_row[0]}\n\n"
                "  has captured the highest \n\n"
                "      number of flags in a match \n\n"
                f"          and it is {flag_row[1]}."
            )

        # Highest XP
        cursor.execute("SELECT player_name, xp FROM player_skill_rating ORDER BY xp DESC LIMIT 1")
        xp_row = cursor.fetchone()
        xp_sentence = ""
        if xp_row:
            xp_sentence = (
                f"                 {xp_row[0]}\n\n"
                "               has earned the \n\n"
                "      highest XP  value in a match \n\n"
                f"          and it is {xp_row[1]}."
            )

        # Team win rate analysis
        cursor.execute("SELECT AVG(red_team_win_rate), AVG(blue_team_win_rate) FROM overall_player_skill_rating")
        win_rate_row = cursor.fetchone()
        win_rate_sentence = ""
        if win_rate_row and win_rate_row[0] is not None and win_rate_row[1] is not None:
            red_win = win_rate_row[0]
            blue_win = win_rate_row[1]
            if abs(red_win - blue_win) < 1e-6:  # practically equal
                win_rate_sentence = (
                    "Did you know there is no advantage \n\n"
                    "specifically being in red or blue team \n\n"
                    "because win ratio for both teams are equal!"
                )
            elif red_win > blue_win:
                win_rate_sentence = (
                    "Did you know most players are successful \n\n"
                    "by playing as the Red team!"
                )
            else:
                win_rate_sentence = (
                    "Did you know most players are successful \n\n"
                    "by playing as the Blue team!"
                )

        # Total matches played
        cursor.execute("SELECT COUNT(match_number) FROM matches")
        match_count_row = cursor.fetchone()
        match_count_sentence = ""
        if match_count_row and match_count_row[0]:
            match_count_sentence = (
                f"So far we have played \n\n"
                f"      {match_count_row[0]} MAYHEM matches!"
            )

        cursor.close()

        return [
            kill_sentence,
            flag_sentence,
            xp_sentence,
            win_rate_sentence,
            match_count_sentence
        ]

    def show_animated_stats(self):
        sentences = self.get_highest_stats_sentences()
        if not sentences:
            return

        if hasattr(self, 'stats_label'):
            self.stats_label.opacity = 0
        else:
            # Create the label if it doesn't exist
            self.stats_label = Label(
                text="",
                font_size=20,
                size_hint=(None, None),
                size=(400, 100),
                pos_hint={'x': 0.74, 'y': 0.38},
                text_size=(400, None),
                halign='left',
                valign='middle',
                opacity=0,
                font_name=resource_path('fonts/cursive.ttf')
            )
            self.stats_label.bind(
                texture_size=lambda instance, value: setattr(instance, 'height', value[1])
            )
            self.main_layout.add_widget(self.stats_label)

        self.current_sentence_index = 0

        def animate_sentence(dt=None):
            sentence = sentences[self.current_sentence_index]
            self.stats_label.text = sentence

            anim_in = Animation(opacity=1, duration=1)
            anim_wait = Animation(duration=8)
            anim_out = Animation(opacity=0, duration=1)
            anim = anim_in + anim_wait + anim_out

            def on_complete(animation, widget):
                self.current_sentence_index = (self.current_sentence_index + 1) % len(sentences)
                Clock.schedule_once(animate_sentence, 0.5)

            anim.bind(on_complete=on_complete)
            anim.start(self.stats_label)

        animate_sentence()

    def on_button_press(self, instance):
        instance.background_color = (0.5, 0.5, 0.5, 1)

    def on_button_release(self, instance):
        instance.background_color = (1, 1, 1, 1)

    def get_countdown_target(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT countdown_to FROM countdown ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result[0]  # Returns a datetime string
        return None


    def prompt_admin_password(self, callback):
        # Function to fetch the stored admin password from the database
        def fetch_stored_password():
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT password FROM admin_credentials WHERE id = 1")  # Adjust the query as needed
                result = cursor.fetchone()
                return result[0] if result else None
            except Exception as e:
                self.show_popup("Database Error", f"Failed to fetch admin password: {e}")
                return None

        # Fetch the stored password
        stored_password = fetch_stored_password()
        if stored_password is None:
            return  # Stop execution if password couldn't be fetched

        # Layout for the password input and buttons
        layout = BoxLayout(orientation='vertical', padding=10, spacing=8)

        # Password input field
        pw_input = TextInput(
            password=True,
            multiline=False,
            hint_text="Enter Admin Password",
            size_hint_y=None,
            height=36,
            font_size=14
        )
        layout.add_widget(pw_input)

        # Buttons layout
        btns = BoxLayout(size_hint_y=None, height=40, spacing=10)
        ok_btn = Button(text="OK", size_hint_x=0.5)
        cancel_btn = Button(text="Cancel", size_hint_x=0.5)

        btns.add_widget(ok_btn)
        btns.add_widget(cancel_btn)
        layout.add_widget(btns)

        # Create popup
        popup = Popup(
            title="Admin Access",
            content=layout,
            size_hint=(0.35, 0.25),  # Smaller popup
            auto_dismiss=False
        )

        # Define what happens when "OK" is clicked
        def on_ok(instance):
            if pw_input.text == stored_password:  # Check the input against the stored password
                popup.dismiss()
                callback()  # Call the original function (e.g., open_create_player_popup)
            else:
                self.show_popup("Access Denied", "Incorrect admin password.")

        # Bind button actions
        ok_btn.bind(on_press=on_ok)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())

        popup.open()

    def animate_refresh(self, instance):
        # Create an animation that scales the button
        animation = Animation(size=(50, 50), duration=0.1) + Animation(size=(50, 50), duration=0.1)
        animation.start(instance)

        # Call the refresh video player method after the animation
        Clock.schedule_once(lambda dt: self.refresh_video_player(), 0.2)  # Delay to allow animation to complete

    def refresh_video_player(self):
        video_id, thumbnail_path = self.fetch_video_data()
        if video_id and thumbnail_path:
            self.video_player.video_id = video_id  # Update the video ID
          #  self.video_player.thumbnail.source = thumbnail_path  # Update the thumbnail
          #  self.video_player.thumbnail.reload()  # Reload the thumbnail image
        else:
            print("No video data found to update.")

    def fetch_video_data(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT video_id, thumbnail_path FROM commentary_games_video ORDER BY id DESC LIMIT 1")  # Get the latest video
            result = cursor.fetchone()
            if result:
                video_id, thumbnail_path = result
                return video_id, thumbnail_path
            else:
                print("No video data found.")
                return None, None
        except mysql.connector.Error as err:
            print(f"Error fetching video data: {err}")
            return None, None

    def hide_video_elements(self):
        print(
            f"Current children in main_layout before hiding: {[type(widget) for widget in self.main_layout.children]}")

        # Remove the YouTube player if it exists
        if hasattr(self, 'video_player') and self.video_player:
            if self.video_player.parent:
                self.video_player.parent.remove_widget(self.video_player)
                print("YouTube Video Player removed.")

        # Remove refresh button if it exists
        if hasattr(self, 'refresh_button') and self.refresh_button.parent:
            self.main_layout.remove_widget(self.refresh_button)
            print("Refresh button removed.")

        print(f"Current children in main_layout after hiding: {[type(widget) for widget in self.main_layout.children]}")

    def toggle_music(self, instance):
        if self.music_playing:
            pygame.mixer.music.pause()
            self.music_playing = False
        else:
            pygame.mixer.music.unpause()
            self.music_playing = True
        self.update_button_image()  # Update the button image to reflect state

    def open_music_selection(self, instance):

        self.ensure_music_folder_exists()

        layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        music_files = [f for f in os.listdir(self.persistent_music_folder) if f.endswith('.mp3')]

        if not music_files:
            btn = Button(text="No music files found.", size_hint_y=None, height=50)
            layout.add_widget(btn)
        else:
            for filename in music_files:
                btn = Button(
                    text=filename,
                    size_hint_y=None,
                    height=50,
                    background_color=(1, 1, 1, 1),
                    color=(0, 0, 0, 1)
                )
                full_path = os.path.join(self.persistent_music_folder, filename)
                btn.bind(on_release=partial(self.select_music, full_path))
                layout.add_widget(btn)

        # Add "Add Custom Music" button
        add_button = Button(text="Add Custom Music", size_hint_y=None, height=50, background_color=(0.6, 0.9, 0.6, 1))
        add_button.bind(on_release=self.add_custom_music)
        layout.add_widget(add_button)

        self.music_selection_popup = Popup(
            title='Select Music',
            content=layout,
            size_hint=(None, None),
            size=(400, 600)
        )
        self.music_selection_popup.open()

    def open_music_selection(self, instance):
        self.ensure_music_folder_exists()

        layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # 1. List bundled/default music files
        default_music_folder = resource_path("music")
        default_music_files = []
        if os.path.exists(default_music_folder):
            default_music_files = [
                f for f in os.listdir(default_music_folder) if f.endswith(".mp3")
            ]

        # 2. List user-added music files
        user_music_files = []
        if os.path.exists(self.persistent_music_folder):
            user_music_files = [
                f for f in os.listdir(self.persistent_music_folder) if f.endswith(".mp3")
            ]

        has_any_music = default_music_files or user_music_files

        if not has_any_music:
            btn = Button(text="No music files found.", size_hint_y=None, height=50)
            layout.add_widget(btn)
        else:
            # Add bundled/default music buttons
            for filename in default_music_files:
                btn = Button(
                    text=f"[Default] {filename}",
                    size_hint_y=None,
                    height=50,
                    background_color=(0.9, 0.9, 1, 1),
                    color=(0, 0, 0, 1)
                )
                full_path = resource_path(os.path.join("music", filename))
                btn.bind(on_release=partial(self.select_music, full_path))
                layout.add_widget(btn)

            # Add user-added music buttons
            for filename in user_music_files:
                btn = Button(
                    text=filename,
                    size_hint_y=None,
                    height=50,
                    background_color=(1, 1, 1, 1),
                    color=(0, 0, 0, 1)
                )
                full_path = os.path.join(self.persistent_music_folder, filename)
                btn.bind(on_release=partial(self.select_music, full_path))
                layout.add_widget(btn)

        # Add "Add Custom Music" button
        add_button = Button(text="Add Custom Music", size_hint_y=None, height=50, background_color=(0.6, 0.9, 0.6, 1))
        add_button.bind(on_release=self.add_custom_music)
        layout.add_widget(add_button)

        self.music_selection_popup = Popup(
            title='Select Music',
            content=layout,
            size_hint=(None, None),
            size=(400, 600)
        )
        self.music_selection_popup.open()

    def select_music(self, path, *args):  # Add *args to accept any extra arguments from the event
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1)  # Play the music in a loop
            self.music_playing = True
            self.update_button_image()  # Refresh the button image
            print(f"Now playing: {os.path.basename(path)}")
        except Exception as e:
            print(f"Error loading selected music: {e}")

        if hasattr(self, 'music_selection_popup'):
            self.music_selection_popup.dismiss()

    def upload_music(self, instance):
        # Close Kivy popup temporarily

        self.ensure_music_folder_exists()

        self.music_selection_popup.dismiss()

        # Open file dialog using Tkinter (headless)
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
        root.destroy()

        if file_path:
            try:
                filename = os.path.basename(file_path)
                destination = os.path.join(self.persistent_music_folder, filename)

                required_space_in_bytes = 50 * 1024 * 1024  # Example: 50 MB required space for the music file

                # Check if there is enough space before proceeding
                if not self.check_disk_space(os.path.expanduser('~/Documents'), required_space_in_bytes):
                    print("Not enough space in Documents. Attempting to use secondary location.")
                    if not self.save_file_with_fallback(filename, "Dummy content", required_space_in_bytes):
                        print("Both primary and secondary locations are full. Cannot upload the music.")
                        return

                shutil.copy(file_path, destination)
                print(f"Copied: {file_path} to {destination}")
                self.select_music(destination)  # Immediately play

            except Exception as e:
                print(f"Failed to copy selected file: {e}")

        # Reopen popup to refresh list
        self.open_music_selection(None)

    def add_custom_music(self, instance):

        self.ensure_music_folder_exists()

        try:
            root = Tk()
            root.withdraw()
            selected_file = filedialog.askopenfilename(filetypes=[("MP3 Files", "*.mp3")])
            root.destroy()

            if selected_file:
                filename = os.path.basename(selected_file)
                destination_path = os.path.join(self.persistent_music_folder, filename)

                required_space_in_bytes = 50 * 1024 * 1024  # Example: 50 MB required space for the music file

                # Check if there is enough space before proceeding
                if not self.check_disk_space(os.path.expanduser('~/Documents'), required_space_in_bytes):
                    print("Not enough space in Documents. Attempting to use secondary location.")
                    if not self.save_file_with_fallback(filename, "Dummy content", required_space_in_bytes):
                        print("Both primary and secondary locations are full. Cannot add the custom music.")
                        return

                if not os.path.exists(destination_path):
                    shutil.copy(selected_file, destination_path)
                    print(f"Copied {filename} to {destination_path}")
                else:
                    print("File already exists in music folder.")

                # Refresh the popup
                self.music_selection_popup.dismiss()
                self.open_music_selection(None)

        except Exception as e:
            print(f"Error adding custom music: {e}")

    def update_button_image(self):
        if self.music_playing:
            pause_img = resource_path('positions/pause.png')
            if os.path.exists(pause_img):
                self.music_control_button.background_normal = pause_img
                self.music_control_button.background_down = pause_img
            else:
                print(f"[Warning] pause.png not found at: {pause_img}")
        else:
            play_img = resource_path('positions/play.png')
            if os.path.exists(play_img):
                self.music_control_button.background_normal = play_img
                self.music_control_button.background_down = play_img
            else:
                print(f"[Warning] play.png not found at: {play_img}")

    def create_refresh_button(self):

        gif_path = resource_path('positions/refresh.gif')
        self.gif_button = Image(
            source=gif_path,
            size_hint=(None, None),
            size=(100, 100),
            opacity=0.88
        )

        self.gif_button.bind(on_touch_down=self.on_gif_click)

        # Use a FloatLayout for positioning
        layout = FloatLayout(size=(750, 740))  # Set layout size to the size of your app window.

        # Set an absolute position (x, y in pixels)
        self.gif_button.pos = (850, 750)  # Change these values as needed (x, y)

        layout.add_widget(self.gif_button)  # Add the GIF to the layout
        return layout

    def on_gif_click(self, instance, touch):
        # This method checks if the touch is on the GIF, without using pressure
        if instance.collide_point(*touch.pos):
            self.refresh_data()  # Call the refresh data method when the GIF is clicked

            return True  # Indicate the event has been handled
        return False  # Allow other touches to be handled normally

    def refresh_data(self):
        # Set the GIF opacity to 1 to make it visible
        self.gif_button.opacity = 1  # Ensure the GIF is visible
        Clock.schedule_once(lambda dt: self.play_gif(), 0)  # Schedule the GIF to play after a click

        # Refresh the statistics
        self.calculate_totals()  # Refresh the totals
        self.fetch_top_players()  # Refresh top player information
        self.show_animated_stats()



    def play_gif(self):
        # Hide or stop showing the GIF after 2.5 seconds
        Clock.schedule_once(self.hide_gif, 2.5)  # Schedule to call hide_gif after 2.5 seconds

    def hide_gif(self, dt):
        self.gif_button.opacity = 0.85  # Make the GIF invisible

    def calculate_totals(self):
        try:
            cursor = self.conn.cursor()

            # Calculate Total Games
            cursor.execute("SELECT COUNT(*) FROM matches")
            total_games = cursor.fetchone()[0]

            # Calculate Total Kills
            cursor.execute("SELECT SUM(kills) FROM overall_player_skill_rating")
            total_kills = cursor.fetchone()[0] or 0  # Default to 0 if None

            # Calculate Total Flags
            cursor.execute("SELECT SUM(flags_captured) FROM overall_player_skill_rating")
            total_flags = cursor.fetchone()[0] or 0  # Default to 0 if None

            # Animate the totals
            self.animate_count_up(self.total_games_label, total_games)
            self.animate_count_up(self.total_kills_label, total_kills)
            self.animate_count_up(self.total_flags_label, total_flags)

        except mysql.connector.Error as err:
            print(f"Error occurred while calculating totals: {err}")
            self.show_popup("Error", str(err))

    def open_create_player_popup(self, instance):
        input_layout = BoxLayout(orientation='vertical', padding=6, spacing=16)

        # --- Countdown Target with Spinners ---
        countdown_label = Label(text="Set Game Starting time in EDT:", size_hint_y=None, height=30)

        # Year Spinner
        current_year = datetime.now().year
        self.year_spinner = Spinner(
            text=str(current_year),
            values=[str(y) for y in range(current_year, current_year + 5)],
            size_hint_y=None, height=40
        )

        # Month Spinner
        self.month_spinner = Spinner(
            text="01",
            values=[f"{m:02}" for m in range(1, 13)],
            size_hint_y=None, height=40
        )

        # Day Spinner
        self.day_spinner = Spinner(
            text="01",
            values=[f"{d:02}" for d in range(1, 32)],
            size_hint_y=None, height=40
        )

        # Hour Spinner
        self.hour_spinner = Spinner(
            text="00",
            values=[f"{h:02}" for h in range(0, 24)],
            size_hint_y=None, height=40
        )

        # Minute Spinner
        self.minute_spinner = Spinner(
            text="00",
            values=[f"{m:02}" for m in range(0, 60)],
            size_hint_y=None, height=40
        )

        # Second Spinner
        self.second_spinner = Spinner(
            text="00",
            values=[f"{s:02}" for s in range(0, 60)],
            size_hint_y=None, height=40
        )

        # Layout for date
        date_spinner_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        date_spinner_layout.add_widget(self.year_spinner)
        date_spinner_layout.add_widget(self.month_spinner)
        date_spinner_layout.add_widget(self.day_spinner)

        # Layout for time
        time_spinner_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        time_spinner_layout.add_widget(self.hour_spinner)
        time_spinner_layout.add_widget(self.minute_spinner)
        time_spinner_layout.add_widget(self.second_spinner)

        # Add a "No Mayhem Scheduled" checkbox
        self.no_mayhem_checkbox = CheckBox(active=False)
        no_mayhem_label = Label(text="No Mayhem Scheduled", size_hint_y=None, height=30)
        no_mayhem_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        no_mayhem_layout.add_widget(self.no_mayhem_checkbox)
        no_mayhem_layout.add_widget(no_mayhem_label)

        # Add it to the input_layout
        input_layout.add_widget(no_mayhem_layout)

        countdown_button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        countdown_ok = Button(text="Set", size_hint_x=0.5)
        countdown_cancel = Button(text="Cancel", size_hint_x=0.5)

        def set_countdown_target(instance):
            try:
                # Check if No Mayhem Scheduled is checked
                if self.no_mayhem_checkbox.active:
                    self.reset_countdown()  # Reset countdown
                    self.show_popup("No Mayhem Scheduled", "Set to No Schedule")

                    return  # Exit the function without setting the countdown if checkbox is checked

                # Debugging: Check spinner states
                print(
                    f"Year Spinner: {self.year_spinner}, Value: {self.year_spinner.text if self.year_spinner else 'None'}")
                print(
                    f"Month Spinner: {self.month_spinner}, Value: {self.month_spinner.text if self.month_spinner else 'None'}")
                print(
                    f"Day Spinner: {self.day_spinner}, Value: {self.day_spinner.text if self.day_spinner else 'None'}")
                print(
                    f"Hour Spinner: {self.hour_spinner}, Value: {self.hour_spinner.text if self.hour_spinner else 'None'}")
                print(
                    f"Minute Spinner: {self.minute_spinner}, Value: {self.minute_spinner.text if self.minute_spinner else 'None'}")
                print(
                    f"Second Spinner: {self.second_spinner}, Value: {self.second_spinner.text if self.second_spinner else 'None'}")

                # Check if any spinner is missing or None
                if any([
                    not self.year_spinner or not self.year_spinner.text,
                    not self.month_spinner or not self.month_spinner.text,
                    not self.day_spinner or not self.day_spinner.text,
                    not self.hour_spinner or not self.hour_spinner.text,
                    not self.minute_spinner or not self.minute_spinner.text,
                    not self.second_spinner or not self.second_spinner.text
                ]):
                    raise ValueError("One or more spinner values are missing or invalid.")

                # Print spinner values to debug
                print(f"Year: {self.year_spinner.text}, Month: {self.month_spinner.text}, "
                      f"Day: {self.day_spinner.text}, Hour: {self.hour_spinner.text}, "
                      f"Minute: {self.minute_spinner.text}, Second: {self.second_spinner.text}")

                # Regular countdown target setting
                date_part = f"{self.year_spinner.text}-{self.month_spinner.text}-{self.day_spinner.text}"
                time_part = f"{self.hour_spinner.text}:{self.minute_spinner.text}:{self.second_spinner.text}"
                full_datetime = f"{date_part} {time_part}"

                # Validate datetime
                print(f"Attempting to parse datetime: {full_datetime}")
                try:
                    dt = datetime.strptime(full_datetime, "%Y-%m-%d %H:%M:%S")
                    print(f"Parsed datetime: {dt}")
                except Exception as e:
                    print(f"Datetime parsing error: {e}")
                    raise

                # Insert the countdown to the database
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO countdown (id, countdown_to) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE countdown_to = VALUES(countdown_to)",
                    (1, full_datetime)
                )
                self.conn.commit()
                self.show_popup("Success", f"Countdown updated to {full_datetime}")
            except Exception as e:
                print(f"Error occurred: {e}")
                self.show_popup("Error", f"Failed to update countdown: {e}")

        countdown_ok.bind(on_press=set_countdown_target)
        countdown_cancel.bind(on_press=lambda x: (
            setattr(self.year_spinner, 'text', str(current_year)),
            setattr(self.month_spinner, 'text', "01"),
            setattr(self.day_spinner, 'text', "01"),
            setattr(self.hour_spinner, 'text', "00"),
            setattr(self.minute_spinner, 'text', "00"),
            setattr(self.second_spinner, 'text', "00"),
        ))

        countdown_button_layout.add_widget(countdown_ok)
        countdown_button_layout.add_widget(countdown_cancel)

        # Add everything to input layout
        input_layout.add_widget(countdown_label)
        input_layout.add_widget(date_spinner_layout)
        input_layout.add_widget(time_spinner_layout)
        input_layout.add_widget(countdown_button_layout)

        # --- Reset Admin Password section ---
        reset_pw_label = Label(text="Reset Admin Password:", size_hint_y=None, height=30)
        self.reset_password_input = TextInput(multiline=False, size_hint_y=None, height=40, password=True)

        reset_pw_button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        reset_ok = Button(text="OK", size_hint_x=0.5)
        reset_cancel = Button(text="Cancel", size_hint_x=0.5)
        reset_cancel.bind(on_press=lambda x: setattr(self.reset_password_input, 'text', ''))

        # --- Actual Reset Logic ---
        def reset_admin_password(instance):
            new_password = self.reset_password_input.text.strip()
            if not new_password:
                self.show_popup("Error", "Password cannot be empty.")
                return

            try:
                cursor = self.conn.cursor()
                # Ensure admin row exists. Using INSERT IGNORE (MySQL syntax); if not, adjust as needed.
                cursor.execute("INSERT IGNORE INTO admin_credentials (id, password) VALUES (%s, %s)", (1, "default123"))
                # Update password with %s placeholder
                cursor.execute("UPDATE admin_credentials SET password = %s WHERE id = 1", (new_password,))
                self.conn.commit()
                self.show_popup("Success", "Admin password updated successfully.")
                self.reset_password_input.text = ""
            except Exception as e:
                self.show_popup("Database Error", f"Failed to update password: {e}")

        reset_ok.bind(on_press=reset_admin_password)
        reset_pw_button_layout.add_widget(reset_ok)
        reset_pw_button_layout.add_widget(reset_cancel)

        input_layout.add_widget(reset_pw_label)
        input_layout.add_widget(self.reset_password_input)
        input_layout.add_widget(reset_pw_button_layout)

        # --- MAYHEM Video URL field ---
        video_label = Label(text="MAYHEM Video URL:", size_hint_y=None, height=30)
        self.video_url_input = TextInput(multiline=False, size_hint_y=None, height=40)
        input_layout.add_widget(video_label)
        input_layout.add_widget(self.video_url_input)

        video_button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        video_ok_button = Button(text="Save Video URL", size_hint_x=0.5)
        video_ok_button.bind(on_press=lambda x: self.save_video_url(self.video_url_input.text))
        video_cancel_button = Button(text="Cancel", size_hint_x=0.5)
        video_cancel_button.bind(on_press=lambda x: setattr(self.video_url_input, 'text', ''))
        video_button_layout.add_widget(video_ok_button)
        video_button_layout.add_widget(video_cancel_button)

        input_layout.add_widget(video_button_layout)

        # --- Player name section ---
        input_label = Label(text="Enter a Player Name to create a player:", size_hint_y=None, height=30)
        self.player_name_input = TextInput(multiline=False, size_hint_y=None, height=40)
        input_layout.add_widget(input_label)
        input_layout.add_widget(self.player_name_input)

        # --- Existing players dropdown ---
        cursor = self.conn.cursor()
        cursor.execute('SELECT player_name FROM overall_player_skill_rating')
        existing_players = cursor.fetchall()

        if existing_players:
            self.dropdown = DropDown()
            for player in existing_players:
                player_name = player[0]
                player_button = Button(text=player_name, size_hint_y=None, height=44)
                player_button.bind(on_release=lambda btn: self.select_existing_player(btn.text))
                self.dropdown.add_widget(player_button)

            self.player_dropdown_button = Button(text="See Existing Players", size_hint_y=None, height=40)
            self.player_dropdown_button.bind(on_release=self.dropdown.open)
            input_layout.add_widget(self.player_dropdown_button)

        # --- Main control buttons ---
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)

        ok_button = Button(text="OK", size_hint_x=0.4)
        ok_button.bind(on_press=lambda x: self.create_player(self.player_name_input.text))

        cancel_button = Button(text="Cancel", size_hint_x=0.3)
        cancel_button.bind(on_press=lambda x: self.player_name_popup.dismiss())

        delete_button = Button(text="Delete", size_hint_x=0.3)

        def confirm_delete():
            """Prompt the user to confirm deletion of the player."""
            player_name = self.player_name_input.text.strip()
            if not player_name:
                self.show_popup("Error", "Please enter a player name to delete.")
                return

            confirmation_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
            confirmation_label = Label(text=f"Are you sure you want to delete '{player_name}'?", size_hint_y=None,
                                       height=40)

            confirmation_layout.add_widget(confirmation_label)
            confirm_button = Button(text="Yes")
            confirm_cancel_button = Button(text="No")

            confirmation_layout.add_widget(confirm_button)
            confirmation_layout.add_widget(confirm_cancel_button)

            confirm_popup = Popup(title="Confirm Deletion", content=confirmation_layout, size_hint=(0.4, 0.3))

            def on_confirm(instance):
                try:
                    cursor = self.conn.cursor()
                    cursor.execute('DELETE FROM overall_player_skill_rating WHERE player_name = %s', (player_name,))
                    self.conn.commit()
                    self.show_popup("Deleted", f"Player '{player_name}' deleted successfully.")
                    self.player_name_input.text = ""  # Clear the input field after deletion
                    self.player_name_popup.dismiss()
                except mysql.connector.Error as err:
                    self.show_popup("Error", f"Could not delete player: {str(err)}")
                confirm_popup.dismiss()  # Close confirmation popup

            confirm_button.bind(on_press=on_confirm)
            cancel_button.bind(on_press=lambda x: confirm_popup.dismiss())

            confirm_popup.open()  # Open the confirmation popup

        delete_button.bind(on_press=lambda x: confirm_delete())

        button_layout.add_widget(ok_button)
        button_layout.add_widget(cancel_button)
        button_layout.add_widget(delete_button)

        input_layout.add_widget(button_layout)

        # Create close button for the popup
        close_button = Button(text="Close", size_hint=(None, None), size=(90, 50), pos_hint={'top': 20.8, 'left':1 })
        close_button.bind(on_press=lambda x: self.player_name_popup.dismiss())


        button_layout.add_widget(close_button)


        self.player_name_popup = Popup(title="Admin Panel", content=input_layout, size_hint=(0.7, 0.9))
        self.player_name_popup.open()






    def save_video_url(self, url):
        video_id = self.extract_video_id(url)
        if not video_id:
            self.show_popup("Error", "Invalid YouTube URL.")
            return

        try:
            cursor = self.conn.cursor()

            thumbnail_path = resource_find(resource_path("positions/default_thumbnail.jpg"))

            cursor.execute('''
                INSERT INTO commentary_games_video (id, video_id, thumbnail_path)
                VALUES (1, %s, %s)
                ON DUPLICATE KEY UPDATE video_id = VALUES(video_id), thumbnail_path = VALUES(thumbnail_path)
            ''', (video_id, thumbnail_path))

            self.conn.commit()

            self.show_popup("Success", f"Video ID saved: {video_id}")

            # 👇 Now update the YouTube player instance if one is showing
            if hasattr(self, 'youtube_player'):
                self.main_layout.remove_widget(self.youtube_player)

            thumbnail_path = resource_find(resource_path("positions/default_thumbnail.jpg"))  # Replace with actual path or thumbnail logic
            self.youtube_player = YouTubeVideoPlayer(video_id, thumbnail_path, self.music_control_button)
            self.main_layout.add_widget(self.youtube_player)

        except mysql.connector.Error as err:
            self.show_popup("Error", f"Could not save video ID: {str(err)}")

    def reset_countdown(self):
        """Reset the countdown to indicate that no mayhem is scheduled."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO countdown (id, countdown_to) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE countdown_to = %s",
                (1, "1900-07-01 00:00:00", "1900-07-01 00:00:00")
            )
            self.conn.commit()

            # Reset the target datetime in the widget
            self.target_datetime = None

            # Reset the label text and progress circle when no mayhem is scheduled
            if self.label:
                self.label.text = "NO MAYHEM SCHEDULED"

            if self.progress_circle:
                self.progress_circle.circle = (self.center_x, self.center_y, 100, 0, 0)  # Reset progress circle

            # Cancel any glowing animation if it exists
            if self.glow_event:
                self.glow_event.cancel()  # Cancel any glowing animation
                self.glow_event = None

            # Debugging: Confirm the reset
            print("Countdown reset successfully, 'No Mayhem Scheduled' displayed.")

        except Exception as e:
            # Catch any errors during the reset process and display them in a popup
            print(f"Error occurred during reset: {e}")
            self.show_popup("Error", f"Failed to reset countdown: {e}")

    def extract_video_id(self, url):
        # Extract the video ID from various YouTube URL formats
        regex = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
        match = re.search(regex, url)
        if match:
            return match.group(1)
        return None


    def delete_player(self, player_name):
        if not player_name:
            self.show_popup("Error", "Please enter a player name to delete.")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM overall_player_skill_rating WHERE player_name = %s', (player_name,))
            self.conn.commit()
            self.show_popup("Deleted", f"Player '{player_name}' deleted.")
            self.player_name_popup.dismiss()
        except mysql.connector.Error as err:
            self.show_popup("Error", f"Could not delete player: {str(err)}")

    def select_existing_player(self, player_name):
        self.player_name_input.text = player_name  # Populate the input field with the existing player's name
        self.dropdown.dismiss()  # Close the dropdown after selection

    def ask_for_create_admin_password(self, on_success_callback):
        # Function to fetch the stored admin password from the database
        def fetch_stored_password():
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT password FROM admin_credentials WHERE id = 1")  # Adjust the query as needed
                result = cursor.fetchone()
                return result[0] if result else None
            except Exception as e:
                self.show_popup("Database Error", f"Failed to fetch admin password: {e}")
                return None

        # Fetch the stored password
        stored_password = fetch_stored_password()
        if stored_password is None:
            return  # Stop execution if password couldn't be fetched

        # Main layout for the popup content
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text="Enter Admin Password:"))

        password_input = TextInput(password=True, multiline=False)
        content.add_widget(password_input)

        button_layout = BoxLayout(size_hint_y=None, height=40)
        ok_button = Button(text="OK")
        cancel_button = Button(text="Cancel")
        button_layout.add_widget(ok_button)
        button_layout.add_widget(cancel_button)

        content.add_widget(button_layout)

        popup = Popup(title="Admin Authentication", content=content, size_hint=(0.4, 0.25))

        # Validate the entered password
        def validate_password(instance):
            if password_input.text == stored_password:
                popup.dismiss()
                on_success_callback()  # Callback function on successful authentication
            else:
                self.show_popup("Access Denied", "Invalid admin password.")

        ok_button.bind(on_press=validate_password)
        cancel_button.bind(on_press=popup.dismiss)

        popup.open()

    def create_player(self, player_name):
        def do_create():
            if player_name.strip() == "":
                self.show_popup("Error", "Please enter a valid player name.")
                return

            try:
                cursor = self.conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM overall_player_skill_rating WHERE player_name = %s', (player_name,))
                exists = cursor.fetchone()[0]

                if exists > 0:
                    self.show_popup("Error", f"Player '{player_name}' already exists.")
                    return

                cursor.execute('''
                    INSERT INTO overall_player_skill_rating (player_name, country_flag)
                    VALUES (%s, %s)
                ''', (player_name, "default.png"))

                self.conn.commit()
                self.show_popup("Success", f"Player '{player_name}' created successfully.")
            except mysql.connector.Error as err:
                self.show_popup("Error", f"Could not create player: {str(err)}")

        #  Trigger admin password prompt
        self.ask_for_create_admin_password(do_create)

    def animate_glow(self, label):
        glow_animation = Animation(opacity=0.5, duration=0.5) + Animation(opacity=1, duration=0.5)
        glow_animation.repeat = True
        glow_animation.start(label)

    def start_breathing_glow(self, label):
        def breathing_cycle(*args):
            breathe = (
                    Animation(opacity=0.5, color=(0.8, 1.0, 0.8, 1.0), duration=4.0) +
                    Animation(opacity=1.0, color=(1.0, 1.0, 1.0, 1.0), duration=4.0)
            )
            breathe.bind(on_complete=breathing_cycle)
            breathe.start(label)

        breathing_cycle()

    def update_rect(self, instance, value):
        self.shadow_rect.pos = self.top_players_label.pos
        self.shadow_rect.size = self.top_players_label.size
        self.bg_rect.pos = self.top_players_label.pos
        self.bg_rect.size = self.top_players_label.size

    def create_header(self):
        header_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=120,
                                  padding=[600, 0, 0, 350], spacing=10)

        # Create the welcome label
        self.welcome_label = Label(
            text="Welcome Commander!",
            font_size="24sp",
            color=(1, 1, 0, 1),
            size_hint=(None, None),
            halign="center"
        )
        self.welcome_label.bind(size=self._update_label_size)
        self.welcome_label.size = (self.welcome_label.texture_size[0], 40)

        header_layout.add_widget(self.welcome_label)

        # Create a grid layout for the statistics labels
        self.stats_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=100, spacing=40,
                                      padding=(290, 0, 0, 400))

        # Total Games label
        self.total_games_label = Label(text="Total Games: 0", color=(1, 1, 1, 1), font_size='20sp')
       # self.total_games_label.font_name = resource_path(os.path.join("fonts", "DancingScript.ttf"))   # Set custom font
        self.stats_layout.add_widget(self.total_games_label)

        # Total Kills label
        self.total_kills_label = Label(text="Total Kills: 0", color=(1, 1, 1, 1), font_size='20sp')
     #   self.total_kills_label.font_name = os.path.join("fonts", "DancingScript.ttf")  # Set custom font
        self.stats_layout.add_widget(self.total_kills_label)

        # Total Flags label
        self.total_flags_label = Label(text="Total Flags: 0", color=(1, 1, 1, 1), font_size='20sp')
      #  self.total_flags_label.font_name = os.path.join("fonts", "DancingScript.ttf")  # Set custom font
        self.stats_layout.add_widget(self.total_flags_label)

        # Add stats layout to header layout
        header_layout.add_widget(self.stats_layout)

        # Add header layout to the main layout
        self.main_layout.add_widget(header_layout)

        # Start the animation for the welcome text
        self.animate_welcome_text()

    def animate_count_up(self, label, final_value, duration=2):
        is_float = isinstance(final_value, float)

        # Start at 0 or 0.00
        label_prefix = label.text.split(": ")[0] + ": "
        label.text = f"{label_prefix}0.00" if is_float else f"{label_prefix}0"

        color_change = Animation(color=(0, 1, 0, 1), duration=0.5) + Animation(color=(1, 1, 1, 1), duration=0.5)

        def update_label(dt):
            current_text = label.text.split(": ")[1]

            try:
                current_value = float(current_text) if is_float else int(current_text)
            except ValueError:
                current_value = 0.0 if is_float else 0

            if current_value < final_value:
                # Float or int increment logic
                steps = 30
                increment = max(0.01, (final_value - current_value) / steps) if is_float else max(1, (
                            final_value - current_value) // steps)
                new_value = min(current_value + increment, final_value)

                label.text = f"{label_prefix}{new_value:.2f}" if is_float else f"{label_prefix}{int(new_value)}"
                color_change.start(label)
            else:
                Clock.unschedule(update_label)

        Clock.schedule_interval(update_label, duration / 30.0)

    def update_statistics(self, total_games, total_kills, total_flags):
        self.total_games_label.text = f"Total Games: {total_games}"
        self.total_kills_label.text = f"Total Kills: {total_kills}"
        self.total_flags_label.text = f"Total Flags: {total_flags}"

    def animate_welcome_text(self):
        # Set the initial opacity to 1 (fully visible)
        self.welcome_label.opacity = 1

        # Define the fade-out animation
        fade_out = Animation(opacity=0, duration=10)  # Fade out over 2.5 seconds

        # Start the fade-out animation
        fade_out.start(self.welcome_label)

    def _update_label_size(self, instance, value):
        # Update the label's size in corresponding the dimension change
        self.welcome_label.x = (Window.width // 2) - (self.welcome_label.width // 2)




    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def request_player_name(self, instance):
        # Create a layout for the input
        input_layout = BoxLayout(orientation='vertical', padding=10)

        input_label = Label(text="Enter your Player Name:", size_hint_y=None, height=40)
        player_name_input = TextInput(multiline=False, size_hint_y=None, height=40)

        # Fetch existing player names from the database
        cursor = self.conn.cursor()
        cursor.execute('SELECT player_name FROM overall_player_skill_rating')
        existing_players = cursor.fetchall()

        if existing_players:
            # Create the dropdown for selecting an existing player
            self.dropdown = DropDown()

            for player in existing_players:
                player_name = player[0]
                player_button = Button(text=player_name, size_hint_y=None, height=44)
                player_button.bind(
                    on_release=lambda btn, name=player_name: self.select_existing_player(name, player_name_input))
                self.dropdown.add_widget(player_button)

            # Button to open the dropdown
            self.player_dropdown_button = Button(text="See Existing Players", size_hint_y=None, height=40)
            self.player_dropdown_button.bind(on_release=self.dropdown.open)
            input_layout.add_widget(self.player_dropdown_button)

        input_layout.add_widget(input_label)
        input_layout.add_widget(player_name_input)

        # Button layout for OK and Cancel
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)

        # Create the popup
        player_name_popup = Popup(title="Player Name", content=input_layout, size_hint=(0.4, 0.3))

        # OK button
        ok_button = Button(text="OK", size_hint_x=0.5)
        ok_button.bind(on_press=lambda x: self.handle_player_name_submission(player_name_input.text, player_name_popup))
        button_layout.add_widget(ok_button)

        # Cancel button
        cancel_button = Button(text="Cancel", size_hint_x=0.5)
        cancel_button.bind(on_press=lambda x: player_name_popup.dismiss())
        button_layout.add_widget(cancel_button)

        input_layout.add_widget(button_layout)

        player_name_popup.open()

    def select_existing_player(self, selected_name, player_name_input):
        # Update the TextInput with the selected player name
        player_name_input.text = selected_name

        # Close the dropdown after selecting a player
        self.dropdown.dismiss()

    def handle_player_name_submission(self, player_name, popup):
        if player_name.strip() == "":
            self.show_popup("Error", "Please enter a player name.")
        else:
            # Fetch player stats and proceed to show the flag dropdown
            self.fetch_player_stats(player_name)
            popup.dismiss()  # Close the popup

    def resolve_flag_path(self,flag_filename):
        try:
            # First try resource_find (best for PyInstaller compatibility)
            path = resource_find(flag_filename)
            if path and os.path.exists(path):
                return path
            else:
                print(f"[WARN] resource_find failed or file doesn't exist: {flag_filename}")
        except Exception as e:
            print(f"[ERROR] Error during resource_find: {e}")

        # Fallback to manual path
        fallback = os.path.abspath(flag_filename)
        if os.path.exists(fallback):
            return fallback
        else:
            print(f"[ERROR] Fallback flag not found: {fallback}")
            return None

    def get_flag_for_player(self, player_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT country_flag FROM overall_player_skill_rating WHERE player_name = %s
        ''', (player_name,))

        result = cursor.fetchone()
        return result[0] if result else None

    def ask_for_admin_password_for_flag_change(self, callback):
        # Function to fetch the stored admin password from DB
        def fetch_stored_password():
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT password FROM admin_credentials WHERE id = 1")
                result = cursor.fetchone()
                return result[0] if result else None
            except Exception as e:
                self.show_popup("Database Error", f"Failed to fetch admin password: {e}")
                return None

        stored_password = fetch_stored_password()
        if stored_password is None:
            return  # Stop execution if password couldn't be fetched

        # Main layout for the popup content
        password_content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10
        )

        # Label with instruction
        instruction_label = Label(
            text='Admin password required to change the flag:',
            size_hint_y=None,
            height=30
        )
        password_content.add_widget(instruction_label)

        # Password input field
        password_input = TextInput(
            multiline=False,
            password=True,
            hint_text="Enter Admin Password",
            size_hint_y=None,
            height=36,
            font_size=14
        )
        password_content.add_widget(password_input)

        # Buttons container
        button_layout = BoxLayout(
            size_hint_y=None,
            height=40,
            spacing=10
        )

        confirm_button = Button(text='Confirm')
        cancel_button = Button(text='Cancel')
        button_layout.add_widget(confirm_button)
        button_layout.add_widget(cancel_button)

        password_content.add_widget(button_layout)

        # Create the popup
        password_popup = Popup(
            title='Authorization Required',
            content=password_content,
            size_hint=(0.35, 0.25),
            auto_dismiss=False
        )

        # Confirmation logic
        def on_confirm(instance):
            if password_input.text == stored_password:
                password_popup.dismiss()
                callback()
            else:
                self.show_popup("Authentication Failed", "Incorrect admin password.")
                password_popup.dismiss()

        # Cancel logic
        def on_cancel(instance):
            password_popup.dismiss()

        # Bind buttons
        confirm_button.bind(on_press=on_confirm)
        cancel_button.bind(on_press=on_cancel)

        # Open the popup
        password_popup.open()

    def fetch_player_stats(self, player_name):
        try:
            if self.conn is None:
                raise Exception("Database connection is not established.")


            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT 
                    total_matches,
                    kills AS total_kills,
                    flags_captured AS total_flags,
                    final_skill_rating AS average_skill,
                    country_flag,
                    last_updated_player_level,
                    overall_win_ratio,
                    red_team_win_rate,
                    blue_team_win_rate,
                    KPG,
                    FPG,
                    XPG
                FROM overall_player_skill_rating
                WHERE player_name = %s
            ''', (player_name,))
            result = cursor.fetchone()

            if result:
                (matches, total_kills, total_flags, average_skill, country_flag,
                 last_updated_player_level, overall_win_ratio, red_team_win_rate,
                 blue_team_win_rate, kpg, fpg, xpg) = result

                # Handle NULLs (just to be safe)
                matches = matches or 0
                total_kills = total_kills or 0
                total_flags = total_flags or 0
                average_skill = average_skill or 0.0
                country_flag = country_flag or 'default.png'
                last_updated_player_level = last_updated_player_level or 0
                overall_win_ratio = overall_win_ratio or 0.0
                red_team_win_rate = red_team_win_rate or 0.0
                blue_team_win_rate = blue_team_win_rate or 0.0
                kpg = kpg or 0
                fpg = fpg or 0
                xpg = xpg or 0



                # Resolve flag path
                if country_flag:
                    country_flag_path = resource_find(f'flags/{country_flag}')
                    if not country_flag_path:
                        country_flag_path = resource_find('flags/default.png')
                else:
                    country_flag_path = resource_find('flags/default.png')

                if not country_flag_path:
                    fallback_path = resource_path('flags/default.png')
                    if os.path.exists(fallback_path):
                        country_flag_path = fallback_path
                    else:
                        country_flag_path = None

                # Instance variable for access in dropdown updates
                self.flag_image = Image(
                    source=country_flag_path if country_flag_path else '',
                    size_hint=(None, None),
                    size=(20, 20)
                )

                input_layout = GridLayout(cols=2, padding=10, spacing=12)
                stats_message = [
                    ("Player Name:", player_name),
                    ("Matches:", matches),
                    ("Total Kills:", total_kills),
                    ("Total Flags:", total_flags),
                    ("Skill Rating:", f"{average_skill:.2f}"),
                    ("Win Ratio:", f"{overall_win_ratio:.2f}"),
                    ("Flags per Game:", f"{fpg:.2f}"),
                    ("Kills per Game:", f"{kpg:.2f}"),
                    ("Xp per Game:", f"{xpg:.2f}"),
                    ("Win Ratio for RED:", f"{red_team_win_rate:.2f}"),
                    ("Win Ratio for BLUE:", f"{blue_team_win_rate:.2f}"),
                ]

                for stat_name, stat_value in stats_message:
                    input_layout.add_widget(Label(text=stat_name, size_hint_y=None, height=40))
                    input_layout.add_widget(Label(text=str(stat_value), size_hint_y=None, height=40))

                # Add flag display
                # Get flag from DB
                flag_filename = self.get_flag_for_player(player_name) or "default.png"

                # Resolve actual file path
                resolved_path = resource_find(f'flags/{flag_filename}')
                if not resolved_path:
                    resolved_path = resource_path(f'flags/{flag_filename}')

                # Create the image widget with the resolved flag
                self.flag_image = Image(source=resolved_path or "flags/default.png", size_hint_y=None, height=100)

                # Add label and image to layout
                input_layout.add_widget(Label(text="Country Flag:", size_hint_y=None, height=40))
                input_layout.add_widget(self.flag_image)

                # Flag selection dropdown
                flag_dropdown = DropDown()
                flags_dir = resource_path('flags')
                self.flag_image_paths = []

                if os.path.isdir(flags_dir):
                    for flag in os.listdir(flags_dir):
                        if flag.endswith('.png'):
                            full_path = os.path.join(flags_dir, flag)
                            self.flag_image_paths.append(full_path)

                current_flag_button = Button(
                    text=country_flag if country_flag else "Select Country Flag",
                    size_hint_y=None, height=40
                )

                def update_player_flag(selected_flag_path):
                    def on_password_success():
                        new_flag_filename = os.path.basename(selected_flag_path)
                        current_flag_button.text = new_flag_filename
                        self.update_flag_in_database(player_name, new_flag_filename)

                        resolved_path = resource_find(f'flags/{new_flag_filename}')
                        if not resolved_path:
                            resolved_path = resource_path(f'flags/{new_flag_filename}')

                        if resolved_path and os.path.exists(resolved_path):
                            self.flag_image.source = resolved_path
                            self.flag_image.reload()
                        else:
                            self.show_popup("Flag Error", "Could not load the updated flag image.")

                    # Secure with admin password
                    self.ask_for_admin_password_for_flag_change(on_password_success)

                # Create dropdown options with secured callback
                flag_dropdown = DropDown()

                if os.path.isdir(flags_dir):
                    for flag in os.listdir(flags_dir):
                        if flag.endswith('.png'):
                            full_path = os.path.join(flags_dir, flag)

                            # Create a layout for each flag (for spacing)
                            flag_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=60, padding=(5, 5))

                            # Create the image (resized smaller)
                            flag_image = HoverButton(
                                size_hint=(None, None),
                                size=(50, 30),
                                background_normal=full_path,
                                background_down=full_path,
                                background_color=(1, 1, 1, 1)
                            )

                            # Add hover behavior if you want (optional glow)
                            flag_image.bind(on_release=lambda btn, path=full_path: [
                                self.ask_for_admin_password_for_flag_change(lambda: update_player_flag(path)),
                                flag_dropdown.dismiss()
                            ])

                            flag_layout.add_widget(flag_image)

                            flag_dropdown.add_widget(flag_layout)

                current_flag_button.bind(on_release=flag_dropdown.open)
                input_layout.add_widget(Label(text="Select Flag:", size_hint_y=None, height=40))
                input_layout.add_widget(current_flag_button)

                # OK and Cancel Buttons
                button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
                ok_button = Button(text="OK", size_hint_x=0.5)
                ok_button.bind(on_press=lambda x: self.close_popup())
                button_layout.add_widget(ok_button)

                cancel_button = Button(text="Cancel", size_hint_x=0.5)
                cancel_button.bind(on_press=lambda x: self.close_popup())
                button_layout.add_widget(cancel_button)

                # Compose popup
                main_layout = BoxLayout(orientation='vertical')
                main_layout.add_widget(input_layout)
                main_layout.add_widget(button_layout)

                self.stats_popup = Popup(title="Player Stats", content=main_layout, size_hint=(1, 0.9))
                self.stats_popup.open()
            else:
                self.show_popup("Player Not Rated", "The player is not rated yet.")

        except mysql.connector.Error as err:
            self.show_popup("Database Error", str(err))
        except FileNotFoundError as err:
            self.show_popup("File Error", str(err))
        except Exception as err:
            self.show_popup("Unexpected Error", str(err))

    def close_popup(self):
        self.stats_popup.dismiss()

    def show_flag_selection_dropdown(self, player_name, current_flag):
        input_layout = BoxLayout(orientation='vertical', padding=10)
        flag_dropdown = DropDown()

        flags = os.listdir('flags')
        self.flag_image_paths = ['flags/' + flag for flag in flags]

        current_flag_button = Button(text=current_flag.split('/')[-1] if current_flag else "Select Country Flag",
                                     size_hint_y=None, height=40)

    def update_player_record(self, player_data):
        # This method updates player record conditionally
        for i, player in enumerate(self.players):
            if player['name'] == player_data['name']:
                self.players[i] = player_data  # Update the existing player's data
                return
        # If player does not exist, append it
        self.players.append(player_data)



    def extract_all_text_inputs(widgets):
        """Extract all TextInput widgets from a mixed list (TextInput or BoxLayout)."""
        inputs = []
        for widget in widgets:
            if isinstance(widget, TextInput):
                inputs.append(widget)
            elif isinstance(widget, BoxLayout):
                for child in widget.children:
                    if isinstance(child, TextInput):
                        inputs.append(child)
        return inputs

    def on_input_change(self):
        self.export_button.disabled = True  # Disable the Export button



    def open_player_dropdown(self, name_input):
        dropdown = DropDown()

        # Fetch existing player names for dropdown
        cursor = self.conn.cursor()
        cursor.execute('SELECT player_name FROM overall_player_skill_rating')
        existing_players = cursor.fetchall()

        for player in existing_players:
            player_name = player[0]
            player_button = Button(text=player_name, size_hint_y=None, height=44)
            player_button.bind(on_release=lambda btn: self.select_player_name(btn.text, name_input, dropdown))
            dropdown.add_widget(player_button)

        dropdown.open(name_input)

    def select_player_name(self, player_name, name_input, dropdown):
        name_input.text = player_name  # Populate the input field with the selected player's name
        dropdown.dismiss()  # Close the dropdown after selection

    def set_flag(self, flag_name, button, player_number):
        button.text = flag_name  # Update the button text to the selected flag
        # You can store the flag path too if necessary

    def create_input_field(self, label_text, default_value='', size_hint_x=0.3):
        box = BoxLayout(orientation='horizontal', size_hint_y=None, height=30,
                        padding=(0, 0, 435, 0))
        label = Label(text=label_text, size_hint_x=0.4, color=(1, 1, 1, 1))

        input_field = TextInput(multiline=False, size_hint_x=size_hint_x, text=default_value)
        input_field.halign = 'center'  # Center the text horizontally
        input_field.padding_x = (10, 10)  # Padding to position text in the middle

        # Bind the focus event to trigger the animation
        input_field.bind(focus=self.animate_input_field)

        box.add_widget(label)
        box.add_widget(input_field)

        return box, input_field

    def create_input_screen(self):
        layout = BoxLayout(orientation='vertical', padding=[40, 20, 5, 5], spacing=3)

        self.game_number_input_box, self.game_number_input = self.create_input_field('Game Number', size_hint_x=0.4)
        self.red_team_size_input_box, self.red_team_size_input = self.create_input_field('Red Team Size',
                                                                                         size_hint_x=0.4)
        self.blue_team_size_input_box, self.blue_team_size_input = self.create_input_field('Blue Team Size',
                                                                                           size_hint_x=0.4)

        layout.add_widget(self.game_number_input_box)
        layout.add_widget(self.red_team_size_input_box)
        layout.add_widget(self.blue_team_size_input_box)

        spacer = Label(size_hint_y=None, height=15)
        layout.add_widget(spacer)

        self.generate_inputs_button = Button(text='Generate Player Inputs', size_hint_y=None, height=40, opacity=0.8)
        self.generate_inputs_button.bind(on_press=self.generate_player_input_fields)
        style_button(self.generate_inputs_button)
        layout.add_widget(self.generate_inputs_button)

        self.player_inputs_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.player_inputs_layout.bind(minimum_height=self.player_inputs_layout.setter('height'))

        scroll_view = ScrollView(size_hint=(1, None), size=(600, 400))
        scroll_view.add_widget(self.player_inputs_layout)
        layout.add_widget(scroll_view)

        return layout

    def generate_player_input_fields(self, instance):
        self.player_inputs_layout.clear_widgets()
        self.players.clear()

        try:
            game_number = self.game_number_input.text.strip()
            if not game_number:
                self.show_popup("Error", "Please enter a game number.")
                return

            red_team_size_text = self.red_team_size_input.text.strip()
            blue_team_size_text = self.blue_team_size_input.text.strip()

            print(f"Red Team Size: '{red_team_size_text}', Blue Team Size: '{blue_team_size_text}'")

            # Attempt to convert inputs to integers
            try:
                red_team_size = int(red_team_size_text)
                blue_team_size = int(blue_team_size_text)
            except ValueError:
                self.show_popup("Error", "Please enter valid integer values for team sizes.")
                return

            total_players = red_team_size + blue_team_size
            if total_players < 1 or total_players > 12:
                self.show_popup("Error", "The total number of players must be between 1 and 12.")
                return

            if red_team_size < 0 or red_team_size > 12:
                self.show_popup("Error", "Red team size must be between 0 and 12.")
                return

            if blue_team_size < 0 or blue_team_size > 12:
                self.show_popup("Error", "Blue team size must be between 0 and 12.")
                return

            unique_names_mapping = set()  # To ensure player names are unique

            # Generate Red Team Inputs
            for i in range(1, red_team_size + 1):
                player_name = f"Red Player {i}"
                if player_name not in unique_names_mapping:
                    unique_names_mapping.add(player_name)
                    self.add_player_inputs("Red", player_name)

            # Generate Blue Team Inputs
            for i in range(1, blue_team_size + 1):
                player_name = f"Blue Player {i}"
                if player_name not in unique_names_mapping:
                    unique_names_mapping.add(player_name)
                    self.add_player_inputs("Blue", player_name)

            self.hide_video_elements()
            self.submit_button.disabled = False
            self.export_button.disabled = True

            moving_gif = MovingGIF(
                gif_source=resource_path('positions/tank3.gif'),
                start_x=Window.width,
                start_y=615,
                end_x=-100,
                duration=15
            )
            self.main_layout.add_widget(moving_gif)

            self.create_stats_layout()

        except Exception as e:
            self.show_popup("Error", str(e))



    def on_input_changed(self, instance, value):
        self.export_button.disabled = True

    def animate_input_field(self, instance, value):
        if value:  # Field focused
            # Reset the background color for the previously focused input
            if self.previous_input and self.previous_input != instance:
                reset_color_animation = Animation(background_color=(1, 1, 1, 1), duration=0.3)
                reset_color_animation.start(self.previous_input)

            # Set the current input field as focused
            self.previous_input = instance

            # Wobble animation
            wobble_animation = (
                    Animation(x=instance.x - 5, duration=0.1) +
                    Animation(x=instance.x + 5, duration=0.1) +
                    Animation(x=instance.x, duration=0.1)
            )
            wobble_animation.start(instance)

            # Blue highlight animation during focus
            color_animation = Animation(background_color=(0.8, 0.9, 1, 1), duration=0.3)  # Subtle blue
            color_animation.start(instance)

        else:  # Field unfocused
            # Reset the background color to white
            reset_color_animation = Animation(background_color=(1, 1, 1, 1), duration=0.3)
            reset_color_animation.start(instance)

            # If the unfocused input was the previously focused input, clear the reference
            if self.previous_input == instance:
                self.previous_input = None

    def go_to_home(self, instance):
        # Clear the input layout of any player input fields
        if hasattr(self, 'player_inputs_layout'):
            self.player_inputs_layout.clear_widgets()
        if hasattr(self, 'players'):
            self.players.clear()

        # Remove the input layout if it exists
        if hasattr(self, 'input_layout') and self.input_layout in self.main_layout.children:
            self.main_layout.remove_widget(self.input_layout)

        # Ensure only one instance of the video player layout is added
        if hasattr(self, 'video_player_layout'):
            if self.video_player_layout not in self.main_layout.children:
                self.main_layout.add_widget(self.video_player_layout)

        if self.video_player not in self.video_player_layout.children:
            self.video_player_layout.add_widget(self.video_player)

        # Remove and re-add the refresh button to avoid duplication
        if hasattr(self, 'refresh_button'):
            if self.refresh_button in self.main_layout.children:
                self.main_layout.remove_widget(self.refresh_button)
            self.main_layout.add_widget(self.refresh_button)

        # Disable submit and export buttons if they exist
        if hasattr(self, 'submit_button'):
            self.submit_button.disabled = True
        if hasattr(self, 'export_button'):
            self.export_button.disabled = True

        print("Returned to home view")

    def create_stats_layout(self):
        """Create and initialize the stats layout."""
        # Initialize stats_layout with appropriate configuration
        self.stats_layout = TransparentGridLayout(cols=6, size_hint_y=None, spacing=5)
        self.stats_layout.bind(minimum_height=self.stats_layout.setter('height'))

        # Add headers to the stats layout
        headers = ['Player Name', 'Kills', 'Flags Captured', 'Level', 'Time Played', 'Skill Rating']
        for header in headers:
            header_label = Label(text=header, bold=True, size_hint_y=None, height=40)
            self.stats_layout.add_widget(header_label)

        # Add the stats layout to the player inputs layout
        self.player_inputs_layout.add_widget(self.stats_layout)

    def display_player_stats(self, player_stats):
        """Display each player's statistics in the stats layout."""

        # Clear previous results
        self.stats_layout.clear_widgets()

        # Add headers
        headers = ['Player Name', 'Kills', 'Flags Captured', 'Level', 'XP', 'Skill Rating']
        for header in headers:
            self.stats_layout.add_widget(Label(
                text=header,
                size_hint_y=None,
                height=40,
                bold=True,
                halign='center'
            ))

        # Populate the stats layout with player results
        for name, stats in player_stats.items():
            self.stats_layout.add_widget(Label(text=name, size_hint_y=None, height=30))  # Player Name
            self.stats_layout.add_widget(Label(text=str(stats['kills']), size_hint_y=None, height=30))  # Kills
            self.stats_layout.add_widget(
                Label(text=str(stats['flags_captured']), size_hint_y=None, height=30))  # Flags Captured
            self.stats_layout.add_widget(Label(text=str(stats['level']), size_hint_y=None, height=30))  # Level
            self.stats_layout.add_widget(Label(text=str(stats['xp']), size_hint_y=None, height=30))  # XP
            self.stats_layout.add_widget(
                Label(text=f"{stats['skill_rating']:.2f}", size_hint_y=None, height=30))  # Skill Rating

    def display_match_results(self, team_stats):
        red_team_flags = team_stats['Red']['flags']
        red_team_kills = team_stats['Red']['kills']

        blue_team_flags = team_stats['Blue']['flags']
        blue_team_kills = team_stats['Blue']['kills']

        if red_team_flags > blue_team_flags:
            result_message = "Red Team Wins!"
        elif blue_team_flags > red_team_flags:
            result_message = "Blue Team Wins!"
        else:
            # Flags are equal
            if red_team_kills > blue_team_kills:
                result_message = "Red Team Wins on Kills!"
            elif blue_team_kills > red_team_kills:
                result_message = "Blue Team Wins on Kills!"
            else:
                result_message = "It's a Draw !"

        # Display the result in a popup
        self.show_popup("Match Result", result_message)

    def add_player_inputs(self, team_name, player_identifier):
        def has_player_switched(dynamic_inputs):
            for field in dynamic_inputs:
                if isinstance(field, TextInput) and field.text and field.text.isdigit() and int(field.text) > 0:
                    return True
            return False

        player_box = BoxLayout(orientation='vertical', size_hint_y=None)
        player_box.bind(minimum_height=player_box.setter('height'))

        player_name_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)

        player_label = Label(text=f"{team_name} Team Player {player_identifier}", bold=True, size_hint_x=0.4)
        player_name_box.add_widget(player_label)

        name_input = TextInput(hint_text="Player Name", size_hint_x=0.6)
        player_name_box.add_widget(name_input)

        dropdown_button = Button(
            size_hint_x=0.2,
            size_hint=(None, None),
            border=(0, 0, 0, 0),
            size=(35, 35),
            background_normal=resource_path('positions/dropdown.png'),
            font_size=18,
        )
        dropdown_button.bind(on_release=lambda btn: self.open_player_dropdown(name_input))
        player_name_box.add_widget(dropdown_button)

        player_box.add_widget(player_name_box)

        standard_inputs = ["Kills", "Flags Captured", "Level", "Time Played (min.)", "XP Earned"]
        field_inputs = []

        for input_hint in standard_inputs:
            if input_hint == "Time Played (min.)":
                standard_time_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)

                standard_minute_input = TextInput(hint_text="Minutes", input_filter='int', size_hint_x=0.5)
                standard_minute_input.text = "8"
                standard_minute_input.bind(text=self.on_input_changed)

                standard_second_input = TextInput(hint_text="Seconds", input_filter='int', size_hint_x=0.5)
                standard_second_input.text = "00"
                standard_second_input.bind(text=self.on_input_changed)

                standard_time_layout.add_widget(standard_minute_input)
                standard_time_layout.add_widget(standard_second_input)

                player_box.add_widget(standard_time_layout)
                field_inputs.extend([standard_minute_input, standard_second_input])
            else:
                input_field = TextInput(hint_text=input_hint, size_hint_y=None, height=40)
                input_field.bind(text=self.on_input_changed)
                field_inputs.append(input_field)
                player_box.add_widget(input_field)

        player_box.add_widget(Label(size_hint_y=None, height=10))

        dynamic_rows = []

        def calculate_total_time(minute_input, second_input):
            minutes = int(minute_input.text) if minute_input.text.isdigit() else 0
            seconds = int(second_input.text) if second_input.text.isdigit() else 0
            return minutes + seconds / 60

        def update_player_switch_status():
            for player in self.players:
                if player.get('name_getter') and player['name_getter']() == name_input.text.strip():
                    total_time = calculate_total_time(standard_minute_input, standard_second_input)
                    player['inputs'] = field_inputs + dynamic_rows
                    player['has_switched'] = has_player_switched(dynamic_rows)
                    if player['has_switched']:
                        # Switch team if player has switched
                        if player['original_team'] == "Red":
                            player['team'] = "Blue"
                        else:
                            player['team'] = "Red"
                    else:
                        player['team'] = player['original_team']
                    player['total_time_played'] = total_time

        add_rows_button = Button(
            text=f"insert {player_identifier} stats before he switched if he switched!",
            background_color=(0, 1, 0, 1),
            size_hint_y=None,
            height=40
        )

        def on_add_rows_button_press(instance):
            nonlocal dynamic_rows

            if not dynamic_rows:
                new_kills_input = TextInput(hint_text="Kills", input_filter='int', size_hint_y=None, height=40)
                new_kills_input.bind(text=self.on_input_changed)
                new_kills_input.bind(text=lambda *_: update_player_switch_status())

                new_flags_input = TextInput(hint_text="Flags Captured", input_filter='int', size_hint_y=None, height=40)
                new_flags_input.bind(text=self.on_input_changed)
                new_flags_input.bind(text=lambda *_: update_player_switch_status())

                time_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)

                minute_input = TextInput(hint_text="Minutes", input_filter='int', size_hint_x=0.5)
                minute_input.bind(text=self.on_input_changed)
                minute_input.bind(text=lambda *_: update_player_switch_status())

                second_input = TextInput(hint_text="Seconds", input_filter='int', size_hint_x=0.5)
                second_input.bind(text=self.on_input_changed)
                second_input.bind(text=lambda *_: update_player_switch_status())

                time_layout.add_widget(minute_input)
                time_layout.add_widget(second_input)

                player_box.add_widget(new_kills_input)
                player_box.add_widget(new_flags_input)
                player_box.add_widget(time_layout)
                player_box.add_widget(Label(size_hint_y=None, height=10))

                dynamic_rows = [new_kills_input, new_flags_input, time_layout]
                add_rows_button.text = 'Please close this if the player did not switch'
            else:
                for widget in dynamic_rows:
                    player_box.remove_widget(widget)
                dynamic_rows.clear()
                add_rows_button.text = f"insert {player_identifier} stats before switched if he switched!"

            update_player_switch_status()

        add_rows_button.bind(on_press=on_add_rows_button_press)
        player_box.add_widget(add_rows_button)

        self.players.append({
            'original_team': team_name,
            'team': team_name,
            'name_getter': lambda: name_input.text.strip(),
            'inputs': field_inputs + dynamic_rows,
            'has_switched': False
        })

        self.player_inputs_layout.add_widget(player_box)

    def calculate_skill_rating_logic(self, player, outcome, teammates_avg_rating, opponents_avg_rating,
                                     teammates_avg_level, opponents_avg_level, switched=False):
        # Clamp level at 239 for rating effect
        max_level = 239
        try:
            level = int(player.level)
        except (TypeError, ValueError, AttributeError):
            level = 0
        level = min(level, max_level)

        # Weights for performance metrics
        kills_weight = 0.3
        flags_weight = 0.5
        xp_weight = 0.2

        # Normalize time played (assume 8 minutes = 480 seconds)
        if player.time_played and player.time_played > 0:
            time_factor = 480 / (60 * player.time_played)
        else:
            time_factor = 0
            performance_score = -5  # Heavy penalty for no playtime
        if time_factor > 0:
            performance_score = (
                    (flags_weight * player.flags_captured +
                     kills_weight * player.kills +
                     (xp_weight * player.xp) / 10000) * time_factor
            )

        # Outcome adjustments with switched player considerations
        if outcome == 'win':
            outcome_bonus = 0.5 if not switched else 0.7  # Switched player rewarded more on win
        elif outcome == 'lose':
            outcome_bonus = -0.25 if not switched else -0.1  # Switched player penalized less on loss
        elif outcome == 'draw':
            outcome_bonus = 0
        else:
            outcome_bonus = 0

        skill_rating = float(player.skill_rating or 0)
        skill_rating += performance_score + outcome_bonus

        # Weighted average benchmark for fairness
        try:
            teammates_avg = float(teammates_avg_rating)
            opponents_avg = float(opponents_avg_rating)
        except (TypeError, ValueError):
            teammates_avg = 0.0
            opponents_avg = 0.0

        player_weight = 0.5
        teammates_weight = 0.3
        opponents_weight = 0.2

        weighted_avg_rating = (
                skill_rating * player_weight +
                teammates_avg * teammates_weight +
                opponents_avg * opponents_weight
        )

        # Bonus or penalty based on comparison to weighted average
        if skill_rating > weighted_avg_rating:
            skill_rating += 0.5
        elif skill_rating < weighted_avg_rating:
            skill_rating -= 0.5

        # Level influence (small negative weight to balance)
        normalized_level = level / max_level
        level_weight = -0.8
        skill_rating += normalized_level * level_weight

        # Level gap influence between teams (capped)
        try:
            level_gap = teammates_avg_level - opponents_avg_level
        except (TypeError, ValueError):
            level_gap = 0
        clamped_gap = max(min(level_gap, 50), -50)
        level_gap_modifier = -(clamped_gap / 10) * 0.1  # Negative gap is a bonus
        skill_rating += level_gap_modifier

        # Soft cap: diminishing returns above 200 rating
        if skill_rating > 200:
            skill_rating = 200 + (skill_rating - 200) * 0.5

        print(skill_rating , "line 3280")

        return round(skill_rating / 100, 2)
        print(skill_rating, "line 3283")

    def calculate_skill_rating(self, instance):
        player_stats = {}
        all_players = set()
        team_stats = {'Red': {'kills': 0, 'flags': 0}, 'Blue': {'kills': 0, 'flags': 0}}
        team_levels = {'Red': [], 'Blue': []}
        empty_fields = []

        # Validate inputs and duplicates
        for player in self.players:
            name = player['name_getter']()
            if not name:
                empty_fields.append("Name")
            static_inputs = player['inputs'][:6]
            for i, input_field in enumerate(static_inputs):
                if not input_field.text.strip():
                    empty_fields.append(f"{player['team']} Player '{name}' field {i + 1} is empty")
            if name in all_players:
                self.show_popup("Assignment Error", f"Duplicate player name '{name}' detected.")
                return
            all_players.add(name)

        if empty_fields:
            self.show_popup("Warning", "\n".join(empty_fields))
            return

        # Parse each player
        for player in self.players:
            name = player['name_getter']()
            final_team = player['team']

            # Parse standard inputs (final segment)
            try:
                kills_final = int(player['inputs'][0].text or 0)
                flags_final = int(player['inputs'][1].text or 0)
                level = int(player['inputs'][2].text or 0)
                minutes_final = int(player['inputs'][3].text or 0)
                seconds_final = int(player['inputs'][4].text or 0)
                time_final = minutes_final + seconds_final / 60.0
                xp_total = int(player['inputs'][5].text or 0)
            except ValueError:
                self.show_popup("Input Error", f"Invalid input for player '{name}'. Please enter valid numbers.")
                return

            # Parse dynamic rows (original segment)
            dynamic_inputs = player['inputs'][6:]
            kills_dynamic = 0
            flags_dynamic = 0
            time_dynamic = 0.0
            has_switch = False

            for i in range(0, len(dynamic_inputs), 3):
                try:
                    kills_dyn = int(dynamic_inputs[i].text or 0)
                    flags_dyn = int(dynamic_inputs[i + 1].text or 0)
                    time_layout = dynamic_inputs[i + 2]
                    minutes_dyn = 0
                    seconds_dyn = 0
                    for child in time_layout.children:
                        if hasattr(child, 'hint_text'):
                            if 'Minutes' in child.hint_text:
                                minutes_dyn = int(child.text) if child.text.isdigit() else 0
                            elif 'Seconds' in child.hint_text:
                                seconds_dyn = int(child.text) if child.text.isdigit() else 0
                    time_dyn = minutes_dyn + seconds_dyn / 60.0
                    if time_dyn > 0 and (kills_dyn > 0 or flags_dyn > 0):
                        kills_dynamic += kills_dyn
                        flags_dynamic += flags_dyn
                        time_dynamic += time_dyn
                        has_switch = True
                except Exception:
                    continue

            # Assign dynamic stats to opposing team if switched
            if has_switch:
                dynamic_team = 'Red' if final_team == 'Blue' else 'Blue'
            else:
                dynamic_team = final_team

            # XP split proportional to time played
            total_time = time_dynamic + time_final
            if total_time > 0:
                xp_dynamic = int(xp_total * (time_dynamic / total_time))
                xp_final = xp_total - xp_dynamic
            else:
                xp_dynamic = 0
                xp_final = xp_total

            # Aggregate team stats for win calculation
            team_stats[dynamic_team]['kills'] += kills_dynamic
            team_stats[dynamic_team]['flags'] += flags_dynamic
            team_levels[dynamic_team].append(level)

            team_stats[final_team]['kills'] += kills_final
            team_stats[final_team]['flags'] += flags_final
            team_levels[final_team].append(level)

            # Store player stats for rating and display
            total_kills = kills_dynamic + kills_final
            total_flags = flags_dynamic + flags_final
            skill_rating = self.fetch_player_rating(name)

            player_stats[name] = {
                'dynamic_team': dynamic_team,
                'final_team': final_team,
                'kills_dynamic': kills_dynamic,
                'flags_dynamic': flags_dynamic,
                'time_dynamic': time_dynamic,
                'kills_final': kills_final,
                'flags_final': flags_final,
                'time_final': time_final,
                'kills': total_kills,
                'flags_captured': total_flags,
                'level': level,
                'time_played': total_time,
                'xp': xp_total,
                'skill_rating': skill_rating,
                'has_switched': has_switch,
                'xp_dynamic': xp_dynamic,
                'xp_final': xp_final,
            }

        # Determine winning team
        red_flags = team_stats['Red']['flags']
        blue_flags = team_stats['Blue']['flags']
        red_kills = team_stats['Red']['kills']
        blue_kills = team_stats['Blue']['kills']

        if red_flags > blue_flags:
            winning_team = "Red"
        elif blue_flags > red_flags:
            winning_team = "Blue"
        else:
            if red_kills > blue_kills:
                winning_team = "Red"
            elif blue_kills > red_kills:
                winning_team = "Blue"
            else:
                winning_team = "Draw"

        # Prepare ratings lists
        red_ratings = [self.fetch_player_rating(p['name_getter']()) for p in self.players if p['team'] == 'Red']
        blue_ratings = [self.fetch_player_rating(p['name_getter']()) for p in self.players if p['team'] == 'Blue']

        # Calculate skill rating for each player segment
        for name, stats in player_stats.items():
            ratings = []

            # Dynamic segment (original team)
            if stats['time_dynamic'] > 0:
                outcome_dynamic = 'draw' if winning_team == 'Draw' else (
                    'win' if stats['dynamic_team'] == winning_team else 'lose')
                teammates_dynamic = red_ratings if stats['dynamic_team'] == 'Red' else blue_ratings
                opponents_dynamic = blue_ratings if stats['dynamic_team'] == 'Red' else red_ratings

                avg_teammate_rating_dynamic = sum(teammates_dynamic) / len(
                    teammates_dynamic) if teammates_dynamic else 0
                avg_opponent_rating_dynamic = sum(opponents_dynamic) / len(
                    opponents_dynamic) if opponents_dynamic else 0
                avg_teammate_level_dynamic = sum(team_levels[stats['dynamic_team']]) / len(
                    team_levels[stats['dynamic_team']]) if team_levels[stats['dynamic_team']] else 0
                avg_opponent_level_dynamic = sum(
                    team_levels['Blue' if stats['dynamic_team'] == 'Red' else 'Red']) / len(
                    team_levels['Blue' if stats['dynamic_team'] == 'Red' else 'Red']) if team_levels[
                    'Blue' if stats['dynamic_team'] == 'Red' else 'Red'] else 0

                player_instance_dynamic = Player(
                    name + " (Dynamic Team)",
                    stats['level'],
                    stats['kills_dynamic'],
                    stats['flags_dynamic'],
                    stats['time_dynamic'],
                    stats['xp_dynamic'],
                    stats['skill_rating']
                )

                rating_dynamic = self.calculate_skill_rating_logic(
                    player_instance_dynamic,
                    outcome_dynamic,
                    avg_teammate_rating_dynamic,
                    avg_opponent_rating_dynamic,
                    avg_teammate_level_dynamic,
                    avg_opponent_level_dynamic,
                    switched=True
                )
                ratings.append((rating_dynamic, stats['time_dynamic']))

            # Final segment (final team)
            if stats['time_final'] > 0:
                outcome_final = 'draw' if winning_team == 'Draw' else (
                    'win' if stats['final_team'] == winning_team else 'lose')
                teammates_final = red_ratings if stats['final_team'] == 'Red' else blue_ratings
                opponents_final = blue_ratings if stats['final_team'] == 'Red' else red_ratings

                avg_teammate_rating_final = sum(teammates_final) / len(teammates_final) if teammates_final else 0
                avg_opponent_rating_final = sum(opponents_final) / len(opponents_final) if opponents_final else 0
                avg_teammate_level_final = sum(team_levels[stats['final_team']]) / len(
                    team_levels[stats['final_team']]) if team_levels[stats['final_team']] else 0
                avg_opponent_level_final = sum(team_levels['Blue' if stats['final_team'] == 'Red' else 'Red']) / len(
                    team_levels['Blue' if stats['final_team'] == 'Red' else 'Red']) if team_levels[
                    'Blue' if stats['final_team'] == 'Red' else 'Red'] else 0

                player_instance_final = Player(
                    name + " (Final Team)",
                    stats['level'],
                    stats['kills_final'],
                    stats['flags_final'],
                    stats['time_final'],
                    stats['xp_final'],
                    stats['skill_rating']
                )

                rating_final = self.calculate_skill_rating_logic(
                    player_instance_final,
                    outcome_final,
                    avg_teammate_rating_final,
                    avg_opponent_rating_final,
                    avg_teammate_level_final,
                    avg_opponent_level_final,
                    switched=False
                )
                ratings.append((rating_final, stats['time_final']))

            # Weighted average of both segments by time played
            if ratings:
                total_time = sum(t for _, t in ratings)
                weighted_rating = sum(r * t for r, t in ratings) / total_time if total_time > 0 else stats[
                    'skill_rating']
            else:
                weighted_rating = stats['skill_rating']


            print(stats['skill_rating'] , "line 3516")

            tier = get_tier(int(weighted_rating))
            stats['skill_rating'] = weighted_rating
            stats['tier'] = tier
            stats['outcome'] = 'win' if winning_team != 'Draw' and stats[
                'final_team'] == winning_team else 'lose' if winning_team != 'Draw' else 'draw'

        # Display results
        self.display_player_stats(player_stats)
        self.display_match_results(team_stats)

        self.submit_button.disabled = False

        self.export_button.disabled = False

        self.player_stats = player_stats

    def player_exists_in_database(self, player_name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM overall_player_skill_rating WHERE player_name = %s", (player_name,))
        return cursor.fetchone()[0] > 0


    def confirm_create_players(self, player_names):
        content = BoxLayout(orientation='vertical')
        warning_text = "The following players do not exist:\n" + "\n".join(
            player_names) + "\nWould you like to create them?"
        content.add_widget(Label(text=warning_text))

        yes_button = Button(text="Yes", size_hint=(0.3, 0.3))
        yes_button.bind(on_release=lambda x: [self.create_new_players(player_names), popup.dismiss()])

        no_button = Button(text="No", size_hint=(0.3, 0.3))
        no_button.bind(on_release=lambda x: popup.dismiss())

        popup_layout = BoxLayout(orientation='horizontal')
        popup_layout.add_widget(yes_button)
        popup_layout.add_widget(no_button)

        content.add_widget(popup_layout)

        popup = Popup(title="Player Creation Confirmation", content=content, size_hint=(0.6, 0.6))
        popup.open()

    def create_new_players(self, player_names):
        for name in player_names:
            self.insert_new_player_into_database(name)  # Assuming this function handles insertion

        # After creating all players, show a single success popup
        self.show_popup("Success", f"The following players were created successfully:\n" + "\n".join(player_names))
        self.submit_button.enabled = True  # Enable the submit button or any other actions necessary

    def insert_new_player_into_database(self, player_name):
        cursor = self.conn.cursor()
        match_inserted = False

        try:
            # Check if the player already exists in this match
            cursor.execute('SELECT COUNT(*) FROM overall_player_skill_rating WHERE player_name = %s', (player_name,))
            exists = cursor.fetchone()[0]

            # Ensure the result is fully consumed
            cursor.fetchall()  # Explicitly fetch all results to avoid potential issues with unconsumed results

            if exists > 0:
                self.show_popup("Error", f"Player '{player_name}' already exists.")
                return

            # Get match number from input
            try:
                match_number = int(self.game_number_input.text.strip())
            except ValueError:
                self.show_popup("Input Error", "Please enter a valid number for Game Number.")
                return

            # Insert or update the match
          #  cursor.execute('''
           #     INSERT INTO matches (match_number, match_date)
           #     VALUES (%s, CURDATE())
           #     ON DUPLICATE KEY UPDATE match_date = CURDATE()
         #   ''', (match_number,))
          #  match_inserted = True

            # Insert player with default values
            cursor.execute('''
                INSERT INTO overall_player_skill_rating (
                    player_name,
                    country_flag
                )
                VALUES (%s, %s)
            ''', (
                player_name,  # player_name
                "default.png",  # xp
            ))

            # Commit the transaction
            self.conn.commit()

        except Exception as e:
            # Rollback in case of an error
            self.conn.rollback()
            self.show_popup("Error", f"Failed to insert player '{player_name}': {str(e)}")

        finally:
            cursor.close()  # Always close the cursor to avoid lingering queries

    def fetch_player_rating(self, player_name):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT final_skill_rating FROM overall_player_skill_rating WHERE player_name = %s',
                (player_name,)
            )
            result = cursor.fetchone()
            cursor.close()

            if result is None or result[0] is None:
                return 0

            print("line 1874" , result[0])
            return float(result[0])


        except mysql.connector.Error as err:
            print(f"Error fetching player rating: {err}")
            return 0

    def show_temp_message(self, message):
        message_label = Label(
            text=message, size_hint=(None, None), size=(400, 50),
            color=(1, 1, 1, 1), bold=True, halign='center'
        )
        message_label.bind(size=message_label.setter('text_size'))
        message_label.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        self.main_layout.add_widget(message_label)

        fade_in = Animation(opacity=1, duration=0.5)
        fade_out = Animation(opacity=0, duration=0.5)

        fade_in.start(message_label)
        fade_out.start(message_label)

        fade_out.bind(on_complete=lambda *args: self.main_layout.remove_widget(message_label))

    def export_data(self, instance):

        self.submit_button.disabled = False

        self.ask_for_admin_password(self.perform_export)

    def perform_export(self, *args):
        new_players_to_create = []

        print("Players List:", self.players)

        global cursor
        self.match_inserted = False  # Track if we inserted match (moved to self.match_inserted for later use)

        try:
            cursor = self.conn.cursor()

            # SAFELY read match number
            match_number_text = self.game_number_input.text.strip()
            if not match_number_text.isdigit():
                self.show_popup("Input Error", "Please enter a valid match number.")
                return
            self.match_number = int(match_number_text)

            # Check if any players are missing
            for player in self.players:
                player_name =player['name_getter']()
                if not self.player_exists_in_database(player_name):
                    new_players_to_create.append(player_name)

            # If there are new players, show confirmation popup
            if new_players_to_create:
                player_list = "\n".join(new_players_to_create)
                message = f"The following players are new and will be created:\n\n{player_list}\n\nProceed?"

                self.show_confirmation_popup(
                    title="Confirm New Players",
                    message=message,
                    on_confirm=lambda: self.create_players_and_continue_export(new_players_to_create),
                    on_cancel=self.cancel_export
                )
                return  # wait for confirmation, stop here until user responds

            # No new players, continue exporting
            self._continue_export()

        except Exception as e:
            self.conn.rollback()
            self.show_popup("Error", f"Export failed: {str(e)}")
            self.submit_button.disabled = False

    def create_players_and_continue_export(self, new_players):
        try:
            cursor = self.conn.cursor()
            for player_name in new_players:
                cursor.execute('''
                    INSERT INTO overall_player_skill_rating (player_name) 
                    VALUES (%s)
                    ON DUPLICATE KEY UPDATE player_name = player_name
                ''', (player_name,))
            self.conn.commit()
            print("New players created successfully.")

            # After creating players, continue exporting
            self._continue_export()

        except Exception as e:
            self.conn.rollback()
            self.show_popup("Error", f"Failed to create new players: {str(e)}")
            self.submit_button.disabled = False

    def cancel_export(self, *args):
        self.show_popup("Cancelled", "Export cancelled.")
        self.submit_button.disabled = False

    def _continue_export(self):
        global cursor
        try:
            cursor = self.conn.cursor()

            # Check if match number already exists
            print(f"[DEBUG] Checking if match {self.match_number} exists...")
            cursor.execute('SELECT COUNT(*) FROM matches WHERE match_number = %s', (self.match_number,))
            (match_exists,) = cursor.fetchone()

            if match_exists:
                self.show_popup("Error",
                                f"Match number {self.match_number} already exists! Please choose a different match number.")
                self.submit_button.disabled = False
                return

            # Insert new match
            print(f"[DEBUG] Inserting match {self.match_number} into 'matches' table...")
            cursor.execute('''
                INSERT INTO matches (match_number, match_date) 
                VALUES (%s, CURDATE())
            ''', (self.match_number,))
            self.match_inserted = True
            print(f"[DEBUG] Match {self.match_number} inserted.")

            # Get player names
            player_names = [player['name_getter']() for player in self.players]
            print(f"[DEBUG] Player names collected: {player_names}")

            if not player_names:
                self.show_popup("Error", "No players to process!")
                return

            # Fetch existing stats
            print(f"[DEBUG] Fetching existing player stats from 'overall_player_skill_rating'...")
            format_strings = ','.join(['%s'] * len(player_names))
            cursor.execute(f'''
                SELECT player_name, total_matches, overall_win_ratio, red_team_win_rate, blue_team_win_rate
                FROM overall_player_skill_rating
                WHERE player_name IN ({format_strings})
            ''', tuple(player_names))

            existing_stats = {
                row[0]: {
                    'total_matches': row[1] or 0,
                    'overall_win_ratio': row[2] or 0.0,
                    'red_team_win_rate': row[3] or 0.0,
                    'blue_team_win_rate': row[4] or 0.0
                }
                for row in cursor.fetchall()
            }

            print(f"[DEBUG] Existing stats fetched: {existing_stats}")

            for name, stats in self.player_stats.items():
                print(f"\n[DEBUG] Processing player: {name}")
                kills = stats['kills']
                flags = stats['flags_captured']
                level = stats['level']
                time_played = stats['time_played']
                xp = stats['xp']
                skill_rating = stats['skill_rating']
                final_team = stats['final_team']
                outcome = stats['outcome']

                print(f"[DEBUG] Inserting/updating player: {name}, "
                      f"Kills: {kills}, Flags: {flags}, XP: {xp}, Level: {level}, "
                      f"Skill Rating: {skill_rating:.2f}, Final Team: {final_team}, Outcome: {outcome}")

                cursor.execute('''
                    INSERT INTO player_skill_rating 
                    (player_name, kills, flags_captured, xp, skill_rating, match_number, player_level, final_team, outcome)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        kills = VALUES(kills),
                        flags_captured = VALUES(flags_captured),
                        xp = VALUES(xp),
                        skill_rating = VALUES(skill_rating),
                        player_level = VALUES(player_level),
                        final_team = VALUES(final_team),
                        outcome = VALUES(outcome)
                ''', (name, kills, flags, xp, skill_rating, self.match_number, level, final_team, outcome))
                print("[DEBUG] Inserted into player_skill_rating")

                prev_stats = existing_stats.get(name, {
                    'total_matches': 0,
                    'overall_win_ratio': 0.0,
                    'red_team_win_rate': 0.0,
                    'blue_team_win_rate': 0.0
                })

                old_total_matches = prev_stats['total_matches']
                old_total_wins = (prev_stats['overall_win_ratio'] * old_total_matches) / 100.0
                old_red_wins = (prev_stats['red_team_win_rate'] * old_total_matches) / 100.0
                old_blue_wins = (prev_stats['blue_team_win_rate'] * old_total_matches) / 100.0

                new_total_matches = old_total_matches + 1
                new_total_wins = old_total_wins + (1 if outcome == 'win' else 0)
                new_red_wins = old_red_wins + (1 if final_team == 'Red' and outcome == 'win' else 0)
                new_blue_wins = old_blue_wins + (1 if final_team == 'Blue' and outcome == 'win' else 0)

                new_overall_win_ratio = (new_total_wins / new_total_matches) * 100
                new_red_team_win_rate = (new_red_wins / new_total_matches) * 100
                new_blue_team_win_rate = (new_blue_wins / new_total_matches) * 100

                print(f"[DEBUG] Updated win ratios for {name}: "
                      f"Total Matches: {new_total_matches}, "
                      f"Overall Win Ratio: {new_overall_win_ratio:.2f}%, "
                      f"Red Win Rate: {new_red_team_win_rate:.2f}%, "
                      f"Blue Win Rate: {new_blue_team_win_rate:.2f}%")

                cursor.execute('''
                    INSERT INTO overall_player_skill_rating 
                    (player_name, kills, flags_captured, xp, final_skill_rating, total_matches, red_team_win_rate, blue_team_win_rate, overall_win_ratio, last_updated_player_level)
                    VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        kills = kills + VALUES(kills),
                        flags_captured = flags_captured + VALUES(flags_captured),
                        xp = xp + VALUES(xp),
                        total_matches = total_matches + 1,
                        red_team_win_rate = VALUES(red_team_win_rate),
                        blue_team_win_rate = VALUES(blue_team_win_rate),
                        overall_win_ratio = VALUES(overall_win_ratio),
                        final_skill_rating = final_skill_rating + VALUES(final_skill_rating),
                        last_updated_player_level = VALUES(last_updated_player_level)
                ''', (
                    name, kills, flags, xp, skill_rating,
                    new_red_team_win_rate, new_blue_team_win_rate, new_overall_win_ratio, level
                ))
                print("[DEBUG] Updated overall_player_skill_rating")

            self.conn.commit()
            print("[DEBUG] Export committed successfully.")
            self.show_popup("Success", "Data exported successfully!")

        except Exception as e:
            print(f"[ERROR] Exception occurred: {e}")
            self.conn.rollback()
            if self.match_inserted:
                try:
                    print("[DEBUG] Rolling back inserted match...")
                    cursor.execute('DELETE FROM matches WHERE match_number = %s', (self.match_number,))
                    self.conn.commit()
                except Exception as cleanup_err:
                    print(f"[ERROR] Cleanup failed: {cleanup_err}")

            self.show_popup("Error", f"Export failed: {str(e)}")

        finally:
            self.submit_button.disabled = False

    def show_confirmation_popup(self, title, message, on_confirm, on_cancel):
        popup = ConfirmationPopup(
            title=title,
            message=message,
            on_confirm=on_confirm,
            on_cancel=on_cancel
        )
        popup.open()

    def export_leaderboard_to_pdf(self, instance=None):
        def on_export(choice):
            popup.dismiss()

            try:
                cursor = self.conn.cursor()

                if choice == 'statistical':
                    query = '''
                        SELECT player_name, total_matches, XPG, KPG, FPG, final_skill_rating,
                               overall_win_ratio, last_updated_player_level
                        FROM overall_player_skill_rating
                        ORDER BY XPG DESC
                    '''
                    headers = ['Player', 'Matches', 'XP/Game', 'Kills/Game', 'Flags/Game',
                               'Skill Rating', 'Win Ratio (%)', 'Last Level']
                else:  # performance
                    query = '''
                        SELECT player_name, total_matches, kills, flags_captured,
                               final_skill_rating, overall_win_ratio, last_updated_player_level
                        FROM overall_player_skill_rating
                        ORDER BY final_skill_rating DESC
                    '''
                    headers = ['Player', 'Matches', 'Kills', 'Flags',
                               'Skill Rating', 'Win Ratio (%)', 'Last Level']

                cursor.execute(query)
                results = cursor.fetchall()

                if not results:
                    self.show_popup("Export Failed", "No leaderboard data available to export.")
                    return

                # Ask user for file save location
                root = Tk()
                root.withdraw()
                file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
                root.destroy()

                if not file_path:
                    return  # User cancelled

                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=10)

                # Title
                pdf.set_font("Arial", 'B', 14)
                title = f"{choice.capitalize()} Leaderboard"
                pdf.cell(200, 10, title, ln=True, align="C")

                pdf.ln(5)
                pdf.set_font("Arial", 'B', 10)

                col_width = 25
                row_height = 8

                # Header row
                for header in headers:
                    pdf.cell(col_width, row_height, header, border=1)
                pdf.ln(row_height)

                pdf.set_font("Arial", size=9)

                # Data rows
                for row in results:
                    for item in row:
                        text = f"{item:.2f}" if isinstance(item, float) else str(item)
                        pdf.cell(col_width, row_height, text, border=1)
                    pdf.ln(row_height)

                pdf.output(file_path)

                self.show_popup("Export Successful", f"{choice.capitalize()} leaderboard exported to:\n{file_path}")

            except mysql.connector.Error as err:
                self.show_popup("Database Error", str(err))

        # Create popup for leaderboard type selection
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text="Choose which leaderboard to export:"))

        btn_statistical = Button(text="Statistical Leaderboard")
        btn_performance = Button(text="Performance Leaderboard")
        content.add_widget(btn_statistical)
        content.add_widget(btn_performance)

        popup = Popup(title="Export Leaderboard", content=content, size_hint=(None, None), size=(600, 400))

        btn_statistical.bind(on_press=lambda x: on_export('statistical'))
        btn_performance.bind(on_press=lambda x: on_export('performance'))

        popup.open()

    def get_flag_path(self, country_flag):
        if not country_flag:
            country_flag = 'default.png'

        # Try Kivy resource_find first
        path = resource_find(f'flags/{country_flag}')
        if path and os.path.exists(path):
            return path

        # If running as PyInstaller bundle, use _MEIPASS
        if hasattr(sys, '_MEIPASS'):
            exe_path = os.path.join(sys._MEIPASS, 'flags', country_flag)
            if os.path.exists(exe_path):
                return exe_path
            # fallback to default
            default_path = os.path.join(sys._MEIPASS, 'flags', 'default.png')
            if os.path.exists(default_path):
                return default_path

        # Fallback for dev mode
        fallback_path = os.path.join('flags', country_flag)
        if os.path.exists(fallback_path):
            return fallback_path

        default_fallback = os.path.join('flags', 'default.png')
        if os.path.exists(default_fallback):
            return default_fallback

        return ''  # Nothing found

    def show_leaderboard(self, instance):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT
                    player_name,
                    total_matches,
                    kills,
                    flags_captured,
                    final_skill_rating,
                    overall_win_ratio,
                    last_updated_player_level,
                    country_flag
                FROM overall_player_skill_rating
                ORDER BY final_skill_rating DESC
            ''')
            results = cursor.fetchall()

            leaderboard_content = BoxLayout(orientation='vertical', padding=10, spacing=10)

            scroll_view = ScrollView(size_hint=(1, None), size=(700, 400))

            leaderboard_grid = GridLayout(cols=9, padding=10, spacing=10, size_hint_y=None)
            leaderboard_grid.bind(minimum_height=leaderboard_grid.setter('height'))

            headers = [
                'Rank', 'Player Name', 'Matches', 'Total Kills',
                'Total Flags', 'Skill Rating', 'Win Ratio', 'Last updated level', 'Country Flag'
            ]
            for header in headers:
                leaderboard_grid.add_widget(Label(
                    text=header,
                    size_hint_y=None,
                    height=40,
                    bold=True
                ))

            for idx, row in enumerate(results):
                leaderboard_grid.add_widget(Label(text=str(idx + 1), size_hint_y=None, height=40))

                player_name = row[0]
                truncated_name = (player_name[:15] + '...') if len(player_name) > 15 else player_name
                leaderboard_grid.add_widget(Label(text=truncated_name, size_hint_y=None, height=40))

                leaderboard_grid.add_widget(Label(text=str(row[1]), size_hint_y=None, height=40))
                leaderboard_grid.add_widget(Label(text=str(row[2]), size_hint_y=None, height=40))
                leaderboard_grid.add_widget(Label(text=str(row[3]), size_hint_y=None, height=40))

                # Skill Rating with yellow background
                skill_box = BoxLayout(size_hint=(1, None), height=40, padding=5)

                with skill_box.canvas.before:
                    Color(1, 1, 0, 0.3)
                    rect = Rectangle(size=skill_box.size, pos=skill_box.pos)

                def update_rect(instance, value, rect=rect):
                    rect.size = instance.size
                    rect.pos = instance.pos

                skill_box.bind(size=update_rect, pos=update_rect)

                skill_label = Label(
                    text=f"{row[4]:.2f}",
                    bold=True,
                    font_size=16,
                    color=(0, 0, 0, 1)
                )
                skill_box.add_widget(skill_label)
                leaderboard_grid.add_widget(skill_box)

                leaderboard_grid.add_widget(Label(text=f"{row[5]:.2f}%", size_hint_y=None, height=40))
                leaderboard_grid.add_widget(Label(text=str(row[6]), size_hint_y=None, height=40))

                # Country Flag with fallback
                country_flag = row[7]
                country_flag_path = self.get_flag_path(country_flag)

                flag_container = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)

                spacer = Widget(size_hint_x=None, width=32)
                flag_image = Image(source=country_flag_path, size_hint=(None, None), size=(30, 30))

                flag_container.add_widget(spacer)
                flag_container.add_widget(flag_image)

                leaderboard_grid.add_widget(flag_container)

            scroll_view.add_widget(leaderboard_grid)
            leaderboard_content.add_widget(scroll_view)

            close_button = Button(text='Close', size_hint=(None, None), size=(100, 40), pos_hint={'center_x': 0.5})
            leaderboard_content.add_widget(close_button)

            leaderboard_popup = Popup(title='Leaderboard', content=leaderboard_content, size_hint=(1, 0.75))
            close_button.bind(on_press=leaderboard_popup.dismiss)
            leaderboard_popup.open()

        except mysql.connector.Error as err:
            print(f"Error occurred: {err}")
            self.show_popup("Database Error", str(err))

    def show_statistical_leaderboard(self, instance=None, sort_field='XPG'):
        # Close existing leaderboard if open
        if hasattr(self, 'leaderboard_popup') and self.leaderboard_popup:
            self.leaderboard_popup.dismiss()

        try:
            cursor = self.conn.cursor()
            query = f'''
                SELECT
                    player_name, total_matches, xp, KPG, FPG, final_skill_rating,
                    overall_win_ratio, last_updated_player_level, country_flag, XPG
                FROM overall_player_skill_rating
                ORDER BY {sort_field} DESC
            '''
            cursor.execute(query)
            results = cursor.fetchall()

            leaderboard_content = BoxLayout(orientation='vertical', padding=10, spacing=10)

            # Dropdown to select sort field
            sort_spinner = Spinner(
                text='Sort by XP/Game',
                values=('XPG', 'KPG', 'FPG', 'final_skill_rating', 'overall_win_ratio'),
                size_hint=(None, None),
                size=(200, 40)
            )

            def on_sort_change(spinner, text):
                self.show_statistical_leaderboard(sort_field=text)

            sort_spinner.bind(text=on_sort_change)
            leaderboard_content.add_widget(sort_spinner)

            scroll_view = ScrollView(size_hint=(1, None), size=(700, 400))
            leaderboard_grid = GridLayout(cols=10, padding=10, spacing=10, size_hint_y=None)
            leaderboard_grid.bind(minimum_height=leaderboard_grid.setter('height'))

            headers = [
                'Rank', 'Player Name', 'Matches', 'XP/Game', 'Kills/Game',
                'Flags/Game', 'Skill Rating', 'Win Ratio', 'Last Level', 'Flag'
            ]
            for header in headers:
                leaderboard_grid.add_widget(Label(text=header, size_hint_y=None, height=40, bold=True))

            for idx, row in enumerate(results):
                player_name, matches, xp, kpg, fpg, rating, win_ratio, level, flag, xpg = row

                leaderboard_grid.add_widget(Label(text=str(idx + 1), size_hint_y=None, height=40))

                truncated_name = (player_name[:15] + '...') if len(player_name) > 15 else player_name
                leaderboard_grid.add_widget(Label(text=truncated_name, size_hint_y=None, height=40))

                leaderboard_grid.add_widget(Label(text=str(matches), size_hint_y=None, height=40))
                leaderboard_grid.add_widget(Label(text=str(xpg), size_hint_y=None, height=40))
                leaderboard_grid.add_widget(Label(text=str(kpg), size_hint_y=None, height=40))
                leaderboard_grid.add_widget(Label(text=str(fpg), size_hint_y=None, height=40))
                leaderboard_grid.add_widget(Label(text=f"{rating:.2f}", size_hint_y=None, height=40))
                leaderboard_grid.add_widget(Label(text=f"{win_ratio:.2f}%", size_hint_y=None, height=40))
                leaderboard_grid.add_widget(Label(text=str(level), size_hint_y=None, height=40))

                # Country flag
                flag_path = self.get_flag_path(flag)

                flag_container = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
                spacer = Widget(size_hint_x=None, width=32)
                flag_image = Image(source=flag_path, size_hint=(None, None), size=(30, 30))
                flag_container.add_widget(spacer)
                flag_container.add_widget(flag_image)
                leaderboard_grid.add_widget(flag_container)

            scroll_view.add_widget(leaderboard_grid)
            leaderboard_content.add_widget(scroll_view)

            close_button = Button(text='Close', size_hint=(None, None), size=(100, 40), pos_hint={'center_x': 0.5})
            leaderboard_content.add_widget(close_button)

            self.leaderboard_popup = Popup(
                title='Statistical Leaderboard',
                content=leaderboard_content,
                size_hint=(1, 0.85)
            )
            close_button.bind(on_press=self.leaderboard_popup.dismiss)
            self.leaderboard_popup.open()

        except mysql.connector.Error as err:
            print(f"Error occurred: {err}")
            self.show_popup("Database Error", str(err))

    def _update_leaderboard_rect(self, instance, value):
        # Update the rectangle size and position for the background of the leaderboard
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def update_flag_in_database(self, player_name, flag_path):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO overall_player_skill_rating (player_name, country_flag)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE country_flag = %s
        ''', (player_name, flag_path, flag_path))  # Update if already exists
        self.conn.commit()
        self.show_popup("Success", f"Flag {flag_path.split('/')[-1]} assigned to {player_name}.")

    def show_popup(self, title, message, show_cancel_button=False):
        content = BoxLayout(orientation='vertical', padding=20)
        content.add_widget(Label(text=message))

        # Create button layout for OK and Cancel
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)

        # OK button
        ok_button = Button(text='OK', size_hint_x=0.5)  # Half width
        ok_button.bind(on_press=lambda x: self.popup.dismiss())  # Dismiss the popup on OK press
        button_layout.add_widget(ok_button)

        # Cancel button (optional)
        if show_cancel_button:
            cancel_button = Button(text='Cancel', size_hint_x=0.5)  # Half width
            cancel_button.bind(on_press=lambda x: self.popup.dismiss())  # Dismiss the popup on Cancel press
            button_layout.add_widget(cancel_button)

        content.add_widget(button_layout)

        # Create the popup window
        self.popup = Popup(title=title, content=content, size_hint=(0.6, 0.4))
        self.popup.open()

    def ask_for_admin_password(self, callback):
        def fetch_stored_password():
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT password FROM admin_credentials WHERE id = 1")
                result = cursor.fetchone()
                return result[0] if result else None
            except Exception as e:
                self.show_popup("DB Error", f"Failed to fetch admin password: {e}")
                return None

        stored_password = fetch_stored_password()
        if stored_password is None:
            return  # Abort if password couldn't be fetched

        password_content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        password_input = TextInput(multiline=False, password=True, hint_text="Enter Admin Password", size_hint_y=None,
                                   height=36)
        password_content.add_widget(Label(text="Admin password required:", size_hint_y=None, height=30))
        password_content.add_widget(password_input)

        btn_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        confirm_btn = Button(text="Confirm")
        cancel_btn = Button(text="Cancel")
        btn_layout.add_widget(confirm_btn)
        btn_layout.add_widget(cancel_btn)
        password_content.add_widget(btn_layout)

        popup = Popup(title='Admin Access', content=password_content, size_hint=(0.5, 0.3), auto_dismiss=False)

        def on_confirm(instance):
            if password_input.text == stored_password:
                popup.dismiss()
                callback()
            else:
                self.show_popup("Access Denied", "Incorrect admin password.")
                popup.dismiss()

        confirm_btn.bind(on_press=on_confirm)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        popup.open()



if __name__ == '__main__':
    # Set the window size
    Window.size = (750, 740)

    # You may want to hide the maximize button on some systems by setting the window to a specified size and avoiding fullscreen
    Window.fullscreen = False  # Ensure the app runs in windowed mode

    # Define a function to restrict window resizing (by keeping it at a fixed size)
    def on_resize(window, width, height):
        # Reset window size if it attempts to resize
        window.size = (1000, 765)

    # Bind the on_resize function to the window
    Window.bind(on_resize=on_resize)

    # Run your Kivy application
    SkillRatingApp().run()


