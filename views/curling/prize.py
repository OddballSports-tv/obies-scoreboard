# imports
import sys
import os

# add the parent directory (absolute, not relative) to the sys.path
# (this makes the games package imports work)
sys.path.append(os.path.abspath(os.pardir))

# PyQt imports
from PyQt5 import QtCore, QtWidgets
from PyQt5 import uic, QtGui, QtTest
from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter, QMovie, QFont
from PyQt5.QtCore import QThread, QTimer, QRect, Qt, QSize, QUrl
from PyQt5.QtWidgets import QInputDialog, QWidget, QDialog, QLabel, QMessageBox, QGridLayout, QVBoxLayout, QLineEdit, QHBoxLayout, QPushButton, QSizePolicy, QSlider, QStyle
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget

# bocce game imports
#from model.games.curling.team import Team, Player

# remote
#from model.remotes.ati import ATI

# color constant imports
#from .colors import *

# other imports
import numpy as np
import cv2
import imutils
from imutils import paths
import argparse
from playsound import playsound
from tinytag import TinyTag
import random
import threading
from collections import deque
import time
import json

# logging
import logging
logging.basicConfig(level=logging.INFO)

# INDICATOR AND GRAPHIC SIZES
TOP_LEFT_LOGO_WIDTH = 150
TOP_CENTER_LOGO_WIDTH = 400
TOP_RIGHT_LOGO_WIDTH = 150
BOTTOM_LEFT_LOGO_WIDTH = 200
BOTTOM_CENTER_LOGO_WIDTH = 400
BOTTOM_RIGHT_LOGO_WIDTH = 200
RFID_INDICATOR_WIDTH = 90

# CARD WIDTH
CARD_WIDTH = 75

# STONE WIDTH
STONE_WIDTH = 80

# HAMMER WIDTH
HAMMER_WIDTH = 150

# TEAM LOGOS
TEAM_A_LOGO_PATH = os.path.join("views", "curling", "graphics", "blueobie.png")
TEAM_B_LOGO_PATH = os.path.join("views", "curling", "graphics", "greenobie.png")

TEAM_LOGO_SIZE = 150

# DEFAULT MINUTES
DEFAULT_GAME_MINUTES = 20
DEFAULT_WARMUP_MINUTES = 5

# BUTTON HISTORY
BUTTON_HISTORY_LENGTH = 20

# todo move sound and animation convenience functions to a helpers file

# MEDIA for ABC
MEDIA_DIR = os.path.join(os.getcwd(), "..", "media-leelanaucurlingclub")
ANNOUNCEMENT_DIR = os.path.join(MEDIA_DIR, "announcement_game", "lastname_firstname")
# PLAYERS = {
#     # "RFID": ("Name", Skip?, entry_video.mp4)
#     "e4bce79c": ("David Gersenson", True, os.path.join(ANNOUNCEMENT_DIR, "Gersenson_David.mp4")),
#     "d7acdcef": ("Dwight Schrute", False, os.path.join(ANNOUNCEMENT_DIR, "Gersenson_David_2.mp4")),
#     "1ab03e86": ("Pam Beesley", False, os.path.join(ANNOUNCEMENT_DIR, "Beesley_Pam.mp4")),
#     "b0e751fd": ("Jim Halpert", False, os.path.join(ANNOUNCEMENT_DIR, "Jim_Halpert.mp4"))
# }

# load the json file
PLAYERS = None
with open(os.path.join(MEDIA_DIR, "prize.json")) as f:
  PLAYERS = json.load(f)

# SOUND FILE TYPES
SOUND_TYPES = (".m4a", ".mp3", ".wav", ".WAV")

# ANIMATION TYPES
ANIMATION_TYPES = (".gif", ".GIF")

###### SET ME!!!!!!!!!!!!!!!!!!! ####################
RFID_READER_CONNECTED = False
#####################################################

def soundfile_duration(path):
    tag = TinyTag.get(path)
    seconds = tag.duration
    return seconds


def list_sounds(dir, contains=None):
    """grabs all sound file paths in a directory"""
    return list(paths.list_files(dir, validExts=SOUND_TYPES, contains=contains))

def play_random_sound(sound_dir):
    """plays a random sound in a directory"""
    # play a random sound
    sounds = list_sounds(sound_dir)
    if len(sounds) == 0:
        return
    sound_filename = random.choice(sounds)
    threading.Thread(target=playsound, args=(sound_filename,)).start()

def list_animations(dir, contains=None):
    """grabs all animations in a directory path"""
    return list(paths.list_files(dir, validExts=ANIMATION_TYPES, contains=contains))

def sleep(timeout):
    """PyQt friendly non-blocking sleep (alternative to `time.sleep()`)"""
    QtTest.QTest.qWait(timeout * 1000)

def load_png_qImg(pngPath, width):
    """
    load the Obie logo
    """
    # load the logo and read all channels (including alpha transparency)
    logo = cv2.imread(pngPath, cv2.IMREAD_UNCHANGED)

    # swap color channels for Qt
    logo = cv2.cvtColor(logo, cv2.COLOR_BGRA2RGBA)

    # resize to a known width maintaining aspect ratio
    logo = imutils.resize(logo, width=width)

    # extract the dimensions of the image and set the bytes per line
    height, width, channel = logo.shape
    bytesPerLine = channel * width

    # create a QImage and ensure to use the alpha transparency format
    qImg = QImage(logo.data, width, height, bytesPerLine, QImage.Format_RGBA8888)

    return qImg

def cv2img_to_qImg(image, width):
    """
    converts a BGRA OpenCV image to qImage RGBA format (A is the alpha transparency
    channel
    """
    # swap color channels for Qt
    image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)

    # resize to a known width maintaining aspect ratio
    image = imutils.resize(image, width=width)

    # extract the dimensions of the image and set the bytes per line
    height, width, channel = image.shape
    bytesPerLine = channel * width

    # create a QImage and ensure to use the alpha transparency format
    qImg = QImage(image.data, width, height, bytesPerLine, QImage.Format_RGBA8888)

    return qImg

def draw_rgba_qimg(label, qImg):
    # set the logo in the GUI
    label.setPixmap(QPixmap(qImg))
    label.repaint()


