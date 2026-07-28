from django.core.management.base import BaseCommand
from django.db import transaction

from application.models.application import ApplicationFolder
from knowledge.models.knowledge import KnowledgeFolder
from tools.models.tool import ToolFolder
from users.models import User


class Command(BaseCommand):
    help = "Bootstrap workspace root folders"

    def add_arguments(self, parser):
        parser.add_argument("--workspace-id", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        workspace_id = str(options["workspace_id"]).strip()
        if not workspace_id:
            raise ValueError("workspace_id is required")

        user = User.objects.filter(username="admin").first() or User.objects.order_by("create_time").first()

        for folder_model in (KnowledgeFolder, ToolFolder, ApplicationFolder):
            folder_model.objects.get_or_create(
                id=workspace_id,
                defaults={
                    "name": workspace_id,
                    "workspace_id": workspace_id,
                    "user": user,
                    "parent": None,
                },
            )

        self.stdout.write(f"workspace bootstrapped: {workspace_id}")

