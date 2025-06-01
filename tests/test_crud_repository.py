from fastapi_lib.patterns.repository import CrudRepository

import pytest

from sqlmodel import Field, Session, SQLModel, create_engine, select


class Model(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def repository(session):
    return CrudRepository[Model, int](model=Model, session=session)


@pytest.fixture
def entity():
    return Model(id=1, name="Entity")


@pytest.fixture
def entities():
    return [
        Model(id=1, name="Entity 1"),
        Model(id=2, name="Entity 2"),
        Model(id=3, name="Entity 3"),
    ]


def test_save(session, repository, entity):
    result: Model = repository.save(entity)

    assert result == entity

    db_entity = session.get(Model, entity.id)
    assert db_entity == entity


def test_save_duplicate(session, repository, entity):
    session.add(entity)
    session.commit()
    session.refresh(entity)

    duplicate = entity.model_copy(update={"name": "Updated Entity"})

    repository.save(duplicate)

    db_entity = session.get(Model, duplicate.id)
    assert db_entity.name == "Updated Entity"


def test_save_none(repository):
    with pytest.raises(ValueError):
        repository.save(None)  # type: ignore


def test_save_all(session, repository, entities):
    result = repository.save_all(entities)

    assert result == entities

    query = select(Model)
    db_entities = session.exec(query).all()
    assert db_entities == entities


def test_save_all_empty_list(repository):
    result = repository.save_all([])
    assert result == []


def test_save_all_none(repository):
    with pytest.raises(ValueError):
        repository.save_all(None)  # type: ignore


def test_save_all_with_none(repository, entities):
    entities.append(None)  # type: ignore

    with pytest.raises(ValueError):
        repository.save_all(entities)


def test_find_all(session, repository, entities):
    for entity in entities:
        session.add(entity)
        session.commit()
        session.refresh(entity)

    result = repository.find_all()

    assert result == entities


def test_find_all_not_found(repository):
    result = repository.find_all()

    assert result == []


def test_find_by_id(session, repository, entity):
    session.add(entity)
    session.commit()
    session.refresh(entity)

    result = repository.find_by_id(entity.id)

    assert result == entity


def test_find_by_id_not_found(repository, entity):
    result = repository.find_by_id(entity.id)

    assert result is None


def test_find_by_id_none(repository):
    with pytest.raises(ValueError):
        repository.find_by_id(None)  # type: ignore


def test_find_all_by_id(session, repository, entities):
    for entity in entities:
        session.add(entity)
        session.commit()
        session.refresh(entity)

    result = repository.find_all_by_id([entity.id for entity in entities])

    assert result == entities


def test_find_all_by_id_not_found(repository, entities):
    result = repository.find_all_by_id([entity.id for entity in entities])

    assert result == []


def test_find_all_by_id_empty_list(repository):
    result = repository.find_all_by_id([])
    assert result == []


def test_find_all_by_id_none(repository):
    with pytest.raises(ValueError):
        repository.find_all_by_id(None)  # type: ignore


def test_find_all_by_id_with_none(repository, entities):
    entity_ids = [entity.id for entity in entities] + [None]

    with pytest.raises(ValueError):
        repository.find_all_by_id(entity_ids)


def test_exists_by_id(session, repository, entity):
    session.add(entity)
    session.commit()
    session.refresh(entity)

    result = repository.exists_by_id(entity.id)

    assert result is True


def test_exists_by_id_not_found(repository, entity):
    result = repository.exists_by_id(entity.id)

    assert result is False


def test_exists_by_id_none(repository):
    with pytest.raises(ValueError):
        repository.exists_by_id(None)  # type: ignore


def test_count(session, repository, entities):
    for entity in entities:
        session.add(entity)
        session.commit()
        session.refresh(entity)

    result = repository.count()

    assert result == len(entities)


def test_count_empty(repository):
    result = repository.count()

    assert result == 0


def test_delete(session, repository, entity):
    session.add(entity)
    session.commit()
    session.refresh(entity)

    assert repository.delete(entity) is None

    db_entity = session.get(Model, entity.id)
    assert db_entity is None


def test_delete_not_found(repository, entity):
    assert repository.delete(entity) is None


def test_delete_none(repository):
    with pytest.raises(ValueError):
        repository.delete(None)  # type: ignore


def test_delete_all_entities(session, repository, entities):
    for entity in entities:
        session.add(entity)
        session.commit()
        session.refresh(entity)

    assert repository.delete_all(entities) is None

    for entity in entities:
        db_entity = session.get(Model, entity.id)
        assert db_entity is None


def test_delete_all_not_found(repository, entities):
    assert repository.delete_all(entities) is None


def test_delete_all_empty_list(repository):
    assert repository.delete_all([]) is None


def test_delete_all_none(repository):
    with pytest.raises(ValueError):
        repository.delete_all(None)  # type: ignore


def test_delete_all_with_none(repository, entities):
    entities.append(None)  # type: ignore

    with pytest.raises(ValueError):
        repository.delete_all(entities)


def test_delete_by_id(session, repository, entity):
    session.add(entity)
    session.commit()
    session.refresh(entity)

    assert repository.delete_by_id(entity.id) is None

    db_entity = session.get(Model, entity.id)
    assert db_entity is None


def test_delete_by_id_not_found(repository, entity):
    assert repository.delete_by_id(entity.id) is None


def test_delete_by_id_none(repository):
    with pytest.raises(ValueError):
        repository.delete_by_id(None)  # type: ignore


def test_delete_all_by_id(session, repository, entities):
    for entity in entities:
        session.add(entity)
        session.commit()
        session.refresh(entity)

    assert repository.delete_all_by_id([entity.id for entity in entities]) is None

    for entity in entities:
        db_entity = session.get(Model, entity.id)
        assert db_entity is None


def test_delete_all_by_id_not_found(repository, entities):
    assert repository.delete_all_by_id([entity.id for entity in entities]) is None


def test_delete_by_id_empty_list(repository):
    assert repository.delete_all([]) is None


def test_delete_all_by_id_none(repository):
    with pytest.raises(ValueError):
        repository.delete_all_by_id(None)  # type: ignore


def test_delete_all_by_id_with_none(repository, entities):
    entity_ids = [entity.id for entity in entities] + [None]

    with pytest.raises(ValueError):
        repository.delete_all_by_id(entity_ids)
