from abc import ABC, abstractmethod

from collections.abc import Iterable

from sqlmodel import Session, SQLModel, func, select

from typing import Generic, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
S = TypeVar("S", bound=SQLModel)
ID = TypeVar("ID")


class Repository(ABC, Generic[T, ID]):
    """
    Abstract generic base class for all repository implementations.

    This class defines the fundamental methods for working with entities of a specific domain type and their identifiers.
    It serves as a template for concrete repositories that may implement various persistence mechanisms.

    :ivar model: the ``BaseModel`` class.
    """

    def __init__(self, model: Type[T]):
        self.model = model

    @abstractmethod
    def save(self, entity: T) -> T:
        """
        Saves a given entity.

        If the entity already exists in the persistence store, it will be updated; otherwise, it will be inserted.

        Use the returned instance for further operations as the save operation might have changed the entity instance completely.

        :param entity: must not be ``None``.
        :returns: the saved entity; will never be ``None``.
        :raises ValueError: in case the given entity is ``None``.
        """
        pass

    @abstractmethod
    def save_all(self, entities: Iterable[T]) -> Iterable[T]:
        """
        Saves all given entities.

        :param entities: must not be ``None`` nor must it contain ``None``.
        :returns: the saved entities; will never be ``None``. The returned ``Iterable`` will have the same size as the ``Iterable`` passed as an argument.
        :raises ValueError: in case the given entities or one of its elements is ``None``.
        """
        pass

    @abstractmethod
    def find_all(self) -> Iterable[T]:
        """
        Returns all entities.

        :returns: all entities.
        """
        pass

    @abstractmethod
    def find_by_id(self, entity_id: ID) -> T | None:
        """
        Retrieves an entity by its ID.

        :param entity_id: must not be ``None``.
        :returns: the entity with the given ID or ``None`` if none found.
        :raises ValueError: in case the given ID is ``None``.
        """
        pass

    @abstractmethod
    def find_all_by_id(self, entity_ids: Iterable[ID]) -> Iterable[T]:
        """
        Returns all entities with the given IDs.

        If some or all IDs are not found, no entities are returned for these IDs.
        Note that the order of elements in the result is not guaranteed.

        :param entity_ids: must not be ``None`` nor must it contain any ``None`` values.
        :returns: guaranteed to be not ``None``. The size can be equal or less than the number of given IDs.
        :raises ValueError: in case the given IDs or one of its elements is ``None``.
        """
        pass

    @abstractmethod
    def exists_by_id(self, entity_id: ID) -> bool:
        """
        Returns whether an entity with the given ID exists.

        :param entity_id: must not be ``None``.
        :returns: ``True`` if an entity with the given id exists, ``False`` otherwise.
        :raises ValueError: in case the given ID is ``None``.
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        Returns the number of entities available.

        :returns: the number of entities.
        """
        pass

    @abstractmethod
    def delete(self, entity: T) -> None:
        """
        Deletes a given entity.

        If the entity is not found in the persistence store it is silently ignored.

        :param entity: must not be ``None``.
        :raises ValueError: in case the given entity is ``None``.
        """
        pass

    @abstractmethod
    def delete_all(self, entities: Iterable[T]) -> None:
        """
        Deletes the given entities.

        :param entities: must not be ``None``. Must not contain ``None`` elements.
        :raises ValueError: in case the given entities or one of its elements is ``None``.
        """
        pass

    @abstractmethod
    def delete_by_id(self, entity_id: ID) -> None:
        """
        Deletes the entity with the given ID.

        If the entity is not found in the persistence store it is silently ignored.

        :param entity_id: must not be ``None``.
        :raises ValueError: in case the given ID is ``None``.
        """
        pass

    @abstractmethod
    def delete_all_by_id(self, entity_ids: Iterable[ID]) -> None:
        """
        Deletes all entities with the given IDs.

        Entities that aren't found in the persistence store are silently ignored.

        :param entity_ids: must not be ``None``. Must not contain ``None`` elements.
        :raises ValueError: in case the given IDs or one of its elements is ``None``.
        """
        pass


