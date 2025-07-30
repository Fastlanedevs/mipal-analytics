from abc import ABC, abstractmethod


class IDatabaseConnection(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def sync_db_schema(self) -> None:
        pass
