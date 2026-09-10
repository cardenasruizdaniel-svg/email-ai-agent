import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config.settings import settings
from database.models import Base, EmailMessage, Sender, CustomRule
from database.repository import Repository
from backend.email_client.mock_client import MockEmailClient
from ai.analyzer import EmailAnalyzer
from backend.services.decision_engine import DecisionEngine
from backend.services.rule_engine import RuleEngine
from backend.services.dispatcher import EmailDispatcher

# In-memory test SQLite DB
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        
    await engine.dispose()

@pytest.mark.asyncio
async def test_mock_email_client_fetching():
    client = MockEmailClient()
    emails = await client.fetch_unprocessed_emails(max_results=20)
    assert len(emails) == 12
    assert emails[0]["id"] == "msg_001"
    assert "Consulta" in emails[0]["subject"]

@pytest.mark.asyncio
async def test_ai_analyzer_scenarios():
    analyzer = EmailAnalyzer()
    
    # Test 1: Simple Info Inquiry
    info_res = await analyzer.process_email(
        sender_name="Carlos", sender_email="carlos@test.com",
        subject="Horarios", body="Quisiera conocer el horario de atención al cliente."
    )
    assert info_res["category"] == "INFORMACION"
    assert info_res["confidence"] >= 95.0
    assert info_res["can_auto_reply"] == True

    # Test 2: High-Risk Financial Urgent Email
    risk_res = await analyzer.process_email(
        sender_name="Roberto", sender_email="roberto@finanzas.com",
        subject="URGENTE: Cambio de cuenta bancaria",
        body="Por favor enviar datos bancarios para transferencia de $10,000 USD antes de las 5 PM."
    )
    assert risk_res["risk_level"] == "ALTO"
    assert risk_res["requires_human_review"] == True
    assert risk_res["can_auto_reply"] == False

    # Test 3: Spam Detection
    spam_res = await analyzer.process_email(
        sender_name="Spammer", sender_email="spam@promo.com",
        subject="¡Gana un viaje gratis!", body="Haga clic aquí para reclamar su premio gratis."
    )
    assert spam_res["category"] == "SPAM"
    assert spam_res["can_auto_reply"] == False

@pytest.mark.asyncio
async def test_decision_engine_supervised_mode_override():
    analysis = {
        "category": "RESPUESTA_SIMPLE",
        "priority": "BAJA",
        "confidence": 99.0,
        "risk_level": "BAJO",
        "can_auto_reply": True,
        "requires_human_review": False,
        "tags": ["Respuesta automática"]
    }
    
    # Save orig mode
    orig_mode = settings.OPERATIONAL_MODE
    settings.OPERATIONAL_MODE = "supervised"
    
    evaluated = DecisionEngine.evaluate(analysis)
    assert evaluated["can_auto_reply"] == False
    assert evaluated["requires_human_review"] == True
    assert "Revisión humana" in evaluated["tags"]
    
    # Restore
    settings.OPERATIONAL_MODE = orig_mode

@pytest.mark.asyncio
async def test_rule_engine_matching():
    rules = [
        CustomRule(
            id=1,
            name="VIP Sender Rule",
            condition_type="SENDER_EMAIL",
            condition_value="banca-capital.com",
            action_priority="CRITICA",
            action_label="Cliente VIP",
            is_active=True
        )
    ]
    email_data = {
        "id": "msg_test",
        "sender_email": "pedro@banca-capital.com",
        "subject": "Hola",
        "body": "Test message",
        "tags": []
    }
    overrides = RuleEngine.evaluate_rules(email_data, rules)
    assert overrides["priority"] == "CRITICA"
    assert "Cliente VIP" in overrides["tags"]

@pytest.mark.asyncio
async def test_full_pipeline_execution(test_db):
    client = MockEmailClient()
    dispatcher = EmailDispatcher(client)
    
    unprocessed = await client.fetch_unprocessed_emails(max_results=12)
    
    processed_count = 0
    for raw_msg in unprocessed:
        res = await dispatcher.process_incoming_email(raw_msg, test_db)
        assert "id" in res
        assert "category" in res
        processed_count += 1
        
    assert processed_count == 12
    
    # Verify DB Metrics
    metrics = await Repository.get_dashboard_metrics(test_db)
    assert metrics["total_received"] == 12
    assert metrics["auto_replied"] > 0
    assert metrics["pending_review"] > 0
