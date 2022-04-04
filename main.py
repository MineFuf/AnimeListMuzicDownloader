import os
import PySimpleGUIQt as sg

from os import path
from time import sleep
from termcolor import cprint
from typing import Tuple
from threading import Thread, Event
from pathvalidate import sanitize_filename
import youtubesearchpython as yt
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import wait

import muzic_library as ml
from anime_lists import AnimeList, Mal
import song_thread as st

should_update_progress = True


def progress_callback(window):
    def _callback():
        global should_update_progress
        if should_update_progress:
            window['--PROGRESS_UPDATE--'].click()
            should_update_progress = False

    return _callback


def run2(window: sg.Window, username: str, list_provider: type, thread_count: int,
         dir=ml.get_default_dir()) -> Tuple[Event, Thread]:
    library_thread = Thread(target=ml.init_library, args=(dir,))
    library_thread.start()
    print('[I] Library thread started')

    stopped = Event()
    run_thread = Thread(target=run_2, args=(window, username, stopped, list_provider, thread_count))

    library_thread.join()
    print('[I] Library thread joined')

    print('[I] Running download thread')
    run_thread.start()

    return stopped, run_thread


def run_2(window: sg.Window, username: str, stopped: Event, list_provider: type, thread_count: int):
    st.init(thread_count=thread_count)

    mal: AnimeList = list_provider(username)
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        page_num = 1
        list_type = ''

        for anime_idx, anime in enumerate(mal.get_animes()):
            if stopped.is_set():
                print('[*] Stopping anime loop')
                break

            print('[I] Doing anime number ' + str(anime_idx + 1))

            types_dir = path.join(username, anime.list_type)
            absolute_types_dir = path.join(ml.library_dir, types_dir)

            os.makedirs(types_dir, exist_ok=True)

            if list_type != anime.list_type:
                list_type = anime.list_type
                print(f'[I] List type: {list_type}')
                page_num = 1

            if page_num < anime.page:
                page_num = anime.page
                print(f'[I] Page number: {page_num}')

            to_search = [f'{anime.title} op {i + 1}' for i in range(anime.ops)] + \
                        [f'{anime.title} ed {i + 1}' for i in range(anime.eds)]

            already_downloaded_in_anime = []
            for idx_video, request in enumerate(to_search):
                if stopped.is_set():
                    print('[*] Stopping video loop')
                    break

                filename_ = f'{request} ({str(anime.id)})'
                filename_ = str(sanitize_filename(filename_))
                filename_old = filename_
                filepath_ = path.join(types_dir, filename_)

                if filename_ in ml.songs_already_downloaded:
                    print(f'[I] File "{filename_old}" already downloaded')
                    _username, _type, _id = ml.songs_already_downloaded[filename_]
                    filename_ = f'{filename_} - {_id}.mp3'

                    full_filename_ = path.join(types_dir, filename_)
                    if username != _username:
                        cprint(
                            f'[*] Copying file "{path.join(_username, _type, filename_)}" to "{full_filename_}"',
                            'yellow')
                        ml.copy(username, list_type, filename_)
                    else:
                        if _type != list_type:
                            cprint(
                                f'[*] Moving file "{path.join(_username, _type, filename_)}" to "{full_filename_}"',
                                'yellow')
                            ml.move(username, list_type, filename_)

                search_res_list: dict = yt.CustomSearch(request, yt.VideoDurationFilter.short, limit=1).result()['result']
                if type(search_res_list) != list or len(search_res_list) == 0:
                    print(f'[*] Video ({request}) wasn\'t found, skipping')
                    continue

                search_res = search_res_list[0]

                response, video_title, video_id = search_res['link'], search_res['title'], search_res['id']

                if response in already_downloaded_in_anime:
                    if response in already_downloaded_in_anime:
                        cprint(f'[*] Video "{response}" already downloaded, skipping', 'yellow')
                        continue

                already_downloaded_in_anime.append(response)

                while not st.can_be_added() and not stopped.is_set():
                    sleep(0.1)

                if stopped.is_set():
                    print('[*] Stopping video loop')
                    break

                free_index = st.find_free()

                filename = f'{request} ({str(anime.id)}) - {video_id}.mp3'
                filename = str(sanitize_filename(filename))
                filepath = path.join(types_dir, filename)

                print(f'[I] Downloading {request}')
                song_thread = st.SongDownloadThread(response, filepath, request)
                future = executor.submit(song_thread.run, progress_callback(window), free_index)
                st.add_thread(song_thread, future)
                sleep(0.001)

        if not stopped.is_set():
            print('[I] Prepared all downloads, waiting for them')

        all_stopped = False
        while len(wait([th[0] for th in st.threads if th is not None], timeout=0.1)[1]) > 0:
            # print('[I] Waiting for finish')
            if stopped.is_set() and not all_stopped:
                print('[I] Stopping running threads')
                for song_thread in st.threads:
                    if song_thread is not None:
                        if hasattr(song_thread[1], 'cancel'):
                            song_thread[1].cancel()
                all_stopped = True

    cprint('[I] All downloads ended', 'green')

    window['--DOWNLOAD_STOP--'].click()

    print('[I] ST Deinit')
    st.deinit()


