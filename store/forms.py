from django import forms
from django.contrib.auth.models import User
from .models import CustomerProfile

class ExtendedRegistrationForm(forms.ModelForm):
    # Campos de Login
    username = forms.CharField(label="Usuario", widget=forms.TextInput(attrs={'placeholder': 'Nombre de usuario'}))
    email = forms.EmailField(label="Correo Electrónico")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput())
    confirm_password = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput())

    # Campos de Información Personal (del Profile)
    first_name = forms.CharField(label="Nombre(s)")
    last_name = forms.CharField(label="Apellidos")
    address_1 = forms.CharField(label="Dirección 1")
    city = forms.CharField(label="Ciudad")
    zip_code = forms.CharField(label="Código Postal")
    telephone = forms.CharField(label="Teléfono")

    class Meta:
        model = CustomerProfile
        fields = ['first_name', 'last_name', 'address_1', 'city', 'zip_code', 'telephone']

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data