from django.db import models

# Create your models here.
from django.db import models

class User(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('owner', 'Owner'),
        ('seller', 'Adoption & Seller'),
        ('vet', 'Veterinarian'),
        ('caretaker', 'Pet Caretaker'),
        ('groomer', 'Pet Groomer'),
    )

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    password = models.CharField(max_length=128)
    profile_image = models.ImageField(upload_to='user_profiles/')

    # Extra professional fields (optional)
    qualification = models.CharField(max_length=150, blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    experience = models.IntegerField(blank=True, null=True)
    services_offered = models.TextField(blank=True, null=True)

    is_approved = models.BooleanField(default=False)   # Admin approval
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"


from django.db import models
from petcare.models import User   # adjust app name if needed

class Pet(models.Model):
    PET_TYPE = (
        ('dog', 'Dog'),
        ('cat', 'Cat'),
    )

    GENDER = (
        ('male', 'Male'),
        ('female', 'Female'),
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    pet_image = models.ImageField(upload_to='pet_images/')
    name = models.CharField(max_length=100)
    pet_type = models.CharField(max_length=10, choices=PET_TYPE)
    breed = models.CharField(max_length=100)

    certification = models.FileField(
        upload_to='pet_certificates/', blank=True, null=True
    )

    gender = models.CharField(max_length=10, choices=GENDER)
    color = models.CharField(max_length=50)
    weight = models.FloatField(help_text="Weight in kg")
    dob = models.DateField()

    about_me = models.TextField()
    location = models.CharField(max_length=150)

    google_map_link = models.URLField(
        blank=True, null=True,
        help_text="Paste Google Maps location link"
    )

    views_count = models.PositiveIntegerField(default=0)
    is_for_sale = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'pet')
