from openai import AsyncOpenAI, OpenAI
from typing import Optional, List, Dict, Any
import numpy as np
import logging

logger = logging.getLogger(__name__)


def format_field_value(value: Any, rag_format: Optional[str], label: str) -> str:
    """Formata valor do campo baseado no tipo de formatacao"""
    if value is None or value == "":
        return ""

    try:
        if rag_format == "currency":
            num_value = float(value)
            formatted = f"R$ {num_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"{label}: {formatted}"
        elif rag_format == "km":
            num_value = int(value)
            formatted = f"{num_value:,}".replace(",", ".")
            return f"{label}: {formatted} km"
        elif rag_format == "number":
            num_value = float(value) if "." in str(value) else int(value)
            formatted = f"{num_value:,}".replace(",", ".")
            return f"{label}: {formatted}"
        else:
            return f"{label}: {value}"
    except (ValueError, TypeError):
        return f"{label}: {value}"


class RAGService:
    """Service para Retrieval Augmented Generation com embeddings"""

    @staticmethod
    async def generate_embedding(
        text: str,
        api_key: str,
        model: str = "text-embedding-3-small"
    ) -> Optional[List[float]]:
        """Gera embedding para um texto usando OpenAI"""
        try:
            client = AsyncOpenAI(api_key=api_key)

            response = await client.embeddings.create(
                model=model,
                input=text
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            return None

    @staticmethod
    def generate_embedding_sync(
        text: str,
        api_key: str,
        model: str = "text-embedding-3-small"
    ) -> Optional[List[float]]:
        """Gera embedding de forma sincrona (para uso em tools do LangChain)"""
        try:
            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(model=model, input=text)
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erro ao gerar embedding (sync): {e}")
            return None

    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calcula similaridade de cosseno entre dois vetores"""
        a = np.array(a)
        b = np.array(b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        # Evitar division by zero se algum vetor for zero
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def search_similar(
        query_embedding: List[float],
        products: List[Dict],
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        Busca produtos similares usando embeddings
        products deve ser lista de dicts com 'embedding' e outros campos
        """
        results = []

        for product in products:
            if not product.get("embedding"):
                continue

            similarity = RAGService.cosine_similarity(query_embedding, product["embedding"])

            if similarity >= threshold:
                results.append({
                    **product,
                    "similarity": similarity
                })

        # Ordenar por similaridade decrescente
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:top_k]

    @staticmethod
    def build_context_from_products(
        products: List[Dict],
        max_products: int = 5,
        include_images: bool = True,
        schema: Optional[Dict] = None
    ) -> str:
        """
        Constrói contexto formatado para a IA a partir dos produtos encontrados.
        Se um schema for fornecido, usa os campos dinamicos.
        """
        if not products:
            return ""

        lines = [
            "=== PRODUTOS ENCONTRADOS NA BASE ===",
            "IMPORTANTE: Use TODOS os dados abaixo ao responder sobre estes produtos.",
            "Quando o cliente perguntar por foto/imagem, use a ferramenta 'enviar_imagem' - NAO inclua URLs na resposta.",
            "Nunca diga que vai 'verificar' ou 'pedir para alguem' - voce TEM os dados aqui.\n"
        ]

        for i, product in enumerate(products[:max_products], 1):
            lines.append(f"--- Produto {i} ---")

            # Campos fixos (sempre presentes)
            if product.get("name"):
                lines.append(f"Nome: {product['name']}")

            if product.get("price"):
                price_fmt = f"R$ {product['price']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                lines.append(f"Preço: {price_fmt}")

            # Se temos schema, usar campos dinamicos
            if schema and schema.get("fields"):
                dynamic_fields = product.get("dynamic_fields", {})

                # Ordenar campos por order
                sorted_fields = sorted(
                    schema["fields"],
                    key=lambda f: f.get("order", 999)
                )

                for field in sorted_fields:
                    if not field.get("show_in_rag", True):
                        continue

                    key = field.get("key")
                    value = dynamic_fields.get(key)

                    # Fallback para campos legados
                    if value is None or value == "":
                        value = product.get(key)

                    if value is not None and value != "":
                        label = field.get("rag_label") or field.get("label", key)
                        rag_format = field.get("rag_format")
                        formatted = format_field_value(value, rag_format, label)
                        if formatted:
                            lines.append(formatted)

            # Fallback: campos legados (para compatibilidade)
            else:
                if product.get("year"):
                    year_fab = product.get("year_fab", product["year"])
                    lines.append(f"Ano: {year_fab}/{product['year']}")

                if product.get("mileage"):
                    km_fmt = f"{product['mileage']:,}".replace(",", ".")
                    lines.append(f"Quilometragem: {km_fmt} km")

                if product.get("color"):
                    lines.append(f"Cor: {product['color']}")

                if product.get("fuel_type"):
                    lines.append(f"Combustível: {product['fuel_type']}")

                if product.get("transmission"):
                    lines.append(f"Câmbio: {product['transmission']}")

                if product.get("engine"):
                    lines.append(f"Motor: {product['engine']}")

            # Campos comuns
            if product.get("short_description"):
                lines.append(f"Descrição: {product['short_description']}")

            if product.get("features"):
                features = product["features"][:5]
                lines.append(f"Principais itens: {', '.join(features)}")

            if include_images and product.get("main_image_url"):
                lines.append(f"📸 TEM FOTO DISPONIVEL - Use a ferramenta 'enviar_imagem' com produto_nome='{product.get('name', 'produto')}' para enviar a foto ao cliente")

            if product.get("is_available") is False:
                lines.append("⚠️ VENDIDO/INDISPONÍVEL")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    async def search_and_build_context(
        query: str,
        products: List[Dict],
        api_key: str,
        top_k: int = 5,
        threshold: float = 0.3,
        include_images: bool = True,
        schema: Optional[Dict] = None
    ) -> tuple[str, List[Dict]]:
        """
        Busca produtos relevantes e constrói contexto para a IA.
        Se um schema for fornecido, formata os campos dinamicamente.
        Retorna (contexto_string, lista_de_produtos_encontrados)
        """
        # Gerar embedding da query
        query_embedding = await RAGService.generate_embedding(query, api_key)

        if not query_embedding:
            return "", []

        # Buscar produtos similares
        similar_products = RAGService.search_similar(
            query_embedding,
            products,
            top_k=top_k,
            threshold=threshold
        )

        # Construir contexto
        context = RAGService.build_context_from_products(
            similar_products,
            max_products=top_k,
            include_images=include_images,
            schema=schema
        )

        return context, similar_products

    @staticmethod
    def keyword_search(
        query: str,
        products: List[Dict],
        fields: List[str] = None
    ) -> List[Dict]:
        """
        Busca simples por palavras-chave (fallback quando não há embeddings)
        """
        if fields is None:
            fields = ["name", "brand", "model", "category", "color", "description", "search_text"]

        query_lower = query.lower()
        query_words = query_lower.split()

        results = []

        for product in products:
            score = 0

            for field in fields:
                value = product.get(field, "")
                if value:
                    value_lower = str(value).lower()

                    # Pontuação por palavra encontrada
                    for word in query_words:
                        if len(word) >= 2 and word in value_lower:
                            score += 1

                            # Bonus para match exato no nome
                            if field == "name":
                                score += 2

            if score > 0:
                results.append({
                    **product,
                    "keyword_score": score
                })

        # Ordenar por score
        results.sort(key=lambda x: x["keyword_score"], reverse=True)

        return results