class CrudRepository(Repository[S, ID]):
    """
    Generic CRUD operations for SQLModel entities.

    :ivar model: the ``SQLModel`` class.
    :ivar session: the database session.
    """

    def __init__(self, model: Type[S], session: Session):
        super().__init__(model)
        self.session = session

    def __get_pk_column(self):
        """
        Function to retrieve the primary key column of the model.
        This is used to ensure that the primary key is always accessed correctly, independent of the model's structure.

        :return: the primary key column of the model.
        """

        return list(self.model.__table__.primary_key.columns)[0]

    def save(self, entity: S) -> S:
        """
        Saves a given entity.

        If the entity already exists in the persistence store, it will be updated; otherwise, it will be inserted.

        Use the returned instance for further operations as the save operation might have changed the entity instance completely.

        :param entity: must not be ``None``.
        :returns: the saved entity; will never be ``None``.
        :raises ValueError: in case the given entity is ``None``.
        """

        if entity is None:
            raise ValueError("The entity must not be ``None``.")

        db_entity = self.session.get(
            self.model, getattr(entity, self.__get_pk_column().name)
        )
        if db_entity:
            self.session.expunge(db_entity)

        merged_entity = self.session.merge(entity)
        self.session.commit()
        self.session.refresh(merged_entity)

        return merged_entity

    def save_all(self, entities: Iterable[S]) -> Iterable[S]:
        """
        Saves all given entities.

        :param entities: must not be ``None`` nor must it contain ``None``.
        :returns: the saved entities; will never be ``None``. The returned ``Iterable`` will have the same size as the ``Iterable`` passed as an argument.
        :raises ValueError: in case the given entities or one of its elements is ``None``.
        """

        if entities is None:
            raise ValueError("The entities must not be ``None``.")

        if any(entity is None for entity in entities):
            raise ValueError("The entities must not contain ``None`` elements.")

        for entity in entities:
            self.save(entity)

        return entities

    def find_all(self) -> Iterable[S]:
        """
        Returns all entities.

        :returns: all entities.
        """

        query = select(self.model)
        entities = self.session.exec(query).all()

        return entities

    def find_by_id(self, entity_id: ID) -> S | None:
        """
        Retrieves an entity by its ID.

        :param entity_id: must not be ``None``.
        :returns: the entity with the given ID or ``None`` if none found.
        :raises ValueError: in case the given ID is ``None``.
        """

        if entity_id is None:
            raise ValueError("The ID must not be ``None``.")

        entity: S | None = self.session.get(self.model, entity_id)

        return entity

    def find_all_by_id(self, entity_ids: Iterable[ID]) -> Iterable[S]:
        """
        Returns all entities with the given IDs.

        If some or all IDs are not found, no entities are returned for these IDs.
        Note that the order of elements in the result is not guaranteed.

        :param entity_ids: must not be ``None`` nor must it contain any ``None`` values.
        :returns: guaranteed to be not ``None``. The size can be equal or less than the number of given IDs.
        :raises ValueError: in case the given IDs or one of its elements is ``None``.
        """

        if entity_ids is None:
            raise ValueError("The IDs must not be ``None``.")

        if any(entity_id is None for entity_id in entity_ids):
            raise ValueError("The IDs must not contain ``None`` elements.")

        query = select(self.model).where(self.__get_pk_column().in_(entity_ids))
        entities = self.session.exec(query).all()

        return entities

    def exists_by_id(self, entity_id: ID) -> bool:
        """
        Returns whether an entity with the given ID exists.

        :param entity_id: must not be ``None``.
        :returns: ``True`` if an entity with the given id exists, ``False`` otherwise.
        :raises ValueError: in case the given ID is ``None``.
        """

        if entity_id is None:
            raise ValueError("The ID must not be ``None``.")

        entity: S | None = self.find_by_id(entity_id)

        return entity is not None

    def count(self) -> int:
        """
        Returns the number of entities available.

        :returns: the number of entities.
        """

        query = select(func.count()).select_from(self.model)
        count = self.session.exec(query).one()

        return count

    def delete(self, entity: S) -> None:
        """
        Deletes a given entity.

        If the entity is not found in the persistence store it is silently ignored.

        :param entity: must not be ``None``.
        :raises ValueError: in case the given entity is ``None``.
        """

        if entity is None:
            raise ValueError("The entity must not be ``None``.")

        entity_id = getattr(entity, self.__get_pk_column().name)
        if not self.exists_by_id(entity_id):
            return

        self.session.delete(entity)
        self.session.commit()

    def delete_all(self, entities: Iterable[S]) -> None:
        """
        Deletes the given entities.

        :param entities: must not be ``None``. Must not contain ``None`` elements.
        :raises ValueError: in case the given entities or one of its elements is ``None``.
        """

        if entities is None:
            raise ValueError("The entities must not be ``None``.")

        if any(entity is None for entity in entities):
            raise ValueError("The entities must not contain ``None`` elements.")

        for entity in entities:
            self.delete(entity)

    def delete_by_id(self, entity_id: ID) -> None:
        """
        Deletes the entity with the given ID.

        If the entity is not found in the persistence store it is silently ignored.

        :param entity_id: must not be ``None``.
        :raises ValueError: in case the given ID is ``None``.
        """

        if entity_id is None:
            raise ValueError("The ID must not be ``None``.")

        entity: S | None = self.find_by_id(entity_id)

        if entity:
            self.delete(entity)

    def delete_all_by_id(self, entity_ids: Iterable[ID]) -> None:
        """
        Deletes all entities with the given IDs.

        Entities that aren't found in the persistence store are silently ignored.

        :param entity_ids: must not be ``None``. Must not contain ``None`` elements.
        :raises ValueError: in case the given IDs or one of its elements is ``None``.
        """

        if entity_ids is None:
            raise ValueError("The IDs must not be ``None``.")

        if any(entity_id is None for entity_id in entity_ids):
            raise ValueError("The IDs must not contain ``None`` elements.")

        for entity_id in entity_ids:
            self.delete_by_id(entity_id)
