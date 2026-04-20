import re
import unicodedata
from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from .models import SiteSettings, Category, DeviceType, DeviceModel, Product

# Función para limpiar slugs
def custom_slugify(texto):
    if not texto: return "n-a"
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^\w\s-]", "", texto.lower().strip())
    return re.sub(r"[\s_-]+", "-", texto).strip("-")

class ProductResource(resources.ModelResource):
    # 'column_name' es 'modelo' porque así viene en tu CSV
    device_model = fields.Field(
        column_name='modelo',
        attribute='device_model',
        widget=ForeignKeyWidget(DeviceModel, 'name')
    )

    class Meta:
        model = Product
        import_id_fields = ('slug',)
        # Campos exactos de tu modelo de Django
        fields = ('name', 'slug', 'description', 'price', 'stock', 'color', 'device_model')

    def before_import_row(self, row, **kwargs):
        """
        Lee el CSV y asegura que Apple > iPhone > iPhone XR existan.
        """
        # Extraer datos de las nuevas columnas de tu scraper
        marca_nombre  = row.get('categoria', 'Apple').strip()
        tipo_nombre   = row.get('tipo_dispositivo', 'iPhone').strip()
        modelo_nombre = row.get('modelo', '').strip()

        if modelo_nombre:
            # 1. Buscar o crear Marca (Apple)
            marca_obj, _ = Category.objects.get_or_create(
                name=marca_nombre,
                defaults={'slug': custom_slugify(marca_nombre)}
            )

            # 2. Buscar o crear Tipo (iPhone) dentro de Apple
            tipo_obj, _ = DeviceType.objects.get_or_create(
                category=marca_obj,
                name=tipo_nombre,
                defaults={'slug': custom_slugify(tipo_nombre)}
            )

            # 3. Buscar o crear Modelo (iPhone XR) dentro de iPhone
            modelo_obj, _ = DeviceModel.objects.get_or_create(
                device_type=tipo_obj,
                name=modelo_nombre,
                defaults={'slug': custom_slugify(f"{tipo_nombre}-{modelo_nombre}")}
            )

            # Sincronizar el nombre para que el validador de Django lo encuentre
            row['modelo'] = modelo_obj.name
        
        # Limpieza de precio (por si el CSV trae '$' o comas)
        # Probamos con 'price' (como viene en tu nuevo CSV)
        p = row.get('price') or row.get('precio')
        if p:
            row['price'] = str(p).replace('$', '').replace(',', '').strip()

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('name', 'device_model', 'price', 'stock', 'active')
    search_fields = ('name', 'slug', 'device_model__name')

# Registramos el resto para que los veas en el panel
admin.site.register([Category, DeviceType, DeviceModel, SiteSettings])