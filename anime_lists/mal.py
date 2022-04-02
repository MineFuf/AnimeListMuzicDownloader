from typing import Iterator
from .anime_list import AnimeList, Anime
from requests import get
from json import loads
from helpers import retry


class Mal(AnimeList):
    @staticmethod
    def check_username(user: str) -> bool:
        page = retry(
            get,
            lambda e: e.response.status_code == 404,
            0,
            f'https://api.myanimelist.net/v2/users/{user}/animelist?limit=1',
            headers={"X-MAL-CLIENT-ID": "788e9404debd2b5f32516de1a4bab8a9"},
        )
        
        return bool(page)

    def get_animes(self) -> Iterator[Anime]:
        statuses = ["watching", "completed", "on_hold", "dropped", "plan_to_watch"]
        for status in statuses:
            url = f"https://api.myanimelist.net/v2/animelist/{self.user}?status={status}&limit=1000"

            get_page = lambda: retry(
                get,
                lambda e: e.response.status_code == 404,
                0,
                url,
                headers={"X-MAL-CLIENT-ID": "788e9404debd2b5f32516de1a4bab8a9"},
            )

            page_number = 1
            while page := loads(get_page().content):
                anime_list = page["data"]
                for json_anime in anime_list:
                    anime = Anime(json_anime["node"]["title"], status, page_number)
                    yield anime

                if page["paging"].has_key("next"):
                    page_number += 1
                    url = page["paging"]["next"]
                else:
                    break
