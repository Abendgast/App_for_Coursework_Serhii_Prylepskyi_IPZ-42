"""Create projects and test-report result tables.

Revision ID: 0002_projects_and_test_runs
Revises: 0001_create_users
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_projects_and_test_runs"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_projects_owner_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.UniqueConstraint("api_key_hash", name="uq_projects_api_key_hash"),
        sa.UniqueConstraint("owner_id", "name", name="uq_projects_owner_name"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    op.create_table(
        "test_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("report_format", sa.String(length=10), nullable=False),
        sa.Column("build_number", sa.Integer(), nullable=True),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_tests", sa.Integer(), nullable=False),
        sa.Column("passed_tests", sa.Integer(), nullable=False),
        sa.Column("failed_tests", sa.Integer(), nullable=False),
        sa.Column("skipped_tests", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("total_tests >= 0", name="ck_test_runs_total_tests_nonnegative"),
        sa.CheckConstraint("passed_tests >= 0", name="ck_test_runs_passed_tests_nonnegative"),
        sa.CheckConstraint("failed_tests >= 0", name="ck_test_runs_failed_tests_nonnegative"),
        sa.CheckConstraint("skipped_tests >= 0", name="ck_test_runs_skipped_tests_nonnegative"),
        sa.CheckConstraint("duration_seconds >= 0", name="ck_test_runs_duration_nonnegative"),
        sa.CheckConstraint(
            "pass_rate >= 0 AND pass_rate <= 100", name="ck_test_runs_pass_rate_range"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_test_runs_project_id_projects",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_runs"),
    )
    op.create_index("ix_test_runs_project_id", "test_runs", ["project_id"])
    op.create_index("ix_test_runs_created_at", "test_runs", ["created_at"])

    op.create_table(
        "test_suites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["test_runs.id"],
            name="fk_test_suites_run_id_test_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_suites"),
    )
    op.create_index("ix_test_suites_run_id", "test_suites", ["run_id"])

    op.create_table(
        "test_cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("suite_id", sa.String(length=36), nullable=False),
        sa.Column("classname", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'skipped')",
            name="ck_test_cases_status_is_valid",
        ),
        sa.CheckConstraint("duration_seconds >= 0", name="ck_test_cases_duration_nonnegative"),
        sa.ForeignKeyConstraint(
            ["suite_id"],
            ["test_suites.id"],
            name="fk_test_cases_suite_id_test_suites",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_cases"),
    )
    op.create_index("ix_test_cases_suite_id", "test_cases", ["suite_id"])

    op.create_table(
        "test_attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["test_runs.id"],
            name="fk_test_attachments_run_id_test_runs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_test_attachments"),
        sa.UniqueConstraint("run_id", name="uq_test_attachments_run_id"),
    )


def downgrade() -> None:
    op.drop_table("test_attachments")
    op.drop_index("ix_test_cases_suite_id", table_name="test_cases")
    op.drop_table("test_cases")
    op.drop_index("ix_test_suites_run_id", table_name="test_suites")
    op.drop_table("test_suites")
    op.drop_index("ix_test_runs_created_at", table_name="test_runs")
    op.drop_index("ix_test_runs_project_id", table_name="test_runs")
    op.drop_table("test_runs")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_table("projects")
