import os
import mysql.connector  # MySQL Driver
from dotenv import load_dotenv
from kivy.uix.dropdown import DropDown
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivymd.app import MDApp
from kivy.animation import Animation  # Import Animation
from kivy.uix.image import Image
from kivy.graphics import Ellipse
from kivy.clock import Clock
import random
import decimal
import pygame
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.pdfencrypt import padding
from reportlab.pdfgen import canvas

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

from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle

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
    def __init__(self, canvas, width):
        self.canvas = canvas
        self.size = random.uniform(5, 10)
        self.x = random.uniform(0, width)
        self.y = random.uniform(0, Window.height)
        self.speed = random.uniform(1, 3)
        with self.canvas:
            self.ellipse = Ellipse(pos=(self.x, self.y), size=(self.size, self.size))
        Clock.schedule_interval(self.update, 1 / 60)

    def update(self, dt):
        self.y -= self.speed
        if self.y < 0:
            splash = Splash(self.canvas, (self.x, 0))
            self.y = Window.height
            self.x = random.uniform(0, Window.width)
        self.ellipse.pos = (self.x, self.y)

class Player:
    def __init__(self, name, level, kills, flags_captured, time_played, xp,skill_rating=0):
        self.skill_rating = skill_rating
        self.name = name
        self.level = level
        self.kills = kills
        self.flags_captured = flags_captured
        self.time_played = time_played
        self.xp = xp


class SkillRatingApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conn = None
        self.create_db()
        self.players = []
        self.music_playing = True

        try:
            pygame.mixer.init()
            pygame.mixer.music.load('positions/background_music.mp3')
            pygame.mixer.music.set_volume(0.5)
        except Exception as e:
            print(f"Error initializing Pygame mixer: {e}")
        # To play the music on application run


    def create_db(self):
        try:
            self.conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USERNAME,
                password=DB_PASSWORD,
                database=DB_NAME,
                port=os.getenv("DB_PORT"),
                ssl_disabled=False
            )
            self.conn.autocommit = True

            cursor = self.conn.cursor()

            # Create player_skill_rating table if it doesn't exist
            cursor.execute(''' 
              CREATE TABLE IF NOT EXISTS player_skill_rating (
     id INT AUTO_INCREMENT PRIMARY KEY,
    team_name VARCHAR(50) NULL,  -- Allow team_name to be NULL
    player_name VARCHAR(255) NOT NULL,
    kills INT NOT NULL,
    flags_captured INT NOT NULL,
    player_level INT NOT NULL,
    skill_rating FLOAT NOT NULL,
    total_skill_rating FLOAT NOT NULL DEFAULT 5,
    matches_played INT NOT NULL DEFAULT 0,
    UNIQUE (player_name)
);
            ''')

            # Create player_country_flags table with a foreign key
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_country_flags (
                    player_name VARCHAR(255) PRIMARY KEY,
                    country_flag VARCHAR(255) DEFAULT NULL,
                    FOREIGN KEY (player_name) REFERENCES player_skill_rating(player_name)
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

            self.conn.commit()
            print("Database connection established and tables created.")
        except mysql.connector.Error as err:
            print("Error connecting to the database:", err)
            self.conn = None

    def create_snowflakes(self):
        self.snowflakes = []
        for _ in range(30):
            snowflake = Snowflake(self.main_layout.canvas, Window.width)
            self.snowflakes.append(snowflake)

    def build(self):


        # Create the main layout using FloatLayout
        self.main_layout = FloatLayout()

        self.title_gif = Image(

            source='positions/title.gif',
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

        # Create snowflakes
        self.create_snowflakes()
        # Add background image at the bottom of the screen
        self.background_image = Image(
            source='positions/tank.png',
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
        self.top_players_label.font_name = os.path.join("fonts", "DancingScript.ttf")
        self.top_players_layout.add_widget(self.top_players_label)

        # Add glowing animation to top players label
        self.animate_glow()



        # Spacer below the label
        spacer = Label(size_hint_y=None, height=10)
        self.top_players_layout.add_widget(spacer)

        # Add container for top players
        self.top_players_container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.top_players_container.bind(minimum_height=self.top_players_container.setter('height'))
        self.fetch_top_players()  # Fetch data
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
        self.create_players_button = Button(text='Create Players', size_hint_x=None, width=150)
        self.create_players_button.bind(on_press=self.open_create_player_popup)
        self.style_button(self.create_players_button)
        self.button_layout.add_widget(self.create_players_button)

        self.submit_button = Button(text='Submit', size_hint_x=None, width=150, disabled=True)
        self.submit_button.bind(on_press=self.calculate_skill_rating)
        self.style_button(self.submit_button)
        self.button_layout.add_widget(self.submit_button)

        self.export_button = Button(text='Export Data', size_hint_x=None, width=150, disabled=True)
        self.export_button.bind(on_press=self.export_data)
        self.style_button(self.export_button)
        self.button_layout.add_widget(self.export_button)

        self.download_pdf_button = Button(
            text='Download Leaderboard as PDF',
            size_hint_x=None,
            width=260,
            disabled=False
        )
        self.download_pdf_button.bind(on_press=self.export_leaderboard_to_pdf)
        self.style_button(self.download_pdf_button)
        self.button_layout.add_widget(self.download_pdf_button)

        self.performance_leaderboard_button = Button(
            text='Performance\nLeaderboard',
            size_hint_x=None,
            width=150,
            disabled=False
        )
        self.performance_leaderboard_button.bind(on_press=self.show_leaderboard)
        self.style_button(self.performance_leaderboard_button)
        self.button_layout.add_widget(self.performance_leaderboard_button)

        self.statistical_leaderboard_button = Button(
            text='Statistical\nLeaderboard',
            size_hint_x=None,
            width=150,
            disabled=False
        )
        self.statistical_leaderboard_button.bind(on_press=self.show_leaderboard)
        self.style_button(self.statistical_leaderboard_button)
        self.button_layout.add_widget(self.statistical_leaderboard_button)

        self.stats_button = Button(text='My Stats', size_hint_x=None, width=150, disabled=False)
        self.stats_button.bind(on_press=self.request_player_name)
        self.style_button(self.stats_button)
        self.button_layout.add_widget(self.stats_button)

        overlay.add_widget(self.button_layout)

        # Add the overlay to the main layout
        self.main_layout.add_widget(overlay)

        # Create animation layout
        self.animation_layout = FloatLayout(size=Window.size)  # Dedicated layout for animations
        self.main_layout.add_widget(self.animation_layout)

        # Perform initial calculations for totals
        self.calculate_totals()

        return self.main_layout

    def toggle_music(self, instance):
        if self.music_playing:
            pygame.mixer.music.pause()
            self.music_playing = False
        else:
            pygame.mixer.music.unpause()
            self.music_playing = True
        self.update_button_image()  # Update the button image to reflect state

    def update_button_image(self):
        if self.music_playing:
            self.music_control_button.background_normal = 'positions/pause.png'
            self.music_control_button.background_down = 'positions/pause.png'
        else:
            self.music_control_button.background_normal = 'positions/play.png'
            self.music_control_button.background_down = 'positions/play.png'

    def create_refresh_button(self):
        # Create an Image widget to display the GIF
        self.gif_button = Image(source='positions/refresh.gif', size_hint=(None, None), size=(100, 100), opacity=0.88)

        # Bind the touch event to the on_gif_click function
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

    def play_gif(self):
        # Hide or stop showing the GIF after 2.5 seconds
        Clock.schedule_once(self.hide_gif, 2.5)  # Schedule to call hide_gif after 2.5 seconds

    def hide_gif(self, dt):
        self.gif_button.opacity = 0.85  # Make the GIF invisible

    def calculate_totals(self):
        try:
            cursor = self.conn.cursor()

            # Calculate Total Games
            cursor.execute("SELECT COUNT(*) FROM commentary_games_details")
            total_games = cursor.fetchone()[0]

            # Calculate Total Kills
            cursor.execute("SELECT SUM(kills) FROM player_skill_rating")
            total_kills = cursor.fetchone()[0] or 0  # Default to 0 if None

            # Calculate Total Flags
            cursor.execute("SELECT SUM(flags_captured) FROM player_skill_rating")
            total_flags = cursor.fetchone()[0] or 0  # Default to 0 if None

            # Animate the totals
            self.animate_count_up(self.total_games_label, total_games)
            self.animate_count_up(self.total_kills_label, total_kills)
            self.animate_count_up(self.total_flags_label, total_flags)

        except mysql.connector.Error as err:
            print(f"Error occurred while calculating totals: {err}")
            self.show_popup("Error", str(err))

    def open_create_player_popup(self, instance):
        input_layout = BoxLayout(orientation='vertical', padding=10)

        input_label = Label(text="Enter Player Name:", size_hint_y=None, height=40)
        self.player_name_input = TextInput(multiline=False, size_hint_y=None, height=40)

        input_layout.add_widget(input_label)
        input_layout.add_widget(self.player_name_input)

        # Fetch existing player names for dropdown
        cursor = self.conn.cursor()
        cursor.execute('SELECT player_name FROM player_skill_rating')
        existing_players = cursor.fetchall()

        # Add dropdown for existing players
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

        # Button layout for OK and Cancel
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)

        ok_button = Button(text="OK", size_hint_x=0.5)
        ok_button.bind(on_press=lambda x: self.create_player(self.player_name_input.text))
        button_layout.add_widget(ok_button)

        cancel_button = Button(text="Cancel", size_hint_x=0.5)
        cancel_button.bind(on_press=lambda x: self.player_name_popup.dismiss())
        button_layout.add_widget(cancel_button)

        input_layout.add_widget(button_layout)

        self.player_name_popup = Popup(title="Create Player", content=input_layout, size_hint=(0.6, 0.4))
        self.player_name_popup.open()

    def select_existing_player(self, player_name):
        self.player_name_input.text = player_name  # Populate the input field with the existing player's name
        self.dropdown.dismiss()  # Close the dropdown after selection

    def create_player(self, player_name):
        # Ensure the player_name is valid
        if player_name.strip() == "":
            self.show_popup("Error", "Please enter a valid player name.")
            return

        try:
            cursor = self.conn.cursor()
            # Check if player already exists
            cursor.execute('SELECT COUNT(*) FROM player_skill_rating WHERE player_name = %s', (player_name,))
            exists = cursor.fetchone()[0]

            if exists > 0:
                self.show_popup("Error", f"Player '{player_name}' already exists.")
                return

            # Insert new player with a default team name
            cursor.execute('''
                INSERT INTO player_skill_rating (team_name, player_name, kills, flags_captured, player_level, skill_rating)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', ("No Team", player_name, 0, 0, 0, 0))  # Insert with default values.

            self.conn.commit()  # Commit the transaction
            self.show_popup("Success", f"Player '{player_name}' created successfully.")
            self.player_name_popup.dismiss()  # Close the popup
        except mysql.connector.Error as err:
            self.show_popup("Error", f"Could not create player: {str(err)}")

    def animate_glow(self):
        glow_animation = Animation(opacity=0.5, duration=0.5) + Animation(opacity=1, duration=0.5)
        glow_animation.repeat = True
        glow_animation.start(self.top_players_label)

    def update_rect(self, instance, value):
        self.shadow_rect.pos = self.top_players_label.pos
        self.shadow_rect.size = self.top_players_label.size
        self.bg_rect.pos = self.top_players_label.pos
        self.bg_rect.size = self.top_players_label.size

    def create_header(self):
        header_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=120,
                                  padding=[600, 0, 0, 350]      , spacing=10)

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
        self.stats_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=100, spacing=40, padding=(290,0,0,400))

        # Total Games label
        self.total_games_label = Label(text="Total Games: 0", color=(1, 1, 1, 1), font_size='20sp')
        self.total_games_label.font_name = os.path.join("fonts", "DancingScript.ttf")  # Set custom font
        self.stats_layout.add_widget(self.total_games_label)

        # Total Kills label
        self.total_kills_label = Label(text="Total Kills: 0", color=(1, 1, 1, 1), font_size='20sp')
        self.total_kills_label.font_name = os.path.join("fonts", "DancingScript.ttf")  # Set custom font
        self.stats_layout.add_widget(self.total_kills_label)

        # Total Flags label
        self.total_flags_label = Label(text="Total Flags: 0", color=(1, 1, 1, 1), font_size='20sp')
        self.total_flags_label.font_name = os.path.join("fonts", "DancingScript.ttf")  # Set custom font
        self.stats_layout.add_widget(self.total_flags_label)

        # Add stats layout to header layout
        header_layout.add_widget(self.stats_layout)

        # Add header layout to the main layout
        self.main_layout.add_widget(header_layout)

        # Start the animation for the welcome text
        self.animate_welcome_text()

    def animate_count_up(self, label, final_value, duration=2):
        # Ensure the final_value is an integer
        final_value = int(final_value)  # This will force final_value to be an integer

        # Start at zero and set label text
        label_prefix = label.text.split(": ")[0] + ": "  # Get everything before the first colon
        label.text = f"{label_prefix}0"  # Initialize the label to zero

        # Animation for color change
        color_change = Animation(color=(0, 1, 0, 1), duration=0.5) + Animation(color=(1, 1, 1, 1), duration=0.5)

        def update_label(dt):
            current_value_string = label.text.split(": ")[1]  # Get the number portion
            current_value = int(current_value_string)  # Convert current value to integer

            if current_value < final_value:
                # Ensure increments are integers
                increment = max(1, (final_value - current_value) // 30)  # Calculate integer increment
                new_value = min(current_value + increment, final_value)
                label.text = f"{label_prefix}{new_value}"  # Display the updated integer value

                color_change.start(label)  # Start color change animation
            else:
                Clock.unschedule(update_label)  # Stop updating once we have reached or exceeded the final value

        Clock.schedule_interval(update_label, duration / 30.0)  # Schedule the updates

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

    def create_input_screen(self):
        # Main layout for inputs
        layout = BoxLayout(orientation='vertical', padding=[30,5,15,0], spacing=3)


        # Input fields
        self.game_number_input = self.create_input_field('Game Number', size_hint_x=0.4)
        self.red_team_size_input = self.create_input_field('Red Team Size', size_hint_x=0.4)
        self.blue_team_size_input = self.create_input_field('Blue Team Size', size_hint_x=0.4)

        layout.add_widget(self.game_number_input)
        layout.add_widget(self.red_team_size_input)
        layout.add_widget(self.blue_team_size_input)

        # Spacer between input fields and the generate button
        spacer = Label(size_hint_y=None, height=15)
        layout.add_widget(spacer)

        # Button to generate player inputs
        self.generate_inputs_button = Button(text='Generate Player Inputs', size_hint_y=None, height=40, opacity=0.8)
        self.generate_inputs_button.bind(on_press=self.generate_player_input_fields)
        self.style_button(self.generate_inputs_button)
        layout.add_widget(self.generate_inputs_button)

        # Layout for player data input with scrollbar
        self.player_inputs_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.player_inputs_layout.bind(minimum_height=self.player_inputs_layout.setter('height'))

        scroll_view = ScrollView(size_hint=(1, None), size=(600, 400))
        scroll_view.add_widget(self.player_inputs_layout)
        layout.add_widget(scroll_view)

        return layout

    def fetch_top_players(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(''' 
                SELECT p.player_name, 
                       SUM(p.kills) AS total_kills, 
                       SUM(p.flags_captured) AS total_flags, 
                       AVG(skill_rating) AS total_skill_rating,
                       COALESCE(c.country_flag, 'flags/default_flag.png') AS country_flag  
                FROM player_skill_rating p
                LEFT JOIN player_country_flags c ON p.player_name = c.player_name  
                GROUP BY p.player_name 
                ORDER BY total_kills DESC  -- Order by total kills, or modify as needed
                LIMIT 3 
            ''')
            results = cursor.fetchall()
            self.top_players_container.clear_widgets()

            for idx, row in enumerate(results):
                # Handle medal assignment
                medal_path = ['positions/1st-prize.png', 'positions/2nd-place.png', 'positions/3rd-place.png'][idx]

                player_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
                medal_image = Image(source=medal_path, size_hint=(None, 1), width=30)
                player_layout.add_widget(medal_image)

                stats_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)

                # Truncate player name if too long
                player_name = row[0]
                truncated_name = (player_name[:15] + '...') if len(player_name) > 15 else player_name

                player_name_label = Label(text=truncated_name, size_hint_y=None, height=40, color=(1, 0.84, 1, 1))
                stats_layout.add_widget(player_name_label)

                # Add country flag image next to the player's name
                country_flag_path = row[4]
                country_flag_image = Image(source=country_flag_path, size_hint=(None, None), size=(30, 30))
                stats_layout.add_widget(country_flag_image)

                # Ensure to extract totals as integers
                total_kills = int(row[1])  # Force integer conversion
                total_flags = int(row[2])  # Force integer conversion
                skill_rating = row[3]  # Skill rating can remain a float

                # Prepare labels for stats
                kills_label = Label(text=f"Kills: {total_kills}", size_hint_y=None, height=40, color=(1, 1, 1, 1))
                flags_label = Label(text=f"Flags: {total_flags}", size_hint_y=None, height=40, color=(1, 1, 1, 1))
                skill_label = Label(text=f"Skill: {skill_rating:.2f}", size_hint_y=None, height=40, color=(1, 1, 1, 1))

                # Animate counts
                self.animate_count_up(kills_label, total_kills)  # Animate kills as integer
                self.animate_count_up(flags_label, total_flags)  # Animate flags as integer
                self.animate_count_up(skill_label, skill_rating)  # Skill as float

                # Add the stats layout to the player layout
                stats_layout.add_widget(kills_label)
                stats_layout.add_widget(flags_label)
                stats_layout.add_widget(skill_label)
                player_layout.add_widget(stats_layout)
                self.top_players_container.add_widget(player_layout)

        except mysql.connector.Error as err:
            print(f"Error occurred: {err}")
            self.show_popup("Error", str(err))



    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size







    def request_player_name(self, instance):
        # Create a layout for the input
        input_layout = BoxLayout(orientation='vertical', padding=10)

        input_label = Label(text="Enter your Player Name:", size_hint_y=None, height=40)
        player_name_input = TextInput(multiline=False, size_hint_y=None, height=40)

        input_layout.add_widget(input_label)
        input_layout.add_widget(player_name_input)

        # Button layout for OK and Cancel
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)

        # Create the popup
        player_name_popup = Popup(title="Player Name", content=input_layout, size_hint=(0.6, 0.4))

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

    def handle_player_name_submission(self, player_name, popup):
        if player_name.strip() == "":
            self.show_popup("Error", "Please enter a player name.")
        else:
            # Fetch player stats and proceed to show the flag dropdown
            self.fetch_player_stats(player_name)
            popup.dismiss()  # Close the popup

    def fetch_player_stats(self, player_name):
        try:
            cursor = self.conn.cursor()
            cursor.execute(''' 
                SELECT COUNT(*) AS matches,
                       SUM(kills) AS total_kills,
                       SUM(flags_captured) AS total_flags,
                       AVG(skill_rating) AS average_skill,
                       MAX(pcf.country_flag) AS country_flag
                FROM player_skill_rating ps
                LEFT JOIN player_country_flags pcf ON ps.player_name = pcf.player_name
                WHERE ps.player_name = %s
            ''', (player_name,))
            result = cursor.fetchone()

            if result and result[0] > 0:  # Check if the player has any matches
                matches, total_kills, total_flags, average_skill, country_flag = result

                matches = matches or 0
                total_kills = total_kills or 0
                total_flags = total_flags or 0
                average_skill = average_skill or 0.0
                country_flag = country_flag if country_flag else 'flags/default_flag.png'  # Default flag if none

                # Create a layout for the stats with GridLayout
                input_layout = GridLayout(cols=2, padding=10, spacing=10)

                # Create the stats labels
                stats_message = [
                    ("Player Name:", player_name),
                    ("Matches:", matches),
                    ("Total Kills:", total_kills),
                    ("Total Flags:", total_flags),
                    ("Average Skill Rating:", f"{average_skill:.2f}"),
                ]

                # Add labels to the layout
                for stat_name, stat_value in stats_message:
                    input_layout.add_widget(Label(text=stat_name, size_hint_y=None, height=40))
                    input_layout.add_widget(Label(text=str(stat_value), size_hint_y=None, height=40))

                # Add the country flag image
                flag_image = Image(source=country_flag, size_hint=(None, None), size=(50, 50))
                input_layout.add_widget(Label(text="Country Flag:", size_hint_y=None, height=40))
                input_layout.add_widget(flag_image)

                # Country flag dropdown for selection
                flag_dropdown = DropDown()
                flags = os.listdir('flags')
                self.flag_image_paths = ['flags/' + flag for flag in flags]

                current_flag_button = Button(
                    text=country_flag.split('/')[-1] if country_flag else "Select Country Flag",
                    size_hint_y=None, height=40)

                # Update the database when a new flag is selected
                def update_player_flag(selected_flag):
                    current_flag_button.text = selected_flag.split('/')[-1]
                    self.update_flag_in_database(player_name, selected_flag)  # Update flag in DB
                    flag_image.source = selected_flag  # Update displayed flag image
                    flag_image.reload()  # Reload the image to reflect the change

                for flag_path in self.flag_image_paths:
                    flag_button = Button(text=flag_path.split('/')[-1], size_hint_y=None, height=44)
                    flag_button.bind(
                        on_release=lambda btn, path=flag_path: [update_player_flag(path), flag_dropdown.dismiss()])
                    flag_dropdown.add_widget(flag_button)

                current_flag_button.bind(on_release=flag_dropdown.open)
                input_layout.add_widget(Label(text="Select Flag:", size_hint_y=None, height=40))
                input_layout.add_widget(current_flag_button)

                # OK and Cancel buttons
                button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
                ok_button = Button(text="OK", size_hint_x=0.5)
                ok_button.bind(on_press=lambda x: self.close_popup())
                button_layout.add_widget(ok_button)

                cancel_button = Button(text="Cancel", size_hint_x=0.5)
                cancel_button.bind(on_press=lambda x: self.close_popup())
                button_layout.add_widget(cancel_button)

                # Combine all into the main layout
                main_layout = BoxLayout(orientation='vertical')
                main_layout.add_widget(input_layout)
                main_layout.add_widget(button_layout)

                self.stats_popup = Popup(title="Player Stats", content=main_layout, size_hint=(0.6, 0.6))
                self.stats_popup.open()

            else:
                # Show a message indicating that the player is not rated yet
                self.show_popup("Player Not Rated", "The player is not rated yet.")

        except mysql.connector.Error as err:
            self.show_popup("Error", str(err))

    def close_popup(self):
        self.stats_popup.dismiss()

    def show_flag_selection_dropdown(self, player_name, current_flag):
        input_layout = BoxLayout(orientation='vertical', padding=10)
        flag_dropdown = DropDown()

        flags = os.listdir('flags')
        self.flag_image_paths = ['flags/' + flag for flag in flags]

        current_flag_button = Button(text=current_flag.split('/')[-1] if current_flag else "Select Country Flag",
                                     size_hint_y=None, height=40)


    def style_button(self, button):
        button.background_color = (0.1, 0.5, 0.8, 1)
        button.color = (1, 1, 1, 1)



    def update_player_record(self, player_data):
        # This method updates player record conditionally
        for i, player in enumerate(self.players):
            if player['name'] == player_data['name']:
                self.players[i] = player_data  # Update the existing player's data
                return
        # If player does not exist, append it
        self.players.append(player_data)




    def add_player_inputs(self, team_name, player_identifier):
        # Create a vertical box layout for each player's input fields
        player_box = BoxLayout(orientation='vertical', size_hint_y=None)
        player_box.bind(minimum_height=player_box.setter('height'))  # Bind height for auto-expansion

        # Create a horizontal layout for player identification
        player_name_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)

        # Label and input for player name
        player_label = Label(text=f"{team_name} Team Player {player_identifier}", bold=True, size_hint_x=0.4)
        player_name_box.add_widget(player_label)

        name_input = TextInput(hint_text="Player Name", size_hint_x=0.6)
        player_name_box.add_widget(name_input)

        # Create the dropdown button
        dropdown_button = Button(text='▼', size_hint_x=0.2)
        dropdown_button.bind(on_release=lambda btn: self.open_player_dropdown(name_input))
        player_name_box.add_widget(dropdown_button)

        player_box.add_widget(player_name_box)

        # Standard inputs (non-expandable)
        standard_inputs = ["Kills", "Flags Captured", "Level", "Time Played (min.)", "XP Earned"]
        field_inputs = []  # Local list for this player's static inputs

        for input_hint in standard_inputs:
            input_field = TextInput(hint_text=input_hint, size_hint_y=None, height=40)
            field_inputs.append(input_field)
            player_box.add_widget(input_field)

        # Spacer
        player_box.add_widget(Label(size_hint_y=None, height=10))

        # Add button for dynamic inputs
        dynamic_rows = []
        add_rows_button = Button(text=f"insert {player_identifier} stats before he switched if he switched!", background_color=(0, 1, 0, 1),
                                 size_hint_y=None, height=40)
        player_box.add_widget(add_rows_button)

        # Functionality for toggling dynamic input fields
        def on_add_rows_button_press(instance):
            if not dynamic_rows:  # Add rows if not already added
                new_kills_input = TextInput(hint_text="Kills", input_filter='int', size_hint_y=None, height=40)
                new_flags_input = TextInput(hint_text="Flags Captured", input_filter='int', size_hint_y=None, height=40)

                player_box.add_widget(new_kills_input)
                player_box.add_widget(new_flags_input)

                # Track dynamic input fields
                dynamic_rows.extend([new_kills_input, new_flags_input])

                player_box.add_widget(Label(size_hint_y=None, height=10))  # Spacer
                add_rows_button.text = 'Please close this if the player did not switch'
                is_switched_player = True  # Flag switched status


            else:  # Remove rows if they are currently added
                for widget in dynamic_rows:
                    player_box.remove_widget(widget)
                dynamic_rows.clear()
                add_rows_button.text = f"insert {player_identifier} stats before switched if he switched!"
                is_switched_player = False  # Reset switched status

            # Update the player's inputs in the `self.players` list
            for player in self.players:
                if player['name'] == name_input:
                    player['inputs'] = field_inputs + dynamic_rows
                    player['team']= team_name
                    player['has_switched'] = is_switched_player

        add_rows_button.bind(on_press=on_add_rows_button_press)

        # Record player info
        self.players.append({
            'team': team_name,
            'name': name_input,
            'inputs': field_inputs + dynamic_rows , # Combine static and dynamic
            'has_switched': False
        })

        self.player_inputs_layout.add_widget(player_box)

    def on_input_change(self):
        self.export_button.disabled = True  # Disable the Export button

    def open_player_dropdown(self, name_input):
        dropdown = DropDown()

        # Fetch existing player names for dropdown
        cursor = self.conn.cursor()
        cursor.execute('SELECT player_name FROM player_skill_rating')
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

    def generate_player_input_fields(self, instance):
        self.player_inputs_layout.clear_widgets()
        self.players.clear()

        try:
            game_number = self.game_number_input.children[0].text.strip()
            if not game_number:
                self.show_popup("Error", "Please enter a game number.")
                self.submit_button.disabled = True
                self.export_button.disabled = True
                return

            red_team_size = int(self.red_team_size_input.children[0].text)
            blue_team_size = int(self.blue_team_size_input.children[0].text)

            total_players = red_team_size + blue_team_size
            if total_players < 1 or total_players > 12:
                self.show_popup("Error", "The total number of players must be between 1 and 12.")
                self.submit_button.disabled = True
                self.export_button.disabled = True
                return

            if red_team_size < 0 or red_team_size > 12:
                self.show_popup("Error", "Red team size must be between 0 and 12.")
                self.submit_button.disabled = True
                self.export_button.disabled = True
                return

            if blue_team_size < 0 or blue_team_size > 12:
                self.show_popup("Error", "Blue team size must be between 0 and 12.")
                self.submit_button.disabled = True
                self.export_button.disabled = True
                return

            self.submit_button.disabled = True
            self.export_button.disabled = True

            unique_names_mapping = set()  # To ensure player names are unique

            # Generate Red Team Inputs
            for i in range(1, red_team_size + 1):
                while True:
                    player_name = f"Red Player {i}"  # Name format
                    if player_name not in unique_names_mapping:  # Ensure uniqueness
                        unique_names_mapping.add(player_name)
                        self.add_player_inputs("Red", player_name)
                        break

            # Generate Blue Team Inputs
            for i in range(1, blue_team_size + 1):
                while True:
                    player_name = f"Blue Player {i}"  # Name format
                    if player_name not in unique_names_mapping:  # Ensure uniqueness
                        unique_names_mapping.add(player_name)
                        self.add_player_inputs("Blue", player_name)
                        break

            self.submit_button.disabled = False
            self.export_button.disabled = True

            moving_gif = MovingGIF(gif_source='positions/tank3.gif',
                                   start_x=Window.width,
                                   start_y=615,
                                   end_x=-100,
                                   duration=15)
            self.main_layout.add_widget(moving_gif)

            self.create_stats_layout()

            self.calculate_skill_rating(None)



        except ValueError:
            self.show_popup("Error", "Please enter valid integer values for team sizes.")

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

        return box

    def animate_input_field(self, instance, value):
        if value:  # Field focused
            # Wobble animation
            wobble_animation = Animation(x=instance.x - 5, duration=0.1) + Animation(x=instance.x + 5,
                                                                                     duration=0.1) + Animation(
                x=instance.x, duration=0.1)
            wobble_animation.start(instance)

            # Color change animation
            color_animation = Animation(background_color=(0.2, 0.5, 1, 1), duration=0.3)
            color_animation.start(instance)

            # Optionally, add shadow for pop effect
            with instance.canvas.before:
                Color(0, 0, 0, 0.5)  # Shadow color (black)
                self.shadow_rect = Rectangle(size=(instance.width, instance.height),
                                             pos=(instance.x, instance.y - 5))  # Shadow below the input field

            shadow_animation = Animation(pos=(instance.x, instance.y - 30), duration=0.2)  # Shadow move effect
            shadow_animation.start(self.shadow_rect)

        else:  # Field unfocused
            # Reset color
            reset_color_animation = Animation(background_color=(1, 1, 1, 1), duration=0.3)
            reset_color_animation.start(instance)

            # Remove shadow when unfocused
            if hasattr(self, 'shadow_rect'):
                self.shadow_rect.pos = (instance.x, instance.y)  # Reset the position
                self.shadow_rect.size = (instance.width, instance.height)

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

    def calculate_skill_rating(self, instance):
        player_stats = {}
        all_players = set()
        team_stats = {'Red': {'kills': 0, 'flags': 0}, 'Blue': {'kills': 0, 'flags': 0}}
        team_levels = {'Red': [], 'Blue': []}

        # Gather player data and calculate team stats
        for player in self.players:
            name = player['name'].text.strip()
            if not name:
                self.show_popup("Warning", "Please fill in all fields for each player.")
                return
            if name in all_players:
                self.show_popup("Assignment Error", f"Error: Duplicate player name '{name}' detected.")
                return
            all_players.add(name)

            team_name = player['team']
            try:
                kills = int(player['inputs'][0].text) if player['inputs'][0].text else 0
                flags_captured = int(player['inputs'][1].text) if player['inputs'][1].text else 0
                level = int(player['inputs'][2].text) if player['inputs'][2].text else 0
                time_played = float(player['inputs'][3].text) if player['inputs'][3].text else 0
                xp = int(player['inputs'][4].text) if player['inputs'][4].text else 0
            except ValueError:
                self.show_popup("Input Error", f"Invalid input for player '{name}'. Please enter valid numbers.")
                return

            # Update the current team's stats
            team_stats[team_name]['kills'] += kills
            team_stats[team_name]['flags'] += flags_captured
            team_levels[team_name].append(level)

            # Process dynamic input fields
            dynamic_inputs = player['inputs'][5:]
            for i in range(0, len(dynamic_inputs), 2):
                try:
                    switched_kills = int(dynamic_inputs[i].text) if dynamic_inputs[i].text else 0
                    switched_flags = int(dynamic_inputs[i + 1].text) if (i + 1) < len(dynamic_inputs) and \
                                                                        dynamic_inputs[i + 1].text else 0

                    # Update player's stats
                    kills += switched_kills
                    flags_captured += switched_flags

                    # Update opposing team's stats based on the player's team
                    if team_name == 'Red':
                        team_stats['Blue']['kills'] += switched_kills
                        team_stats['Blue']['flags'] += switched_flags
                    elif team_name == 'Blue':
                        team_stats['Red']['kills'] += switched_kills
                        team_stats['Red']['flags'] += switched_flags
                except ValueError:
                    continue

            # Fetch or create the player's skill rating
            skill_rating, kills_from_db, is_new_player = self.fetch_player_rating(name)  # Adjusted to unpack properly

            if is_new_player:
                self.show_temp_message(f"New player '{name}' created.")

            # Create player instance
            player_instance = Player(name, kills, flags_captured, time_played, xp, skill_rating)

            # Store player stats
            player_stats[name] = {
                'kills': kills,
                'flags_captured': flags_captured,
                'level': level,
                'time_played': time_played,
                'xp': xp,
                'skill_rating': player_instance.skill_rating
            }

        # Fetch ratings for red and blue players
        red_players_ratings = [self.fetch_player_rating(p['name'].text.strip()) for p in self.players if
                               p['team'] == 'Red']
        blue_players_ratings = [self.fetch_player_rating(p['name'].text.strip()) for p in self.players if
                                p['team'] == 'Blue']

        # Extracting skill ratings
        red_ratings = [rating[0] for rating in red_players_ratings]  # Extracting skill ratings
        blue_ratings = [rating[0] for rating in blue_players_ratings]  # Extracting skill ratings

        # Determine the winning team
        if team_stats['Red']['flags'] > team_stats['Blue']['flags']:
            winning_team = "Red"
            teammates_ratings = red_ratings
            opponents_ratings = blue_ratings
        elif team_stats['Red']['flags'] < team_stats['Blue']['flags']:
            winning_team = "Blue"
            teammates_ratings = blue_ratings
            opponents_ratings = red_ratings
        else:
            if team_stats['Red']['kills'] > team_stats['Blue']['kills']:
                winning_team = "Red"
                teammates_ratings = red_ratings
                opponents_ratings = blue_ratings
            elif team_stats['Red']['kills'] < team_stats['Blue']['kills']:
                winning_team = "Blue"
                teammates_ratings = blue_ratings
                opponents_ratings = red_ratings
            else:
                winning_team = "Draw"
                teammates_ratings = []
                opponents_ratings = []

        # Calculate average ratings for teammates and opponents
        avg_teammate_rating = sum(teammates_ratings) / len(teammates_ratings) if teammates_ratings else 0
        avg_opponent_rating = sum(opponents_ratings) / len(opponents_ratings) if opponents_ratings else 0

        # Calculate skill ratings for each player based on the match outcome
        for name in player_stats.keys():
            stats = player_stats[name]
            outcome = ('draw' if winning_team == 'Draw' else
                       'win' if winning_team in name else
                       'lose')

            # Create a player instance for skill rating calculation
            player_instance = Player(name, stats['level'], stats['kills'], stats['flags_captured'],
                                     stats['time_played'], stats['xp'])

            # Calculate the skill rating based on performance
            skill_rating = self.calculate_skill_rating_logic(player_instance, outcome, avg_teammate_rating,
                                                             avg_opponent_rating)
            stats['skill_rating'] = skill_rating  # Update the player's stats with the calculated skill rating

        # Display results
        self.display_match_results(team_stats)
        self.display_player_stats(player_stats)

    def fetch_player_rating(self, player_name):
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT skill_rating, kills FROM player_skill_rating WHERE player_name = %s', (player_name,))
            result = cursor.fetchone()

            if result is None:
                default_skill_rating = 5
                default_kills = 0

                # Insert new player into the database with default values
                cursor.execute('''
                               INSERT INTO player_skill_rating (team_name, player_name, kills, flags_captured, player_level, skill_rating)
                               VALUES (%s, %s, %s, %s, %s, %s)
                           ''', ("No Team", player_name, 0, 0, 0, 0))
                self.conn.commit()  # Ensure changes are committed to the database
                return default_skill_rating, default_kills, True  # Return the default skill rating, kills, and a flag indicating a new player

            return result[0], result[1], False  # Return skill_rating, kills, and indicate no new player was created
        except mysql.connector.Error as err:
            print(f"Error fetching player rating: {err}")
            return 5, 0, True  # Also return defaults in case of an error

    def calculate_skill_rating_logic(self, player, outcome, teammates_average_rating, opponents_average_rating):
        # Initialize skill rating
        skill_rating = player.skill_rating

        # Weights for performance-based rating adjustments
        kills_weight = 0.3
        flags_weight = 0.5
        xp_weight = 0.2

        # Outcome-based performance score calculation
        if player.time_played > 0:
            performance_score = (
                    (flags_weight * player.flags_captured +
                     kills_weight * player.kills +
                     (xp_weight * player.xp) / 10000) * (480 / (60 * player.time_played))
            )
        else:
            performance_score = -5  # Penalty for no time played

        # Outcome adjustments
        if outcome == 'win':
            skill_rating += performance_score + 0.5
        elif outcome == 'lose':
            skill_rating += performance_score - 0.25
        elif outcome == 'switched_win':
            real_xp = player.xp / 1.5  # Adjusted real XP for switched win
            performance_score = (
                    (flags_weight * player.flags_captured +
                     kills_weight * player.kills +
                     (xp_weight * real_xp) / 10000) * (480 / (60 * player.time_played))
            )
            skill_rating += performance_score + 0.85
        elif outcome == 'switched_lose':
            skill_rating += performance_score - 0.05
        elif outcome == 'draw':
            skill_rating += performance_score

        # Define weights for weighted average calculation
        player_weight = 0.5
        teammates_weight = 0.3
        opponents_weight = 0.2

        # Calculate weighted average benchmark
        weighted_average_rating = (
                (skill_rating * player_weight) +
                (teammates_average_rating * teammates_weight) +
                (opponents_average_rating * opponents_weight)
        )

        # Adjust skill rating based on weighted average comparison
        if skill_rating > weighted_average_rating:
            skill_rating += 0.5  # Bonus for exceeding weighted average
        elif skill_rating < weighted_average_rating:
            skill_rating -= 0.5  # Penalty for falling below weighted average

        return round(skill_rating, 2)

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
        self.ask_for_admin_password(self.perform_export)

    def export_leaderboard_to_pdf(self, instance):
        if not self.players:
            self.show_popup("Error", "No leaderboard data available to export.")
            return

        filechooser = FileChooserIconView(filters=['*.pdf'])
        filechooser.bind(on_submit=self.save_pdf)

        popup = Popup(title="Choose Save Location for PDF", content=filechooser, size_hint=(0.9, 0.9))
        popup.open()

    def save_pdf(self, chooser, selection, touch):
        if selection:
            pdf_path = selection[0]
            if not pdf_path.endswith('.pdf'):
                pdf_path += '.pdf'

            self.generate_pdf(pdf_path, self.players)
            self.show_popup("Success", f"Leaderboard exported to {pdf_path} successfully!")

    def generate_pdf(self, path, data):
        c = canvas.Canvas(path, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 16)
        c.drawString(30, height - 40, "Leaderboard")
        c.setFont("Helvetica", 12)
        c.drawString(30, height - 60, "-----------------------------------")

        c.drawString(30, height - 80, "Rank")
        c.drawString(150, height - 80, "Player Name")
        c.drawString(280, height - 80, "Matches")
        c.drawString(380, height - 80, "Total Kills")
        c.drawString(480, height - 80, "Total Flags")
        c.drawString(580, height - 80, "Overall Skill")

        y_position = height - 100
        for idx, row in enumerate(data):
            if y_position < 50:
                c.showPage()
                c.setFont("Helvetica", 12)
                y_position = height - 50

            c.drawString(30, y_position, str(idx + 1))
            c.drawString(150, y_position, row['name'])
            c.drawString(280, y_position, str(row['kills']))
            c.drawString(380, y_position, str(row['total_kills']))
            c.drawString(480, y_position, str(row['total_flags']))
            c.drawString(580, y_position, f"{row['skill_rating']:.2f}")
            y_position -= 20

        c.save()

    from kivy.uix.gridlayout import GridLayout  # Import GridLayout

    def show_leaderboard(self, instance):
        try:
            cursor = self.conn.cursor()
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT 
                    p.player_name, 
                    COUNT(*) AS matches, 
                    SUM(p.kills) AS total_kills, 
                    SUM(p.flags_captured) AS total_flags, 
                    COALESCE(SUM(p.skill_rating) / NULLIF(COUNT(*), 0), 0) AS overall_skill_rating, 
                    COALESCE(c.country_flag, 'flags/default_flag.png') AS flag 
                FROM player_skill_rating p 
                LEFT JOIN player_country_flags c ON p.player_name = c.player_name 
                GROUP BY p.player_name 
                ORDER BY overall_skill_rating DESC
            ''')
            results = cursor.fetchall()

            # Create a scrollable content layout for the leaderboard
            leaderboard_content = BoxLayout(orientation='vertical', padding=10)
            scroll_view = ScrollView(size_hint=(1, None), size=(500, 400))

            # Create a GridLayout for leaderboard data with fixed column width
            leaderboard_grid = GridLayout(cols=7, padding=10, spacing=10, size_hint_y=None)
            leaderboard_grid.bind(minimum_height=leaderboard_grid.setter('height'))

            # Adding headers
            headers = ['Rank', 'Player Name', 'Matches', 'Total Kills', 'Total Flags', 'Overall Skill', 'Country Flag']
            for header in headers:
                leaderboard_grid.add_widget(Label(text=header, size_hint_y=None, height=40, bold=True))

            # Populate leaderboard data
            for idx, row in enumerate(results):
                leaderboard_grid.add_widget(Label(text=str(idx + 1), size_hint_y=None, height=40))  # Rank

                # Truncate player name if too long
                player_name = row[0]
                truncated_name = (player_name[:15] + '...') if len(player_name) > 15 else player_name

                leaderboard_grid.add_widget(Label(text=truncated_name, size_hint_y=None, height=40))  # Player Name
                leaderboard_grid.add_widget(Label(text=str(row[1]), size_hint_y=None, height=40))  # Matches
                leaderboard_grid.add_widget(Label(text=str(row[2]), size_hint_y=None, height=40))  # Total Kills
                leaderboard_grid.add_widget(Label(text=str(row[3]), size_hint_y=None, height=40))  # Total Flags
                leaderboard_grid.add_widget(Label(text=f"{row[4]:.2f}", size_hint_y=None, height=40))  # Ovelogicrall Skill

                # Add flag image on this line
                flag_image_path = row[5] if isinstance(row[5], str) else 'flags/default_flag.png'  # Flag path
                flag_image = Image(source=flag_image_path, size_hint=(0.6, None), size=(30, 30))
                leaderboard_grid.add_widget(flag_image)  # Flag image

            # Add the GridLayout to the ScrollView
            scroll_view.add_widget(leaderboard_grid)

            # Add scroll view to the content layout
            leaderboard_content.add_widget(scroll_view)

            leaderboard_popup = Popup(title='Leaderboard', content=leaderboard_content, size_hint=(1, 0.66))
            leaderboard_popup.open()
        except mysql.connector.Error as err:
            print(f"Error occurred: {err}")
            self.show_popup("Error", str(err))

    def _update_leaderboard_rect(self, instance, value):
        # Update the rectangle size and position for the background of the leaderboard
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def update_flag_in_database(self, player_name, flag_path):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO player_country_flags (player_name, country_flag) 
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
        password_content = BoxLayout(orientation='vertical', padding=10)
        password_content.add_widget(Label(text='Enter Admin Password to Confirm:', size_hint_y=None, height=40))

        password_input = TextInput(multiline=False, size_hint=(1, 0.2), password=True)
        password_content.add_widget(password_input)

        ok_button = Button(text='Confirm', size_hint=(1, 0.2))
        password_content.add_widget(ok_button)

        password_popup = Popup(title='Admin Password Required', content=password_content, size_hint=(0.6, 0.4))

        def on_ok(instance):
            if password_input.text == "Admin123@@":
                password_popup.dismiss()
                callback()
            else:
                self.show_popup("Error", "Incorrect password!")
                password_popup.dismiss()

        ok_button.bind(on_press=on_ok)
        password_popup.open()

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

