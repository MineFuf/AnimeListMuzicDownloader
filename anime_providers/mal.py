from typing import Iterator, List
from .anime_provider import AnimeProvider, Anime
from requests import get
from json import loads
from helpers import retry


class Mal(AnimeProvider):
    @staticmethod
    def check_username(user: str) -> bool:
        page = retry(
            get,
            lambda e: e.response.status_code == 404,
            0, 0.2,
            f"https://api.myanimelist.net/v2/users/{user}/animelist?limit=1",
            headers={"X-MAL-CLIENT-ID": "788e9404debd2b5f32516de1a4bab8a9"},
        )

        return bool(page)

    @staticmethod
    def get_list_types() -> List[str]:
        return ['watching', 'completed', 'on_hold', 'dropped', 'plan_to_watch']

    @staticmethod
    def get_provider_name() -> str:
        return 'MAL'

    def get_animes(self) -> Iterator[Anime]:
        statuses = Mal.get_list_types()
        for status in statuses:
            url = f"https://api.myanimelist.net/v2/users/{self.user}/animelist?status={status}&limit=1000"

            get_page = lambda: retry(
                get,
                lambda e: e.response.status_code == 404,
                0,
                0.1,
                url,
                headers={"X-MAL-CLIENT-ID": "788e9404debd2b5f32516de1a4bab8a9"},
            )

            page_number = 1
            print('[I] Getting page 1')
            while page := loads(get_page().content):
                anime_list = page["data"]
                for json_anime in anime_list:
                    mal_id = json_anime["node"]["id"]
                    details_url = f"https://api.myanimelist.net/v2/anime/{mal_id}?fields=opening_themes,ending_themes"

                    details = loads(retry(
                        get,
                        lambda e: e.response.status_code == 404,
                        0,
                        0.2,
                        details_url,
                        headers={"X-MAL-CLIENT-ID": "788e9404debd2b5f32516de1a4bab8a9"},
                    ).content)

                    anime = Anime(
                        mal_id,
                        json_anime["node"]["title"],
                        status,
                        page_number,
                        len(details["opening_themes"]) if 'opening_themes' in details else 0,
                        len(details["ending_themes"]) if 'ending_themes' in details else 0,
                        self,
                    )
                    yield anime

                if 'next' in page['paging']:
                    page_number += 1
                    url = page["paging"]["next"]
                    # print(f'[I] Getting page {page_number}')
                else:
                    break
