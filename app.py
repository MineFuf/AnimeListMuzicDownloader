from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, Future
from os import path, makedirs
from threading import Event, Thread
from time import sleep
from typing import Union, List, Callable, Type, Optional
import PySimpleGUIQt as sg

from muzic_library import Library
from anime_providers import Mal, AnimeProvider
from song_providers import SongProvider, SongQuery
from song_providers.youtube import Youtube
from constants import *


# TODO: Logging manager
# TODO: Add documentation


class App:
    class DownloadProgress:
        def __init__(self, title: str, callback: Callable = None):
            self.title = title
            self.done = 0
            self.total = 0
            self.callback = callback

        def update(self, done: int, total):
            self.done = done
            self.total = total
            if self.callback:
                self.callback()

    class DownloaderThread(Thread):
        def __init__(self, progresses: List[App.DownloadProgress], canceled: Event, username: str,
                     anime_provider_type: Type[AnimeProvider],
                     song_provider_type: Type[SongProvider], library_path: str):
            super().__init__()

            self.library = None
            self.username = username

            self.anime_provider_type = anime_provider_type
            self.song_provider_type = song_provider_type

            self.anime_provider = self.anime_provider_type(self.username)
            self.song_provider = None
            self.thread_count = len(progresses)
            self.progresses = progresses
            self.canceled = canceled
            self.library_path = library_path

        def run(self):
            print(f'[I] Loading library...')
            self.library = Library(self.username, self.anime_provider.get_list_types(), self.library_path)
            print(f'[I] Loaded library')

            self.song_provider = self.song_provider_type(self.library)

            futures: List[Optional[Future]] = [None] * self.thread_count

            def find_free_future():
                while True:
                    for i, future in enumerate(futures):
                        if future is None or future.done():
                            return i
                    sleep(0.1)

            def update_progress(i: int, done: int, total: int):
                self.progresses[i].update(done, total)

            username_dir = path.join(self.library_path, self.username)

            with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
                page_num = 0
                list_type = ''

                for anime_idx, anime in enumerate(self.anime_provider.get_animes()):
                    if self.canceled.is_set():
                        print('[*] Stopping anime loop...')
                        break

                    print(f'[I] Doing anime number {anime_idx}, {anime}...')

                    if list_type != anime.list_type:
                        list_type = anime.list_type
                        print(f'[I] List type: {list_type}')
                        page_num = 1

                    if page_num < anime.page:
                        page_num = anime.page
                        print(f'[I] Page number: {page_num}')

                    types_dir = path.join(username_dir, anime.list_type)

                    makedirs(types_dir, exist_ok=True)

                    to_search = [SongQuery(anime, i + 1, False) for i in range(anime.ops)] + \
                                [SongQuery(anime, i + 1, True) for i in range(anime.eds)]

                    for song_query in to_search:
                        stream = self.song_provider.search(song_query, list_type)
                        index = find_free_future()

                        self.progresses[index].title = song_query.query

                        stream.connect_to_progressbar(index)
                        stream.set_callback(update_progress)
                        futures[index] = executor.submit(stream.download)

                print('[I] Waiting for all threads to finish...')

    def __init__(self, run_app=True):
        self.song_provider = None
        self.anime_list = None
        self.downloader_thread = None

        # set theme
        self.default_colors = None
        self.theme_name = 'DarkBrown4'
        self.set_theme(self.theme_name)

        # make progresses
        self.progresses = [[sg.Text(f'ProgBar {index}: None', key=f'-{index}_text', visible=False),
                            sg.ProgressBar(100, key=f'-{index}_progressbar', visible=False)] for index in
                           range(1, MAX_PROGRESSES + 1)]

        self.download_progresses = [App.DownloadProgress('Waiting...', None) for _ in range(MAX_PROGRESSES)]

        # make events
        self.list_of_events = ['update-progress', 'cancel-download']
        self.events_buttons = {event: sg.Button('', visible=False, key=f'--{event}--') for event in self.list_of_events}
        # self.events = {event: self.events_buttons[event].click for event in self.list_of_events}

        # make window
        self.layout = [
            [
                sg.Text('Username: ', size_px=(100, None), justification='right'),
                sg.Input('morsee31', key='username_input', enable_events=True),
                sg.Button('Check', key='username_button', size_px=(100, None))],
            [
                sg.Text('Anime Music Dir: ', size_px=(100, None), justification='right'),
                sg.Input(Library.get_default_path(), key='dir_input', disabled=True, enable_events=True),
                sg.FolderBrowse(initial_folder=Library.get_default_path(), key='dir_browse', size=(100, None))],

            [sg.Text('Thread count: ', size_px=(100, None), justification='right'),
             sg.Stretch(),
             sg.Slider(range=(1, MAX_PROGRESSES), default_value=5, key='thread_count_slider', enable_events=True,
                       size_px=(100, None), orientation='horizontal')],

            [sg.Frame('Downloads...', [[sg.Column(self.progresses, scrollable=True, size=(800, 500),
                                                  key='-progresses_column-')]], pad=(0, 0))],
            [sg.Button('Download', key='download_button'), sg.Button('Exit', key='exit_button'),
             sg.Button('Cancel downloads', key='cancel_download', visible=False)],
            list(self.events_buttons.values())
        ]
        self.window = sg.Window('ALMeD', self.layout, finalize=True)

        self.keys_to_disable_during_download = ['username_input', 'dir_browse', 'thread_count_slider',
                                                'download_button', 'exit_button']
        self.keys_to_hide_during_download = ['download_button', 'exit_button']
        self.keys_to_show_during_download = ['cancel_download']

        self.cancel_download_event: Union[Event, None] = None

        self.running = False
        if run_app:
            self.run()

    def run(self):
        self.running = True
        while self.running:
            event, values = self.window.read(100)
            if event == sg.WIN_CLOSED or event is None or event == 'exit_button':
                self.running = False
                break

            if event == 'username_button':
                self.check_username(values)

            if event == 'download_button':
                self.download(values)

            for i, progress in enumerate(self.progresses):
                progress[0].update(self.download_progresses[i].title)
                progress[1].UpdateBar(
                    self.download_progresses[i].done,
                    self.download_progresses[i].total if self.download_progresses[i].total > 0 else 1)

        self.window.close()
        del self.window

    def download(self, values):
        if not self.check_username(values):
            return

        # enable progress bars
        count_of_threads = int(values['thread_count_slider'])
        for index in range(count_of_threads):
            self.progresses[index][0](visible=True)
            self.progresses[index][1](visible=True)

        # disable elements to prevent user from changing them
        self.enable_disable_elements(self.keys_to_disable_during_download, False)
        self.enable_disable_elements(self.keys_to_hide_during_download, False, show_hide=True)
        self.enable_disable_elements(self.keys_to_show_during_download, True, show_hide=True)

        # start downloader thread
        self.cancel_download_event = Event()
        self.song_provider = Youtube
        self.downloader_thread = self.DownloaderThread(self.download_progresses[:count_of_threads],
                                                       self.cancel_download_event,
                                                       values['username_input'], Mal, self.song_provider,
                                                       values['dir_input'])
        self.downloader_thread.start()

    def enable_disable_elements(self, elements: List[str], enable=True, show_hide: bool = False):
        for key in elements:
            if show_hide:
                self.window[key](visible=enable)
            else:
                self.window[key](disabled=not enable)
        if len(elements) > 0 and show_hide:
            self.window.VisibilityChanged()
            print(f'[I] Visibility changed')

    def set_theme(self, theme_name: str):
        print(f'[I] Setting theme to: {theme_name}')
        self.theme_name = theme_name
        sg.theme(self.theme_name)
        self.default_colors = sg.LOOK_AND_FEEL_TABLE[self.theme_name].copy()

    def check_username(self, values):
        exists = Mal.check_username(values["username_input"])
        if exists:
            self.window['username_input'].update(background_color=self.default_colors['INPUT'])
            print('[I] Username exists')
        else:
            self.window['username_input'].update(background_color='#FF7777')
            print('[I] Username doesn\'t exists')
        return exists
