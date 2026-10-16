import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config.settings import settings
from database.models import Base, EmailMessage, Sender, CustomRule, CaseTicket, WorkflowDefinition
from database.repository import Repository
from backend.email_client.mock_client import MockEmailClient
from ai.analyzer import EmailAnalyzer
from backend.services.decision_engine import DecisionEngine
from backend.services.rule_engine import RuleEngine
from backend.services.dispatcher import EmailDispatcher
from backend.services.workflow_engine import WorkflowEngine

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
    assert len(emails) >= 12
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

@pytest.mark.asyncio
async def test_clinical_email_analysis_and_folder_assignment():
    """Tests AI extraction of patient info, doc, and thematic folder routing."""
    analyzer = EmailAnalyzer()
    res = await analyzer.process_email(
        sender_name="Dra. Sofía Herrera",
        sender_email="urgencias@centromedico.org",
        subject="Solicitud Ingreso Paciente: Juan David Gómez - CC 10203040",
        body="Buenas tardes, remitimos solicitud de ingreso para procedimiento de colecistectomía.",
        attachments=[{
            "filename": "orden.pdf",
            "content_text": "ORDEN MÉDICA DE INGRESO HOSPITALARIO\nPaciente: Juan David Gómez\nDocumento: CC 10203040"
        }]
    )
    assert res["target_folder"] == "Ingreso Pacientes"
    assert res["workflow_topic"] == "Ingreso de Pacientes"
    assert res["patient_name"] == "Juan David Gómez"
    assert "10203040" in res["patient_id_doc"]
    assert res["workflow_action"] == "NUEVO_CASO"
    assert res["requires_human_review"] == True
    assert res["can_auto_reply"] == False

@pytest.mark.asyncio
async def test_workflow_intake_and_step1_dispatch(test_db):
    """Tests incoming clinical email triggers case creation and forwards to Step 1 (Admisiones)."""
    client = MockEmailClient()
    dispatcher = EmailDispatcher(client)

    clinical_raw = {
        "id": "msg_patient_test",
        "thread_id": "thread_pt_001",
        "sender_email": "urgencias@clinica.com",
        "sender_name": "Dra. Sofía Herrera",
        "subject": "Solicitud Ingreso Paciente: Juan David Gómez - CC 10203040",
        "body": "Remitimos solicitud formal de ingreso del paciente Juan David Gómez identificado con CC 10203040.",
        "attachments": []
    }

    res = await dispatcher.process_incoming_email(clinical_raw, test_db)
    assert "case_code" in res
    assert res["target_folder"] == "Ingreso Pacientes"

    # Verify folder move
    assert "msg_patient_test" in client.folders_assigned
    assert client.folders_assigned["msg_patient_test"] == "Ingreso Pacientes"

    # Verify forward to Step 1 user (Admisiones)
    assert len(client.forwarded_emails) >= 1
    fw = client.forwarded_emails[0]
    assert fw["to"] == "admisiones@clinica.com"
    assert res["case_code"] in fw["subject"]

