from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),

    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('vet/dashboard/', views.vet_dashboard, name='vet_dashboard'),
    path('caretaker/dashboard/', views.caretaker_dashboard, name='caretaker_dashboard'),
    path('groomer/dashboard/', views.groomer_dashboard, name='groomer_dashboard'),

    path('owner/add-pet/', views.add_pet, name='add_pet'),
    path('owner/predict-breed/', views.predict_breed, name='predict_breed'),
    path('owner/pet-profile/<int:pet_id>/', views.pet_profile, name='pet_profile'),
    path('owner/edit-pet/<int:pet_id>/', views.edit_pet, name='edit_pet'),
    path('discover-pets/', views.discover_pets, name='discover_pets'),
    path('like-pet/<int:pet_id>/', views.like_pet, name='like_pet'),
]
