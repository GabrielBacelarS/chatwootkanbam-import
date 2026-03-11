from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List
from pydantic import BaseModel
import json
import io

from backend.core.database import get_db
from backend.core.config import settings
from backend.models import Client, Product, AIConfig
from backend.services import MinioService, RAGService

router = APIRouter()


class ProductCreate(BaseModel):
    name: str
    code: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    year_fab: Optional[int] = None
    price: Optional[float] = None
    price_fipe: Optional[float] = None
    price_promo: Optional[float] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    features: Optional[List[str]] = None
    specifications: Optional[dict] = None
    video_url: Optional[str] = None
    is_available: Optional[bool] = True
    is_featured: Optional[bool] = False
    stock_quantity: Optional[int] = 1
    location: Optional[str] = None
    mileage: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    color: Optional[str] = None
    doors: Optional[int] = None
    engine: Optional[str] = None
    dynamic_fields: Optional[dict] = None  # Campos dinamicos do schema


class ProductUpdate(ProductCreate):
    name: Optional[str] = None


async def get_client(slug: str, db: AsyncSession) -> Client:
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


def get_minio_service():
    """Retorna instância do MinioService configurada"""
    return MinioService(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        public_endpoint=settings.minio_public_endpoint
    )


# ===== CRUD de Produtos =====

@router.get("/{slug}/products")
async def list_products(
    slug: str,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    available_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Lista produtos do cliente"""
    await get_client(slug, db)

    query = select(Product).where(Product.client_slug == slug)

    if category:
        query = query.where(Product.category == category)
    if brand:
        query = query.where(Product.brand == brand)
    if available_only:
        query = query.where(Product.is_available == True)

    query = query.order_by(Product.is_featured.desc(), Product.created_at.desc())

    result = await db.execute(query)
    products = result.scalars().all()

    # Gerar URLs das imagens
    minio = get_minio_service()
    products_list = []
    for p in products:
        product_dict = p.to_dict()
        if p.main_image:
            product_dict["main_image_url"] = minio.get_presigned_url(p.main_image)
        if p.images:
            product_dict["images_urls"] = [minio.get_presigned_url(img) for img in p.images]
        products_list.append(product_dict)

    return products_list


@router.get("/{slug}/products/{product_id}")
async def get_product(slug: str, product_id: int, db: AsyncSession = Depends(get_db)):
    """Obtém detalhes de um produto"""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.client_slug == slug)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    product_dict = product.to_dict()

    # Gerar URLs das imagens
    minio = get_minio_service()
    if product.main_image:
        product_dict["main_image_url"] = minio.get_presigned_url(product.main_image)
    if product.images:
        product_dict["images_urls"] = [minio.get_presigned_url(img) for img in product.images]

    return product_dict


@router.post("/{slug}/products")
async def create_product(
    slug: str,
    data: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    """Cria um novo produto"""
    await get_client(slug, db)

    product = Product(
        client_slug=slug,
        **data.model_dump(exclude_unset=True)
    )

    # Gerar texto de busca
    product.search_text = product.to_search_text()

    db.add(product)
    await db.commit()
    await db.refresh(product)

    return product.to_dict()


@router.put("/{slug}/products/{product_id}")
async def update_product(
    slug: str,
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Atualiza um produto"""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.client_slug == slug)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    # Atualizar texto de busca
    product.search_text = product.to_search_text()

    await db.commit()
    await db.refresh(product)

    return product.to_dict()


@router.delete("/{slug}/products/{product_id}")
async def delete_product(slug: str, product_id: int, db: AsyncSession = Depends(get_db)):
    """Remove um produto"""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.client_slug == slug)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Remover imagens do MinIO
    minio = get_minio_service()
    if product.main_image:
        minio.delete_file(product.main_image)
    if product.images:
        for img in product.images:
            minio.delete_file(img)

    await db.delete(product)
    await db.commit()

    return {"message": "Produto removido"}


# ===== Upload de Imagens =====

@router.post("/{slug}/products/{product_id}/images")
async def upload_product_image(
    slug: str,
    product_id: int,
    file: UploadFile = File(...),
    is_main: bool = Form(default=False),
    db: AsyncSession = Depends(get_db)
):
    """Faz upload de imagem para um produto"""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.client_slug == slug)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Validar tipo de arquivo
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido")

    # Upload para MinIO
    minio = get_minio_service()
    content = await file.read()

    object_name = minio.upload_bytes(
        data=content,
        filename=file.filename,
        content_type=file.content_type,
        folder=f"{slug}/products/{product_id}"
    )

    if not object_name:
        raise HTTPException(status_code=500, detail="Erro ao fazer upload da imagem")

    # Atualizar produto
    if is_main:
        # Remover imagem principal antiga
        if product.main_image:
            minio.delete_file(product.main_image)
        product.main_image = object_name
    else:
        # Adicionar à lista de imagens
        images = list(product.images or [])
        images.append(object_name)
        product.images = images

    await db.commit()

    # Retornar URL da imagem
    image_url = minio.get_presigned_url(object_name)

    return {
        "object_name": object_name,
        "url": image_url,
        "is_main": is_main
    }


