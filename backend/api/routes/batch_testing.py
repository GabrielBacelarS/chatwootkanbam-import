"""
Rotas da API para testes em lote de agentes IA
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from backend.core.database import get_db, AsyncSessionLocal
from backend.core.config import settings
from backend.models import Client, AIConfig, Product, ProductSchema
from backend.models.ai_test_case import AITestCase, DEFAULT_TEST_TEMPLATES
from backend.models.ai_test_run import AITestRun, AITestResult
from backend.services.batch_testing_service import BatchTestingService
from backend.services.test_generator_service import TestGeneratorService
from backend.services.conversation_simulator_service import ConversationSimulatorService
from backend.services import MinioService

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== Pydantic Models =====

class TestCaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    input_message: str
    expected_tools: Optional[List[str]] = []
    expected_keywords: Optional[List[str]] = []
    should_not_contain: Optional[List[str]] = []
    weight_tools: int = 10
    weight_keywords: int = 10
    weight_no_errors: int = 10
    weight_quality: int = 5


class TestCaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    input_message: Optional[str] = None
    expected_tools: Optional[List[str]] = None
    expected_keywords: Optional[List[str]] = None
    should_not_contain: Optional[List[str]] = None
    weight_tools: Optional[int] = None
    weight_keywords: Optional[int] = None
    weight_no_errors: Optional[int] = None
    weight_quality: Optional[int] = None
    is_active: Optional[bool] = None


class BatchRunConfig(BaseModel):
    test_case_ids: Optional[List[int]] = None  # None = todos ativos
    concurrent_tests: int = 10  # 10, 15 ou 20
    category_filter: Optional[str] = None


class GenerateTestsConfig(BaseModel):
    num_tests: int = 10  # Quantidade de testes a gerar
    save_tests: bool = True  # Se True, salva os testes gerados


class ConversationTestConfig(BaseModel):
    num_conversations: int = 5  # Quantas conversas simular
    turns_per_conversation: int = 5  # Turnos por conversa (cliente -> agente)
    client_profile: Optional[str] = None  # Perfil do cliente (aleatorio se None)


# ===== Helpers =====

async def get_client_or_404(slug: str, db: AsyncSession) -> Client:
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return client


async def get_ai_config_or_404(slug: str, db: AsyncSession) -> AIConfig:
    result = await db.execute(select(AIConfig).where(AIConfig.client_slug == slug))
    ai_config = result.scalar_one_or_none()
    if not ai_config:
        raise HTTPException(status_code=404, detail="Configuracao de IA nao encontrada")
    if not ai_config.api_key:
        raise HTTPException(status_code=400, detail="API key nao configurada")
    return ai_config


async def get_products_with_urls(slug: str, db: AsyncSession) -> List[dict]:
    """Busca produtos e gera URLs de imagens"""
    result = await db.execute(
        select(Product).where(Product.client_slug == slug, Product.is_available == True)
    )
    products = result.scalars().all()

    minio = MinioService(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        public_endpoint=settings.minio_public_endpoint
    )

    products_list = []
    for p in products:
        product_dict = p.to_dict()
        product_dict["embedding"] = p.embedding
        if p.main_image:
            try:
                product_dict["main_image_url"] = minio.get_presigned_url(p.main_image)
            except Exception:
                pass
        products_list.append(product_dict)

    return products_list


# ===== Test Case CRUD =====

@router.get("/{slug}/batch-tests/cases")
async def list_test_cases(
    slug: str,
    category: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Lista todos os casos de teste do cliente"""
    await get_client_or_404(slug, db)

    query = select(AITestCase).where(AITestCase.client_slug == slug)

    if category:
        query = query.where(AITestCase.category == category)
    if active_only:
        query = query.where(AITestCase.is_active == True)

    query = query.order_by(AITestCase.category, AITestCase.name)

    result = await db.execute(query)
    test_cases = result.scalars().all()

    return [tc.to_dict() for tc in test_cases]


