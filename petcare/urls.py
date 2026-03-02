from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('logout/', views.logout, name='logout'),

    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/vets/', views.admin_vets, name='admin_vets'),
    path('admin-dashboard/caretakers/', views.admin_caretakers, name='admin_caretakers'),
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
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('admin-dashboard/messages/', views.admin_messages, name='admin_messages'),
    path('appointment/', views.book_appointment, name='book_appointment'),
    path('like-pet/<int:pet_id>/', views.like_pet, name='like_pet'),
    path('admin-dashboard/approve-user/<int:user_id>/', views.approve_user, name='approve_user'),

    # Appointment, Payment, Review URLs
    path('owner/vets/', views.list_vets, name='list_vets'),
    path('owner/book-appointment/<int:vet_id>/', views.book_appointment, name='book_appointment'),
    path('owner/process-payment/<int:appointment_id>/', views.process_payment, name='process_payment'),
    path('owner/add-review/<int:appointment_id>/', views.add_review, name='add_review'),
    path('owner/vet-profile/<int:vet_id>/', views.vet_profile, name='vet_profile'),
    
    path('vet/appointments/', views.vet_appointments, name='vet_appointments'),
    path('vet/update-appointment/<int:appointment_id>/', views.update_appointment_status, name='update_appointment_status'),
    path('vet/income/', views.vet_income, name='vet_income'),
    path('vet/edit-profile/', views.edit_vet_profile, name='edit_vet_profile'),

    # Caretaker Booking URLs
    path('owner/caretakers/', views.list_caretakers, name='list_caretakers'),
    path('owner/book-care/<int:caretaker_id>/', views.book_care, name='book_care'),
    path('owner/process-care-payment/<int:booking_id>/', views.process_care_payment, name='process_care_payment'),
    path('owner/add-care-review/<int:booking_id>/', views.add_care_review, name='add_care_review'),
    path('owner/caretaker-profile/<int:caretaker_id>/', views.caretaker_profile, name='caretaker_profile'),
    path('caretaker/update-booking/<int:booking_id>/', views.update_care_status, name='update_care_status'),
    path('caretaker/income/', views.caretaker_income, name='caretaker_earnings'),
    path('caretaker/edit-profile/', views.edit_caretaker_profile, name='edit_caretaker_profile'),
    
    # Tracking URLs
    path('owner/track-appointment/<int:appointment_id>/', views.track_appointment, name='track_appointment'),
    path('owner/track-care/<int:booking_id>/', views.track_care, name='track_care'),
    path('owner/invoice/<int:appointment_id>/', views.view_invoice, name='view_invoice'),
    path('owner/care-invoice/<int:booking_id>/', views.view_care_invoice, name='view_care_invoice'),
    path('owner/delete-appointment/<int:appointment_id>/', views.delete_appointment, name='delete_appointment'),
    path('owner/delete-care-booking/<int:booking_id>/', views.delete_care_booking, name='delete_care_booking'),
]
