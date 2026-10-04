# routers/schema.py
from fastapi import APIRouter
from models.schema import SchemaInfo
from mock_data.schemas import get_mock_ecommerce_schema

router = APIRouter(prefix="/schema", tags=["Schema Explorer"])


@router.get("/{dialect}", response_model=SchemaInfo)
async def get_schema(dialect: str = "mysql"):
    """Returns database schema graph for the ER Diagram visualizer (M14)."""
    return get_mock_ecommerce_schema(dialect)