@router.get("/{slug}/batch-tests/cases/{case_id}")
async def get_test_case(
    slug: str,
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtem um caso de teste especifico"""
    result = await db.execute(
        select(AITestCase).where(
            AITestCase.id == case_id,
            AITestCase.client_slug == slug
        )
    )
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Caso de teste nao encontrado")

    return test_case.to_dict()


@router.post("/{slug}/batch-tests/cases")
async def create_test_case(
    slug: str,
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Cria um novo caso de teste"""
    await get_client_or_404(slug, db)

    test_case = AITestCase(
        client_slug=slug,
        **data.model_dump()
    )

    db.add(test_case)
    await db.commit()
    await db.refresh(test_case)

    logger.info(f"[{slug}] Caso de teste criado: {test_case.name}")

    return test_case.to_dict()


@router.put("/{slug}/batch-tests/cases/{case_id}")
async def update_test_case(
    slug: str,
    case_id: int,
    data: TestCaseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Atualiza um caso de teste"""
    result = await db.execute(
        select(AITestCase).where(
            AITestCase.id == case_id,
            AITestCase.client_slug == slug
        )
    )
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Caso de teste nao encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(test_case, field, value)

    await db.commit()
    await db.refresh(test_case)

    return test_case.to_dict()


@router.delete("/{slug}/batch-tests/cases/{case_id}")
async def delete_test_case(
    slug: str,
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove um caso de teste"""
    result = await db.execute(
        select(AITestCase).where(
            AITestCase.id == case_id,
            AITestCase.client_slug == slug
        )
    )
    test_case = result.scalar_one_or_none()

    if not test_case:
        raise HTTPException(status_code=404, detail="Caso de teste nao encontrado")

    await db.delete(test_case)
    await db.commit()

    return {"message": "Caso de teste removido"}


@router.post("/{slug}/batch-tests/cases/seed")
async def seed_test_templates(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Cria casos de teste padrao baseado em templates"""
    await get_client_or_404(slug, db)

    # Verificar se ja existem casos
    result = await db.execute(
        select(AITestCase).where(AITestCase.client_slug == slug)
    )
    existing = result.scalars().all()

    if existing:
        return {
            "message": f"Ja existem {len(existing)} casos de teste",
            "created": 0
        }

    # Criar templates padrao
    created = 0
    for template in DEFAULT_TEST_TEMPLATES:
        test_case = AITestCase(
            client_slug=slug,
            name=template["name"],
            description=template.get("description"),
            category=template.get("category"),
            input_message=template["input_message"],
            expected_tools=template.get("expected_tools", []),
            expected_keywords=template.get("expected_keywords", []),
            should_not_contain=template.get("should_not_contain", [])
        )
        db.add(test_case)
        created += 1

    await db.commit()

    logger.info(f"[{slug}] {created} casos de teste criados a partir de templates")

    return {"message": f"{created} casos de teste criados", "created": created}


@router.post("/{slug}/batch-tests/cases/generate")
async def generate_test_cases(
    slug: str,
    config: GenerateTestsConfig,
    db: AsyncSession = Depends(get_db)
):
    """
    Gera casos de teste AUTOMATICAMENTE baseado nos produtos e prompt do cliente.
    Usa IA para criar perguntas realistas simulando um cliente.
    """
    # Obter configuracao de IA
    ai_config = await get_ai_config_or_404(slug, db)

    # Buscar produtos
    products = await get_products_with_urls(slug, db)

    if not products:
        raise HTTPException(400, "Cadastre produtos antes de gerar testes automaticos")

    logger.info(f"[{slug}] Gerando {config.num_tests} casos de teste automaticos...")

    try:
        # Gerar testes usando IA
        generated_tests = await TestGeneratorService.generate_tests(
            api_key=ai_config.api_key,
            model=ai_config.model,
            system_prompt=ai_config.system_prompt,
            products=products,
            enabled_tools=ai_config.enabled_tools,
            num_tests=config.num_tests
        )

        if not generated_tests:
            raise HTTPException(500, "Nao foi possivel gerar casos de teste")

        saved_tests = []

        if config.save_tests:
            # Salvar testes gerados no banco
            for test_data in generated_tests:
                test_case = AITestCase(
                    client_slug=slug,
                    name=test_data.get("name", "Teste gerado"),
                    description=test_data.get("description"),
                    category=test_data.get("category", "other"),
                    input_message=test_data.get("input_message", ""),
                    expected_tools=test_data.get("expected_tools", []),
                    expected_keywords=test_data.get("expected_keywords", []),
                    should_not_contain=test_data.get("should_not_contain", [])
                )
                db.add(test_case)
                saved_tests.append(test_data)

            await db.commit()

            logger.info(f"[{slug}] {len(saved_tests)} casos de teste gerados e salvos")

            return {
                "message": f"{len(saved_tests)} casos de teste gerados com sucesso!",
                "generated": len(saved_tests),
                "test_cases": saved_tests
            }
        else:
            # Apenas retorna preview sem salvar
            return {
                "message": "Preview dos testes gerados (nao salvos)",
                "generated": len(generated_tests),
                "test_cases": generated_tests
            }

    except Exception as e:
        logger.error(f"[{slug}] Erro ao gerar testes: {e}", exc_info=True)
        raise HTTPException(500, f"Erro ao gerar testes: {str(e)}")


# ===== Conversation Simulation =====

@router.post("/{slug}/batch-tests/conversation")
async def run_conversation_test(
    slug: str,
    config: ConversationTestConfig,
    db: AsyncSession = Depends(get_db)
):
    """
    Simula conversas COMPLETAS entre um cliente virtual e o agente.
    Cada conversa tem multiplos turnos (cliente -> agente -> cliente -> ...).
    """
    # Obter configuracao de IA
    ai_config = await get_ai_config_or_404(slug, db)

    # Buscar produtos
    products = await get_products_with_urls(slug, db)

    if not products:
        raise HTTPException(400, "Cadastre produtos antes de simular conversas")

    # Buscar schema
    client = await get_client_or_404(slug, db)
    schema = None
    if client.product_schema_id:
        result = await db.execute(
            select(ProductSchema).where(ProductSchema.id == client.product_schema_id)
        )
        schema_obj = result.scalar_one_or_none()
        if schema_obj:
            schema = {"fields": schema_obj.fields or []}

    # Perfil do cliente
    client_profile = None
    if config.client_profile:
        for profile in ConversationSimulatorService.CLIENT_PROFILES:
            if profile["name"].lower() == config.client_profile.lower():
                client_profile = profile
                break

    logger.info(
        f"[{slug}] Iniciando {config.num_conversations} simulacoes de conversa "
        f"({config.turns_per_conversation} turnos cada)"
    )

    conversations = []
    total_tools = []

    for i in range(config.num_conversations):
        try:
            logger.info(f"[{slug}] Conversa {i + 1}/{config.num_conversations}")

            result = await ConversationSimulatorService.run_conversation(
                api_key=ai_config.api_key,
                model=ai_config.model,
                system_prompt=ai_config.system_prompt,
                products=products,
                enabled_tools=ai_config.enabled_tools,
                client_slug=slug,
                num_turns=config.turns_per_conversation,
                client_profile=client_profile,
                schema=schema,
                product_keywords=ai_config.product_keywords
            )

            conversations.append({
                "conversation_id": i + 1,
                **result
            })

            total_tools.extend(result.get("tools_used", []))

        except Exception as e:
            logger.error(f"[{slug}] Erro na conversa {i + 1}: {e}")
            conversations.append({
                "conversation_id": i + 1,
                "error": str(e)
            })

    # Resumo
    successful = [c for c in conversations if "error" not in c]
    unique_tools = list(set(total_tools))

    # Calcular metricas agregadas
    scores = [c.get("evaluation", {}).get("score", 0) for c in successful if c.get("evaluation")]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Contagem por status
    passed = len([c for c in successful if c.get("evaluation", {}).get("status") == "success"])
    warning = len([c for c in successful if c.get("evaluation", {}).get("status") == "warning"])
    failed = len([c for c in successful if c.get("evaluation", {}).get("status") == "error"])
    errors = len([c for c in conversations if "error" in c])

    # Breakdown medio
    avg_breakdown = {"tools": 0, "quality": 0, "flow": 0, "goal": 0}
    if successful:
        for key in avg_breakdown:
            values = [c.get("evaluation", {}).get("breakdown", {}).get(key, 0) for c in successful]
            avg_breakdown[key] = round(sum(values) / len(values), 1) if values else 0

    # Issues mais comuns
    all_issues = []
    for c in successful:
        all_issues.extend(c.get("evaluation", {}).get("issues", []))
    issue_counts = {}
    for issue in all_issues:
        issue_counts[issue] = issue_counts.get(issue, 0) + 1
    top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "message": f"{len(successful)}/{config.num_conversations} conversas simuladas com sucesso",
        "total_conversations": config.num_conversations,
        "successful": len(successful),
        "turns_per_conversation": config.turns_per_conversation,
        "tools_used": unique_tools,
        "conversations": conversations,
        # Metricas agregadas
        "metrics": {
            "average_score": round(avg_score, 1),
            "passed": passed,
            "warning": warning,
            "failed": failed,
            "errors": errors,
            "pass_rate": round((passed / len(successful) * 100) if successful else 0, 1),
            "breakdown": avg_breakdown,
            "top_issues": [{"issue": issue, "count": count} for issue, count in top_issues]
        }
    }


@router.get("/{slug}/batch-tests/client-profiles")
async def list_client_profiles(slug: str):
    """Lista perfis de cliente disponiveis para simulacao"""
    return ConversationSimulatorService.CLIENT_PROFILES


# ===== Batch Run =====

@router.post("/{slug}/batch-tests/run")
async def run_batch_tests(
    slug: str,
    config: BatchRunConfig,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Inicia execucao de testes em lote.
    Retorna imediatamente com run_id, resultados sao buscados depois.
    """
    # Validar concurrent_tests
    if config.concurrent_tests not in [10, 15, 20]:
        raise HTTPException(400, "concurrent_tests deve ser 10, 15 ou 20")

    # Obter configuracao
    ai_config = await get_ai_config_or_404(slug, db)

    # Buscar casos de teste
    query = select(AITestCase).where(
        AITestCase.client_slug == slug,
        AITestCase.is_active == True
    )

    if config.test_case_ids:
        query = query.where(AITestCase.id.in_(config.test_case_ids))
    if config.category_filter:
        query = query.where(AITestCase.category == config.category_filter)

    result = await db.execute(query)
    test_cases = result.scalars().all()

    if not test_cases:
        raise HTTPException(400, "Nenhum caso de teste encontrado")

    # Criar registro de execucao
    test_run = AITestRun(
        client_slug=slug,
        status="running",
        concurrent_tests=config.concurrent_tests,
        total_tests=len(test_cases)
    )
    db.add(test_run)
    await db.commit()
    await db.refresh(test_run)

    # Buscar produtos
    products = await get_products_with_urls(slug, db)

    # Buscar schema se houver
    client = await get_client_or_404(slug, db)
    schema = None
    if client.product_schema_id:
        result = await db.execute(
            select(ProductSchema).where(ProductSchema.id == client.product_schema_id)
        )
        schema_obj = result.scalar_one_or_none()
        if schema_obj:
            schema = {"fields": schema_obj.fields or []}

    # Executar em background
    background_tasks.add_task(
        execute_batch_run,
        run_id=test_run.id,
        test_cases=[tc.to_dict() for tc in test_cases],  # Serializar para evitar problemas de sessao
        ai_config_dict=ai_config.to_dict(),
        products=products,
        concurrent_limit=config.concurrent_tests,
        schema=schema
    )

    logger.info(f"[{slug}] Batch test iniciado: run_id={test_run.id}, tests={len(test_cases)}")

    return {
        "run_id": test_run.id,
        "status": "started",
        "total_tests": len(test_cases),
        "concurrent_tests": config.concurrent_tests
    }


async def execute_batch_run(
    run_id: int,
    test_cases: List[dict],
    ai_config_dict: dict,
    products: List[dict],
    concurrent_limit: int,
    schema: dict = None
):
    """Funcao executada em background para rodar os testes"""
    async with AsyncSessionLocal() as db:
        try:
            # Recriar objetos AITestCase
            test_case_objs = []
            for tc_dict in test_cases:
                tc = AITestCase(**{
                    k: v for k, v in tc_dict.items()
                    if k not in ['created_at', 'updated_at']
                })
                test_case_objs.append(tc)

            # Recriar AIConfig
            ai_config = AIConfig(**{
                k: v for k, v in ai_config_dict.items()
                if k not in ['created_at', 'updated_at', 'working_hours_start', 'working_hours_end']
            })

            # Executar batch
            service = BatchTestingService()
            results = await service.run_batch(
                test_cases=test_case_objs,
                ai_config=ai_config,
                products=products,
                concurrent_limit=concurrent_limit,
                schema=schema
            )

            # Buscar run
            result = await db.execute(
                select(AITestRun).where(AITestRun.id == run_id)
            )
            test_run = result.scalar_one_or_none()

            if not test_run:
                logger.error(f"[BatchTest] Run {run_id} nao encontrado")
                return

            # Salvar resultados
            for test_result in results["results"]:
                test_result.run_id = run_id
                db.add(test_result)

            # Atualizar run
            test_run.status = "completed"
            test_run.completed_at = datetime.utcnow()
            test_run.passed_count = results["passed_count"]
            test_run.warning_count = results["warning_count"]
            test_run.failed_count = results["failed_count"]
            test_run.average_score = results["average_score"]
            test_run.total_execution_time_ms = results["total_execution_time_ms"]
            test_run.total_tokens_used = results["total_tokens_used"]
            test_run.estimated_cost = results["estimated_cost"]

            await db.commit()

            logger.info(f"[BatchTest] Run {run_id} concluido com sucesso")

        except Exception as e:
            logger.error(f"[BatchTest] Erro no run {run_id}: {e}", exc_info=True)

            # Marcar como falhou
            result = await db.execute(
                select(AITestRun).where(AITestRun.id == run_id)
            )
            test_run = result.scalar_one_or_none()
            if test_run:
                test_run.status = "failed"
                test_run.completed_at = datetime.utcnow()
                await db.commit()


@router.get("/{slug}/batch-tests/runs/{run_id}")
async def get_run_status(
    slug: str,
    run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtem status e resultados de uma execucao"""
    result = await db.execute(
        select(AITestRun)
        .options(selectinload(AITestRun.results).selectinload(AITestResult.test_case))
        .where(AITestRun.id == run_id, AITestRun.client_slug == slug)
    )
    test_run = result.scalar_one_or_none()

    if not test_run:
        raise HTTPException(status_code=404, detail="Execucao nao encontrada")

    return test_run.to_dict(include_results=True)


@router.get("/{slug}/batch-tests/runs")
async def list_runs(
    slug: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Lista execucoes recentes"""
    await get_client_or_404(slug, db)

    result = await db.execute(
        select(AITestRun)
        .where(AITestRun.client_slug == slug)
        .order_by(AITestRun.started_at.desc())
        .limit(limit)
    )
    runs = result.scalars().all()

    return [run.to_dict() for run in runs]


@router.delete("/{slug}/batch-tests/runs/{run_id}")
async def delete_run(
    slug: str,
    run_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove uma execucao e seus resultados"""
    result = await db.execute(
        select(AITestRun).where(
            AITestRun.id == run_id,
            AITestRun.client_slug == slug
        )
    )
    test_run = result.scalar_one_or_none()

    if not test_run:
        raise HTTPException(status_code=404, detail="Execucao nao encontrada")

    await db.delete(test_run)
    await db.commit()

    return {"message": "Execucao removida"}


# ===== Categorias =====

@router.get("/{slug}/batch-tests/categories")
async def list_categories(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Lista categorias de testes disponiveis"""
    return [
        {"value": "product_search", "label": "Busca de Produtos"},
        {"value": "financing", "label": "Financiamento"},
        {"value": "scheduling", "label": "Agendamento"},
        {"value": "media", "label": "Fotos e Midias"},
        {"value": "greeting", "label": "Saudacoes"},
        {"value": "out_of_scope", "label": "Fora do Escopo"},
        {"value": "other", "label": "Outros"}
    ]


@router.get("/batch-tests/templates")
async def get_templates():
    """Retorna templates padrao de testes"""
    return DEFAULT_TEST_TEMPLATES
