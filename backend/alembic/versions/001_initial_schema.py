"""Initial schema: organizations, users, subscriptions, audit_logs

Revision ID: 001
Revises: 
Create Date: 2026-05-14 00:00:00.000000

This migration creates the foundational PostgreSQL schema for TenderMatch Phase 2.
Tables:
  - organizations  (tenant root)
  - users          (identity + auth, FK → organizations)
  - subscriptions  (billing + feature limits, one-to-one with organizations)
  - audit_logs     (immutable action trail, FK → users)

All tables use UUID primary keys.
The pgvector extension is enabled via init_pgvector.sql (not in this migration).
Vector tables (tenders_embeddings, vendor_embeddings) will be added in Phase 3.
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. organizations ──────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("mongo_id", sa.String(24), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_organizations_mongo_id", "organizations", ["mongo_id"], unique=True)
    op.create_index("ix_organizations_name", "organizations", ["name"])

    # ── 2. users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("mongo_id", sa.String(24), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="USER"),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_mongo_id", "users", ["mongo_id"], unique=True)
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_email_active", "users", ["email", "is_active"])

    # ── Add FK from organizations.owner_id → users.id (deferred, circular ref) ──
    op.create_foreign_key(
        "fk_organizations_owner_id_users",
        "organizations",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── 3. subscriptions ──────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("status", sa.String(50), nullable=False, server_default="trialing"),
        sa.Column("max_vendor_profiles", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("max_tenders_per_month", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("max_match_runs_per_day", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("email_notifications_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ai_explanation_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("external_subscription_id", sa.String(255), nullable=True),
        sa.Column("external_customer_id", sa.String(255), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_subscriptions_org_id", "subscriptions", ["org_id"], unique=True)
    op.create_index("ix_subscriptions_external_id", "subscriptions", ["external_subscription_id"])

    # ── 4. audit_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_org_id", "audit_logs", ["org_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_org_created", "audit_logs", ["org_id", "created_at"])
    op.create_index("ix_audit_logs_action_status", "audit_logs", ["action", "status"])


def downgrade() -> None:
    # Drop in reverse order to avoid FK constraint violations
    op.drop_table("audit_logs")
    op.drop_table("subscriptions")
    op.drop_constraint("fk_organizations_owner_id_users", "organizations", type_="foreignkey")
    op.drop_table("users")
    op.drop_table("organizations")
