from __future__ import annotations

from datetime import UTC, datetime
import json
import sqlite3

from .security import (
    ROLE_PERMISSIONS,
    hash_password,
    new_session_token,
    role_allows,
    session_expiry_timestamp,
    verify_password,
)
from .services import ValidationError


DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


def ensure_default_admin(connection: sqlite3.Connection) -> None:
    user = connection.execute("SELECT user_id FROM app_users LIMIT 1").fetchone()
    if user is not None:
        return

    connection.execute(
        """
        INSERT INTO app_users (
            username,
            full_name,
            password_hash,
            role
        )
        VALUES (?, ?, ?, 'ADMIN')
        """,
        (
            DEFAULT_ADMIN_USERNAME,
            "Administrador do Sistema",
            hash_password(DEFAULT_ADMIN_PASSWORD),
        ),
    )


def authenticate_user(
    connection: sqlite3.Connection,
    username: str,
    password: str,
    ip_address: str = "",
    user_agent: str = "",
) -> tuple[str, dict[str, object]]:
    user = connection.execute(
        """
        SELECT
            user_id,
            username,
            full_name,
            password_hash,
            role,
            is_active
        FROM app_users
        WHERE username = ?
        """,
        (username.strip(),),
    ).fetchone()

    if user is None or not user["is_active"] or not verify_password(password, user["password_hash"]):
        raise ValidationError("Utilizador ou senha invalidos.")

    token = new_session_token()
    expires_at = session_expiry_timestamp()
    connection.execute(
        """
        INSERT INTO app_sessions (
            user_id,
            session_token,
            ip_address,
            user_agent,
            expires_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (user["user_id"], token, ip_address or None, user_agent or None, expires_at),
    )
    connection.execute(
        """
        UPDATE app_users
        SET last_login_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (user["user_id"],),
    )

    public_user = {
        "user_id": user["user_id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
    }
    return token, public_user


def get_user_by_session(connection: sqlite3.Connection, session_token: str | None) -> dict[str, object] | None:
    if not session_token:
        return None

    session = connection.execute(
        """
        SELECT
            s.session_id,
            s.user_id,
            s.expires_at,
            u.username,
            u.full_name,
            u.role,
            u.is_active
        FROM app_sessions s
        JOIN app_users u ON u.user_id = s.user_id
        WHERE s.session_token = ?
        """,
        (session_token,),
    ).fetchone()

    if session is None:
        return None

    expires_at = datetime.strptime(session["expires_at"], "%Y-%m-%d %H:%M:%S")
    if expires_at.replace(tzinfo=UTC) <= datetime.now(UTC) or not session["is_active"]:
        connection.execute("DELETE FROM app_sessions WHERE session_id = ?", (session["session_id"],))
        connection.commit()
        return None

    connection.execute(
        """
        UPDATE app_sessions
        SET last_seen_at = CURRENT_TIMESTAMP,
            expires_at = ?
        WHERE session_id = ?
        """,
        (session_expiry_timestamp(), session["session_id"]),
    )
    connection.commit()

    return {
        "user_id": session["user_id"],
        "username": session["username"],
        "full_name": session["full_name"],
        "role": session["role"],
    }


def destroy_session(connection: sqlite3.Connection, session_token: str | None) -> None:
    if not session_token:
        return
    connection.execute("DELETE FROM app_sessions WHERE session_token = ?", (session_token,))


def list_users(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            user_id,
            username,
            full_name,
            role,
            is_active,
            last_login_at,
            created_at
        FROM app_users
        ORDER BY full_name, username
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_user(connection: sqlite3.Connection, form: dict[str, str]) -> int:
    username = form.get("username", "").strip().lower()
    full_name = form.get("full_name", "").strip()
    password = form.get("password", "")
    role = form.get("role", "").strip().upper()

    if not username:
        raise ValidationError("Informe o nome de utilizador.")
    if not full_name:
        raise ValidationError("Informe o nome completo.")
    if len(password) < 6:
        raise ValidationError("A senha precisa ter pelo menos 6 caracteres.")
    if role not in ROLE_PERMISSIONS:
        raise ValidationError("Escolha um papel valido.")

    cursor = connection.execute(
        """
        INSERT INTO app_users (
            username,
            full_name,
            password_hash,
            role
        )
        VALUES (?, ?, ?, ?)
        """,
        (username, full_name, hash_password(password), role),
    )
    return int(cursor.lastrowid)


def change_user_password(
    connection: sqlite3.Connection,
    user_id: int,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> None:
    user = connection.execute(
        """
        SELECT
            user_id,
            password_hash
        FROM app_users
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    if user is None:
        raise ValidationError("Utilizador nao encontrado.")
    if not verify_password(current_password, user["password_hash"]):
        raise ValidationError("A senha atual nao confere.")
    if len(new_password) < 6:
        raise ValidationError("A nova senha precisa ter pelo menos 6 caracteres.")
    if new_password != confirm_password:
        raise ValidationError("A confirmacao da nova senha nao confere.")
    if new_password == current_password:
        raise ValidationError("A nova senha precisa ser diferente da atual.")

    connection.execute(
        """
        UPDATE app_users
        SET password_hash = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (hash_password(new_password), user_id),
    )


def list_audit_logs(connection: sqlite3.Connection, limit: int = 100) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            a.audit_log_id,
            a.created_at,
            a.action,
            a.entity_type,
            a.entity_id,
            a.details,
            COALESCE(u.full_name, 'Sistema') AS actor_name
        FROM audit_logs a
        LEFT JOIN app_users u ON u.user_id = a.user_id
        ORDER BY a.audit_log_id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def write_audit_log(
    connection: sqlite3.Connection,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    user_id: int | None = None,
    details: dict[str, object] | str | None = None,
    ip_address: str = "",
) -> None:
    payload = details
    if isinstance(details, dict):
        payload = json.dumps(details, ensure_ascii=True)

    connection.execute(
        """
        INSERT INTO audit_logs (
            user_id,
            action,
            entity_type,
            entity_id,
            details,
            ip_address
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            action,
            entity_type,
            None if entity_id is None else str(entity_id),
            payload,
            ip_address or None,
        ),
    )


def get_business_settings(connection: sqlite3.Connection) -> dict[str, object]:
    row = connection.execute("SELECT * FROM business_settings WHERE settings_id = 1").fetchone()
    return dict(row)


def update_business_settings(connection: sqlite3.Connection, form: dict[str, str]) -> None:
    company_name = form.get("company_name", "").strip()
    if not company_name:
        raise ValidationError("Informe o nome da empresa.")

    default_tax_rate = form.get("default_tax_rate", "0").strip().replace(",", ".") or "0"
    invoice_prefix = form.get("invoice_prefix", "").strip().upper() or "INV"

    connection.execute(
        """
        UPDATE business_settings
        SET company_name = ?,
            tax_id = ?,
            company_address = ?,
            company_phone = ?,
            company_email = ?,
            currency_code = ?,
            currency_symbol = ?,
            tax_label = ?,
            default_tax_rate = ?,
            invoice_prefix = ?,
            receipt_footer = ?,
            legal_notice = ?,
            require_customer_tax_number = ?
        WHERE settings_id = 1
        """,
        (
            company_name,
            form.get("tax_id", "").strip() or None,
            form.get("company_address", "").strip() or None,
            form.get("company_phone", "").strip() or None,
            form.get("company_email", "").strip() or None,
            form.get("currency_code", "AOA").strip().upper() or "AOA",
            form.get("currency_symbol", "Kz").strip() or "Kz",
            form.get("tax_label", "IVA").strip() or "IVA",
            default_tax_rate,
            invoice_prefix,
            form.get("receipt_footer", "").strip() or None,
            form.get("legal_notice", "").strip() or None,
            1 if form.get("require_customer_tax_number") else 0,
        ),
    )


def has_permission(user: dict[str, object] | None, permission: str) -> bool:
    if user is None:
        return False
    return role_allows(str(user["role"]), permission)

