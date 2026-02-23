from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional, List
from pydantic import BaseModel

from backend.core.database import get_db
from backend.models.product_schema import ProductSchema, DEFAULT_SCHEMAS
from backend.models.client import Client

router = APIRouter()


# ===== Pydantic Models =====

class SchemaFieldModel(BaseModel):
    key: str
    label: str
    type: str  # text, number, select, textarea, boolean, date
    required: Optional[bool] = False
    placeholder: Optional[str] = None
    group: Optional[str] = None
    order: Optional[int] = 0
    options: Optional[List[str]] = None
    show_in_card: Optional[bool] = True
    show_in_rag: Optional[bool] = True
    rag_label: Optional[str] = None
    rag_format: Optional[str] = None  # currency, number, km


class SchemaCreate(BaseModel):
    slug: str
    name: str
    icon: Optional[str] = "mdi-package"
    description: Optional[str] = None
    fields: List[SchemaFieldModel] = []
    card_title_field: Optional[str] = "name"
    card_subtitle_template: Optional[str] = None
    card_price_field: Optional[str] = "price"
    is_active: Optional[bool] = True


class SchemaUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[List[SchemaFieldModel]] = None
    card_title_field: Optional[str] = None
    card_subtitle_template: Optional[str] = None
    card_price_field: Optional[str] = None
    is_active: Optional[bool] = None


# ===== API Endpoints =====

@router.get("/schemas")
async def list_schemas(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Lista todos os schemas de produto"""
    query = select(ProductSchema)
    if active_only:
        query = query.where(ProductSchema.is_active == True)
    query = query.order_by(ProductSchema.is_default.desc(), ProductSchema.name)

    result = await db.execute(query)
    schemas = result.scalars().all()
    return [s.to_dict() for s in schemas]


@router.get("/schemas/{schema_id}")
async def get_schema(
    schema_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtem detalhes de um schema"""
    result = await db.execute(
        select(ProductSchema).where(ProductSchema.id == schema_id)
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema nao encontrado")
    return schema.to_dict()


@router.post("/schemas")
async def create_schema(
    data: SchemaCreate,
    db: AsyncSession = Depends(get_db)
):
    """Cria um novo schema de produto (requer superadmin)"""
    # Verificar se slug ja existe
    result = await db.execute(
        select(ProductSchema).where(ProductSchema.slug == data.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ja existe um schema com esse slug")

    schema = ProductSchema(
        slug=data.slug,
        name=data.name,
        icon=data.icon,
        description=data.description,
        fields=[f.model_dump() for f in data.fields],
        card_title_field=data.card_title_field,
        card_subtitle_template=data.card_subtitle_template,
        card_price_field=data.card_price_field,
        is_active=data.is_active
    )
    db.add(schema)
    await db.commit()
    await db.refresh(schema)
    return schema.to_dict()


@router.put("/schemas/{schema_id}")
async def update_schema(
    schema_id: int,
    data: SchemaUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Atualiza um schema existente (requer superadmin)"""
    result = await db.execute(
        select(ProductSchema).where(ProductSchema.id == schema_id)
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema nao encontrado")

    # Atualizar campos fornecidos
    if data.name is not None:
        schema.name = data.name
    if data.icon is not None:
        schema.icon = data.icon
    if data.description is not None:
        schema.description = data.description
    if data.fields is not None:
        schema.fields = [f.model_dump() for f in data.fields]
    if data.card_title_field is not None:
        schema.card_title_field = data.card_title_field
    if data.card_subtitle_template is not None:
        schema.card_subtitle_template = data.card_subtitle_template
    if data.card_price_field is not None:
        schema.card_price_field = data.card_price_field
    if data.is_active is not None:
        schema.is_active = data.is_active

    await db.commit()
    await db.refresh(schema)
    return schema.to_dict()


@router.delete("/schemas/{schema_id}")
async def delete_schema(
    schema_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove um schema (requer superadmin)"""
    result = await db.execute(
        select(ProductSchema).where(ProductSchema.id == schema_id)
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema nao encontrado")

    if schema.is_default:
        raise HTTPException(status_code=400, detail="Nao e possivel remover o schema padrao")

    # Verificar se algum cliente usa este schema
    client_result = await db.execute(
        select(Client).where(Client.product_schema_id == schema_id)
    )
    if client_result.scalars().first():
        raise HTTPException(status_code=400, detail="Este schema esta em uso por clientes")

    await db.delete(schema)
    await db.commit()
    return {"message": "Schema removido com sucesso"}


@router.post("/schemas/{schema_id}/set-default")
async def set_default_schema(
    schema_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Define um schema como padrao (requer superadmin)"""
    result = await db.execute(
        select(ProductSchema).where(ProductSchema.id == schema_id)
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema nao encontrado")

    # Remover default de todos
    await db.execute(
        update(ProductSchema).values(is_default=False)
    )

    # Definir este como default
    schema.is_default = True
    await db.commit()
    return {"message": "Schema definido como padrao"}


@router.post("/schemas/seed")
async def seed_default_schemas(
    db: AsyncSession = Depends(get_db)
):
    """Popula o banco com os schemas padrao (requer superadmin)"""
    created = 0
    for schema_data in DEFAULT_SCHEMAS:
        # Verificar se ja existe
        result = await db.execute(
            select(ProductSchema).where(ProductSchema.slug == schema_data["slug"])
        )
        if result.scalar_one_or_none():
            continue

        schema = ProductSchema(**schema_data)
        db.add(schema)
        created += 1

    await db.commit()
    return {"message": f"{created} schemas criados"}


# ===== Client Schema Assignment =====

@router.put("/clients/{slug}/schema")
async def set_client_schema(
    slug: str,
    schema_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Atribui um schema de produto a um cliente"""
    # Verificar cliente
    result = await db.execute(
        select(Client).where(Client.slug == slug)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    # Verificar schema
    result = await db.execute(
        select(ProductSchema).where(ProductSchema.id == schema_id)
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise HTTPException(status_code=404, detail="Schema nao encontrado")

    client.product_schema_id = schema_id
    await db.commit()
    return {"message": f"Schema '{schema.name}' atribuido ao cliente '{client.name}'"}


@router.get("/{slug}/products/schema")
async def get_client_product_schema(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Obtem o schema de produto do cliente (para renderizar o form)"""
    # Buscar cliente
    result = await db.execute(
        select(Client).where(Client.slug == slug)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    if not client.product_schema_id:
        # Buscar schema default
        result = await db.execute(
            select(ProductSchema).where(ProductSchema.is_default == True)
        )
        schema = result.scalar_one_or_none()
        if not schema:
            # Retorna schema vazio se nao houver default
            return {"fields": [], "message": "Nenhum schema configurado"}
        return schema.to_dict()

    # Buscar schema do cliente
    result = await db.execute(
        select(ProductSchema).where(ProductSchema.id == client.product_schema_id)
    )
    schema = result.scalar_one_or_none()
    if not schema:
        return {"fields": [], "message": "Schema nao encontrado"}

    return schema.to_dict()
