from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal, init_database
from app.core.security import hash_password
from app.models.enums import Role
from app.models.orm import User
from app.rag.index import index_manager
from app.rag.retrieval import retrieval_service
from app.services.documents import document_service


def create_admin(email: str, name: str, password: str | None) -> None:
    configured = settings.initial_admin_password.get_secret_value()
    value = password or configured or getpass.getpass("管理员密码（至少 8 位）：")
    if len(value) < 8:
        raise SystemExit("密码至少需要 8 位")
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email.lower()))
        if existing:
            existing.role = Role.ADMIN
            existing.is_active = True
            existing.password_hash = hash_password(value)
            existing.name = name
        else:
            db.add(
                User(
                    name=name,
                    email=email.lower(),
                    password_hash=hash_password(value),
                    role=Role.ADMIN,
                )
            )
        db.commit()
    print(f"管理员已就绪: {email}")


def index_corpus(directory: Path, admin_email: str) -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.email == admin_email.lower()))
        if admin is None or admin.role != Role.ADMIN:
            raise SystemExit("请先使用 create-admin 创建对应管理员")
        admin_id = admin.id
    files = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in settings.allowed_extensions
    )
    added = skipped = failed = 0
    for number, path in enumerate(files, start=1):
        try:
            category = path.relative_to(directory).parts[0] if path != directory else "其他"
            document = document_service.import_path(
                path, uploaded_by=admin_id, category=category, rebuild=False
            )
            if document is None:
                skipped += 1
            else:
                added += 1
        except Exception as exc:
            failed += 1
            print(f"[{number}/{len(files)}] 失败 {path.name}: {exc}")
        if number % 50 == 0:
            print(f"进度 {number}/{len(files)}，新增 {added}，跳过 {skipped}，失败 {failed}")
    count = index_manager.rebuild()
    print(f"导入完成：新增 {added}，跳过 {skipped}，失败 {failed}，索引 chunk {count}")


def query(text: str) -> None:
    index_manager.rebuild()
    results = retrieval_service.search(text)
    for index, result in enumerate(results, start=1):
        print(f"[S{index}] score={result.score:.4f} {result.title}")
        print(result.content[:400], "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="CampusQA management CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin")
    admin.add_argument("--email", default=settings.initial_admin_email)
    admin.add_argument("--name", default=settings.initial_admin_name)
    admin.add_argument("--password", default=None)
    index = sub.add_parser("index")
    index.add_argument("directory", nargs="?", default=str(settings.knowledge_dir))
    index.add_argument("--admin-email", default=settings.initial_admin_email)
    search = sub.add_parser("query")
    search.add_argument("text")
    args = parser.parse_args()
    init_database()
    if args.command == "create-admin":
        create_admin(args.email, args.name, args.password)
    elif args.command == "index":
        index_corpus(Path(args.directory), args.admin_email)
    elif args.command == "query":
        query(args.text)


if __name__ == "__main__":
    main()
