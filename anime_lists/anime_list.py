from typing import Iterator


class Anime:
    def __init__(self, title: str, list_type: str, page: int):
        self.title = title
        self.list_type = list_type
        self.page = page


class AnimeList:
    @staticmethod
    def check_username(user: str) -> bool:
        raise NotImplementedError()
    
    def __init__(self, user: str):
        self.user = user

    def get_animes(self) -> Iterator[Anime]:
        raise NotImplementedError()
