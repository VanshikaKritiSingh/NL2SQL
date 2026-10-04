# mock_data/diffs.py
from models.approval import DiffData, DmlRowDiff


def get_mock_ddl_diff() -> DiffData:
    """Mock DDL diff for adding a discount_code column to orders table."""
    before = """-- Schema BEFORE migration (Dolt Commit: 7f8a9b)
CREATE TABLE `orders` (
  `order_id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `order_date` DATETIME NOT NULL,
  `status` VARCHAR(20) NOT NULL,
  `total_amount` DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (`order_id`),
  CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"""

    after = """-- Schema AFTER migration (Staged for commit)
CREATE TABLE `orders` (
  `order_id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `order_date` DATETIME NOT NULL,
  `status` VARCHAR(20) NOT NULL,
  `total_amount` DECIMAL(10,2) NOT NULL,
  `discount_code` VARCHAR(30) DEFAULT NULL,
  PRIMARY KEY (`order_id`),
  CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"""

    return DiffData(
        diff_type="ddl",
        ddl_before=before,
        ddl_after=after,
        dml_rows=None,
    )


def get_mock_dml_diff() -> DiffData:
    """Mock DML diff for increasing product prices by 10%."""
    dml_rows = [
        DmlRowDiff(
            row_id=101,
            columns={
                "name": {"before": "Wireless Headphones", "after": "Wireless Headphones"},
                "price": {"before": 49.99, "after": 54.99},
                "category": {"before": "Electronics", "after": "Electronics"},
            },
            change_type="update",
        ),
        DmlRowDiff(
            row_id=102,
            columns={
                "name": {"before": "Mechanical Keyboard", "after": "Mechanical Keyboard"},
                "price": {"before": 89.00, "after": 97.90},
                "category": {"before": "Electronics", "after": "Electronics"},
            },
            change_type="update",
        ),
        DmlRowDiff(
            row_id=103,
            columns={
                "name": {"before": "USB-C Hub", "after": "USB-C Hub"},
                "price": {"before": 25.50, "after": 28.05},
                "category": {"before": "Accessories", "after": "Accessories"},
            },
            change_type="update",
        ),
    ]

    return DiffData(
        diff_type="dml",
        ddl_before=None,
        ddl_after=None,
        dml_rows=dml_rows,
    )
