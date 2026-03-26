from django.db import models
from django.core.exceptions import ValidationError

class FamilyMember(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    name = models.CharField(max_length=200)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )

    spouse = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reverse_spouse'
    )

    date_of_birth = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='family_photos/', null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


    # ==========================
    # 1. VALIDATION LOGIC
    # ==========================
    def clean(self):
        # Self checks
        if self.parent == self:
            raise ValidationError("A person cannot be their own parent.")
        if self.spouse == self:
            raise ValidationError("A person cannot marry themselves.")

        # Parent circular check
        ancestor = self.parent
        while ancestor:
            if ancestor == self:
                raise ValidationError("Circular parent relationship detected.")
            ancestor = ancestor.parent

        if self.spouse:
            # Spouse already married
            if self.spouse.spouse and self.spouse.spouse != self:
                raise ValidationError(f"{self.spouse.name} is already married.")

            # Prevent marrying ancestors
            ancestor = self.parent
            while ancestor:
                if ancestor == self.spouse:
                    raise ValidationError(
                        f"Invalid marriage: {self.spouse.name} is an ancestor of {self.name}."
                    )
                ancestor = ancestor.parent

            # Prevent marrying descendants
            if self.pk:
                def check_descendants(member):
                    for child in member.children.all():
                        if child == self.spouse:
                            raise ValidationError(
                                f"Invalid marriage: {self.spouse.name} is a descendant of {self.name}."
                            )
                        check_descendants(child)

                check_descendants(self)


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)