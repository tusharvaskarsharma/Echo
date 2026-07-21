from app.db.client import get_db
from app.services.finetune_builder import FinetuneBuilderService


async def _retrain_persona_async(subject_id: str):
    """Core async business logic — callable directly in development mode."""
    async for conn in get_db():
        service = FinetuneBuilderService(conn)
        try:
            await service.build_and_submit(subject_id)
            print(f"Successfully launched fine-tuning job for {subject_id}")
        except ValueError as e:
            # Eligibility failed, totally normal.
            print(f"Skipping finetune for {subject_id}: {e}")
        except Exception as e:
            print(f"Finetune error for {subject_id}: {e}")
        break


async def retrain_persona(subject_id: str) -> None:
    await _retrain_persona_async(subject_id)
