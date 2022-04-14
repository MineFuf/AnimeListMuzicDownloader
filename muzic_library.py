from __future__ import annotations
import os
import shutil
# TODO: use pathlib instead of os.path
from os import path
from typing import List, Union, Literal, Dict, Tuple, Optional
import re

from constants import *


# file name example:
class SongFile:
    _filename_regex = re.compile(r'(?P<anime>.+) (?P<themetype>op|ed) (?P<themeindex>\d+) \(('
                                 r'?P<animeprovider>\w{3})-(?P<animeid>\d+)\) - (?P<songprovider>\w{2})-('
                                 r'?P<songid>[a-zA-Z0-9_-]+)\.mp3')

    class InvalidFileSongName(Exception):
        def __init__(self, filename: str):
            super().__init__(f"Invalid song file: {filename}")

    class InvalidMP3File(Exception):
        def __init__(self, filename: str):
            super().__init__(f"Invalid MPEG file: {filename}")

    # noinspection PyTypeChecker
    def __init__(self, library: Library, username: str, list_type: str, filename: str, temp: bool = False):
        self.file_path: str = None
        self.local_path: str = None
        if temp:
            self.temp_file_path: str = None

        if (match := self._filename_regex.fullmatch(filename)) is None:
            raise self.InvalidFileSongName(filename)

        self.library = library
        self.library_path = library.path
        self.username = username
        self.type = list_type
        self.filename = filename

        self.temp = temp
        self.deleted = False

        self.anime_title: str = match.group('anime')
        self.theme_type: Union[Literal['op'], Literal['ed']] = match.group('themetype')
        self.theme_index: int = int(match.group('themeindex'))
        self.anime_provider_id: Literal['MAL'] = match.group('animeprovider')
        self.anime_id: int = int(match.group('animeid'))
        self.song_provider: Literal['YT'] = match.group('songprovider')
        self.song_id: str = match.group('songid')

        self.update_path()

    def update_path(self):
        self.local_path = path.join(self.username, self.type, self.filename)
        self.file_path = path.join(self.library_path, self.local_path)
        if self.temp:
            self.temp_file_path = path.join(self.library_path, TEMP_DIR_NAME, self.local_path)

    def untemp(self):
        if not self.temp:
            return

        self.temp = False
        shutil.move(self.temp_file_path, self.file_path)
        del self.temp_file_path

    def move(self, new_type: str, new_user: str = None):
        if self.temp:
            self.untemp()

        if not new_user:
            new_user = self.username

        # Move the file
        shutil.move(self.file_path, path.join(self.library_path, new_user, new_type, self.filename))

        # Update the object
        self.username = new_user
        self.type = new_type
        self.update_path()

    def copy(self, new_user: str, new_type: str) -> SongFile:
        if self.temp:
            self.untemp()

        shutil.copy2(self.file_path, path.join(self.library_path, new_user, new_type, self.filename))
        return SongFile(self.library, new_user, new_type, self.filename)

    def delete(self):
        filepath = self.get_real_filepath()

        os.remove(filepath)

    def get_real_filepath(self) -> str:
        if self.temp:
            return self.temp_file_path
        return self.file_path

    def __hash__(self):
        return hash(self.file_path)

    def __eq__(self, other):
        return self.file_path == other.file_path

    def __str__(self) -> str:
        return self.local_path

    def __repr__(self) -> str:
        return str(self)


class Library:
    @staticmethod
    def get_default_path():
        # return path.join(path.expanduser(path.normpath("~/Music")), DEFAULT_LIBRARY_NAME)
        # TODO: change to real path, not temporary
        return path.abspath(DEFAULT_LIBRARY_NAME)

    def __init__(self, mainuser: str, types: List[str], library_path: str = None):
        self.user = mainuser
        self.types = types

        self.downloaded_songs: Dict[str, SongFile] = {}
        self.downloaded_ids: Dict[Tuple[str, str], SongFile] = {}

        self.path = Library.get_default_path() if library_path is None else library_path
        os.makedirs(self.path, exist_ok=True)
        self.user_dir = path.join(self.path, self.user)
        self.temp_dir = self.get_temp_dir()
        self.temp_user_dir = path.join(self.temp_dir, self.user)

        # delete temp folder
        self.clean_temp()

        self.users: List[str] = []
        for user in os.scandir(self.path):
            user: os.DirEntry
            if user.name == TEMP_DIR_NAME or not user.is_dir():
                continue
            self.users.append(user.name)
            for listtype in self.types:
                listpath = path.join(user.path, listtype)
                if path.isdir(listpath):
                    for song in os.scandir(listpath):
                        song: os.DirEntry
                        if song.name.endswith('.mp3'):
                            song_file = SongFile(self, user.name, listtype, song.name)
                            self.downloaded_songs[song.name] = song_file
                            self.downloaded_ids[(song_file.song_provider, song_file.song_id)] = song_file

    def get_temp_dir(self, type_dir: Optional[str] = None) -> str:
        temp_dir = path.join(self.path, TEMP_DIR_NAME)
        return path.join(temp_dir, self.user, type_dir) if type_dir else temp_dir

    def clean_temp(self):
        if path.isdir(self.get_temp_dir()):
            shutil.rmtree(self.get_temp_dir())

    def make_type_list_folder(self, type_name: str, temp: bool = False):
        if type_name not in self.types:
            raise ValueError(f"{type_name} is not a valid type")
        os.makedirs(path.join(self.user_dir, type_name), exist_ok=True)
