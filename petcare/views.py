from django.shortcuts import render

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from .models import User, Pet, Appointment, Payment, Review, CareBooking, CarePayment, CareReview
import os
import random
from django.conf import settings
from .ml_utils import predict_pet_breed
from django.core.files.storage import default_storage
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Count, Avg
import re


# Create your views here.
# Triggering server reload
from .models import Like

def index(request):
    return render(request,'index.html')

def discover_pets(request):
    pets = Pet.objects.all().order_by('-created_at')
    return render(request, 'discover_pets.html', {'pets': pets})


def register(request):
    if request.method == 'POST':
        data = request.POST

        email = data['email']
        password = data['password']
        confirm_password = data.get('confirm_password')
        phone = data['phone']

        # --- Server-Side Validations ---
        
        # 1. Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        # 2. Validate Email Format
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format")
            return redirect('register')

        # 3. Validate Phone Number (10 digits)
        if not re.fullmatch(r'\d{10}', phone):
            messages.error(request, "Phone number must be exactly 10 digits")
            return redirect('register')

        # 4. Password Complexity
        # At least 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char
        password_regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        if not re.fullmatch(password_regex, password):
            messages.error(request, "Password must be at least 8 characters long and include uppercase, lowercase, number, and special character")
            return redirect('register')

        # 5. Check if email already exists for this role
        if User.objects.filter(email=email, role=data['role']).exists():
            messages.error(request, "Account with this email and role already exists")
            return redirect('register')

        if data['role'] == 'owner':
            # Handle Pet Owner specific OPT flow
            # Generate a 6-digit OTP
            otp = str(random.randint(100000, 999999))
            
            # Save the profile image uniquely for temp access
            profile_image = request.FILES['profile_image']
            temp_img_path = default_storage.save(f"temp/{profile_image.name}", profile_image)

            # Store OTP and form data in session
            request.session['otp'] = otp
            request.session['registration_data'] = {
                'full_name': data['full_name'],
                'email': email,
                'phone': phone,
                'address': data['address'],
                'role': 'owner',
                'password': password,  # Storing unhashed momentarily is less ideal, but acceptable for rapid dev workflow. Let's hash it instead to be safe.
            }
            # Actually store password securely hash to use later
            request.session['registration_temp_password'] = make_password(password)
            request.session['registration_temp_image'] = temp_img_path

            # Send Email (console backend for testing)
            send_mail(
                'Verify Your Pet Care Account',
                f'Your verification code is: {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            messages.success(request, "An OTP has been sent to your email. Please verify.")
            return redirect('verify_otp')

        else:
            # Existing flow for vets and caretakers (requires admin approval)
            user = User(
                full_name=data['full_name'],
                email=email,
                phone=phone,
                address=data['address'],
                role=data['role'],
                password=make_password(password),
                profile_image=request.FILES['profile_image']
            )

            if data['role'] in ['vet']:
                user.qualification = data.get('qualification')
                user.registration_number = data.get('registration_number')

            if data['role'] in ['caretaker', 'groomer']:
                user.experience = data.get('experience')
                user.services_offered = data.get('services_offered')

            user.save()

            messages.success(request, "Registration successful. Waiting for admin approval.")
            return redirect('login')

    return render(request,'register.html')

def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        session_otp = request.session.get('otp')

        if session_otp and entered_otp == session_otp:
            # Success, retrieve data
            reg_data = request.session.get('registration_data')
            temp_pass = request.session.get('registration_temp_password')
            temp_img = request.session.get('registration_temp_image')

            if reg_data and temp_pass:
                user = User(
                    full_name=reg_data['full_name'],
                    email=reg_data['email'],
                    phone=reg_data['phone'],
                    address=reg_data['address'],
                    role=reg_data['role'],
                    password=temp_pass,
                    is_approved=True # Pet owners are approved immediately
                )
                
                # Fetch temp image and assign to profile_image
                if temp_img and default_storage.exists(temp_img):
                    # For simplicity, assign the relative temp path. Django handles it fine.
                    user.profile_image = temp_img 
                
                user.save()

                # Clean up session keys
                del request.session['otp']
                del request.session['registration_data']
                del request.session['registration_temp_password']
                del request.session['registration_temp_image']

                messages.success(request, "Email verified and registration complete. Please login.")
                return redirect('login')
            else:
                messages.error(request, "Registration session expired. Please register again.")
                return redirect('register')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            
    return render(request, 'verify_otp.html')

def login(request):
    # Redirect if already logged in
    if request.session.get('user_id'):
        role = request.session.get('role')
        return redirect(f"{role}_dashboard")

    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        role = request.POST['role']

        try:
            # Check for user with specific email AND role in the custom User model
            user = User.objects.get(email=email, role=role)

            if not user.is_approved:
                messages.error(request, "Account not approved by admin")
                return redirect('login')

            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['role'] = user.role
                request.session['name'] = user.full_name

                return redirect(f"{user.role}_dashboard")

            messages.error(request, "Invalid password")

        except User.DoesNotExist:
            # Fallback for Django Superuser if role is admin
            if role == 'admin':
                from django.contrib.auth import authenticate
                from django.contrib.auth.models import User as DjangoUser
                
                try:
                    # Try to find a Django user with this email
                    django_auth_user = DjangoUser.objects.get(email=email)
                    authenticated_user = authenticate(username=django_auth_user.username, password=password)
                    
                    if authenticated_user and (authenticated_user.is_superuser or authenticated_user.is_staff):
                        # Use auth_login for superusers to maintain Django auth state if needed
                        from django.contrib.auth import login as auth_login
                        auth_login(request, authenticated_user)
                        
                        request.session['user_id'] = authenticated_user.id
                        request.session['role'] = 'admin'
                        request.session['name'] = authenticated_user.username
                        return redirect('admin_dashboard')
                except DjangoUser.DoesNotExist:
                    # Also try to authenticate by username if they entered username in the email field
                    authenticated_user = authenticate(username=email, password=password)
                    if authenticated_user and (authenticated_user.is_superuser or authenticated_user.is_staff):
                        from django.contrib.auth import login as auth_login
                        auth_login(request, authenticated_user)
                        
                        request.session['user_id'] = authenticated_user.id
                        request.session['role'] = 'admin'
                        request.session['name'] = authenticated_user.username
                        return redirect('admin_dashboard')

            messages.error(request, "No account found with this email and role")

    return render(request, 'login.html')
def role_required(role):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.session.get('role') != role:
                return redirect('login')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@role_required('admin')
def admin_dashboard(request):
    role_filter = request.GET.get('role')
    
    if role_filter:
        users = User.objects.filter(role=role_filter).order_by('-created_at')
    else:
        users = User.objects.all().exclude(role='admin').order_by('-created_at')

    return render(request, 'admin_dashboard.html', {
        'users': users,
        'current_role': role_filter
    })

@role_required('admin')
def admin_vets(request):
    vets = User.objects.filter(role='vet').annotate(
        avg_rating=Avg('received_reviews__rating'),
        appointment_count=Count('vet_appointments')
    ).order_by('-avg_rating', '-appointment_count')
    return render(request, 'admin_vets.html', {'vets': vets})

@role_required('admin')
def admin_caretakers(request):
    caretakers = User.objects.filter(role='caretaker').annotate(
        avg_rating=Avg('received_care_reviews__rating'),
        booking_count=Count('my_care_tasks')
    ).order_by('-avg_rating', '-booking_count')
    return render(request, 'admin_caretakers.html', {'caretakers': caretakers})


@role_required('admin')
def approve_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_approved = True
        user.save()
        messages.success(request, f"User {user.full_name} has been approved.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")
    
    return redirect('admin_dashboard')


from django.utils import timezone

@role_required('owner')
def owner_dashboard(request):
    pets = Pet.objects.filter(owner_id=request.session['user_id'])
    appointments = Appointment.objects.filter(owner_id=request.session['user_id']).order_by('-appointment_date', '-appointment_time')
    care_bookings = CareBooking.objects.filter(owner_id=request.session['user_id']).order_by('-booking_date', '-booking_time')
    return render(request, 'owner_dashboard.html', {
        'pets': pets,
        'appointments': appointments,
        'care_bookings': care_bookings,
        'today': timezone.now().date()
    })

def pet_profile(request, pet_id):
    try:
        pet = Pet.objects.get(id=pet_id)
        # Increment view count
        pet.views_count += 1
        pet.save()
        
        user_id = request.session.get('user_id')
        is_liked = False
        if user_id:
            is_liked = Like.objects.filter(user_id=user_id, pet=pet).exists()

        return render(request, 'pet_profile.html', {
            'pet': pet,
            'is_liked': is_liked,
            'likes_count': pet.likes.count()
        })
    except Pet.DoesNotExist:
        messages.error(request, "Pet profile not found")
        return redirect('owner_dashboard')

def like_pet(request, pet_id):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Please login to like pets")
        return redirect('login')
    
    pet = Pet.objects.get(id=pet_id)
    like_obj, created = Like.objects.get_or_create(user_id=user_id, pet=pet)
    
    if not created:
        like_obj.delete()
        messages.info(request, "Unliked pet profile")
    else:
        messages.success(request, "Liked pet profile!")
        
    return redirect('pet_profile', pet_id=pet_id)


@role_required('seller')
def seller_dashboard(request):
    return render(request, 'seller_dashboard.html')


@role_required('vet')
def vet_dashboard(request):
    vet_id = request.session['user_id']
    appointments = Appointment.objects.filter(vet_id=vet_id).order_by('-appointment_date', '-appointment_time')
    
    # Simple stats
    pending_count = appointments.filter(status='pending').count()
    treated_count = appointments.filter(status='treated').count()
    
    # Reviews - with pre-rendered HTML to bypass destructive auto-formatting
    reviews = Review.objects.filter(vet_id=vet_id).order_by('-created_at')
    for review in reviews:
        # Build star HTML
        stars = ""
        for i in range(review.rating):
            stars += '<i class="fas fa-star"></i>'
        for i in range(5 - review.rating):
            stars += '<i class="far fa-star"></i>'
            
        date_str = review.created_at.strftime("%b %d, %Y")
        owner_name = review.owner.full_name
        comment = review.comment
        
        # Pre-render the entire card content to be immune to template splitting
        review.display_html = f"""
            <div class="p-3 rounded bg-light border h-100 shadow-sm border-opacity-10">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="fw-bold mb-0 text-dark">{owner_name}</h6>
                    <div class="text-warning small">{stars}</div>
                </div>
                <p class="text-muted small mb-2 fst-italic">"{comment}"</p>
                <div class="text-end">
                    <small class="text-muted" style="font-size: 0.7rem;">{date_str}</small>
                </div>
            </div>
        """
    
    return render(request, 'vet_dashboard.html', {
        'appointments': appointments,
        'reviews': reviews,
        'pending_count': pending_count,
        'treated_count': treated_count
    })

@role_required('vet')
def vet_income(request):
    vet_id = request.session['user_id']
    # Paid appointments
    paid_appointments = Appointment.objects.filter(
        vet_id=vet_id,
        payment__status='completed'
    ).select_related('payment', 'pet', 'owner')
    
    # Pre-calculate totals and format dates
    total_income = sum(app.payment.amount for app in paid_appointments if hasattr(app, 'payment') and app.payment)
    for app in paid_appointments:
        if hasattr(app, 'payment') and app.payment:
            app.payment_date_display = app.payment.payment_date.strftime("%b %d, %Y")
    
    return render(request, 'vet_income.html', {
        'paid_appointments': paid_appointments,
        'total_income': total_income
    })


@role_required('caretaker')
def caretaker_dashboard(request):
    caretaker_id = request.session['user_id']
    bookings = CareBooking.objects.filter(caretaker_id=caretaker_id).order_by('-booking_date', '-booking_time')
    
    # Simple stats
    pending_count = bookings.filter(status='pending').count()
    active_count = bookings.filter(status='confirmed').count()
    
    # Reviews - with pre-rendered HTML to bypass destructive auto-formatting
    reviews = CareReview.objects.filter(caretaker_id=caretaker_id).order_by('-created_at')
    for review in reviews:
        # Build star HTML
        stars = ""
        for i in range(review.rating):
            stars += '<i class="fas fa-star"></i>'
        for i in range(5 - review.rating):
            stars += '<i class="far fa-star"></i>'
            
        date_str = review.created_at.strftime("%b %d, %Y")
        owner_name = review.owner.full_name
        comment = review.comment
        
        # Pre-render the entire card content to be immune to template splitting
        review.display_html = f"""
            <div class="p-3 rounded bg-light border h-100 shadow-sm border-opacity-10">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="fw-bold mb-0 text-dark">{owner_name}</h6>
                    <div class="text-warning small">{stars}</div>
                </div>
                <p class="text-muted small mb-2 fst-italic">"{comment}"</p>
                <div class="text-end">
                    <small class="text-muted" style="font-size: 0.7rem;">{date_str}</small>
                </div>
            </div>
        """
    
    return render(request, 'caretaker_dashboard.html', {
        'bookings': bookings,
        'pending_count': pending_count,
        'active_count': active_count,
        'reviews': reviews
    })

@role_required('caretaker')
def caretaker_income(request):
    caretaker_id = request.session['user_id']
    # Paid bookings
    paid_bookings = CareBooking.objects.filter(
        caretaker_id=caretaker_id,
        care_payment__status='completed'
    ).select_related('care_payment', 'pet', 'owner')
    
    # Pre-calculate totals and format dates
    total_income = sum(booking.amount for booking in paid_bookings if booking.amount)
    for booking in paid_bookings:
        if booking.care_payment:
            booking.payment_date_display = booking.care_payment.payment_date.strftime("%b %d, %Y")
    
    return render(request, 'caretaker_income.html', {
        'paid_bookings': paid_bookings,
        'total_income': total_income
    })


@role_required('owner')
def list_caretakers(request):
    caretakers = User.objects.filter(role='caretaker', is_approved=True)
    return render(request, 'list_caretakers.html', {'caretakers': caretakers})

@role_required('owner')
def book_care(request, caretaker_id):
    try:
        caretaker = User.objects.get(id=caretaker_id, role='caretaker')
    except User.DoesNotExist:
        messages.error(request, "Caretaker not found")
        return redirect('owner_dashboard')

    pets = Pet.objects.filter(owner_id=request.session['user_id'])
    
    if request.method == 'POST':
        pet_id = request.POST['pet_id']
        date = request.POST['date']
        time = request.POST['time']
        reason = request.POST['reason']
        
        CareBooking.objects.create(
            owner_id=request.session['user_id'],
            caretaker=caretaker,
            pet_id=pet_id,
            booking_date=date,
            booking_time=time,
            reason=reason
        )
        messages.success(request, f"Care session booked with {caretaker.full_name}")
        return redirect('owner_dashboard')

    return render(request, 'book_care.html', {'caretaker': caretaker, 'pets': pets})

@role_required('caretaker')
def update_care_status(request, booking_id):
    try:
        booking = CareBooking.objects.get(id=booking_id, caretaker_id=request.session['user_id'])
        status = request.POST.get('status')
        
        if status == 'confirmed':
            amount = request.POST.get('amount')
            if amount:
                booking.amount = amount
                booking.status = 'confirmed'
                booking.save()
                messages.success(request, f"Booking confirmed with amount ${amount}")
            else:
                messages.error(request, "Please enter an amount to confirm the booking")
        
        elif status == 'completed':
            # Check if payment exists and is completed
            if hasattr(booking, 'care_payment') and booking.care_payment.status == 'completed':
                booking.status = 'completed'
                booking.save()
                messages.success(request, "Booking marked as completed")
            else:
                messages.error(request, "Cannot complete booking: Payment not yet received from owner")
                
        elif status == 'cancelled':
            booking.status = 'cancelled'
            booking.save()
            messages.success(request, "Booking cancelled")
            
    except CareBooking.DoesNotExist:
        messages.error(request, "Booking not found")
    
    return redirect('caretaker_dashboard')


@role_required('groomer')
def groomer_dashboard(request):
    return render(request, 'groomer_dashboard.html')

def logout(request):
    request.session.flush()
    return redirect('login')


def add_pet(request):
    if request.session.get('role') != 'owner':
        return redirect('login')

    if request.method == 'POST':
        Pet.objects.create(
            owner_id=request.session['user_id'],
            pet_image=request.FILES['pet_image'],
            name=request.POST['name'],
            pet_type=request.POST['pet_type'],
            breed=request.POST['breed'],
            certification=request.FILES.get('certification'),
            gender=request.POST['gender'],
            color=request.POST['color'],
            weight=request.POST['weight'],
            dob=request.POST['dob'],
            about_me=request.POST['about_me'],
            location=request.POST['location'],
            google_map_link=request.POST.get('google_map_link'),
            is_for_sale=request.POST.get('is_for_sale') == 'on',
            price=request.POST.get('price') if request.POST.get('is_for_sale') == 'on' else None
        )

        messages.success(request, "Pet profile added successfully")
        return redirect('owner_dashboard')

    return render(request, 'add_pet.html')


@role_required('owner')
def edit_pet(request, pet_id):
    try:
        pet = Pet.objects.get(id=pet_id, owner_id=request.session['user_id'])
    except Pet.DoesNotExist:
        messages.error(request, "Pet not found")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        pet.name = request.POST['name']
        pet.pet_type = request.POST['pet_type']
        pet.breed = request.POST['breed']
        pet.gender = request.POST['gender']
        pet.color = request.POST['color']
        pet.weight = request.POST['weight']
        pet.dob = request.POST['dob']
        pet.about_me = request.POST['about_me']
        pet.location = request.POST['location']
        pet.google_map_link = request.POST.get('google_map_link')
        pet.is_for_sale = request.POST.get('is_for_sale') == 'on'
        pet.price = request.POST.get('price') if pet.is_for_sale else None

        if request.FILES.get('pet_image'):
            pet.pet_image = request.FILES['pet_image']
        
        if request.FILES.get('certification'):
            pet.certification = request.FILES['certification']

        pet.save()
        messages.success(request, "Pet profile updated successfully")
        return redirect('pet_profile', pet_id=pet.id)

    return render(request, 'edit_pet.html', {'pet': pet})


@role_required('owner')
def predict_breed(request):
    if request.method == 'POST' and request.FILES.get('pet_image'):
        pet_image = request.FILES['pet_image']
        
        file_name = default_storage.save('ml_predictions/' + pet_image.name, pet_image)
        full_path = default_storage.path(file_name)
        image_url = default_storage.url(file_name)

        all_predictions = predict_pet_breed(full_path)
        # top_prediction = all_predictions[0] if all_predictions else None   <-- Removed causing KeyError on dict

        return render(request, 'breed_prediction.html', {
            'prediction': all_predictions,  # Pass the list (success) or dict (error) directly
            'uploaded_image_url': image_url,
        })

    return render(request, 'breed_prediction.html')

@role_required('owner')
def list_vets(request):
    vets = User.objects.filter(role='vet', is_approved=True)
    return render(request, 'list_vets.html', {'vets': vets})

@role_required('owner')
def book_appointment(request, vet_id):
    try:
        vet = User.objects.get(id=vet_id, role='vet')
    except User.DoesNotExist:
        messages.error(request, "Veterinarian not found")
        return redirect('owner_dashboard')

    pets = Pet.objects.filter(owner_id=request.session['user_id'])
    
    if request.method == 'POST':
        pet_id = request.POST['pet_id']
        date = request.POST['date']
        time = request.POST['time']
        reason = request.POST['reason']
        
        Appointment.objects.create(
            owner_id=request.session['user_id'],
            vet=vet,
            pet_id=pet_id,
            appointment_date=date,
            appointment_time=time,
            reason=reason
        )
        messages.success(request, f"Appointment booked with Dr. {vet.full_name}")
        return redirect('owner_dashboard')

    return render(request, 'book_appointment.html', {'vet': vet, 'pets': pets})

@role_required('vet')
def vet_appointments(request):
    appointments = Appointment.objects.filter(vet_id=request.session['user_id']).order_by('-appointment_date', '-appointment_time')
    return render(request, 'vet_appointments.html', {'appointments': appointments})

@role_required('vet')
def update_appointment_status(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id, vet_id=request.session['user_id'])
        status = request.POST.get('status')
        if status in ['confirmed', 'cancelled', 'treated']:
            appointment.status = status
            if status == 'treated':
                appointment.treatment_summary = request.POST.get('treatment_summary')
            appointment.save()
            messages.success(request, f"Appointment status updated to {status}")
    except Appointment.DoesNotExist:
        messages.error(request, "Appointment not found")
    
    return redirect('vet_dashboard')

@role_required('owner')
def process_payment(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id, owner_id=request.session['user_id'])
    except Appointment.DoesNotExist:
        messages.error(request, "Appointment not found")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        method = request.POST['payment_method']
        amount = request.POST['amount']
        
        Payment.objects.create(
            appointment=appointment,
            amount=amount,
            payment_method=method,
            status='completed'
        )
        messages.success(request, "Payment successful")
        return redirect('owner_dashboard')

    return render(request, 'process_payment.html', {'appointment': appointment})

@role_required('owner')
def add_review(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id, owner_id=request.session['user_id'])
    except Appointment.DoesNotExist:
        messages.error(request, "Appointment not found")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        rating = request.POST['rating']
        comment = request.POST['comment']
        
        Review.objects.create(
            owner_id=request.session['user_id'],
            vet=appointment.vet,
            appointment=appointment,
            rating=rating,
            comment=comment
        )
        messages.success(request, "Review submitted successfully")
        return redirect('owner_dashboard')

    return render(request, 'add_review.html', {'appointment': appointment})

# Add review for vet directly (not tied to a specific appointment if needed)
@role_required('owner')
def vet_profile(request, vet_id):
    try:
        vet = User.objects.get(id=vet_id, role='vet')
        reviews = Review.objects.filter(vet=vet).order_by('-created_at')
        return render(request, 'vet_profile.html', {'vet': vet, 'reviews': reviews})
    except User.DoesNotExist:
        messages.error(request, "Veterinarian not found")
        return redirect('owner_dashboard')

@role_required('owner')
def process_care_payment(request, booking_id):
    try:
        booking = CareBooking.objects.get(id=booking_id, owner_id=request.session['user_id'])
    except CareBooking.DoesNotExist:
        messages.error(request, "Booking not found")
        return redirect('owner_dashboard')

    if not booking.amount:
        messages.error(request, "Caretaker has not set an amount for this booking yet.")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        method = request.POST['payment_method']
        # Use the amount from the booking
        amount = booking.amount
        
        CarePayment.objects.create(
            care_booking=booking,
            amount=amount,
            payment_method=method,
            status='completed'
        )
        messages.success(request, "Payment successful. Caretaker can now complete the session.")
        return redirect('owner_dashboard')

    return render(request, 'process_care_payment.html', {'booking': booking})

@role_required('owner')
def add_care_review(request, booking_id):
    try:
        booking = CareBooking.objects.get(id=booking_id, owner_id=request.session['user_id'])
    except CareBooking.DoesNotExist:
        messages.error(request, "Booking not found")
        return redirect('owner_dashboard')

    if request.method == 'POST':
        rating = request.POST['rating']
        comment = request.POST['comment']
        
        CareReview.objects.create(
            owner_id=request.session['user_id'],
            caretaker=booking.caretaker,
            care_booking=booking,
            rating=rating,
            comment=comment
        )
        messages.success(request, "Review submitted successfully")
        return redirect('owner_dashboard')

    return render(request, 'add_care_review.html', {'booking': booking})

@role_required('owner')
def caretaker_profile(request, caretaker_id):
    try:
        caretaker = User.objects.get(id=caretaker_id, role='caretaker')
        reviews = CareReview.objects.filter(caretaker=caretaker).order_by('-created_at')
        return render(request, 'caretaker_profile.html', {'caretaker': caretaker, 'reviews': reviews})
    except User.DoesNotExist:
        messages.error(request, "Caretaker not found")
        return redirect('owner_dashboard')

@role_required('vet')
def edit_vet_profile(request):
    try:
        vet = User.objects.get(id=request.session['user_id'], role='vet')
    except User.DoesNotExist:
        messages.error(request, "Veterinarian not found")
        return redirect('login')

    if request.method == 'POST':
        vet.full_name = request.POST['full_name']
        vet.phone = request.POST['phone']
        vet.address = request.POST['address']
        vet.qualification = request.POST['qualification']
        vet.registration_number = request.POST['registration_number']

        if request.FILES.get('profile_image'):
            vet.profile_image = request.FILES['profile_image']

        vet.save()
        messages.success(request, "Profile updated successfully")
        return redirect('vet_dashboard')

    return render(request, 'edit_vet_profile.html', {'vet': vet})

@role_required('caretaker')
def edit_caretaker_profile(request):
    try:
        caretaker = User.objects.get(id=request.session['user_id'], role='caretaker')
    except User.DoesNotExist:
        messages.error(request, "Caretaker not found")
        return redirect('login')

    if request.method == 'POST':
        caretaker.full_name = request.POST['full_name']
        caretaker.phone = request.POST['phone']
        caretaker.address = request.POST['address']
        caretaker.experience = request.POST['experience']
        caretaker.services_offered = request.POST['services_offered']

        if request.FILES.get('profile_image'):
            caretaker.profile_image = request.FILES['profile_image']

        caretaker.save()
        messages.success(request, "Profile updated successfully")
        return redirect('caretaker_dashboard')

    return render(request, 'edit_caretaker_profile.html', {'caretaker': caretaker})
