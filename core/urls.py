from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('therapy-schedule/pdf/', views.therapy_schedule_pdf, name='therapy_schedule_pdf'),
]
