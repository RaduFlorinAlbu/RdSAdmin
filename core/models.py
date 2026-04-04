from datetime import timedelta

from django.db import models


# ──────────────────────────────────────────────────────────────────────────────
# Parent
# ──────────────────────────────────────────────────────────────────────────────
class Parent(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, default="")
    phone_number = models.CharField(max_length=30)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Parent"
        verbose_name_plural = "Parents"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ──────────────────────────────────────────────────────────────────────────────
# Therapist
# ──────────────────────────────────────────────────────────────────────────────
class Therapist(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Therapist"
        verbose_name_plural = "Therapists"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ──────────────────────────────────────────────────────────────────────────────
# Child
# ──────────────────────────────────────────────────────────────────────────────
class Child(models.Model):

    class ChildType(models.TextChoices):
        UNDERAGE = "underage", "Underage"
        OVERAGE = "overage", "Overage"

    class Sex(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    child_type = models.CharField(
        "Type",
        max_length=10,
        choices=ChildType.choices,
        default=ChildType.UNDERAGE,
    )
    sex = models.CharField(max_length=10, choices=Sex.choices)
    diagnostic = models.TextField(blank=True, default="")

    # One parent can have many children; each child has exactly one parent.
    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        related_name="children",
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Child"
        verbose_name_plural = "Children"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ──────────────────────────────────────────────────────────────────────────────
# Therapy  (each session is its own row)
#
#   Child  ──1─┐
#               ├──> Therapy (date, start_time, duration)
#   Therapist─1─┘
#
#   A child can have many therapy sessions.
#   A therapist can have many therapy sessions.
#   Each session belongs to exactly one child AND one therapist.
# ──────────────────────────────────────────────────────────────────────────────
class Therapy(models.Model):
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name="therapies",
    )
    therapist = models.ForeignKey(
        Therapist,
        on_delete=models.CASCADE,
        related_name="therapies",
    )
    date = models.DateField()
    start_time = models.TimeField()
    duration = models.DurationField(
        default=timedelta(hours=1, minutes=40),
        help_text="Session duration (default 1 h 40 min).",
    )

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name = "Therapy session"
        verbose_name_plural = "Therapy sessions"
        # Prevent double-booking the same therapist at the same slot
        constraints = [
            models.UniqueConstraint(
                fields=["therapist", "date", "start_time"],
                name="unique_therapist_slot",
            ),
        ]

    def __str__(self):
        return (
            f"{self.child} ↔ {self.therapist} | "
            f"{self.date:%Y-%m-%d} {self.start_time:%H:%M}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Document
# ──────────────────────────────────────────────────────────────────────────────
class Document(models.Model):
    name = models.CharField(
        max_length=200,
        help_text='e.g. "Birth certificate", "Medical report"',
    )
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    exists = models.BooleanField(
        default=False,
        help_text="Has this document been provided?",
    )
    creation_date = models.DateField(
        blank=True,
        null=True,
        help_text="Filled in when the document is provided (exists = True).",
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Can be reset at any time.",
    )

    class Meta:
        ordering = ["child", "name"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        status = "✔" if self.exists else "✘"
        return f"{self.name} [{status}] – {self.child}"
