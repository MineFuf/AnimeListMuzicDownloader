from os import makedirs
from typing import Callable
import youtubesearchpython as yt
import pytube as ptb

from muzic_library import Library, SongFile
from .song_provider import SongProvider, SongQuery, SongDownload, SongNotFound, StreamNotFound
from helpers import retry


class YoutubeSongDownload(SongDownload):
    @staticmethod
    def get_provider_name() -> str:
        return 'YT'

    def __init__(self, query: SongQuery, url, video_id, library: Library, type_dir: str,
                 on_progress: Callable[[int, int, int], None] = None):
        super().__init__()
        self.query = query
        self.url = url
        self.id = video_id
        self.library = library
        self.type_dir = type_dir

        self.set_callback(on_progress)

        self.filesize = 0
        self.video = ptb.YouTube(self.url, on_progress_callback=lambda _0, _1, remaining: self.on_progress(
            self.progressbar_idx, self.filesize - remaining, self.filesize) if self.on_progress else None,
                                 on_complete_callback=lambda _1, _2: self.on_progress(self.progressbar_idx,
                                                                                      self.filesize, self.filesize))

    def download(self):
        if self.on_progress and self.progressbar_idx is None:
            raise RuntimeError('Progressbar not connected')

        stream = self.video.streams.get_audio_only()
        self.filesize = stream.filesize

        if self.on_progress:
            self.on_progress(self.progressbar_idx, 0, self.filesize)

        if not stream:
            raise StreamNotFound(self.query)

        print(f'[I] Downloading {self.query}...')
        download_dir = self.library.get_temp_dir(self.type_dir)
        makedirs(download_dir, exist_ok=True)
        stream.download(download_dir, filename=self.get_filename())

        # print(f'[I] Downloaded {self.query}')

        song_file = SongFile(self.library, self.library.user, self.type_dir, self.get_filename(), True)
        song_file.untemp()

        print(f'[I] File {song_file.local_path} saved')

        # TODO: Add song to library
        # print('[I] Adding to library...')
        # self.library.add_song(song_file)
        # print('[I] Added to library')

    def get_id(self) -> str:
        return self.id

    def get_query(self):
        return self.query


class Youtube(SongProvider):
    def __init__(self, library: Library):
        super().__init__(library)

    def search(self, query: SongQuery, type_dir: str) -> SongDownload:
        results: list = retry(
            lambda: yt.CustomSearch(query.query, yt.VideoDurationFilter.short, limit=1).result()['result'],
            lambda _: True, )
        if type(results) is not list or len(results) == 0:
            print(f'[E] No results for {query}')
            raise SongNotFound(query)

        url, title, video_id = results[0]['link'], results[0]['title'], results[0]['id']

        return YoutubeSongDownload(query, url, video_id, self.library, type_dir)