@pytest.mark.asyncio
async def test_sequential_approval_cycle_and_supervisor_completion(test_db):
    """Tests full sequential chain: Admisiones -> Auditoría Médica -> Camas -> Supervisor (Dossier Final)."""
    client = MockEmailClient()
    engine = WorkflowEngine(client)

    # 1. Create initial case
    wf_list = await Repository.get_or_create_default_workflows(test_db)
    wf_ingreso = wf_list[0]

    case = await Repository.create_case(test_db, {
        "workflow_id": wf_ingreso.id,
        "thread_id": "thread_full_cycle",
        "patient_name": "Pedro Nel Gómez",
        "patient_id_doc": "CC 708090",
        "subject": "Ingreso Hospitalario Pedro Nel Gómez",
        "target_folder": "Ingreso Pacientes",
        "current_step_number": 1,
        "current_step_name": "Admisiones",
        "current_assigned_email": "admisiones@clinica.com",
        "supervisor_email": "coordinacion@clinica.com"
    })
    assert case.current_step_number == 1
    assert case.status == "EN_PROCESO"

    # 2. Step 1 (Admisiones) approves -> moves to Step 2 (Auditoría Médica)
    case = await engine.advance_step(test_db, case, actor_email="admisiones@clinica.com", comments="Documentos en orden")
    assert case.current_step_number == 2
    assert case.current_step_name == "Auditoría Médica"
    assert case.current_assigned_email == "auditoria@clinica.com"
    assert case.total_transitions == 2

    # 3. Step 2 (Auditoría) approves -> moves to Step 3 (Asignación de Camas)
    case = await engine.advance_step(test_db, case, actor_email="auditoria@clinica.com", comments="Cobertura EPS verificada")
    assert case.current_step_number == 3
    assert case.current_step_name == "Asignación de Camas"
    assert case.current_assigned_email == "camas@clinica.com"
    assert case.total_transitions == 3

    # 4. Step 3 (Camas) approves -> Culminates and sends dossier to Supervisor
    case = await engine.advance_step(test_db, case, actor_email="camas@clinica.com", comments="Cama 304 asignada")
    assert case.status == "COMPLETADO"
    assert case.completed_at is not None
    assert case.total_transitions == 4

    # Verify dossier email was sent to Supervisor
    sent_to_supervisor = [m for m in client.sent_emails if m["to"] == "coordinacion@clinica.com"]
    assert len(sent_to_supervisor) >= 1
    assert "PROCESO COMPLETADO" in sent_to_supervisor[0]["subject"]
    assert case.case_code in sent_to_supervisor[0]["subject"]

@pytest.mark.asyncio
async def test_rejection_problem_reporting_and_supervisor_alert(test_db):
    """Tests when a user reports a problem: status becomes DETENIDO_PROBLEMA and sends immediate alert to Supervisor."""
    client = MockEmailClient()
    engine = WorkflowEngine(client)

    wf_list = await Repository.get_or_create_default_workflows(test_db)
    wf_ingreso = wf_list[0]

    case = await Repository.create_case(test_db, {
        "workflow_id": wf_ingreso.id,
        "thread_id": "thread_problem_test",
        "patient_name": "María Eugenia Ramos",
        "patient_id_doc": "CC 52100200",
        "subject": "Ingreso Hospitalario María Eugenia Ramos",
        "target_folder": "Ingreso Pacientes",
        "current_step_number": 3,
        "current_step_name": "Asignación de Camas",
        "current_assigned_email": "camas@clinica.com",
        "supervisor_email": "coordinacion@clinica.com"
    })

    # Camas user reports: No beds available
    updated_case = await engine.report_problem(
        db=test_db,
        case=case,
        actor_email="camas@clinica.com",
        reason="No hay camas disponibles en medicina interna ni cuidados intermedios",
        bottleneck_category="Sin disponibilidad de camas"
    )

    assert updated_case.status == "DETENIDO_PROBLEMA"
    assert updated_case.total_returns == 1
    assert updated_case.bottleneck_reason == "Sin disponibilidad de camas"
    assert "No hay camas" in updated_case.last_problem_reported

    # Verify immediate alert sent to Supervisor
    alert_emails = [m for m in client.sent_emails if m["to"] == "coordinacion@clinica.com"]
    assert len(alert_emails) >= 1
    alert = alert_emails[-1]
    assert "ALERTA DETENCIÓN - REQUERIDO CORRECTIVO" in alert["subject"]
    assert updated_case.case_code in alert["subject"]
    assert "No hay camas disponibles" in alert["body"]

@pytest.mark.asyncio
async def test_bottleneck_report_metrics(test_db):
    """Tests bottleneck analytics calculation."""
    report = await Repository.get_bottleneck_report(test_db)
    assert "total_cases" in report
    assert "stopped_cases" in report
    assert "completed_cases" in report
    assert "total_returns" in report
    assert "bottlenecks_by_reason" in report
    assert "delayed_cases" in report

