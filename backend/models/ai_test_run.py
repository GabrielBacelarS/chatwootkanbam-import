from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, func, Float
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from backend.core.database import Base


class AITestRun(Base):
    """Execucao de lote de testes"""
    __tablename__ = "ai_test_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"))

    # Configuracao da execucao
    concurrent_tests = Column(Integer)  # 10, 15 ou 20
    total_tests = Column(Integer)

    # Status
    status = Column(String(20), default="running")  # running, completed, failed
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)

    # Resultados agregados
    passed_count = Column(Integer, default=0)  # score >= 9
    warning_count = Column(Integer, default=0)  # score 5-8
    failed_count = Column(Integer, default=0)  # score < 5
    average_score = Column(Float)

    # Metricas
    total_execution_time_ms = Column(Integer)
    total_tokens_used = Column(Integer)
    estimated_cost = Column(Float)

    # Relacionamento com resultados
    results = relationship("AITestResult", back_populates="run", cascade="all, delete-orphan")

    def to_dict(self, include_results=False):
        data = {
            "id": self.id,
            "client_slug": self.client_slug,
            "concurrent_tests": self.concurrent_tests,
            "total_tests": self.total_tests,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "passed_count": self.passed_count,
            "warning_count": self.warning_count,
            "failed_count": self.failed_count,
            "average_score": round(self.average_score, 2) if self.average_score else None,
            "total_execution_time_ms": self.total_execution_time_ms,
            "total_tokens_used": self.total_tokens_used,
            "estimated_cost": round(self.estimated_cost, 4) if self.estimated_cost else None
        }

        if include_results and self.results:
            data["results"] = [r.to_dict() for r in self.results]

        return data


class AITestResult(Base):
    """Resultado individual de um teste"""
    __tablename__ = "ai_test_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("ai_test_runs.id", ondelete="CASCADE"))
    test_case_id = Column(Integer, ForeignKey("ai_test_cases.id", ondelete="CASCADE"))

    # Resposta do agente
    ai_response = Column(Text)
    tools_used = Column(ARRAY(String), default=[])
    execution_time_ms = Column(Integer)

    # Pontuacao
    score = Column(Float)  # 0-10
    score_breakdown = Column(JSONB)  # Detalhamento por criterio

    # Problemas encontrados
    issues = Column(ARRAY(String), default=[])

    # Tokens utilizados
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)

    # Relacionamentos
    run = relationship("AITestRun", back_populates="results")
    test_case = relationship("AITestCase")

    @property
    def status(self) -> str:
        """Retorna status baseado na nota"""
        if self.score is None:
            return "unknown"
        if self.score >= 9:
            return "success"
        elif self.score >= 5:
            return "warning"
        return "error"

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "test_case_id": self.test_case_id,
            "test_case_name": self.test_case.name if self.test_case else None,
            "input_message": self.test_case.input_message if self.test_case else None,
            "ai_response": self.ai_response,
            "tools_used": self.tools_used or [],
            "execution_time_ms": self.execution_time_ms,
            "score": round(self.score, 2) if self.score is not None else None,
            "score_breakdown": self.score_breakdown,
            "issues": self.issues or [],
            "status": self.status,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output
        }
