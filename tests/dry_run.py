import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import json
from database.db import init_db, AsyncSessionLocal
from database.repository import Repository
from backend.email_client.mock_client import MockEmailClient
from backend.services.dispatcher import EmailDispatcher

async def main():
    print("==================================================================")
    print("AGENTE AUTONOMO DE GESTION INTELIGENTE DE CORREOS - DRY RUN")
    print("==================================================================")
    
    await init_db()
    client = MockEmailClient()
    dispatcher = EmailDispatcher(client)
    
    emails = await client.fetch_unprocessed_emails(max_results=20)
    print(f"\n[INFO] Leyendo {len(emails)} correos de prueba...")
    
    async with AsyncSessionLocal() as db:
        for idx, email in enumerate(emails, start=1):
            res = await dispatcher.process_incoming_email(email, db)
            status_text = "[RESPONDIDO AUTOMATICO]" if res['status'] == 'RESPONDIDO_IA' else "[REVISION HUMANA REQUERIDA]" if res['requires_human_review'] else "[IGNORADO / SPAM]"
            print(f"\n[{idx}/{len(emails)}] Asunto: '{res['subject']}'")
            print(f"   De: {res['sender_name']} <{res['sender_email']}> ({res['company']})")
            print(f"   Categoria: {res['category']} | Prioridad: {res['priority']} | Confianza: {res['confidence']}%")
            print(f"   Riesgo: {res['risk_level']} | Etiquetas: {res['tags']}")
            print(f"   Accion: {status_text}")
            if res.get('sent_reply'):
                first_line = res['sent_reply'].splitlines()[0] if res['sent_reply'] else ""
                print(f"   Respuesta Enviada: {first_line}")
                
        metrics = await Repository.get_dashboard_metrics(db)
        print("\n==================================================================")
        print("METRICAS DEL DASHBOARD DE CONTROL:")
        print(json.dumps(metrics, indent=2))
        print("==================================================================")

if __name__ == "__main__":
    asyncio.run(main())
