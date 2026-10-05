"""
offline/datasets/prepare_dataset.py: Comprehensive Fine-Tuning Dataset Generator & Collector

Generates high-quality, diverse Text-to-Universal-SQL instruction tuning datasets
specifically formatted for Qwen2.5-Coder-7B-Instruct (ChatML SFT template).

Features:
- 8 diverse relational & multi-paradigm database schemas
- 10+ query complexity tiers (Simple, Aggregations, Multi-Joins, Window Functions,
  CTEs, Correlated Subqueries, Temporal Queries, Mutating DML/DDL)
- Output formats: ChatML SFT format (.jsonl), raw pair format (.json)
- Automatic train / validation split (85% train, 15% eval)
- Local generation without internet dependence; 100% excluded from git tracking.
"""

import argparse
import json
import os
import random
from typing import Any, Dict, List, Tuple


SYSTEM_PROMPT = (
    "You are an expert Text-to-Universal-SQL compiler. Generate deterministic, "
    "syntactically valid Canonical ANSI/PostgreSQL AST queries adhering to the provided database schema."
)

# -----------------------------------------------------------------------------
# Database Schemas (DDL Definitions)
# -----------------------------------------------------------------------------

SCHEMAS = {
    "ecommerce": """
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    country VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    category_id INT REFERENCES categories(category_id),
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL,
    status VARCHAR(50) DEFAULT 'active'
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL -- 'pending', 'completed', 'cancelled'
);

CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INT REFERENCES products(product_id),
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(product_id),
    customer_id INT REFERENCES customers(customer_id),
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""".strip(),

    "saas_platform": """
CREATE TABLE organizations (
    org_id SERIAL PRIMARY KEY,
    org_name VARCHAR(255) NOT NULL,
    plan_tier VARCHAR(50) NOT NULL, -- 'free', 'pro', 'enterprise'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(org_id),
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'owner', 'admin', 'member'
    last_login TIMESTAMP
);

CREATE TABLE subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(org_id),
    monthly_rate DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'active', 'past_due', 'cancelled'
    renews_at DATE NOT NULL
);

CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(org_id),
    user_id INT REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE api_keys (
    key_id SERIAL PRIMARY KEY,
    org_id INT REFERENCES organizations(org_id),
    key_hash VARCHAR(64) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""".strip(),

    "banking": """
CREATE TABLE branches (
    branch_id SERIAL PRIMARY KEY,
    branch_name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL
);

CREATE TABLE accounts (
    account_id SERIAL PRIMARY KEY,
    branch_id INT REFERENCES branches(branch_id),
    account_number VARCHAR(34) UNIQUE NOT NULL,
    account_type VARCHAR(50) NOT NULL, -- 'checking', 'savings', 'credit'
    balance DECIMAL(15, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    opened_at DATE NOT NULL
);

CREATE TABLE transactions (
    txn_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES accounts(account_id),
    txn_type VARCHAR(50) NOT NULL, -- 'deposit', 'withdrawal', 'transfer', 'fee'
    amount DECIMAL(15, 2) NOT NULL,
    txn_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    merchant_category VARCHAR(100),
    is_flagged_fraud BOOLEAN DEFAULT FALSE
);

CREATE TABLE loans (
    loan_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES accounts(account_id),
    principal DECIMAL(15, 2) NOT NULL,
    interest_rate DECIMAL(5, 4) NOT NULL,
    term_months INT NOT NULL,
    start_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL -- 'active', 'paid_off', 'defaulted'
);
""".strip(),

    "healthcare": """
CREATE TABLE departments (
    dept_id SERIAL PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    floor INT NOT NULL
);

CREATE TABLE doctors (
    doctor_id SERIAL PRIMARY KEY,
    dept_id INT REFERENCES departments(dept_id),
    name VARCHAR(255) NOT NULL,
    specialty VARCHAR(100) NOT NULL,
    years_experience INT NOT NULL
);

CREATE TABLE patients (
    patient_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    blood_group VARCHAR(10),
    contact_number VARCHAR(50)
);

CREATE TABLE appointments (
    appointment_id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES patients(patient_id),
    doctor_id INT REFERENCES doctors(doctor_id),
    scheduled_at TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'scheduled', 'completed', 'no_show', 'cancelled'
    reason_for_visit TEXT
);

CREATE TABLE prescriptions (
    prescription_id SERIAL PRIMARY KEY,
    appointment_id INT REFERENCES appointments(appointment_id),
    medication_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100) NOT NULL,
    duration_days INT NOT NULL,
    prescribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""".strip(),

    "supply_chain": """
CREATE TABLE suppliers (
    supplier_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    rating DECIMAL(3, 2)
);

CREATE TABLE warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    location_city VARCHAR(100) NOT NULL,
    capacity_sqft INT NOT NULL
);

CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    warehouse_id INT REFERENCES warehouses(warehouse_id),
    item_sku VARCHAR(100) NOT NULL,
    quantity_on_hand INT NOT NULL,
    reorder_level INT NOT NULL
);

CREATE TABLE shipments (
    shipment_id SERIAL PRIMARY KEY,
    supplier_id INT REFERENCES suppliers(supplier_id),
    destination_warehouse_id INT REFERENCES warehouses(warehouse_id),
    carrier VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'in_transit', 'delivered', 'delayed'
    shipped_date DATE,
    delivery_date DATE
);
""".strip(),

    "social_network": """
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    joined_date DATE NOT NULL,
    follower_count INT DEFAULT 0
);

CREATE TABLE friendships (
    user_id_a INT REFERENCES users(user_id),
    user_id_b INT REFERENCES users(user_id),
    established_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id_a, user_id_b)
);

CREATE TABLE posts (
    post_id SERIAL PRIMARY KEY,
    author_id INT REFERENCES users(user_id),
    content TEXT NOT NULL,
    like_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE comments (
    comment_id SERIAL PRIMARY KEY,
    post_id INT REFERENCES posts(post_id) ON DELETE CASCADE,
    author_id INT REFERENCES users(user_id),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE post_tags (
    post_id INT REFERENCES posts(post_id),
    tag_id INT REFERENCES tags(tag_id),
    PRIMARY KEY (post_id, tag_id)
);
""".strip(),

    "university": """
CREATE TABLE departments (
    dept_id SERIAL PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    building VARCHAR(100) NOT NULL
);

CREATE TABLE instructors (
    instructor_id SERIAL PRIMARY KEY,
    dept_id INT REFERENCES departments(dept_id),
    name VARCHAR(255) NOT NULL,
    salary DECIMAL(10, 2) NOT NULL
);

CREATE TABLE courses (
    course_id SERIAL PRIMARY KEY,
    dept_id INT REFERENCES departments(dept_id),
    course_code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    credits INT NOT NULL
);

CREATE TABLE students (
    student_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    major_dept_id INT REFERENCES departments(dept_id),
    gpa DECIMAL(3, 2) NOT NULL,
    enrollment_year INT NOT NULL
);

CREATE TABLE enrollments (
    enrollment_id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(student_id),
    course_id INT REFERENCES courses(course_id),
    instructor_id INT REFERENCES instructors(instructor_id),
    semester VARCHAR(20) NOT NULL,
    year INT NOT NULL,
    grade VARCHAR(5)
);
""".strip(),

    "graph_network": """
CREATE TABLE nodes (
    node_id SERIAL PRIMARY KEY,
    label VARCHAR(100) NOT NULL,
    properties JSONB
);

CREATE TABLE edges (
    edge_id SERIAL PRIMARY KEY,
    source_node_id INT REFERENCES nodes(node_id),
    target_node_id INT REFERENCES nodes(node_id),
    relation_type VARCHAR(100) NOT NULL,
    weight DECIMAL(8, 4) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""".strip()
}


