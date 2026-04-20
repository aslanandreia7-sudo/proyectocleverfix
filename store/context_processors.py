from .models import SiteSettings, Category

def global_context(request):
    """
    Procesador de contexto global para CleverFix.
    Centraliza configuraciones, navegación y estado del carrito.
    """
    # 1. Obtener configuraciones del sitio
    try:
        settings = SiteSettings.objects.first()
    except:
        settings = None

    # 2. Obtener categorías con prefetch para el Mega Menú (evita consultas N+1)
    nav_categories = Category.objects.all().prefetch_related('types__models')

    # 3. Lógica del carrito (unificada y dinámica)
    cart = request.session.get('cart', {})
    total_items = sum(cart.values()) if cart else 0

    return {
        'site_settings': settings,
        'nav_brands': nav_categories,
        'cart_count': total_items,           # Usado en el header principal
        'global_cart_count': total_items,    # Alias para compatibilidad con otros fragmentos
    }

def cart_contents(request):
    """
    Mantiene compatibilidad con llamadas específicas al conteo del carrito.
    """
    cart = request.session.get('cart', {})
    total_items = sum(cart.values()) if cart else 0
    return {
        'global_cart_count': total_items
    }