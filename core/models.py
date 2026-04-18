import re
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models


def _compute_from_cnp(cnp: str):
    """Calculează (vârstă, este_minor) din CNP românesc folosind cifrele 2-7.
    Logica an: dacă yy <= ultimele 2 cifre ale anului curent → 2000+yy, altfel 1900+yy.
    Returnează None dacă CNP-ul e invalid.
    """
    if not re.fullmatch(r"\d{13}", cnp):
        return None
    yy = int(cnp[1:3])
    mm = int(cnp[3:5])
    dd = int(cnp[5:7])
    current_yy = date.today().year % 100
    century = 2000 if yy <= current_yy else 1900
    try:
        birth_date = date(century + yy, mm, dd)
    except ValueError:
        return None
    today = date.today()
    age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    return age, age < 18


# ──────────────────────────────────────────────────────────────────────────────
# Părinte
# ──────────────────────────────────────────────────────────────────────────────
class Parent(models.Model):
    first_name = models.CharField("Prenume", max_length=100)
    last_name = models.CharField("Nume", max_length=100)
    email = models.EmailField("Email", blank=True, default="")
    phone_number = models.CharField("Număr de telefon", max_length=30)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Părinte"
        verbose_name_plural = "Părinți"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ──────────────────────────────────────────────────────────────────────────────
# Terapeut
# ──────────────────────────────────────────────────────────────────────────────
class Therapist(models.Model):
    first_name = models.CharField("Prenume", max_length=100)
    last_name = models.CharField("Nume", max_length=100)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Terapeut"
        verbose_name_plural = "Terapeuți"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ──────────────────────────────────────────────────────────────────────────────
# Copil
# ──────────────────────────────────────────────────────────────────────────────
class Child(models.Model):

    class ChildType(models.TextChoices):
        UNDERAGE = "underage", "Minor"
        OVERAGE = "overage", "Major"

    class Sex(models.TextChoices):
        MALE = "male", "Masculin"
        FEMALE = "female", "Feminin"

    class Diagnostic(models.TextChoices):
        F84 = "F84", "F84"
        F349 = "349", "349"

    class Status(models.TextChoices):
        ACTIV = "activ", "Activ"
        ARHIVAT = "arhivat", "Arhivat"

    first_name = models.CharField("Prenume", max_length=100)
    last_name = models.CharField("Nume", max_length=100)
    cnp = models.CharField(
        "CNP",
        max_length=13,
        unique=True,
        default="",
        help_text="13 cifre – vârsta și tipul (minor/major) se calculează automat.",
    )
    age = models.PositiveIntegerField("Vârstă", default=0)
    child_type = models.CharField(
        "Tip",
        max_length=10,
        choices=ChildType.choices,
        default=ChildType.UNDERAGE,
    )
    sex = models.CharField("Sex", max_length=10, choices=Sex.choices)
    diagnostic = models.CharField(
        "Diagnostic",
        max_length=10,
        choices=Diagnostic.choices,
        blank=False,
        default="",
    )
    status = models.CharField(
        "Status",
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIV,
    )

    # Un părinte poate avea mai mulți copii; fiecare copil are exact un părinte.
    parent = models.ForeignKey(
        Parent,
        verbose_name="Părinte",
        on_delete=models.CASCADE,
        related_name="children",
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Copil"
        verbose_name_plural = "Copii"

    def clean(self):
        if self.cnp:
            if _compute_from_cnp(self.cnp) is None:
                raise ValidationError(
                    {"cnp": "CNP invalid – trebuie să conțină exact 13 cifre corecte."}
                )

    def save(self, *args, **kwargs):
        if self.cnp:
            result = _compute_from_cnp(self.cnp)
            if result is not None:
                self.age, is_minor = result
                self.child_type = (
                    self.ChildType.UNDERAGE if is_minor else self.ChildType.OVERAGE
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# ──────────────────────────────────────────────────────────────────────────────
# Terapie  (fiecare ședință este o înregistrare separată)
#
#   Copil   ──1─┐
#               ├──> Terapie (dată, oră start, durată)
#   Terapeut──1─┘
#
#   Un copil poate avea mai multe ședințe de terapie.
#   Un terapeut poate avea mai multe ședințe de terapie.
#   Fiecare ședință aparține exact unui copil ȘI unui terapeut.
# ──────────────────────────────────────────────────────────────────────────────
class Therapy(models.Model):
    child = models.ForeignKey(
        Child,
        verbose_name="Copil",
        on_delete=models.CASCADE,
        related_name="therapies",
    )
    therapist = models.ForeignKey(
        Therapist,
        verbose_name="Terapeut",
        on_delete=models.CASCADE,
        related_name="therapies",
    )
    date = models.DateField("Dată")
    start_time = models.TimeField("Oră start")

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name = "Ședință de terapie"
        verbose_name_plural = "Ședințe de terapie"
        # Previne dubla programare a aceluiași terapeut în același interval
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
        "Nume document",
        max_length=200,
        help_text='ex: "Certificat de naștere", "Raport medical"',
    )
    child = models.ForeignKey(
        Child,
        verbose_name="Copil",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    exists = models.BooleanField(
        "Există",
        default=False,
        help_text="A fost furnizat acest document?",
    )
    creation_date = models.DateField(
        "Dată creare",
        blank=True,
        null=True,
        help_text="Se completează când documentul este furnizat (Există = Da).",
    )
    expiry_date = models.DateField(
        "Dată expirare",
        blank=True,
        null=True,
        help_text="Poate fi resetată oricând.",
    )

    class Meta:
        ordering = ["child", "name"]
        verbose_name = "Document"
        verbose_name_plural = "Documente"

    def __str__(self):
        status = "✔" if self.exists else "✘"
        return f"{self.name} [{status}] – {self.child}"