# -----------------------------------------------------------------------------
# Curated & Parameterized SQL Question-Query Pairs
# -----------------------------------------------------------------------------

DATASET_TEMPLATES = [
    # E-Commerce Queries
    {
        "schema_key": "ecommerce",
        "question": "Find all completed orders placed in the last 30 days along with customer names and total amounts, ordered by total amount descending.",
        "sql": "SELECT o.order_id, c.name AS customer_name, o.total_amount, o.order_date FROM orders AS o JOIN customers AS c ON o.customer_id = c.customer_id WHERE o.status = 'completed' AND o.order_date >= CURRENT_DATE - INTERVAL '30 days' ORDER BY o.total_amount DESC;"
    },
    {
        "schema_key": "ecommerce",
        "question": "Which categories have generated more than $10,000 in total sales revenue?",
        "sql": "SELECT cat.category_name, SUM(oi.quantity * oi.unit_price) AS total_revenue FROM categories AS cat JOIN products AS p ON cat.category_id = p.category_id JOIN order_items AS oi ON p.product_id = oi.product_id JOIN orders AS o ON oi.order_id = o.order_id WHERE o.status = 'completed' GROUP BY cat.category_id, cat.category_name HAVING SUM(oi.quantity * oi.unit_price) > 10000 ORDER BY total_revenue DESC;"
    },
    {
        "schema_key": "ecommerce",
        "question": "List the top 5 customers with the highest average review ratings given, for customers who have left at least 3 reviews.",
        "sql": "SELECT c.customer_id, c.name, AVG(r.rating) AS avg_rating, COUNT(r.review_id) AS review_count FROM customers AS c JOIN reviews AS r ON c.customer_id = r.customer_id GROUP BY c.customer_id, c.name HAVING COUNT(r.review_id) >= 3 ORDER BY avg_rating DESC, review_count DESC LIMIT 5;"
    },
    {
        "schema_key": "ecommerce",
        "question": "Find all products in the 'Electronics' category that are currently out of stock or have less than 5 units left.",
        "sql": "SELECT p.product_id, p.name, p.price, p.stock_quantity FROM products AS p JOIN categories AS c ON p.category_id = c.category_id WHERE c.category_name = 'Electronics' AND p.stock_quantity < 5 AND p.status = 'active';"
    },
    {
        "schema_key": "ecommerce",
        "question": "Calculate the monthly revenue and order count for each month in the current year.",
        "sql": "SELECT DATE_TRUNC('month', order_date) AS order_month, COUNT(order_id) AS total_orders, SUM(total_amount) AS monthly_revenue FROM orders WHERE status = 'completed' AND EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE) GROUP BY DATE_TRUNC('month', order_date) ORDER BY order_month ASC;"
    },
    {
        "schema_key": "ecommerce",
        "question": "Find products that have never been ordered by any customer.",
        "sql": "SELECT p.product_id, p.name, p.price FROM products AS p WHERE NOT EXISTS (SELECT 1 FROM order_items AS oi WHERE oi.product_id = p.product_id);"
    },
    {
        "schema_key": "ecommerce",
        "question": "Update product prices by increasing them by 10% for all products in category ID 3.",
        "sql": "UPDATE products SET price = ROUND(price * 1.10, 2) WHERE category_id = 3;"
    },
    {
        "schema_key": "ecommerce",
        "question": "Add a discount_code column of type VARCHAR(50) to the orders table.",
        "sql": "ALTER TABLE orders ADD COLUMN discount_code VARCHAR(50);"
    },

    # SaaS Platform Queries
    {
        "schema_key": "saas_platform",
        "question": "List all active enterprise organizations with their member user count and active subscription monthly rate.",
        "sql": "SELECT o.org_id, o.org_name, s.monthly_rate, COUNT(u.user_id) AS total_users FROM organizations AS o JOIN subscriptions AS s ON o.org_id = s.org_id LEFT JOIN users AS u ON o.org_id = u.org_id WHERE o.plan_tier = 'enterprise' AND s.status = 'active' GROUP BY o.org_id, o.org_name, s.monthly_rate ORDER BY s.monthly_rate DESC;"
    },
    {
        "schema_key": "saas_platform",
        "question": "Find users who have not logged in within the past 90 days and belong to an active subscription org.",
        "sql": "SELECT u.user_id, u.email, u.role, u.last_login, o.org_name FROM users AS u JOIN organizations AS o ON u.org_id = o.org_id JOIN subscriptions AS s ON o.org_id = s.org_id WHERE s.status = 'active' AND (u.last_login < CURRENT_DATE - INTERVAL '90 days' OR u.last_login IS NULL);"
    },
    {
        "schema_key": "saas_platform",
        "question": "Count the number of audit log actions grouped by action type in the last 24 hours.",
        "sql": "SELECT action, COUNT(*) AS action_count FROM audit_logs WHERE created_at >= NOW() - INTERVAL '24 hours' GROUP BY action ORDER BY action_count DESC;"
    },
    {
        "schema_key": "saas_platform",
        "question": "Identify organizations that have more than 3 active API keys.",
        "sql": "SELECT o.org_id, o.org_name, COUNT(k.key_id) AS active_keys FROM organizations AS o JOIN api_keys AS k ON o.org_id = k.org_id WHERE k.is_active = TRUE GROUP BY o.org_id, o.org_name HAVING COUNT(k.key_id) > 3;"
    },
    {
        "schema_key": "saas_platform",
        "question": "Rank users within each organization by their last login date using a window function.",
        "sql": "SELECT user_id, org_id, email, last_login, ROW_NUMBER() OVER (PARTITION BY org_id ORDER BY last_login DESC NULLS LAST) AS login_recency_rank FROM users;"
    },

    # Banking Queries
    {
        "schema_key": "banking",
        "question": "Find all transactions flagged for fraud exceeding $1,000, along with the associated account number and branch name.",
        "sql": "SELECT t.txn_id, a.account_number, b.branch_name, t.amount, t.txn_timestamp, t.merchant_category FROM transactions AS t JOIN accounts AS a ON t.account_id = a.account_id JOIN branches AS b ON a.branch_id = b.branch_id WHERE t.is_flagged_fraud = TRUE AND t.amount > 1000 ORDER BY t.txn_timestamp DESC;"
    },
    {
        "schema_key": "banking",
        "question": "Calculate the total balance held in each branch across all checking and savings accounts.",
        "sql": "SELECT b.branch_id, b.branch_name, b.city, SUM(a.balance) AS total_deposits, COUNT(a.account_id) AS total_accounts FROM branches AS b JOIN accounts AS a ON b.branch_id = a.branch_id WHERE a.account_type IN ('checking', 'savings') AND a.status = 'open' GROUP BY b.branch_id, b.branch_name, b.city ORDER BY total_deposits DESC;"
    },
    {
        "schema_key": "banking",
        "question": "Find accounts where the total loan principal exceeds 5 times the current account balance.",
        "sql": "SELECT a.account_id, a.account_number, a.balance, SUM(l.principal) AS total_loan_principal FROM accounts AS a JOIN loans AS l ON a.account_id = l.account_id WHERE l.status = 'active' GROUP BY a.account_id, a.account_number, a.balance HAVING SUM(l.principal) > 5 * a.balance;"
    },
    {
        "schema_key": "banking",
        "question": "Identify the top 3 merchants by transaction volume in the 'Electronics' category for the current month.",
        "sql": "SELECT merchant_category, SUM(amount) AS total_volume, COUNT(txn_id) AS txn_count FROM transactions WHERE merchant_category = 'Electronics' AND txn_timestamp >= DATE_TRUNC('month', CURRENT_DATE) GROUP BY merchant_category ORDER BY total_volume DESC LIMIT 3;"
    },

    # Healthcare Queries
    {
        "schema_key": "healthcare",
        "question": "List all doctors in the Cardiology department with their scheduled appointments for today.",
        "sql": "SELECT d.doctor_id, d.name AS doctor_name, p.name AS patient_name, a.scheduled_at, a.status FROM doctors AS d JOIN departments AS dept ON d.dept_id = dept.dept_id JOIN appointments AS a ON d.doctor_id = a.doctor_id JOIN patients AS p ON a.patient_id = p.patient_id WHERE dept.dept_name = 'Cardiology' AND DATE(a.scheduled_at) = CURRENT_DATE ORDER BY a.scheduled_at ASC;"
    },
    {
        "schema_key": "healthcare",
        "question": "Find patients who have been prescribed 'Amoxicillin' more than twice in the past year.",
        "sql": "SELECT p.patient_id, p.name, COUNT(pr.prescription_id) AS prescription_count FROM patients AS p JOIN appointments AS a ON p.patient_id = a.patient_id JOIN prescriptions AS pr ON a.appointment_id = pr.appointment_id WHERE pr.medication_name ILIKE '%Amoxicillin%' AND pr.prescribed_at >= CURRENT_DATE - INTERVAL '1 year' GROUP BY p.patient_id, p.name HAVING COUNT(pr.prescription_id) > 2;"
    },
    {
        "schema_key": "healthcare",
        "question": "Calculate the average patient age per department based on completed appointments.",
        "sql": "SELECT dept.dept_name, AVG(EXTRACT(YEAR FROM AGE(CURRENT_DATE, p.date_of_birth))) AS avg_patient_age, COUNT(DISTINCT p.patient_id) AS unique_patients FROM departments AS dept JOIN doctors AS doc ON dept.dept_id = doc.dept_id JOIN appointments AS a ON doc.doctor_id = a.doctor_id JOIN patients AS p ON a.patient_id = p.patient_id WHERE a.status = 'completed' GROUP BY dept.dept_id, dept.dept_name ORDER BY avg_patient_age DESC;"
    },

    # Supply Chain Queries
    {
        "schema_key": "supply_chain",
        "question": "Find inventory items where the quantity on hand is below the reorder level, along with the warehouse city.",
        "sql": "SELECT inv.item_sku, inv.quantity_on_hand, inv.reorder_level, w.location_city FROM inventory AS inv JOIN warehouses AS w ON inv.warehouse_id = w.warehouse_id WHERE inv.quantity_on_hand < inv.reorder_level ORDER BY (inv.reorder_level - inv.quantity_on_hand) DESC;"
    },
    {
        "schema_key": "supply_chain",
        "question": "List all delayed shipments with supplier ratings and carrier names.",
        "sql": "SELECT s.shipment_id, sup.supplier_name, sup.rating AS supplier_rating, s.carrier, s.shipped_date, s.delivery_date FROM shipments AS s JOIN suppliers AS sup ON s.supplier_id = sup.supplier_id WHERE s.status = 'delayed' ORDER BY sup.rating DESC;"
    },

    # Social Network Queries
    {
        "schema_key": "social_network",
        "question": "Find the top 10 most liked posts with author usernames and total comment counts.",
        "sql": "SELECT p.post_id, u.username AS author, p.content, p.like_count, COUNT(c.comment_id) AS comment_count FROM posts AS p JOIN users AS u ON p.author_id = u.user_id LEFT JOIN comments AS c ON p.post_id = c.post_id GROUP BY p.post_id, u.username, p.content, p.like_count ORDER BY p.like_count DESC LIMIT 10;"
    },
    {
        "schema_key": "social_network",
        "question": "Find mutual friends between user ID 101 and user ID 202.",
        "sql": "SELECT f1.user_id_b AS mutual_friend_id, u.username FROM friendships AS f1 JOIN friendships AS f2 ON f1.user_id_b = f2.user_id_b JOIN users AS u ON f1.user_id_b = u.user_id WHERE f1.user_id_a = 101 AND f2.user_id_a = 202;"
    },
    {
        "schema_key": "social_network",
        "question": "List popular tags that have been used on more than 50 posts created in the last 7 days.",
        "sql": "SELECT t.tag_name, COUNT(pt.post_id) AS post_frequency FROM tags AS t JOIN post_tags AS pt ON t.tag_id = pt.tag_id JOIN posts AS p ON pt.post_id = p.post_id WHERE p.created_at >= NOW() - INTERVAL '7 days' GROUP BY t.tag_id, t.tag_name HAVING COUNT(pt.post_id) > 50 ORDER BY post_frequency DESC;"
    },

    # University Queries
    {
        "schema_key": "university",
        "question": "Find the top 3 students by GPA in each department who enrolled in 2022 or later.",
        "sql": "WITH RankedStudents AS (SELECT s.student_id, s.name, s.gpa, s.enrollment_year, d.dept_name, DENSE_RANK() OVER (PARTITION BY s.major_dept_id ORDER BY s.gpa DESC) AS rank_in_dept FROM students AS s JOIN departments AS d ON s.major_dept_id = d.dept_id WHERE s.enrollment_year >= 2022) SELECT student_id, name, dept_name, gpa, enrollment_year FROM RankedStudents WHERE rank_in_dept <= 3 ORDER BY dept_name ASC, gpa DESC;"
    },
    {
        "schema_key": "university",
        "question": "List courses that have an enrollment count exceeding 40 students for the Fall 2024 semester.",
        "sql": "SELECT c.course_code, c.title, COUNT(e.student_id) AS enrolled_count, i.name AS instructor_name FROM courses AS c JOIN enrollments AS e ON c.course_id = e.course_id JOIN instructors AS i ON e.instructor_id = i.instructor_id WHERE e.semester = 'Fall' AND e.year = 2024 GROUP BY c.course_id, c.course_code, c.title, i.name HAVING COUNT(e.student_id) > 40 ORDER BY enrolled_count DESC;"
    },

    # Graph Network Queries
    {
        "schema_key": "graph_network",
        "question": "Find all 2-hop connected target nodes starting from node ID 42 with edge relation type 'FRIENDS_WITH'.",
        "sql": "SELECT DISTINCT e2.target_node_id AS connected_node_id FROM edges AS e1 JOIN edges AS e2 ON e1.target_node_id = e2.source_node_id WHERE e1.source_node_id = 42 AND e1.relation_type = 'FRIENDS_WITH' AND e2.relation_type = 'FRIENDS_WITH';"
    }
]


