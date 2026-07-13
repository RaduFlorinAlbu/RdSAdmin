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
    phone_number = models.CharField("Număr de telefon", max_length=30, blank=True, default="")

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Părinte"
        verbose_name_plural = "Părinți"

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


# ──────────────────────────────────────────────────────────────────────────────
# Centru
# ──────────────────────────────────────────────────────────────────────────────
class Centru(models.Model):
    name = models.CharField("Nume", max_length=200, unique=True)

    class Meta:
        verbose_name = "Centru"
        verbose_name_plural = "Centre"

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────────────────────────────────────
# Terapeut
# ──────────────────────────────────────────────────────────────────────────────
class Therapist(models.Model):
    first_name = models.CharField("Prenume", max_length=100)
    last_name = models.CharField("Nume", max_length=100)
    centru = models.ForeignKey(
        Centru,
        verbose_name="Centru",
        on_delete=models.PROTECT,
        related_name="therapists",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Terapeut"
        verbose_name_plural = "Terapeuți"

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


# ──────────────────────────────────────────────────────────────────────────────
# Pacient
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
    sex = models.CharField("Sex", max_length=10, choices=Sex.choices, blank=True, default="")
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

    # Un părinte poate avea mai mulți copii; fiecare copil minor are exact un părinte.
    # Pacienții majori pot fi fără părinte.
    parent = models.ForeignKey(
        Parent,
        verbose_name="Părinte",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Pacient"
        verbose_name_plural = "Pacienți"

    def clean(self):
        if self.cnp:
            result = _compute_from_cnp(self.cnp)
            if result is None:
                raise ValidationError(
                    {"cnp": "CNP invalid – trebuie să conțină exact 13 cifre corecte."}
                )
            _, is_minor = result
            if is_minor and not self.parent_id:
                raise ValidationError(
                    {"parent": "Părintele este obligatoriu pentru pacienții minori."}
                )
        elif self.child_type == self.ChildType.UNDERAGE and not self.parent_id:
            raise ValidationError(
                {"parent": "Părintele este obligatoriu pentru pacienții minori."}
            )

    def save(self, *args, **kwargs):
        if self.cnp:
            result = _compute_from_cnp(self.cnp)
            if result is not None:
                self.age, is_minor = result
                self.child_type = (
                    self.ChildType.UNDERAGE if is_minor else self.ChildType.OVERAGE
                )
            # Sex from first CNP digit: odd (1,3,5,7) → masculin, even (2,4,6,8) → feminin
            first = self.cnp[0]
            if first in ('1', '3', '5', '7'):
                self.sex = self.Sex.MALE
            elif first in ('2', '4', '6', '8'):
                self.sex = self.Sex.FEMALE
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


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
        verbose_name="Pacient",
        on_delete=models.CASCADE,
        related_name="therapies",
    )
    therapist = models.ForeignKey(
        Therapist,
        verbose_name="Terapeut",
        on_delete=models.CASCADE,
        related_name="therapies",
    )
    centru = models.ForeignKey(
        "Centru",
        verbose_name="Centru (snapshot)",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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

    def save(self, *args, **kwargs):
        # Snapshot centru from therapist at save time if not already set
        if self.centru_id is None and self.therapist_id:
            try:
                self.centru = Therapist.objects.select_related("centru").get(pk=self.therapist_id).centru
            except Therapist.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.child} ↔ {self.therapist} | "
            f"{self.date:%Y-%m-%d} {self.start_time:%H:%M}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Document
# ──────────────────────────────────────────────────────────────────────────────
class Document(models.Model):
    FISA_INITIALA  = "Fișă de evaluare inițială"
    FISA_PERIODICA = "Fișă de evaluare periodică"

    name = models.CharField(
        "Nume document",
        max_length=200,
        help_text='ex: "Certificat de naștere", "Raport medical"',
    )
    child = models.ForeignKey(
        Child,
        verbose_name="Pacient",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    exists = models.BooleanField(
        "Există",
        default=False,
        help_text="A fost furnizat acest document?",
    )
    has_expiry = models.BooleanField(
        "Are dată de expirare",
        default=True,
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
        verbose_name = "Document pacient"
        verbose_name_plural = "Documente pacienți"

    def clean(self):
        if self.has_expiry and not self.expiry_date:
            raise ValidationError(
                {"expiry_date": "Completează data de expirare sau deselectează „Are dată de expirare‟."}
            )

    def save(self, *args, **kwargs):
        if self.creation_date:
            self.exists = True
        super().save(*args, **kwargs)
        # When a "Fișă de evaluare periodică" is saved, mark all "inițială" docs
        # for this patient as has_expiry=False so they stop appearing in warnings.
        if self.name == self.FISA_PERIODICA and self.child_id:
            Document.objects.filter(
                child_id=self.child_id,
                name=self.FISA_INITIALA,
            ).update(has_expiry=False)

    def __str__(self):
        status = "✔" if self.exists else "✘"
        return f"{self.name} [{status}] – {self.child}"


# ──────────────────────────────────────────────────────────────────────────────
# Document eligibilitate psiholog
# ──────────────────────────────────────────────────────────────────────────────
def _therapist_doc_upload_path(instance, filename):
    return f"therapist_docs/{instance.therapist_id}/{filename}"


class TherapistDocument(models.Model):
    therapist = models.ForeignKey(
        Therapist,
        verbose_name="Terapeut",
        on_delete=models.CASCADE,
        related_name="eligibility_documents",
    )
    name = models.CharField("Nume document", max_length=200)
    has_expiry = models.BooleanField(
        "Are dată de expirare",
        default=False,
    )
    expiry_date = models.DateField(
        "Dată expirare",
        blank=True,
        null=True,
    )
    pdf_file = models.FileField(
        "Fișier PDF",
        upload_to=_therapist_doc_upload_path,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["therapist", "name"]
        verbose_name = "Document eligibilitate psiholog"
        verbose_name_plural = "Documente eligibilitate psiholog"

    def clean(self):
        if self.has_expiry and not self.expiry_date:
            raise ValidationError(
                {"expiry_date": "Completează data de expirare sau deselectează \u201eAre dată de expirare\u201f."}
            )

    def __str__(self):
        return f"{self.name} – {self.therapist}"
