from django.core.management.base import BaseCommand

from core.models import Child, _compute_from_cnp


class Command(BaseCommand):
    help = "Recalculează vârsta și tipul (minor/major) pentru toți copiii, bazat pe CNP."

    def handle(self, *args, **options):
        updated = 0
        skipped = 0

        for child in Child.objects.exclude(cnp=""):
            result = _compute_from_cnp(child.cnp)
            if result is None:
                skipped += 1
                continue

            age, is_minor = result
            new_type = Child.ChildType.UNDERAGE if is_minor else Child.ChildType.OVERAGE

            if child.age != age or child.child_type != new_type:
                child.age = age
                child.child_type = new_type
                Child.objects.filter(pk=child.pk).update(
                    age=age,
                    child_type=new_type,
                )
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Recalculare finalizată: {updated} actualizați, {skipped} sărați (CNP invalid)."
            )
        )