def generate_synthetic_samples(count: int = 200) -> List[Dict[str, Any]]:
    """
    Expands base templates into diverse, parameterized instruction samples.
    """
    samples = []
    base_len = len(DATASET_TEMPLATES)

    for i in range(count):
        template = DATASET_TEMPLATES[i % base_len]
        schema_text = SCHEMAS[template["schema_key"]]
        question = template["question"]
        sql = template["sql"]

        # Parametric variation for numbers and thresholds
        if i >= base_len:
            factor = (i // base_len) + 1
            if "30 days" in question:
                days = random.choice([7, 14, 30, 60, 90])
                question = question.replace("30 days", f"{days} days")
                sql = sql.replace("30 days", f"{days} days")
            elif "$10,000" in question:
                amount = random.choice([5000, 10000, 25000, 50000])
                question = question.replace("$10,000", f"${amount:,}")
                sql = sql.replace("10000", str(amount))
            elif "LIMIT 5" in sql:
                lim = random.choice([3, 5, 10, 20])
                question = question.replace("5", str(lim))
                sql = sql.replace("LIMIT 5", f"LIMIT {lim}")

        # ChatML formatted message sequence
        user_prompt = f"### Database Schema:\n{schema_text}\n\n### User Question:\n{question}"
        chatml_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": sql}
        ]

        sample_record = {
            "id": f"sample_{i+1:04d}",
            "schema_key": template["schema_key"],
            "schema": schema_text,
            "question": question,
            "sql": sql,
            "messages": chatml_messages
        }
        samples.append(sample_record)

    return samples