class VideoPlayer(QWidget):

    def __init__(self, parent=None):
        super(VideoPlayer, self).__init__(parent)

        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        videoWidget = QVideoWidget()

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.play)

        self.positionSlider = QSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 0)
        self.positionSlider.sliderMoved.connect(self.setPosition)

        self.errorLabel = QLabel()
        self.errorLabel.setSizePolicy(QSizePolicy.Preferred,
                QSizePolicy.Maximum)

        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(self.playButton)
        controlLayout.addWidget(self.positionSlider)

        layout = QVBoxLayout()
        layout.addWidget(videoWidget)
        layout.addLayout(controlLayout)
        layout.addWidget(self.errorLabel)

        self.setLayout(layout)

        self.mediaPlayer.setVideoOutput(videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)

        # set size
        self.resize(1280, 720)
        self.error = False

    def openFile(self, video_path):
        self.mediaPlayer.setMedia(
                QMediaContent(QUrl.fromLocalFile(video_path)))
        self.playButton.setEnabled(True)

    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.errorLabel.setText("")
            self.playButton.setEnabled(True)
            self.error = False
            self.mediaPlayer.play()


    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playButton.setIcon(
                    self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playButton.setIcon(
                    self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        self.positionSlider.setValue(position)

    def durationChanged(self, duration):
        self.positionSlider.setRange(0, duration)

    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def handleError(self):
        video_path = os.path.join(MEDIA_DIR, "announcement_game",
                                  "lastname_firstname", "Random_Curler.mp4")
        self.openFile(video_path)
        self.play()
        # self.playButton.setEnabled(False)
        # self.errorLabel.setText("Error: " + self.mediaPlayer.errorString())
        # self.error = True

    def sizeHint(self):
        return QSize(1280, 720)

class Animation():
    """Plays GIF animations nearly fullscreen"""
    # todo grab screen resolution and adjust the window size programmatically

    def __init__(self, gif_path, timeout=8):
        #super(Animation, self).__init__()
        self.timeout=timeout
        self.dlg = QDialog()
        self.dlg.setWindowTitle("animation")
        self.dlg.setWindowModality(False)
        self.dlg.setFixedSize(800, 800)
        self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        self.label_animation = QLabel(self.dlg)
        self.movie = QMovie(gif_path)
        self.movie.setScaledSize(QSize(self.dlg.width(), self.dlg.height()))
        self.label_animation.setMovie(self.movie)

    def start(self):
        self.run()

    def run(self):
        self.movie.start()
        self.dlg.show()
        sleep(self.timeout)
        self.quit()

    def quit(self):
        self.movie.stop()
        self.dlg.done(0)

class PlayerRFID(QWidget):
    """Waits for Num Players and displays names"""
    # todo grab screen resolution and adjust the window size programmatically

    def __init__(self, team, num_players):
        super().__init__()
        self.num_players = num_players
        self.setWindowTitle("Oddball Prize")

        # creat num_players indicators and names
        self.indicators = [QLabel() for x in range(num_players)]
        self.names = ["" for x in range(num_players)]

        # build the grid
        self.grid = QGridLayout()
        for (i, (indicator, name)) in enumerate(zip(self.indicators, self.names)):
            self.grid.addWidget(indicator, i, 0)
            qImg = load_png_qImg(os.path.join("views", "oddball_graphics", "cut_assets", "Mark-Primary.png"), RFID_INDICATOR_WIDTH)
            draw_rgba_qimg(indicator, qImg)
            label = QLabel(name)
            label.setFont(QFont("Luckiest Guy", 40))
            self.grid.addWidget(label, i, 1)

        # layout HBox contains VBox
        winLayout = QHBoxLayout()
        layout = QVBoxLayout()

        # add the rfid text endtry box
        self.id = QLineEdit()
        self.id.setEchoMode(QLineEdit.Password)
        self.id.returnPressed.connect(self.rfid_entered)

        # add message to players
        self.teamLabel = QLabel("Tap a fob...")
        self.teamLabel.setAlignment(Qt.AlignCenter)
        self.teamLabel.setFont(QFont("Luckiest Guy", 70))
        instructionLabel = QLabel("win a prize?")
        instructionLabel.setAlignment(Qt.AlignCenter)
        instructionLabel.setFont(QFont("Luckiest Guy", 32))

        # add the indicator / name grid
        layout.addWidget(self.id)
        layout.addWidget(self.teamLabel)
        layout.addWidget(instructionLabel)
        layout.addLayout(self.grid)

        self.v = VideoPlayer()


        # set the dialog layout
        winLayout.addLayout(layout)
        winLayout.addWidget(self.v)
        self.setLayout(winLayout)
        self.showMaximized()

        # index of grid will increment up to num_players
        self.name_idx = 0

    def start(self):
        self.run()

    def run(self):
        self.show()
        self.setFocus()
        self.id.setFocus()

        while not self.name_idx >= self.num_players:
            num_remaining = self.num_players - self.name_idx
            logging.info("waiting for {} more players to badge in".format(num_remaining))
            sleep(1)

        sleep(1)
        self.quit()

    def rfid_entered(self):
        # grab the rfid string and set the text box back to empty
        rfid_string = self.id.text()
        self.id.setText("")

        # lookup the string in the players list
        try:
            with open(os.path.join(MEDIA_DIR, "prize.json")) as f:
                PLAYERS = json.load(f)
            name = PLAYERS[rfid_string][0]
            skip = PLAYERS[rfid_string][1]
            video_path = os.path.join(MEDIA_DIR, "announcement_game", "lastname_firstname", PLAYERS[rfid_string][2])
        except KeyError:
            self.teamLabel.setStyleSheet("QLabel { color : red }")
            for i in range(5):
                self.teamLabel.setText("INVALID")
                sleep(.25)
                self.teamLabel.setText("")
                sleep(.25)
            self.teamLabel.setText(str("Tap a fob..."))
            self.teamLabel.setStyleSheet("QLabel { color : black }")
            return



        # grab the icon and name label widget
        iconLabel_widget = self.grid.itemAtPosition(self.name_idx, 0).widget()
        nameLabel_widget = self.grid.itemAtPosition(self.name_idx, 1).widget()

        # set the name Label
        nameLabel_widget.setText(name)

        # set the icon
        if skip:
            qImg = load_png_qImg(os.path.join("views", "curling", "graphics",
                                              "skip.png"), RFID_INDICATOR_WIDTH)
            draw_rgba_qimg(iconLabel_widget, qImg)
        else:
            qImg = load_png_qImg(os.path.join("views", "oddball_graphics", "cut_assets",
                                              "Mark-2C-Teal.png"), RFID_INDICATOR_WIDTH)
            draw_rgba_qimg(iconLabel_widget, qImg)


        # play the video
        self.v.openFile(video_path)
        self.v.play()
        self.id.setFocus()

        # when there is not an error and the video is playing, keep playing until it is done
        while not self.v.error and self.v.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.id.setEnabled(False)
            sleep(1)

        nameLabel_widget = self.grid.itemAtPosition(self.name_idx, 1).widget()

        # set the name Label
        nameLabel_widget.setText("")

        # increement the name index and test that it doesn't exceed the number of players
        sleep(1)

        self.id.setEnabled(True)
        self.id.setFocus()

    def quit(self):
        self.close()

    def closeEvent(self, event) -> None:
        logging.info("close rfid window pressed")
        self.name_idx = 4
        self.quit()
        event.accept()


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, ui, clargs, *args, **kwargs):
        """
        constructor
        """
        super().__init__(*args, **kwargs)

        # load the user interface
        uic.loadUi(ui, self)

        # MainWindow settings
        # set the window title
        self.setWindowTitle("Obie's Scoreboard - {} - {}".format(clargs["game"], clargs["view"]))
        # maximize the window
        self.showMaximized()


        # TOP LOGOS
        # draw the top left logo
        qImg = self.load_png_qImg(os.path.join(MEDIA_DIR, "graphics", "broomstack_logo.png"),
                                   TOP_LEFT_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_sponsor_top_left, qImg)

        # draw the top center logo
        qImg = self.load_png_qImg(
            os.path.join(os.getcwd(), "views", "oddball_graphics", "ODDBALLSPORTS.TV.png"),
                                   TOP_CENTER_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_sponsor_top_center, qImg)

        # draw the top right logo
        qImg = self.load_png_qImg(
            os.path.join(MEDIA_DIR, "graphics", "leelanau_logo.png"), TOP_RIGHT_LOGO_WIDTH)
        self.draw_rgba_qimg(self.label_sponsor_top_right, qImg)

        # # BOTTOM LOGOS
        # #draw the bottom left logo
        # path = os.path.join(os.getcwd(), "views", "oddball_graphics", "cut_assets", "Mark-2C-Pink.png")
        # qImg = self.load_png_qImg(path, BOTTOM_LEFT_LOGO_WIDTH)
        # self.draw_rgba_qimg(self.label_sponsor_bottom_left, qImg)
        #
        # # draw the bottom center logo
        # qImg = self.load_png_qImg(
        #     os.path.join(os.getcwd(), "views", "oddball_graphics", "ODDBALLSPORTS.TV.png"),
        #                            BOTTOM_CENTER_LOGO_WIDTH)
        # self.draw_rgba_qimg(self.label_sponsor_bottom_center, qImg)
        #
        # # draw the bottom right logo
        # qImg = self.load_png_qImg(
        #     os.path.join(os.getcwd(), "views", "oddball_graphics", "cut_assets", "Mark-2C-Teal.png"),
        #     BOTTOM_LEFT_LOGO_WIDTH)
        # self.draw_rgba_qimg(self.label_sponsor_bottom_right, qImg)

        self.teamA = Team(teamName="tbd")
        self.teamB = Team(teamName="tbd")
        self.team_edit_mode = False

        self.teamA_points_place_labels = [
            self.label_teamA_points1,
            self.label_teamA_points2,
            self.label_teamA_points3,
            self.label_teamA_points4,
            self.label_teamA_points5,
            self.label_teamA_points6,
            self.label_teamA_points7,
            self.label_teamA_points8,
            self.label_teamA_points9,
            self.label_teamA_points10,
            self.label_teamA_points11,
            self.label_teamA_points12,
            self.label_teamA_points13,
            self.label_teamA_points14
        ]
        self.teamB_points_place_labels = [
            self.label_teamB_points1,
            self.label_teamB_points2,
            self.label_teamB_points3,
            self.label_teamB_points4,
            self.label_teamB_points5,
            self.label_teamB_points6,
            self.label_teamB_points7,
            self.label_teamB_points8,
            self.label_teamB_points9,
            self.label_teamB_points10,
            self.label_teamB_points11,
            self.label_teamB_points12,
            self.label_teamB_points13,
            self.label_teamB_points14
        ]
        self.card_start_positions = [
            self.label_end_card1,
            self.label_end_card2,
            self.label_end_card3,
            self.label_end_card4,
            self.label_end_card5,
            self.label_end_card6,
            self.label_end_card7,
            self.label_end_card8,
            self.label_end_card9,
            self.label_end_card10
        ]
        self.blank_end_positions = [
            self.label_blank_end1,
            self.label_blank_end2,
            self.label_blank_end3,
            self.label_blank_end4,
            self.label_blank_end5,
            self.label_blank_end6,
            self.label_blank_end7,
            self.label_blank_end8,
            self.label_blank_end9,
            self.label_blank_end10
        ]

        # maps end card to a location
        # these are the initial positions for each card
        self.card_place_color_map = {
            1: [self.card_start_positions[0], "white", False],
            2: [self.card_start_positions[1], "white", False],
            3: [self.card_start_positions[2], "white", False],
            4: [self.card_start_positions[3], "white", False],
            5: [self.card_start_positions[4], "white", False],
            6: [self.card_start_positions[5], "white", False],
            7: [self.card_start_positions[6], "white", False],
            8: [self.card_start_positions[7], "white", False],
            9: [self.card_start_positions[8], "white", False],
            10: [self.card_start_positions[9], "white", False]
        }


        # initialize points places to empty
        for point_placeA, point_placeB in zip(self.teamA_points_place_labels, self.teamB_points_place_labels):
            if point_placeA is not None:
                point_placeA.setText("")
            if point_placeB is not None:
                point_placeB.setText("")


        self.game_in_progress = False


        # TV REMOTE STATUS VARS
        # run the TV remote receiver task (it is threaded with signals)
        self.enableKeyPressEventHandler = False
        self.add_points_mode = False
        self._prevButton_str = None
        self._prevButton = None
        self._wait_for_ok = False
        self.buttonHistory = deque(maxlen=BUTTON_HISTORY_LENGTH)
        self.waitForRemoteButtonPressSignal(clargs["remote"])

        self.ignore_keys = []

        self.NUM_ENDS = 8
        self.ends_chosen = False
        self.selected_card = self.NUM_ENDS
        self.current_end = 0
        self.teamA_card_idx = 0
        self.teamB_card_idx = 0
        self.blank_end_idx = 0

        # stones
        self.teamA_num_stones = 8
        self.teamB_num_stones = 8

        self.rfid_window = None

        # clearing the hammer draws team logos
        self.clear_hammer()

        # set the window focus
        self.setFocus()

    def game_launch_steps(self):

        # step #0 - wait for PWR key

        # step #1 - draw team logos by clearing hammer and choose ends
        self.clear_hammer()
        self.clear_cards()
        self.ends_chosen = False
        self.NUM_ENDS = 8
        self.selected_card = self.NUM_ENDS
        self.choose_ends()

        # step #2 - input team names
        self.input_team_names()

        # step #3 - rfid
        logging.info("inputting team A via RFID")
        self.input_player_rfid_USB(self.teamA)
        logging.info("inputting team B via RFID")
        self.input_player_rfid_USB(self.teamB)

        #self.input_player_rfid_SimpleMFRC522()

        # step #4 - start game
        self.start_game()

        # step #5 - game runner
        self.game_runner()

    def start_game(self):
        logging.info("starting game")
        self.game_in_progress = True
        self.current_end = 0
        self.teamA_card_idx = -1
        self.teamB_card_idx = -1
        self.previous_locked_card_teamA = None
        self.previous_locked_card_teamB = None
        self.blank_end_idx = -1
        self.selected_card = 1

    def game_runner(self):
        while self.game_in_progress:
            self.increment_end()
            while self.stones_remaining(self.teamA) or self.stones_remaining(self.teamB):
                self.ignore_keys = [
                    QtCore.Qt.Key_S,
                    QtCore.Qt.Key_C,
                    QtCore.Qt.Key_Up,
                    QtCore.Qt.Key_Down,
                    QtCore.Qt.Key_Left,
                    QtCore.Qt.Key_Right,
                    QtCore.Qt.Key_Return
                ]
                sleep(1)
            logging.info("no stones remaining; selecting end card {} for moving".format(str(self.current_end)))
            while not self.end_card_locked(self.current_end):
                self.ignore_keys = [
                    QtCore.Qt.Key_S,
                    QtCore.Qt.Key_C,
                    QtCore.Qt.Key_A,
                    QtCore.Qt.Key_B,
                ]
                sleep(1)
            logging.info("end card {} is locked".format(str(self.current_end)))
        logging.info("game is no longer in progress")



    def end_card_locked(self, end):
        logging.debug("is end card {} locked: {}".format(str(end), str(self.card_place_color_map[end][2])))
        return self.card_place_color_map[end][2]

    def move_card_down(self):
        card_num = self.selected_card
        logging.info("moving card down")
        if not self.end_card_locked(card_num):
            # if the card is in the starting positions, then move it down to team A positions
            if self.card_place_color_map[card_num][0] in self.card_start_positions:
                # set to the next open end card position
                index_to_clear = self.card_start_positions.index(self.card_place_color_map[card_num][0])
                self.draw_card(card_num, "clear_it", self.card_start_positions[index_to_clear])
                self.card_place_color_map[card_num][0] = self.first_open_team_card_position(self.teamA)

            # or if the card is in team A's positions, move it down to team B positions
            elif self.card_place_color_map[card_num][0] in self.teamA_points_place_labels:
                # set to the next open end card position
                index_to_clear = self.teamA_points_place_labels.index(self.card_place_color_map[card_num][0])
                self.draw_card(card_num, "clear_it", self.teamA_points_place_labels[index_to_clear])
                self.card_place_color_map[card_num][0] = self.first_open_team_card_position(self.teamB)

            # or if the card is in team B's positions, move it down to the blank end positions
            elif self.card_place_color_map[card_num][0] in self.teamB_points_place_labels:
                # set to the next open end card position
                index_to_clear = self.teamB_points_place_labels.index(self.card_place_color_map[card_num][0])
                self.draw_card(card_num, "clear_it", self.teamB_points_place_labels[index_to_clear])
                self.card_place_color_map[card_num][0] = self.next_open_blank_end()

            logging.info("drawing card")
            self.draw_card(card_num, "blue", self.card_place_color_map[card_num][0])

    def move_card_up(self):
        card_num = self.selected_card
        logging.info("moving card down")
        if not self.end_card_locked(card_num):
            # if the card is in the blank end positions, then move it up to team B positions
            if self.card_place_color_map[card_num][0] in self.blank_end_positions:
                # set to the next open end card position
                index_to_clear = self.blank_end_positions.index(self.card_place_color_map[card_num][0])
                self.draw_card(card_num, "clear_it", self.blank_end_positions[index_to_clear])
                self.card_place_color_map[card_num][0] = self.first_open_team_card_position(self.teamB)

            # or if the card is in team B's positions, move it up to team A positions
            elif self.card_place_color_map[card_num][0] in self.teamB_points_place_labels:
                # set to the next open end card position
                index_to_clear = self.teamB_points_place_labels.index(self.card_place_color_map[card_num][0])
                self.draw_card(card_num, "clear_it", self.teamB_points_place_labels[index_to_clear])
                self.card_place_color_map[card_num][0] = self.first_open_team_card_position(self.teamA)

            else:
                raise ValueError("can't move unlocked card back to start position")

            logging.info("drawing card")
            self.draw_card(card_num, "blue", self.card_place_color_map[card_num][0])


    def move_card_right(self):
        card_num = self.selected_card
        logging.info("moving card right")
        if not self.end_card_locked(card_num):
            # if the card is in team A's positions, move it right to next open position
            if self.card_place_color_map[card_num][0] in self.teamA_points_place_labels:
                # set to the next open end card position
                index_to_clear = self.teamA_points_place_labels.index(self.card_place_color_map[card_num][0])
                self.draw_card(card_num, "clear_it", self.teamA_points_place_labels[index_to_clear])
                self.card_place_color_map[card_num][0] = self.first_open_team_card_position(self.teamA)

            # or if the card is in team B's positions, move it right to next open position
            elif self.card_place_color_map[card_num][0] in self.teamB_points_place_labels:
                # set to the next open end card position
                index_to_clear = self.teamB_points_place_labels.index(self.card_place_color_map[card_num][0])
                self.draw_card(card_num, "clear_it", self.teamB_points_place_labels[index_to_clear])
                self.card_place_color_map[card_num][0] = self.first_open_team_card_position(self.teamB)

            logging.info("drawing card")
            self.draw_card(card_num, "blue", self.card_place_color_map[card_num][0])

    def move_card_left(self):
        card_num = self.selected_card
        logging.info("attempting moving card left")
        if not self.end_card_locked(card_num):
            # if the card is in team A's positions, move it left to next open position
            if self.card_place_color_map[card_num][0] in self.teamA_points_place_labels:
                logging.info("the card is in team A points places")

                # try moving it left
                if self.teamA_points_place_labels[self.teamA_card_idx - 1].pixmap() is None:
                    # clear it from previous position
                    logging.info("clearing previous card position")
                    index_to_clear = self.teamA_points_place_labels.index(self.card_place_color_map[card_num][0])
                    self.draw_card(card_num, "clear_it", self.teamA_points_place_labels[index_to_clear])
                    # move it
                    logging.info("moving card left")
                    self.card_place_color_map[card_num][0] = self.teamA_points_place_labels[self.teamA_card_idx - 1]
                    logging.info("drawing card")
                    self.draw_card(card_num, "blue", self.card_place_color_map[card_num][0])
                    self.teamA_card_idx -= 1
            # or if the card is in team B's positions, move it left right to next open position
            elif self.card_place_color_map[card_num][0] in self.teamB_points_place_labels:
                if self.teamB_points_place_labels[self.teamB_card_idx - 1].pixmap() is None:
                    # clear it from previous position
                    logging.info("clearing previous card position")
                    index_to_clear = self.teamB_points_place_labels.index(self.card_place_color_map[card_num][0])
                    self.draw_card(card_num, "clear_it", self.teamB_points_place_labels[index_to_clear])
                    # move it
                    logging.info("moving card left")
                    self.card_place_color_map[card_num][0] = self.teamB_points_place_labels[self.teamB_card_idx - 1]
                    logging.info("drawing card")
                    self.draw_card(card_num, "blue", self.card_place_color_map[card_num][0])
                    self.teamB_card_idx -= 1

    def lock_card(self, card_num):
        self.card_place_color_map[card_num][2] = True
        self.draw_card(card_num, "white", self.card_place_color_map[card_num][0])

        if self.card_place_color_map[card_num][0] in self.teamA_points_place_labels:
            self.previous_locked_card_teamA = card_num
        elif self.card_place_color_map[card_num][0] in self.teamB_points_place_labels:
            self.previous_locked_card_teamB = card_num

    def next_open_blank_end(self):
        self.blank_end_idx += 1
        return self.blank_end_positions[self.blank_end_idx]

    def first_open_team_card_position(self, team):
        if team is self.teamA:
            self.teamA_card_idx += 1
            if self.teamA_card_idx >= len(self.teamA_points_place_labels):
                self.teamA_card_idx = len(self.teamA_points_place_labels) - 1
            return self.teamA_points_place_labels[self.teamA_card_idx]
        elif team is self.teamB:
            self.teamB_card_idx += 1
            if self.teamB_card_idx >= len(self.teamB_points_place_labels):
                self.teamB_card_idx = len(self.teamB_points_place_labels) - 1
            return self.teamB_points_place_labels[self.teamB_card_idx]
        
    def previous_open_team_card_position(self, team):
        if team is self.teamA:
            # if the previous card is positioned there, you can go left
            logging.info("selected card: {}".format(self.selected_card))
            logging.info("selected card minus 1: {}".format(self.selected_card-1))
            # if not self.teamA_points_place_labels[self.teamA_card_idx-1] in [v[0] for v in self.card_place_color_map.values()]:
            # if card is in team b, then need to check previous team A card because if statement fails
            # maybe get index of last locked card and can't go left of there

            logging.info("previous locked card: {}".format(self.previous_locked_card_teamA))


            # if not self.teamA_points_place_labels[self.previous_locked_card_teamA] is self.card_place_color_map[self.selected_card - 1][0]:
            #     self.teamA_card_idx -= 1
            #     # the card gets pinned as far left as it can go
            #     if self.teamA_card_idx <= 0:
            #         self.teamA_card_idx = 0
            # # otherwise, no change
            # else:
            #     pass
            self.teamA_card_idx -= 1
            return self.teamA_points_place_labels[self.previous_locked_card_teamA + 1]
        elif team is self.teamB:
            # if the previous card is not positioned there, you can go left
            if not self.teamB_points_place_labels[self.previous_locked_card_teamB] is self.card_place_color_map[self.selected_card - 1][0]:
                self.teamA_card_idx -= 1
                # the card gets pinned as far left as it can go
                if self.teamB_card_idx <= 0:
                    self.teamB_card_idx = 0
            # otherwise, no change
            else:
                    pass
            return self.teamB_points_place_labels[self.teamB_card_idx]


    def choose_ends(self):
        logging.info("choosing ends")
        # display all end cards
        self.display_all_end_cards_at_top()

        # set keys to ignore
        self.ignore_keys = [
            QtCore.Qt.Key_S,
            QtCore.Qt.Key_A,
            QtCore.Qt.Key_B,
            QtCore.Qt.Key_C,
            QtCore.Qt.Key_Up,
            QtCore.Qt.Key_Down
        ]

        # select the default
        self.select_card(self.NUM_ENDS, ignore_prev=True)

        # blink ends label
        text = self.label_end_cards.text()
        while not self.ends_chosen:
            sleep(.4)
            self.label_end_cards.setText("")
            sleep(.4)
            self.label_end_cards.setText(text)
        self.label_end_cards.setText(text)

        if self.ends_chosen:
            self.NUM_ENDS = self.selected_card

            # clear other cards
            for card_num, label_color in self.card_place_color_map.items():
                label = label_color[0]
                if card_num <= self.NUM_ENDS:
                    self.draw_card(card_num, "white", label)
                else:
                    self.draw_card(card_num, "clear_it", label)

        # clear ignored keys
        self.ignore_keys = []

    def clear_cards(self):
        # clear other cards
        for label in self.teamA_points_place_labels:
            self.draw_card(0, "clear_it", label)
        for label in self.teamB_points_place_labels:
            self.draw_card(0, "clear_it", label)
        for label in self.blank_end_positions:
            self.draw_card(0, "clear_it", label)


    def select_card(self, card_num, ignore_prev=False):
        logging.info("selecting card {}".format(card_num))
        if self.ends_chosen:
            if not card_num <= self.NUM_ENDS and not card_num >= 1:
                raise ValueError("card_num invalid")
        else:
            if card_num > max(self.card_place_color_map.keys()):
                card_num = 1
            if card_num < 1:
                card_num = max(self.card_place_color_map.keys())

        prev_selected_card = self.selected_card
        self.selected_card = card_num
        label, _, _ = self.get_card(card_num)
        color = "blue"
        self.draw_card(card_num, color, label)

        if not ignore_prev:
            label, color, _ = self.card_place_color_map[prev_selected_card]
            self.card_place_color_map[prev_selected_card] = [label, "white", False]
            self.draw_card(prev_selected_card, "white", label)

    def get_card(self, card_num):
        return self.card_place_color_map[card_num]

    def stones_remaining(self, team):
        if team is self.teamA:
            if self.teamA_num_stones >= 1:
                return True
        elif team is self.teamB:
            if self.teamB_num_stones >= 1:
                return True

    def draw_card(self, card_num, color, label):
        if color == "white":
            letter = ""
        elif color == "gray":
            letter = "x"
        elif color == "blue":
            letter = "b"
        elif color == "clear_it":
            label.clear()
            label.repaint()
            self.card_place_color_map[card_num] = [label, "clear", False]
            return
        else:
            raise ValueError("invalid card color")

        logging.info("drawing end card {} {}".format(str(card_num), color))
        filename = "{}{}.png".format(str(card_num), letter)
        path = os.path.join("views", "curling", "graphics", "cards", filename)
        logging.info("attempting to draw card at {}".format(path))
        qImg = self.load_png_qImg(path, width=CARD_WIDTH)
        self.draw_rgba_qimg(label, qImg)
        logging.info("success: drew card at {}".format(path))

    def display_all_end_cards_at_top(self):
        logging.info("drawing all end cards at top")

        # reposition all cards:
        # these are the initial positions for each card
        self.card_place_color_map = None
        self.card_place_color_map = {
            1: [self.card_start_positions[0], "white", False],
            2: [self.card_start_positions[1], "white", False],
            3: [self.card_start_positions[2], "white", False],
            4: [self.card_start_positions[3], "white", False],
            5: [self.card_start_positions[4], "white", False],
            6: [self.card_start_positions[5], "white", False],
            7: [self.card_start_positions[6], "white", False],
            8: [self.card_start_positions[7], "white", False],
            9: [self.card_start_positions[8], "white", False],
            10: [self.card_start_positions[9], "white", False]
        }

        try:
            for card_num, place_color_locked in self.card_place_color_map.items():
                label = place_color_locked[0]
                color = place_color_locked[1]
                locked = place_color_locked[2]
                print(locked)
                self.draw_card(card_num, color, label)
                logging.info("END card {} loaded into top position".format(str(card_num)))
        except Exception as e:
            logging.critical("card not loaded")
            print(str(e))
            return
        logging.info("success: drew all end cards at top")

    def input_team_names(self):
        self.show_team_change_popup(self.teamA)
        self.show_team_change_popup(self.teamB)

    def input_player_rfid_SimpleMFRC522(self):
        def wait_for_four_players():
            # import the RFID reader
            import RPi.GPIO as GPIO
            from mfrc522 import SimpleMFRC522
            GPIO.setwarnings(False)

            # initialize the reader
            reader = SimpleMFRC522()

            # set the previous id and previous read time
            prevID = None
            prevReadTime = time.time()

            # loop until everyone is present
            names = []
            while len(names) < 4:
                try:
                    ID, name = reader.read()
                    readTime = time.time()
                    elapsed = readTime - prevReadTime
                    if elapsed < 5:
                        continue
                    ID = str(ID).zfill(16)
                    name = name.strip()
                    names.append(name)

                    # play specific media
                    try:
                        lastname_firstname = name.strip(" ")[1] + name.strip(" ")[0]

                        media_path = os.path.join("..", "media-leelanaucurlingclub",
                            "announcement_enters_venue", "lastname_firstname",
                            lastname_firstname, ".mp4")

                        # todo determine length of video

                        self.load_animation(media_path, timeout=8)

                    # if error, play random media
                    except:
                        logging.WARNING("entry media not found, playing random entry media")
                        media_path = os.path.join("..", "media-leelanaucurlingclub",
                                                  "announcement_enters_venue",
                                                  "random")

                        media_path = random.choice(list_animations(media_path))

                        # todo determine length of video

                        self.load_animation(media_path, timeout=8)

                    prevReadTime = readTime
                except Exception as e:
                    print(str(e))
                    prevReadTime = 0
                    continue
            return names


        teamA_players = wait_for_four_players()
        teamB_players = wait_for_four_players()


    def input_player_rfid_USB(self, team):
        logging.info("starting to collect {} names via RFID".format(str(team)))
        self.rfid_window = PlayerRFID(team, 4)
        self.rfid_window.start()
        logging.info("finished collecting {} names via RFID".format(str(team)))
        self.rfid_window = None


    def initialize_team(self, team, teamName):
        team.change_team_name(teamName)

        return team



    def load_animation(self, gif_path, timeout=8):
        logging.info("loading animation")
        self.animation = Animation(gif_path, timeout)
        self.animation.start()
        logging.info("animation started")
        self.setFocus()
        logging.info("window focus set back to main window")


    def stop_animation(self):
        logging.info("stopping animation")
        self.animation.quit()
        self.animation = None
        logging.info("animation stopped and set to None")
        self.setFocus()
        logging.info("window focus set back to main window")

    def closeEvent(self, event) -> None:
        logging.info("close window pressed")
        result = QMessageBox.question(self,
                                            "Confirm Exit...",
                                            "Are you sure you want to exit ?",
                                            QMessageBox.Yes | QMessageBox.No)
        event.ignore()

        if result == QMessageBox.Yes:
            try:
                self.animation.quit()
            except AttributeError:
                pass
            try:
                self.rfid.quit()
            except AttributeError:
                pass
            event.accept()
        logging.info("window closed")
        logging.info("most recent {} buttons = {}".format(str(len(self.buttonHistory)), str(self.buttonHistory)))
        sys.exit()

    def play_random_animation(self, gif_dir, timeout=5):
        logging.info("playing random animation")
        animations = list_animations(gif_dir)
        if len(animations)== 0:
            return
        gif_filename = random.choice(animations)
        self.load_animation(gif_path=gif_filename, timeout=timeout)

    def play_animation(self, path, timeout=5):
        logging.info("playing animation located at {}".format(str(path)))
        gif_filename = path
        self.load_animation(gif_path=gif_filename, timeout=timeout)

    def _stop_animation(self, button):
        if self.animation is not None:
            if self._prevButton_str == button or self._prevButton == button:
                logging.info("key was pressed twice, so stopping the animation")
                self.stop_animation()
                self._prevButton_str = None
                self._prevButton = None


    def waitForRemoteButtonPressSignal(self, remote):
        if remote.lower() == "ati":
            logging.info("using ATI remote so starting a QThread worker to listen")
            """uses PyQt QThread, signals, and slots concepts"""
            # Step 1: implement a QObject with a signal `models.remote.ATI(QObject)`
            # Step 2: Create a QThread object
            self.thread = QThread()

            # Step 3: Create a worker object
            self.worker = ATI()

            self.worker.connect()

            # Step 4: Move worker to the thread
            self.worker.moveToThread(self.thread)

            # Step 5: Connect signals and slots
            self.thread.started.connect(self.worker.run)
            # finished could be when the power button is pressed
            #self.worker.finished.connect(self.thread.quit)
            #self.worker.finished.connect(self.worker.deleteLater)
            # end finished
            # call a function when there is a new unique ATI remote keypress
            self.worker.newUniqueKeyPress.connect(self.handle_ati_remote_button_press)

            # Step 6: Start the thread
            self.thread.start()

            # Step 7: Final resets
            #nothing in this case

        elif remote == "sparkfun":
            logging.info("using Sparkfun remote")
            self.enableKeyPressEventHandler = True



    def increment_end(self):
        if self.current_end >= self.NUM_ENDS:
            self.game_in_progress = False
            logging.info("game is over")
            # todo inform viewer that the game is over
            self.game_launch_steps()
            return

        logging.info("incrementing end from {} to {}".format(str(self.current_end), str(self.current_end + 1)))
        self.current_end += 1
        self.selected_card = self.current_end
        self.draw_card(self.selected_card, "blue", self.card_place_color_map[self.selected_card][0])
        self.hammer_set = False
        self.clear_hammer()
        self.teamA_num_stones = 8
        self.teamB_num_stones = 8
        self.draw_stones(self.teamA)
        self.draw_stones(self.teamB)



    def clear_hammer(self):
        logging.info("clearing the hammer (aka drawing both team logos)")
        # draw team logo A
        qImg = load_png_qImg(TEAM_A_LOGO_PATH, TEAM_LOGO_SIZE)
        draw_rgba_qimg(self.label_teamA_graphic, qImg)

        # draw team logo B
        qImg = load_png_qImg(TEAM_B_LOGO_PATH, TEAM_LOGO_SIZE)
        draw_rgba_qimg(self.label_teamB_graphic, qImg)

    # KEYPRESSES ##################################################################
    def handle_key_PWR(self):
        if not self.game_in_progress:
            self.game_launch_steps()

        # # if we're in add points mode, lock in the points
        elif self.game_in_progress:
            if self.add_points_mode:
                self.lock_in_end_score(self.teamA)
                self.lock_in_end_score(self.teamB)
                # reset mode
                self.add_points_mode = False
                self.label_sponsor_bottom_left.clear()
                self.label_sponsor_bottom_left.repaint()

            # if we're not adding points, activate add points mode
            elif not self.add_points_mode:
                self.add_points_mode = True
                # show the team graphic
                qImg = self.load_png_qImg('views/oddball_graphics/numbers.png',
                                           BOTTOM_LEFT_LOGO_WIDTH)
                self.draw_rgba_qimg(self.label_sponsor_bottom_left, qImg)

    def handle_key_A(self):
        if self.game_in_progress:
            self.teamA_num_stones -= 1
            self.draw_stones(self.teamA)
            if not self.hammer_set:
                hammer_path = os.path.join("views", "curling", "graphics", "hammer.png")
                qImg = load_png_qImg(hammer_path, width=HAMMER_WIDTH)
                draw_rgba_qimg(self.label_teamB_graphic, qImg)

                # draw team logo A
                qImg = load_png_qImg(TEAM_A_LOGO_PATH, TEAM_LOGO_SIZE)
                draw_rgba_qimg(self.label_teamA_graphic, qImg)

                self.hammer_set = True

    def handle_key_B(self):
        # must be in clock mode to edit teams
        if self.game_in_progress:
            self.teamB_num_stones -=1
            self.draw_stones(self.teamB)
            if not self.hammer_set:
                hammer_path = os.path.join("views", "curling", "graphics", "hammer.png")
                qImg = load_png_qImg(hammer_path, width=HAMMER_WIDTH)
                draw_rgba_qimg(self.label_teamA_graphic, qImg)
                # draw team logo B
                qImg = load_png_qImg(TEAM_B_LOGO_PATH, TEAM_LOGO_SIZE)
                draw_rgba_qimg(self.label_teamB_graphic, qImg)
                self.hammer_set = True
        else:
            pass

    def handle_key_C(self):
        pass

    def handle_key_RETURN(self):

        if not self.ends_chosen:
            self.ends_chosen = True
            return

        if self.game_in_progress:
            # if the card is selected, lock the card and deselect
            if self.selected_card is not None:
                if self.card_place_color_map[self.selected_card] not in self.card_start_positions:
                    logging.info("locking end card {}".format(str(self.selected_card)))
                    self.lock_card(self.selected_card)
                    self.previously_locked_card = self.selected_card
                    self.selected_card = None

            # otherwise if no card is selected, select the next card
            elif self.selected_card is None:
                if self.previously_locked_card <= self.NUM_ENDS:
                    self.selected_card = self.previously_locked_card + 1
                    logging.info("selected next card {}".format(str(self.selected_card)))


    def handle_key_UP(self):
        if self.game_in_progress:
            try:
                self.move_card_up()
            except Exception as e:
                print(str(e))
                return

    def handle_key_DOWN(self):
        if self.game_in_progress:
            self.move_card_down()

    def handle_key_LEFT(self):
        if not self.ends_chosen:
            self.select_card(self.selected_card - 1)

        else:
            if self.game_in_progress:
                self.move_card_left()

    def handle_key_RIGHT(self):
        if not self.ends_chosen:
            self.select_card(self.selected_card + 1)

        else:
            if self.game_in_progress:
                self.move_card_right()

    # END KEYPRESSES ##################################################################

    def keyPressEvent(self, event):
        logging.info("key pressed: {}".format(str(event.key())))
        self.buttonHistory.append(event.key())

        if not self.enableKeyPressEventHandler:
            logging.critical("key is not being handled")
            return

        if event.key() in self.ignore_keys:
            logging.info("key ignored!")
            return

        # play a beep
        threading.Thread(target=playsound, args=("sounds/beep/beep_padded.mp3",)).start()

        # pwr key reads as an "s"
        if event.key() == QtCore.Qt.Key_S:
            self.handle_key_PWR()
        elif event.key() == QtCore.Qt.Key_A:
            self.handle_key_A()
        elif event.key() == QtCore.Qt.Key_B:
            self.handle_key_B()
        elif event.key() == QtCore.Qt.Key_C:
            self.handle_key_C()
        # center of D pad reads as "return"
        elif event.key() == QtCore.Qt.Key_Return:
            self.handle_key_RETURN()
        elif event.key() == QtCore.Qt.Key_Up:
            self.handle_key_UP()
        elif event.key() == QtCore.Qt.Key_Down:
            self.handle_key_DOWN()
        elif event.key() == QtCore.Qt.Key_Left:
            self.handle_key_LEFT()
        elif event.key() == QtCore.Qt.Key_Right:
            self.handle_key_RIGHT()

        # set the previous button
        self._prevButton = event.key

    def other_team(self, team):
        """convenience function returns the opposite team of what is provided"""
        if team is self.teamA:
            team = self.teamB
        elif team is self.teamB:
            team = self.teamA
        return team

    def set_widget_font_foreground_color(self, widget, color):
        # create a QColor and swap BGR to RGB
        color = QColor(color[2], color[1], color[0])

        # extract the widget palette
        palette = widget.palette()

        # set the text color and palette
        palette.setColor(palette.WindowText, color)
        widget.setPalette(palette)

    # formerly load_png_qImg
    def load_png_qImg(self, pngPath, width):
        """
        load the Obie logo
        """
        # load the logo and read all channels (including alpha transparency)
        logo = cv2.imread(pngPath, cv2.IMREAD_UNCHANGED)

        # swap color channels for Qt
        logo = cv2.cvtColor(logo, cv2.COLOR_BGRA2RGBA)

        # resize to a known width maintaining aspect ratio
        logo = imutils.resize(logo, width=width)

        # extract the dimensions of the image and set the bytes per line
        height, width, channel = logo.shape
        bytesPerLine = channel * width

        # create a QImage and ensure to use the alpha transparency format
        qImg = QImage(logo.data, width, height, bytesPerLine, QImage.Format_RGBA8888)

        return qImg

    def cv2img_to_qImg(self, image, width):
        """
        converts a BGRA OpenCV image to qImage RGBA format (A is the alpha transparency
        channel
        """
        # swap color channels for Qt
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)

        # resize to a known width maintaining aspect ratio
        image = imutils.resize(image, width=width)

        # extract the dimensions of the image and set the bytes per line
        height, width, channel = image.shape
        bytesPerLine = channel * width

        # create a QImage and ensure to use the alpha transparency format
        qImg = QImage(image.data, width, height, bytesPerLine, QImage.Format_RGBA8888)

        return qImg

    def draw_rgba_qimg(self, label, qImg):
        # set the logo in the GUI
        label.setPixmap(QPixmap(qImg))
        label.repaint()

    def show_team_change_popup(self, team):
        teamText = None
        labelTeamName = None
        if team is self.teamA:
            teamText = "Team A"
            labelTeamName = self.label_teamA_name
        elif team is self.teamB:
            teamText = "Team B"
            labelTeamName = self.label_teamB_name

        # pop up a text entry dialog
        newTeamName, ok = QInputDialog.getText(self, "Team Name Change", "Enter new {} team name".format(teamText))

        # if the ok button was pressed, then change the team name
        if ok:
            team = self.initialize_team(team, newTeamName)
            labelTeamName.setText(str(team))


    def draw_stones(self, team):
        # initialize vars
        num_stones = None
        stone_graphics = None
        stone_png = None

        # set vars depending on team
        if team is self.teamA:
            num_stones = self.teamA_num_stones
            stone_graphics = [
                self.label_teamA_stone1,
                self.label_teamA_stone2,
                self.label_teamA_stone3,
                self.label_teamA_stone4,
                self.label_teamA_stone5,
                self.label_teamA_stone6,
                self.label_teamA_stone7,
                self.label_teamA_stone8
            ]
            stone_png = os.path.join("views", "curling", "graphics", "curling_stone_blue.png")
        elif team is self.teamB:
            num_stones = self.teamB_num_stones
            stone_graphics = [
                self.label_teamB_stone1,
                self.label_teamB_stone2,
                self.label_teamB_stone3,
                self.label_teamB_stone4,
                self.label_teamB_stone5,
                self.label_teamB_stone6,
                self.label_teamB_stone7,
                self.label_teamB_stone8
            ]
            stone_png = os.path.join("views", "curling", "graphics", "curling_stone_green.png")

        # logging
        logging.info("drawing {} stones for {}".format(num_stones, str(team)))

        # draw stones
        for i, stone in enumerate(stone_graphics):
            if i < num_stones:
                qImg = load_png_qImg(stone_png, width=STONE_WIDTH)
                draw_rgba_qimg(stone, qImg)
            else:
                stone.clear()
                stone.repaint()



if __name__ == '__main__':
    # initialize the app and window
    app = QtWidgets.QApplication(sys.argv)
    window = PlayerRFID(None, 1)

    # show the window and run the app
    window.show()
    app.exec_()
