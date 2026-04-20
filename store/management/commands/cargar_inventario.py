import csv
import re
import unicodedata
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from store.models import Category, DeviceType, DeviceModel, Product

def slugify(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^\w\s-]", "", texto.lower().strip())
    return re.sub(r"[\s_-]+", "-", texto).strip("-")

def get_or_create_jerarquia(cat_name, tipo_name, modelo_name):
    """
    Asegura la existencia de la jerarquía completa:
    Category (Marca) -> DeviceType (Tipo) -> DeviceModel (Modelo Exacto)
    """
    # Nivel 1: Marca (Apple, Samsung...)
    categoria, _ = Category.objects.get_or_create(
        name=cat_name.strip(),
        defaults={"slug": slugify(cat_name)}
    )

    # Nivel 2: Tipo de Dispositivo (iPhone, Galaxy S...)
    tipo, _ = DeviceType.objects.get_or_create(
        category=categoria,
        name=tipo_name.strip(),
        defaults={"slug": slugify(tipo_name)}
    )

    # Nivel 3: Modelo Exacto (iPhone XR, iPhone 15 Pro Max...)
    # Aquí usamos un slug combinado para evitar colisiones entre marcas
    modelo, _ = DeviceModel.objects.get_or_create(
        device_type=tipo,
        name=modelo_name.strip(),
        defaults={"slug": slugify(f"{tipo_name}-{modelo_name}")}
    )

    return modelo

class Command(BaseCommand):
    help = "Carga masiva de refacciones asegurando la jerarquía de modelos"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Ruta al archivo CSV")
        parser.add_argument("--update", action="store_true", default=False,
                            help="Actualiza el producto si el slug ya existe")
        parser.add_argument("--dry-run", action="store_true", default=False,
                            help="Simula la carga sin guardar cambios en la base de datos")

    def handle(self, *args, **options):
        ruta_csv = Path(options["csv_file"])
        if not ruta_csv.exists():
            raise CommandError(f"Archivo no encontrado en: {ruta_csv.absolute()}")

        update = options["update"]
        dry_run = options["dry_run"]
        creados = actualizados = errores = omitidos = 0

        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  MODO SIMULACIÓN (DRY RUN)\n"))

        with open(ruta_csv, newline="", encoding="utf-8") as f:
            # El scraper genera: categoria,tipo_dispositivo,modelo,nombre,slug,descripcion,precio,stock,color
            reader = csv.DictReader(f)
            
            for i, fila in enumerate(reader, 1):
                try:
                    # Extraer y limpiar datos básicos
                    cat_name = fila.get("categoria", "").strip()
                    tipo_name = fila.get("tipo_dispositivo", "").strip()
                    modelo_name = fila.get("modelo", "").strip()
                    nombre_prod = fila.get("nombre", "").strip()
                    slug_prod = fila.get("slug", "").strip()

                    # Validación de datos obligatorios
                    if not all([cat_name, tipo_name, modelo_name, nombre_prod, slug_prod]):
                        self.stdout.write(self.style.WARNING(f"  Fila {i}: Datos incompletos, omitida."))
                        omitidos += 1
                        continue

                    # PASO CRUCIAL: Obtener o crear la jerarquía de modelos
                    # Esto evita el error de "NOT NULL constraint failed"
                    if not dry_run:
                        device_obj = get_or_create_jerarquia(cat_name, tipo_name, modelo_name)
                    else:
                        device_obj = None

                    # Limpieza de precio (quitar símbolos si los hay)
                    precio_str = fila.get("precio", "0").replace("$", "").replace(",", "")
                    
                    datos_producto = {
                        "name": nombre_prod,
                        "description": fila.get("descripcion", "").strip(),
                        "price": float(precio_str) if precio_str else 0.0,
                        "stock": int(fila.get("stock", 0)) if fila.get("stock") else 0,
                        "color": fila.get("color", "N/A").strip(),
                        "device_model": device_obj,
                        "active": True,
                    }

                    if dry_run:
                        self.stdout.write(f"  [SIM] {nombre_prod} -> {modelo_name}")
                        creados += 1
                        continue

                    # Lógica de guardado
                    if update:
                        obj, created = Product.objects.update_or_create(
                            slug=slug_prod,
                            defaults=datos_producto
                        )
                        if created:
                            creados += 1
                        else:
                            actualizados += 1
                    else:
                        if Product.objects.filter(slug=slug_prod).exists():
                            omitidos += 1
                        else:
                            Product.objects.create(slug=slug_prod, **datos_producto)
                            creados += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Error fila {i} ({fila.get('nombre', 'ID:'+str(i))}): {e}"))
                    errores += 1

        # Resumen final
        self.stdout.write(self.style.SUCCESS("\n--- RESUMEN DE IMPORTACIÓN ---"))
        self.stdout.write(f"✅ Nuevos productos:  {creados}")
        if update:
            self.stdout.write(f"🔄 Actualizados:      {actualizados}")
        self.stdout.write(self.style.WARNING(f"⏭️  Omitidos:          {omitidos}"))
        if errores:
            self.stdout.write(self.style.ERROR(f"❌ Errores:           {errores}"))