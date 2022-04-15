from abc import abstractmethod
from typing import Callable

from pathvalidate import sanitize_filename

from muzic_library import Library
from anime_providers import Anime


class SongQuery:
    def __init__(self, anime: Anime, song_idx: int, is_ending: bool):
        self.anime = anime
        self.song_idx = song_idx
        self.is_ending = is_ending
        self.query = f'{self.anime.title} {"ed" if self.is_ending else "op"} {song_idx}'

    def __str__(self):
        return self.query

    def __repr__(self):
        return str(self)


class SongNotFound(Exception):
    def __init__(self, query: SongQuery):
        super().__init__(f'Song not found: {query.query}')


class StreamNotFound(Exception):
    def __init__(self, query: SongQuery):
        super().__init__(f'Stream not found: {query.query}')


class SongDownload:
    @staticmethod
    def get_provider_name() -> str:
        raise NotImplementedError()

    @abstractmethod
    def __init__(self):
        self.on_progress = None
        self.progressbar_idx = None

    def get_filename(self) -> str:
        query = self.get_query()
        
        return sanitize_filename(f'{query.anime.title} {"ed" if query.is_ending else "op"} '
                                 f'{query.song_idx} ({query.anime.provider}-'
                                 f'{query.anime.id}) - {type(self).get_provider_name()}-{self.get_id()}.mp3')

    @abstractmethod
    def get_query(self) -> SongQuery:
        raise NotImplementedError()

    @abstractmethod
    def get_id(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def download(self):
        raise NotImplementedError()

    # @abstractmethod
    def set_callback(self, callback: Callable[[int, int, int], None]):
        self.on_progress = callback

    # @abstractmethod
    def connect_to_progressbar(self, progressbar_idx: int) -> None:
        self.progressbar_idx = progressbar_idx


class SongProvider:
    @abstractmethod
    def __init__(self, library: Library):
        self.library = library

    @abstractmethod
    def search(self, query: SongQuery, type_dir: str) -> SongDownload:
        pass
