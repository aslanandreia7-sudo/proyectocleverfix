from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- 0. CONFIGURACIÓN DEL SITIO ---

class SiteSettings(models.Model):
    logo = models.ImageField(upload_to='logo/', verbose_name="Logo CleverFix")
    phone = models.CharField(max_length=20, default='686 178 0903', verbose_name="Teléfono")
    site_name = models.CharField(max_length=50, default='CleverFix')

    class Meta:
        verbose_name = "0. Configuración"
        verbose_name_plural = "0. Configuración"

# --- PERFILES DE USUARIO ---

class CustomerProfile(models.Model):
    """Información extendida para envíos, facturación y verificación"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=100, verbose_name="Nombre(s)")
    last_name = models.CharField(max_length=100, verbose_name="Apellidos")
    address_1 = models.CharField(max_length=255, verbose_name="Dirección 1")
    address_2 = models.CharField(max_length=255, blank=True, verbose_name="Dirección 2 (Opcional)")
    city = models.CharField(max_length=100, default="Mexicali", verbose_name="Ciudad")
    state = models.CharField(max_length=100, default="Baja California", verbose_name="Estado")
    zip_code = models.CharField(max_length=10, verbose_name="Código Postal")
    telephone = models.CharField(max_length=15, verbose_name="Teléfono")
    
    # Campos de verificación
    is_verified = models.BooleanField(default=False, verbose_name="¿Verificado?")
    auth_token = models.CharField(max_length=100, blank=True, verbose_name="Token de Autenticación")

    class Meta:
        verbose_name = "Perfil de Cliente"
        verbose_name_plural = "Perfiles de Clientes"

    def __str__(self):
        return f"Perfil de {self.user.username}"

# SIGNAL: Crea el perfil automáticamente cuando se crea un usuario
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        CustomerProfile.objects.create(user=instance)

# --- JERARQUÍA DE PRODUCTOS ---

class Category(models.Model):
    """Nivel 1: Marca Principal (Ej: Apple, Samsung)"""
    name = models.CharField(max_length=100, verbose_name="Marca Principal")
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = "Categoría (Marca)"
        verbose_name_plural = "1. Categorías (Marcas)"

    def __str__(self): 
        return self.name

class DeviceType(models.Model):
    """Nivel 2: Tipo de Dispositivo (Ej: iPhone, Galaxy S)"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='types', verbose_name="Marca")
    name = models.CharField(max_length=100, verbose_name="Tipo de Dispositivo")
    slug = models.SlugField()

    class Meta:
        verbose_name = "Tipo de Dispositivo"
        verbose_name_plural = "2. Tipos de Dispositivos"

    def __str__(self): 
        return f"{self.category.name} - {self.name}"

class DeviceModel(models.Model):
    """Nivel 3: Modelo Exacto (Ej: iPhone 13 Pro, Galaxy S21 Ultra)"""
    device_type = models.ForeignKey(DeviceType, on_delete=models.CASCADE, related_name='models', verbose_name="Tipo")
    name = models.CharField(max_length=100, verbose_name="Modelo / Variante Exacta")
    slug = models.SlugField()

    class Meta:
        verbose_name = "Modelo Exacto"
        verbose_name_plural = "3. Modelos Exactos"

    def __str__(self): 
        return f"{self.device_type} - {self.name}"

class Product(models.Model):
    """Nivel 4: Producto Final (Refacción específica)"""
    device_model = models.ForeignKey(DeviceModel, on_delete=models.CASCADE, related_name='products', verbose_name="Modelo")
    name = models.CharField(max_length=200, verbose_name="Nombre de la Refacción")
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, verbose_name="Descripción")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")
    image = models.ImageField(upload_to='products/', verbose_name="Foto del Producto")
    stock = models.PositiveIntegerField(default=1, verbose_name="Existencia")
    active = models.BooleanField(default=True)
    
    # Campo de Color / Variante
    color = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Color / Variante",
        help_text="Escribe el color manualmente (ej: Azul Sierra, Negro Mate)"
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "4. Productos Finales"

    def __str__(self):
        # Identificador claro para el Admin: "Nombre - Color (Modelo)"
        display_name = self.name
        if self.color:
            display_name = f"{self.name} - {self.color}"
        return f"{display_name} ({self.device_model.name})"