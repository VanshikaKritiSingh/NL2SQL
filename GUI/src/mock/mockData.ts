import { SchemaInfo } from '../types/schema';
import { ApprovalPayload, DiffData } from '../types/approval';
import { QueryResponse } from '../types/query';

export const MOCK_SCHEMA: SchemaInfo = {
  database_name: 'ecommerce_db',
  dialect: 'mysql',
  tables: [
    {
      name: 'users',
      columns: [
        { name: 'id', data_type: 'INT', is_primary_key: true, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'email', data_type: 'VARCHAR(255)', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'full_name', data_type: 'VARCHAR(100)', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'created_at', data_type: 'TIMESTAMP', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'role', data_type: 'VARCHAR(20)', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
      ],
    },
    {
      name: 'orders',
      columns: [
        { name: 'id', data_type: 'INT', is_primary_key: true, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'user_id', data_type: 'INT', is_primary_key: false, is_foreign_key: true, fk_references: 'users.id', nullable: false },
        { name: 'order_date', data_type: 'TIMESTAMP', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'total_amount', data_type: 'DECIMAL(10,2)', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'status', data_type: 'VARCHAR(30)', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
      ],
    },
    {
      name: 'order_items',
      columns: [
        { name: 'id', data_type: 'INT', is_primary_key: true, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'order_id', data_type: 'INT', is_primary_key: false, is_foreign_key: true, fk_references: 'orders.id', nullable: false },
        { name: 'product_id', data_type: 'INT', is_primary_key: false, is_foreign_key: true, fk_references: 'products.id', nullable: false },
        { name: 'quantity', data_type: 'INT', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'unit_price', data_type: 'DECIMAL(10,2)', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
      ],
    },
    {
      name: 'products',
      columns: [
        { name: 'id', data_type: 'INT', is_primary_key: true, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'name', data_type: 'VARCHAR(255)', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'sku', data_type: 'VARCHAR(50)', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'price', data_type: 'DECIMAL(10,2)', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
        { name: 'stock_quantity', data_type: 'INT', is_primary_key: false, is_foreign_key: false, fk_references: null, nullable: false },
      ],
    },
  ],
  foreign_keys: [
    { from_table: 'orders', from_column: 'user_id', to_table: 'users', to_column: 'id' },
    { from_table: 'order_items', from_column: 'order_id', to_table: 'orders', to_column: 'id' },
    { from_table: 'order_items', from_column: 'product_id', to_table: 'products', to_column: 'id' },
  ],
};

export const MOCK_SELECT_RESPONSE: QueryResponse = {
  query_id: 'q_select_demo_101',
  status: 'completed',
  generated_sql:
    'SELECT o.id AS order_id, u.full_name, o.order_date, o.total_amount, o.status\nFROM orders o\nJOIN users u ON o.user_id = u.id\nWHERE o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)\nORDER BY o.order_date DESC;',
  result_data: {
    columns: ['order_id', 'full_name', 'order_date', 'total_amount', 'status'],
    rows: [
      { order_id: 1042, full_name: 'Aarav Patel', order_date: '2025-02-14 10:30:00', total_amount: '$149.99', status: 'COMPLETED' },
      { order_id: 1043, full_name: 'Diya Sharma', order_date: '2025-02-16 15:45:00', total_amount: '$320.50', status: 'COMPLETED' },
      { order_id: 1044, full_name: 'Rohan Verma', order_date: '2025-02-20 18:20:00', total_amount: '$89.00', status: 'PENDING' },
      { order_id: 1045, full_name: 'Sneha Rao', order_date: '2025-02-24 09:15:00', total_amount: '$450.00', status: 'SHIPPED' },
      { order_id: 1046, full_name: 'Kabir Mehta', order_date: '2025-02-28 21:05:00', total_amount: '$75.25', status: 'COMPLETED' },
    ],
    row_count: 5,
  },
  approval_payload: null,
  error_message: null,
  cache_hit: false,
};

export const MOCK_UPDATE_APPROVAL: ApprovalPayload = {
  query_id: 'q_update_demo_202',
  generated_sql:
    'UPDATE products\nSET price = price * 1.10\nWHERE stock_quantity < 20;\n-- Checkpoint: Dolt CAS Branch #482',
  target_dialect: 'mysql',
  risk_tier: 'high',
  impacted_tables: [
    {
      name: 'products',
      impact_level: 'direct',
      operation: 'UPDATE',
    },
    {
      name: 'order_items',
      impact_level: 'referenced',
      operation: 'FOREIGN_KEY_REFERENCE',
    },
  ],
  cost_estimate: {
    estimated_rows: 4,
    estimated_cost: 48.0,
    scan_type: 'index_scan',
    warnings: ['Clustered primary index scan with WHERE condition filter'],
  },
  security_check: {
    deadlock_risk: 'medium',
    lock_level: 'ROW',
    privilege_ok: true,
    flags: ['Row exclusive lock acquired on active catalog items'],
  },
  diff_data: {
    diff_type: 'dml',
    ddl_before: null,
    ddl_after: null,
    dml_rows: [
      {
        row_id: 1,
        change_type: 'update',
        columns: {
          name: { before: 'Ergonomic Mechanical Keyboard', after: 'Ergonomic Mechanical Keyboard' },
          price: { before: '$120.00', after: '$132.00' },
          stock_quantity: { before: 8, after: 8 },
        },
      },
      {
        row_id: 4,
        change_type: 'update',
        columns: {
          name: { before: 'Wireless Noise-Canceling Headphones', after: 'Wireless Noise-Canceling Headphones' },
          price: { before: '$250.00', after: '$275.00' },
          stock_quantity: { before: 5, after: 5 },
        },
      },
      {
        row_id: 7,
        change_type: 'update',
        columns: {
          name: { before: '4K Ultra-HD Monitor 27-inch', after: '4K Ultra-HD Monitor 27-inch' },
          price: { before: '$380.00', after: '$418.00' },
          stock_quantity: { before: 12, after: 12 },
        },
      },
      {
        row_id: 11,
        change_type: 'update',
        columns: {
          name: { before: 'USB-C Multi-Port Docking Station', after: 'USB-C Multi-Port Docking Station' },
          price: { before: '$85.00', after: '$93.50' },
          stock_quantity: { before: 3, after: 3 },
        },
      },
    ],
  },
};

export const MOCK_ALTER_APPROVAL: ApprovalPayload = {
  query_id: 'q_alter_demo_303',
  generated_sql:
    'ALTER TABLE orders\nADD COLUMN discount_code VARCHAR(30) NULL DEFAULT NULL\nAFTER total_amount;\n-- Version Control: Stage 15 Dolt CAS Commit checkpoint',
  target_dialect: 'mysql',
  risk_tier: 'critical',
  impacted_tables: [
    {
      name: 'orders',
      impact_level: 'direct',
      operation: 'ALTER_ADD_COLUMN',
    },
    {
      name: 'order_items',
      impact_level: 'referenced',
      operation: 'FOREIGN_KEY_DEPENDENCY',
    },
  ],
  cost_estimate: {
    estimated_rows: 15400,
    estimated_cost: 320.0,
    scan_type: 'full_table_scan',
    warnings: ['Online DDL metadata update with instant column addition'],
  },
  security_check: {
    deadlock_risk: 'high',
    lock_level: 'TABLE',
    privilege_ok: true,
    flags: [
      'Metadata lock required on table `orders`',
      'Requires stage 15 Dolt CAS transaction checkpoint',
    ],
  },
  diff_data: {
    diff_type: 'ddl',
    ddl_before:
      'CREATE TABLE orders (\n  id INT PRIMARY KEY AUTO_INCREMENT,\n  user_id INT NOT NULL,\n  order_date TIMESTAMP NOT NULL,\n  total_amount DECIMAL(10,2) NOT NULL,\n  status VARCHAR(30) NOT NULL,\n  CONSTRAINT fk_orders_users FOREIGN KEY (user_id) REFERENCES users(id)\n);',
    ddl_after:
      'CREATE TABLE orders (\n  id INT PRIMARY KEY AUTO_INCREMENT,\n  user_id INT NOT NULL,\n  order_date TIMESTAMP NOT NULL,\n  total_amount DECIMAL(10,2) NOT NULL,\n  discount_code VARCHAR(30) NULL DEFAULT NULL,\n  status VARCHAR(30) NOT NULL,\n  CONSTRAINT fk_orders_users FOREIGN KEY (user_id) REFERENCES users(id)\n);',
    dml_rows: null,
  },
};
