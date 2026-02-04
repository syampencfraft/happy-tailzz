from django.shortcuts import render

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import User
from .models import Pet
import os
from django.conf import settings
from .ml_utils import predict_pet_breed
from django.core.files.storage import default_storage


# Create your views here.
from .models import Like

def index(request):
    return render(request,'index.html')

def discover_pets(request):
    pets = Pet.objects.all().order_by('-created_at')
    return render(request, 'discover_pets.html', {'pets': pets})


def register(request):
    if request.method == 'POST':
        data = request.POST

        if User.objects.filter(email=data['email']).exists():
            messages.error(request, "Email already registered")
            return redirect('register')

        user = User(
            full_name=data['full_name'],
            email=data['email'],
            phone=data['phone'],
            address=data['address'],
            role=data['role'],
            password=make_password(data['password']),
            profile_image=request.FILES['profile_image']
        )

        # Role-based extra fields
        if data['role'] in ['vet']:
            user.qualification = data.get('qualification')
            user.registration_number = data.get('registration_number')

        if data['role'] in ['caretaker', 'groomer']:
            user.experience = data.get('experience')
            user.services_offered = data.get('services_offered')

        user.save()

        messages.success(
            request,
            "Registration successful. Waiting for admin approval."
        )
        return redirect('login')

    return render(request,'register.html')

def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        try:
            user = User.objects.get(email=email)

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
            messages.error(request, "Invalid email")

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
    return render(request, 'admin_dashboard.html')


@role_required('owner')
def owner_dashboard(request):
    pets = Pet.objects.filter(owner_id=request.session['user_id'])
    return render(request, 'owner_dashboard.html', {'pets': pets})

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
    return render(request, 'vet_dashboard.html')


@role_required('caretaker')
def caretaker_dashboard(request):
    return render(request, 'caretaker_dashboard.html')


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
        top_prediction = all_predictions[0] if all_predictions else None

        return render(request, 'breed_prediction.html', {
            'prediction': top_prediction,
            'uploaded_image_url': image_url,
        })

    return render(request, 'breed_prediction.html')
