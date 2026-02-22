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
    email = models.EmailField()  # Removed unique=True
    phone = models.CharField(max_length=15)
    address = models.TextField()
    
    class Meta:
        unique_together = ('email', 'role')

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

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('treated', 'Treated'),
        ('cancelled', 'Cancelled'),
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owner_appointments')
    vet = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vet_appointments')
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='pet_appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    treatment_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pet.name} with Dr. {self.vet.full_name} on {self.appointment_date}"

class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    METHOD_CHOICES = (
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('cash', 'Cash'),
    )

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)

    def __str__(self):
        return f"Payment for {self.appointment}"

class Review(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews')
    vet = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.PositiveIntegerField(default=5) # 1 to 5
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.vet.full_name} by {self.owner.full_name}"

class CareBooking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='caretaker_bookings')
    caretaker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_care_tasks')
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='care_bookings')
    booking_date = models.DateField()
    booking_time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Care for {self.pet.name} by {self.caretaker.full_name}"

class CarePayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    METHOD_CHOICES = (
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('cash', 'Cash'),
    )

    care_booking = models.OneToOneField(CareBooking, on_delete=models.CASCADE, related_name='care_payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)

    def __str__(self):
        return f"Payment for {self.care_booking}"

class CareReview(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_care_reviews')
    caretaker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_care_reviews')
    care_booking = models.ForeignKey(CareBooking, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.PositiveIntegerField(default=5) # 1 to 5
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.caretaker.full_name} by {self.owner.full_name}"
