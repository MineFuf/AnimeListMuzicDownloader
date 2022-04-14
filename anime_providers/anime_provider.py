from __future__ import annotations

from abc import abstractmethod
from typing import Iterator, List


class Anime:
    def __init__(self, id: int, title: str, list_type: str, page: int, ops: int, eds: int, provider: AnimeProvider):
        self.id = id
        self.title = title
        self.list_type = list_type
        self.page = page
        self.ops = ops
        self.eds = eds
        self.provider = type(provider).get_provider_name()

    def __str__(self):
        return f"{self.title} ({self.provider}-{self.id}) (ops:{self.ops},eds:{self.eds})"


class AnimeProvider:
    @staticmethod
    @abstractmethod
    def check_username(user: str) -> bool:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_list_types() -> List[str]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def get_provider_name() -> str:
        raise NotImplementedError()
    
    def __init__(self, user: str):
        self.user = user

    @abstractmethod
    def get_animes(self) -> Iterator[Anime]:
        raise NotImplementedError()
