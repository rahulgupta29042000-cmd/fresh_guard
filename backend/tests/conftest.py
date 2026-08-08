import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.clear()


@pytest.fixture()
def client(db_session):
    return TestClient(app)


@pytest.fixture()
def seeded(db_session):
    warehouse = models.Warehouse(name="Test Dark Store", location="Test City", capacity=40, current_load=10)
    db_session.add(warehouse)
    product1 = models.Product(
        name="Tomatoes", category="produce", weight_kg=0.15, fragility_score=45,
        temperature_sensitive=False, packaging_type="loose", historical_damage_rate=0.10,
    )
    product2 = models.Product(
        name="Glass Sauce Bottle", category="condiments", weight_kg=0.4, fragility_score=90,
        temperature_sensitive=False, packaging_type="glass", historical_damage_rate=0.15,
    )
    product3 = models.Product(
        name="Apples", category="produce", weight_kg=0.18, fragility_score=20,
        temperature_sensitive=False, packaging_type="bag", historical_damage_rate=0.04,
    )
    db_session.add_all([product1, product2, product3])
    db_session.commit()
    db_session.refresh(warehouse)
    db_session.refresh(product1)
    db_session.refresh(product2)
    db_session.refresh(product3)
    return {"warehouse": warehouse, "product1": product1, "product2": product2, "product3": product3}
