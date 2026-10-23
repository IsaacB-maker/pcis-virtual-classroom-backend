from django.core.management.base import BaseCommand

from classroom.models import SchoolClass


class Command(BaseCommand):
    help = "Create the default primary school classes P1 to P7"

    def handle(self, *args, **options):
        classes = [
            ("P1", "Primary 1"),
            ("P2", "Primary 2"),
            ("P3", "Primary 3"),
            ("P4", "Primary 4"),
            ("P5", "Primary 5"),
            ("P6", "Primary 6"),
            ("P7", "Primary 7"),
        ]

        for class_code, class_name in classes:
            school_class, created = SchoolClass.objects.get_or_create(
                name=class_code
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {class_name} ({class_code})"
                    )
                )
            else:
                self.stdout.write(
                    f"{class_name} ({class_code}) already exists"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Primary classes are ready."
            )
        )