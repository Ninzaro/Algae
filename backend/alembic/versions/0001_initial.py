"""initial schema — all core tables

Revision ID: 0001_initial
Revises: None
Create Date: 2026-09-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "bars",
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False, server_default="1d"),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("asset_class", sa.String(16), nullable=False, server_default="equity"),
        sa.PrimaryKeyConstraint("symbol", "timestamp", "timeframe"),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("strategy_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signals_strategy_id", "signals", ["strategy_id"])
    op.create_index("ix_signals_symbol", "signals", ["symbol"])
    op.create_index("ix_signals_timestamp", "signals", ["timestamp"])

    op.create_table(
        "orders",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("intent_id", sa.String(36), nullable=False),
        sa.Column("strategy_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("filled_quantity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("order_type", sa.String(16), nullable=False, server_default="market"),
        sa.Column("limit_price", sa.Float(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("broker_order_id", sa.String(64), nullable=True),
        sa.Column("avg_fill_price", sa.Float(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_intent_id", "orders", ["intent_id"])
    op.create_index("ix_orders_strategy_id", "orders", ["strategy_id"])
    op.create_index("ix_orders_symbol", "orders", ["symbol"])
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "fills",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fee", sa.Float(), nullable=False, server_default="0.0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fills_order_id", "fills", ["order_id"])
    op.create_index("ix_fills_symbol", "fills", ["symbol"])
    op.create_index("ix_fills_timestamp", "fills", ["timestamp"])

    op.create_table(
        "positions",
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("avg_price", sa.Float(), nullable=False),
        sa.Column("market_price", sa.Float(), nullable=False),
        sa.Column("unrealized_pnl", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )

    op.create_table(
        "equity",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("cash", sa.Float(), nullable=False),
        sa.Column("equity", sa.Float(), nullable=False),
        sa.Column("peak_equity", sa.Float(), nullable=False),
        sa.Column("drawdown_pct", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("timestamp", "id"),
    )

    op.create_table(
        "journal_entries",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint("timestamp", "id"),
    )
    op.create_index("ix_journal_event_type", "journal_entries", ["event_type"])
    op.create_index("ix_journal_correlation_id", "journal_entries", ["correlation_id"])

    op.create_table(
        "account_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cash", sa.Float(), nullable=False),
        sa.Column("peak_equity", sa.Float(), nullable=False),
        sa.Column("daily_start_equity", sa.Float(), nullable=False),
        sa.Column("daily_reset_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("orders_today", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("kill_switch", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("kill_reason", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "signal_holds",
        sa.Column("strategy_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("bar_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("strategy_id", "symbol"),
    )

    op.create_table(
        "strategies",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("symbols", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("timeframe", sa.String(8), nullable=False, server_default="1d"),
        sa.Column("params", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("strategies")
    op.drop_table("signal_holds")
    op.drop_table("account_state")
    op.drop_index("ix_journal_correlation_id", "journal_entries")
    op.drop_index("ix_journal_event_type", "journal_entries")
    op.drop_table("journal_entries")
    op.drop_table("equity")
    op.drop_table("positions")
    op.drop_index("ix_fills_timestamp", "fills")
    op.drop_index("ix_fills_symbol", "fills")
    op.drop_index("ix_fills_order_id", "fills")
    op.drop_table("fills")
    op.drop_index("ix_orders_status", "orders")
    op.drop_index("ix_orders_symbol", "orders")
    op.drop_index("ix_orders_strategy_id", "orders")
    op.drop_index("ix_orders_intent_id", "orders")
    op.drop_table("orders")
    op.drop_index("ix_signals_timestamp", "signals")
    op.drop_index("ix_signals_symbol", "signals")
    op.drop_index("ix_signals_strategy_id", "signals")
    op.drop_table("signals")
    op.drop_table("bars")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")
