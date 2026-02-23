"""
Rotas de A/B Testing
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging

from backend.core.database import get_db
from backend.services.ab_testing_service import ABTestingService

router = APIRouter()
logger = logging.getLogger(__name__)


class VariantCreate(BaseModel):
    """Variante para criar"""
    id: Optional[str] = None
    name: str
    prompt: str
    traffic_percentage: int


class ABTestCreate(BaseModel):
    """Request para criar teste A/B"""
    name: str
    description: Optional[str] = None
    variants: List[VariantCreate]
    success_metric: str = "conversion_rate"
    min_sample_size: int = 100
    confidence_level: float = 0.95


class ABTestUpdate(BaseModel):
    """Request para atualizar teste A/B"""
    name: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[List[VariantCreate]] = None
    success_metric: Optional[str] = None
    min_sample_size: Optional[int] = None


@router.get("/{slug}/ab-tests")
async def list_ab_tests(
    slug: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista todos os testes A/B do cliente"""
    try:
        tests = await ABTestingService.list_tests(
            db=db,
            client_slug=slug,
            status=status
        )
        return {"tests": tests}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slug}/ab-tests")
async def create_ab_test(
    slug: str,
    request: ABTestCreate,
    db: AsyncSession = Depends(get_db)
):
    """Cria novo teste A/B"""
    try:
        variants = [v.dict() for v in request.variants]

        test = await ABTestingService.create_test(
            db=db,
            client_slug=slug,
            name=request.name,
            description=request.description,
            variants=variants,
            success_metric=request.success_metric,
            min_sample_size=request.min_sample_size,
            confidence_level=request.confidence_level
        )

        return {
            "success": True,
            "test": test.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/ab-tests/{test_id}")
async def get_ab_test(
    slug: str,
    test_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retorna detalhes de um teste A/B"""
    try:
        stats = await ABTestingService.calculate_statistics(db, test_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slug}/ab-tests/{test_id}/start")
async def start_ab_test(
    slug: str,
    test_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Inicia um teste A/B"""
    try:
        test = await ABTestingService.start_test(db, test_id)
        return {
            "success": True,
            "message": "Teste iniciado com sucesso",
            "test": test.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slug}/ab-tests/{test_id}/pause")
async def pause_ab_test(
    slug: str,
    test_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Pausa um teste A/B"""
    try:
        test = await ABTestingService.pause_test(db, test_id)
        return {
            "success": True,
            "message": "Teste pausado",
            "test": test.to_dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slug}/ab-tests/{test_id}/stop")
async def stop_ab_test(
    slug: str,
    test_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Encerra um teste A/B e determina vencedor"""
    try:
        test = await ABTestingService.stop_test(db, test_id)
        stats = await ABTestingService.calculate_statistics(db, test_id)

        return {
            "success": True,
            "message": "Teste encerrado",
            "test": test.to_dict(),
            "statistics": stats
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{slug}/ab-tests/{test_id}")
async def delete_ab_test(
    slug: str,
    test_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Deleta um teste A/B"""
    from sqlalchemy import select, delete
    from backend.models.ab_test import ABTest, ABTestResult

    try:
        # Verificar se existe
        result = await db.execute(select(ABTest).where(ABTest.id == test_id))
        test = result.scalar_one_or_none()

        if not test:
            raise HTTPException(status_code=404, detail="Teste nao encontrado")

        # Deletar resultados primeiro
        await db.execute(
            delete(ABTestResult).where(ABTestResult.test_id == test_id)
        )

        # Deletar teste
        await db.delete(test)
        await db.commit()

        return {
            "success": True,
            "message": "Teste deletado com sucesso"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/ab-tests/active/variant")
async def get_active_variant(
    slug: str,
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retorna variante para uma conversa especifica"""
    try:
        variant = await ABTestingService.get_variant_for_conversation(
            db=db,
            client_slug=slug,
            conversation_id=conversation_id
        )

        if not variant:
            return {
                "has_active_test": False,
                "variant": None
            }

        return {
            "has_active_test": True,
            "variant": variant
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