def main():
    global should_update_progress

    # set program theme
    # theme_name = 'DarkPurple4'
    theme_name = 'DarkBrown4'
    sg.theme(theme_name)

    os.system('color')
    #
    # define default values for UI

    MAX_PROGRESSES = 50

    # create progress bars and their labels
    progresses = [(sg.Text(f'ProgBar {key}: None', key=f'-{key}_text', visible=False),
                   sg.ProgressBar(100, key=f'-{key}_progressbar', visible=False)) for key in
                  range(1, MAX_PROGRESSES + 1)]
    # make layout
    layout = [
        [
            sg.Text('Username: '),
            sg.Input('', key='username_input', enable_events=True),
            sg.Button('Check', key='username_button')],
        [
            sg.Text('Anime Music Dir: '),
            sg.Input(ml.library_dir, key='dir_input', disabled=True, enable_events=True),
            sg.FolderBrowse(initial_folder=ml.get_default_dir(), key='dir_browse')],

        [sg.Text('Thread count: '),
         sg.Combo(list(range(1, MAX_PROGRESSES + 1)), default_value=1, key='thread_count_combo', enable_events=True)],
        [sg.Column(progresses, scrollable=True, key='progresses_column', size=(700, 600))],
        [sg.Button('Download', key='download_button'), sg.Button('Exit', key='exit_button')],
        [sg.Button('', visible=False, key='--PROGRESS_UPDATE--'), sg.Button('', visible=False, key='--DOWNLOAD_STOP--')]
    ]

    to_disable = ['username_input', 'username_button', 'dir_input',
                  'dir_browse', 'thread_count_combo']

    # make window
    window = sg.Window("MalMuzic", layout, finalize=True, resizable=False, disable_close=True)

    # set default values to UI
    layout[2][0].update(value=True)

    # set more variables
    input_default_color = sg.LOOK_AND_FEEL_TABLE[theme_name]['INPUT']
    run_thread_running = False
    run_thread: Tuple[Event, Thread] = None  # type: ignore
    to_close = False

    # helper function for main
    def check_username():
        exists = Mal.check_username(values["username_input"])
        print('[I] Username exists' if exists else '[I] Username doesn\'t exists')
        if not exists:
            window['username_input'].update(background_color='#FF7777')
        else:
            window['username_input'].update(background_color=input_default_color)
        return exists

    def cancel_request():
        resp = sg.PopupOKCancel('Are you sure you want to cancel download?', keep_on_top=True)
        return resp != 'Cancel'

    # UI loop
    while not to_close:
        event, values = window.read()  # type: ignore
        if event == sg.WIN_CLOSED or event is None:
            if cancel_request():
                to_close = True
                if run_thread is not None:
                    run_thread[0].set()
                    # print('[I] stopped is set')
                continue
        # print('[I]', event, values[event] if event in values else '')
        if event == 'username_button':
            check_username()
        if event == 'download_button':
            if not run_thread_running:
                print('[I] Checking username')
                if not check_username():
                    continue

                ml.library_dir = values['dir_input']

                print('[I] ml.library: ' + str(ml.library_dir))

                window['download_button']('Cancel download')
                for dis in to_disable:
                    window[dis](disabled=True)

                window['exit_button'](visible=False)
                window.VisibilityChanged()

                for i in range(len(progresses)):
                    progresses[i][0].update(visible=False)
                    progresses[i][1].update(visible=False)

                print('[I] Updating visibility')
                for i in range(values['thread_count_combo']):
                    progresses[i][0].update(visible=True)
                    progresses[i][1].update(visible=True)

                run_thread = run2(window, values["username_input"], Mal, values['thread_count_combo'], ml.library_dir)
                run_thread_running = True
            else:
                cprint('[E] Download already running', 'yellow')
                if cancel_request():
                    run_thread[0].set()
        if event == 'thread_count_combo':
            print(f'[I] User choose {values[event]} threads to run async')
        if event == '--PROGRESS_UPDATE--':
            for i, thread in enumerate(st.threads):
                if run_thread_running and thread is not None:
                    if hasattr(thread[1], 'percent'):
                        progresses[i][1].UpdateBar(thread[1].percent)
                    if hasattr(thread[1], 'total_kb') and hasattr(thread[1], 'rate'):
                        progresses[i][0].update(value=thread[1].request + ': ' + str(thread[1].total_kb) + 'kB, ' + str(
                            round(thread[1].rate, 1)) + 'kB/s')

            should_update_progress = True
        if event == '--DOWNLOAD_STOP--' and run_thread_running:
            run_thread_running = False
            run_thread = None  # type: ignore

            print('[I] Download thread stopped')

            window['exit_button'](visible=True)
            window['download_button']('Download')
            for dis in to_disable:
                window[dis](disabled=False)
            for i, prog in enumerate(progresses):
                prog[0].update(f'ProgBar {i + 1}: None')
                prog[0].update(visible=False)
                prog[1].UpdateBar(0)
                prog[1].update(visible=False)
                st.init(0)

            window.VisibilityChanged()
        if event == 'exit_button':
            to_close = True
    if run_thread is not None:
        print('[I] Download thread still running, joining with it.')
        run_thread[1].join()

    window.close()
    print('[!] Exiting program')


# run program
if __name__ == '__main__':
    main()
