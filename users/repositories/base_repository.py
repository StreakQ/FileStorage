from abc import ABC, abstractmethod


class BaseRepository(ABC):
    @abstractmethod
    def create(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_all(self):
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, id):
        raise NotImplementedError

    @abstractmethod
    def update(self, id, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def delete(self, id):
        raise NotImplementedError