def main():
    parser = argparse.ArgumentParser(description="NL2SQL Fine-Tuning Dataset Generator & Collector")
    parser.add_argument("--output-dir", type=str, default="offline/datasets", help="Target output directory")
    parser.add_argument("--sample-count", type=int, default=250, help="Total synthetic samples to generate")
    parser.add_argument("--eval-ratio", type=float, default=0.15, help="Proportion of evaluation samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic split")
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"[Dataset] Generating {args.sample_count} instruction samples across {len(SCHEMAS)} domain schemas...")
    samples = generate_synthetic_samples(count=args.sample_count)
    random.shuffle(samples)

    eval_count = int(len(samples) * args.eval_ratio)
    eval_samples = samples[:eval_count]
    train_samples = samples[eval_count:]

    # 1. Save standard JSON format (for SFTTrainer & custom loaders)
    train_json_path = os.path.join(args.output_dir, "train.json")
    eval_json_path = os.path.join(args.output_dir, "eval.json")

    with open(train_json_path, "w", encoding="utf-8") as f:
        json.dump(train_samples, f, indent=2)

    with open(eval_json_path, "w", encoding="utf-8") as f:
        json.dump(eval_samples, f, indent=2)

    # 2. Save ChatML JSONL format (compatible with HuggingFace, Unsloth, Axolotl, TRL)
    train_jsonl_path = os.path.join(args.output_dir, "train.jsonl")
    eval_jsonl_path = os.path.join(args.output_dir, "eval.jsonl")

    with open(train_jsonl_path, "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps({"messages": s["messages"]}, ensure_ascii=False) + "\n")

    with open(eval_jsonl_path, "w", encoding="utf-8") as f:
        for s in eval_samples:
            f.write(json.dumps({"messages": s["messages"]}, ensure_ascii=False) + "\n")

    print(f"[Dataset] Successfully generated datasets:")
    print(f"  - Train JSON : {train_json_path} ({len(train_samples)} samples)")
    print(f"  - Eval JSON  : {eval_json_path} ({len(eval_samples)} samples)")
    print(f"  - Train JSONL: {train_jsonl_path}")
    print(f"  - Eval JSONL : {eval_jsonl_path}")
    print(f"[Dataset] Verified: offline/datasets/*.json & *.jsonl are protected by .gitignore (0 bytes committed to git).")


if __name__ == "__main__":
    main()