@router.delete("/{slug}/products/{product_id}/images/{image_index}")
async def delete_product_image(
    slug: str,
    product_id: int,
    image_index: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove uma imagem específica do produto"""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.client_slug == slug)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if not product.images or image_index >= len(product.images):
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    # Remover do MinIO
    minio = get_minio_service()
    image_to_delete = product.images[image_index]
    minio.delete_file(image_to_delete)

    # Atualizar lista
    images = list(product.images)
    images.pop(image_index)
    product.images = images

    await db.commit()

    return {"message": "Imagem removida"}


# ===== Embeddings e RAG =====

@router.post("/{slug}/products/{product_id}/generate-embedding")
async def generate_product_embedding(
    slug: str,
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Gera embedding para um produto específico"""
    # Buscar config de IA para pegar API key
    result = await db.execute(select(AIConfig).where(AIConfig.client_slug == slug))
    ai_config = result.scalar_one_or_none()

    if not ai_config or not ai_config.api_key:
        raise HTTPException(status_code=400, detail="Configuração de IA não encontrada")

    # Buscar produto
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.client_slug == slug)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Gerar embedding
    search_text = product.to_search_text()
    embedding = await RAGService.generate_embedding(search_text, ai_config.api_key)

    if not embedding:
        raise HTTPException(status_code=500, detail="Erro ao gerar embedding")

    # Salvar
    product.embedding = embedding
    product.search_text = search_text
    await db.commit()

    return {"message": "Embedding gerado com sucesso", "dimensions": len(embedding)}


@router.post("/{slug}/products/generate-all-embeddings")
async def generate_all_embeddings(slug: str, db: AsyncSession = Depends(get_db)):
    """Gera embeddings para todos os produtos do cliente"""
    # Buscar config de IA
    result = await db.execute(select(AIConfig).where(AIConfig.client_slug == slug))
    ai_config = result.scalar_one_or_none()

    if not ai_config or not ai_config.api_key:
        raise HTTPException(status_code=400, detail="Configuração de IA não encontrada")

    # Buscar produtos sem embedding
    result = await db.execute(
        select(Product).where(
            Product.client_slug == slug,
            Product.embedding == None
        )
    )
    products = result.scalars().all()

    generated = 0
    errors = 0

    for product in products:
        search_text = product.to_search_text()
        embedding = await RAGService.generate_embedding(search_text, ai_config.api_key)

        if embedding:
            product.embedding = embedding
            product.search_text = search_text
            generated += 1
        else:
            errors += 1

    await db.commit()

    return {
        "total": len(products),
        "generated": generated,
        "errors": errors
    }


@router.post("/{slug}/products/search")
async def search_products(
    slug: str,
    query: str,
    top_k: int = 5,
    use_embedding: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Busca produtos usando RAG (embeddings) ou keywords"""
    # Buscar todos os produtos
    result = await db.execute(
        select(Product).where(Product.client_slug == slug, Product.is_available == True)
    )
    products = result.scalars().all()

    if not products:
        return {"products": [], "context": ""}

    # Gerar URLs das imagens
    minio = get_minio_service()
    products_list = []
    for p in products:
        product_dict = p.to_dict()
        product_dict["embedding"] = p.embedding
        if p.main_image:
            product_dict["main_image_url"] = minio.get_presigned_url(p.main_image)
        products_list.append(product_dict)

    if use_embedding:
        # Buscar config de IA
        result = await db.execute(select(AIConfig).where(AIConfig.client_slug == slug))
        ai_config = result.scalar_one_or_none()

        if ai_config and ai_config.api_key:
            context, found_products = await RAGService.search_and_build_context(
                query=query,
                products=products_list,
                api_key=ai_config.api_key,
                top_k=top_k,
                include_images=True
            )

            if found_products:
                return {
                    "products": found_products,
                    "context": context,
                    "search_type": "embedding"
                }

    # Fallback para busca por keywords
    found_products = RAGService.keyword_search(query, products_list)[:top_k]
    context = RAGService.build_context_from_products(found_products, include_images=True)

    return {
        "products": found_products,
        "context": context,
        "search_type": "keyword"
    }
