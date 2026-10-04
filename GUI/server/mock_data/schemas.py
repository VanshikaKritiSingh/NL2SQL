# mock_data/schemas.py
from models.schema import SchemaInfo, TableInfo, ColumnInfo, ForeignKey


def get_mock_ecommerce_schema(dialect: str = "mysql") -> SchemaInfo:
    """Returns a realistic 4-table e-commerce schema with explicit PK/FK relationships."""
    
    users_table = TableInfo(
        name="users",
        columns=[
            ColumnInfo(name="user_id", data_type="INT", is_primary_key=True, nullable=False),
            ColumnInfo(name="username", data_type="VARCHAR(50)", nullable=False),
            ColumnInfo(name="email", data_type="VARCHAR(100)", nullable=False),
            ColumnInfo(name="role", data_type="VARCHAR(20)", nullable=False),
            ColumnInfo(name="created_at", data_type="DATETIME", nullable=False),
        ]
    )

    products_table = TableInfo(
        name="products",
        columns=[
            ColumnInfo(name="product_id", data_type="INT", is_primary_key=True, nullable=False),
            ColumnInfo(name="name", data_type="VARCHAR(100)", nullable=False),
            ColumnInfo(name="category", data_type="VARCHAR(50)", nullable=False),
            ColumnInfo(name="price", data_type="DECIMAL(10,2)", nullable=False),
            ColumnInfo(name="stock_quantity", data_type="INT", nullable=False),
        ]
    )

    orders_table = TableInfo(
        name="orders",
        columns=[
            ColumnInfo(name="order_id", data_type="INT", is_primary_key=True, nullable=False),
            ColumnInfo(name="user_id", data_type="INT", is_foreign_key=True, fk_references="users.user_id", nullable=False),
            ColumnInfo(name="order_date", data_type="DATETIME", nullable=False),
            ColumnInfo(name="status", data_type="VARCHAR(20)", nullable=False),
            ColumnInfo(name="total_amount", data_type="DECIMAL(10,2)", nullable=False),
        ]
    )

    order_items_table = TableInfo(
        name="order_items",
        columns=[
            ColumnInfo(name="item_id", data_type="INT", is_primary_key=True, nullable=False),
            ColumnInfo(name="order_id", data_type="INT", is_foreign_key=True, fk_references="orders.order_id", nullable=False),
            ColumnInfo(name="product_id", data_type="INT", is_foreign_key=True, fk_references="products.product_id", nullable=False),
            ColumnInfo(name="quantity", data_type="INT", nullable=False),
            ColumnInfo(name="unit_price", data_type="DECIMAL(10,2)", nullable=False),
        ]
    )

    foreign_keys = [
        ForeignKey(from_table="orders", from_column="user_id", to_table="users", to_column="user_id"),
        ForeignKey(from_table="order_items", from_column="order_id", to_table="orders", to_column="order_id"),
        ForeignKey(from_table="order_items", from_column="product_id", to_table="products", to_column="product_id"),
    ]

    return SchemaInfo(
        dialect=dialect,
        database_name="ecommerce_prod",
        tables=[users_table, products_table, orders_table, order_items_table],
        foreign_keys=foreign_keys,
    )
