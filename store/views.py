import stripe
import random
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.contrib import messages

# Importamos tus modelos (incluyendo los que definimos antes)
from .models import Category, DeviceType, DeviceModel, Product, SiteSettings, CustomerProfile
from .forms import ExtendedRegistrationForm

# Configuración de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# --- UTILIDADES DE CORREO ---

def send_verification_email(user, token):
    """Envía el código de 6 dígitos con manejo de errores"""
    subject = f"CÓDIGO DE VERIFICACIÓN: {token} - CleverFix"
    message = f"""
==================================================
            BIENVENIDO A CLEVERFIX
==================================================
Hola {user.username},

Gracias por registrarte. Para activar tu cuenta, 
utiliza el siguiente enlace o ingresa el código manual.

VERIFICAR CUENTA:
http://127.0.0.1:8000/verify/{token}/

TU CÓDIGO DE ACCESO: {token}

Atentamente,
El Equipo de Soporte de CleverFix
Mexicali, B.C.
==================================================
    """
    email_from = settings.EMAIL_HOST_USER
    try:
        send_mail(subject, message, email_from, [user.email], fail_silently=False)
    except Exception as e:
        print(f"Error enviando correo a {user.email}: {e}")

# --- VISTAS DE PRODUCTOS ---

def product_list(request, category_slug=None, type_slug=None, model_slug=None):
    """Listado general con filtros por marca, tipo y modelo"""
    products = Product.objects.filter(active=True)
    selected_category = selected_type = selected_model = None

    # Buscador manual
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)

    # Filtrado jerárquico
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(device_model__device_type__category=selected_category)

    if type_slug:
        selected_type = get_object_or_404(DeviceType, slug=type_slug)
        products = products.filter(device_model__device_type=selected_type)

    if model_slug:
        selected_model = get_object_or_404(DeviceModel, slug=model_slug)
        products = products.filter(device_model=selected_model)

    # Título dinámico
    page_title = "Nuestras Refacciones"
    if selected_model:
        page_title = f"Refacciones para {selected_model.name}"
    elif selected_category:
        page_title = f"Refacciones {selected_category.name}"

    return render(request, 'store/product_list.html', {
        'products': products,
        'selected_category': selected_category,
        'selected_type': selected_type,
        'selected_model': selected_model,
        'page_title': page_title,
    })

def product_detail(request, slug):
    """Detalle de un producto específico"""
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'store/product_list.html', {
        'products': [product], 
        'page_title': f"{product.name} ({product.color})" if product.color else product.name
    })

# --- LÓGICA DEL CARRITO ---

def cart_view(request):
    """Visualización de los productos en el carrito"""
    cart = request.session.get('cart', {})
    cart_items = []
    cart_subtotal = 0

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        total_price = product.price * quantity
        cart_subtotal += total_price
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'total_price': total_price,
            'color': product.color, # Pasamos el color al contexto del carrito
        })

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'cart_subtotal': cart_subtotal,
        'cart_count': len(cart_items),
        'page_title': 'Tu Carrito'
    })

def cart_add(request, product_id):
    """Añadir o restar cantidad de un producto en el carrito"""
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    delta = int(request.GET.get('delta', 1))

    if product_id_str in cart:
        cart[product_id_str] += delta
        if cart[product_id_str] <= 0:
            del cart[product_id_str]
    elif delta > 0:
        cart[product_id_str] = delta

    request.session['cart'] = cart
    return redirect('cart')

# --- PASARELA DE PAGOS (STRIPE) ---

def create_checkout_session(request):
    """Crea la sesión de pago en Stripe"""
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('cart')

    total_amount = 0
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        # Convertimos a centavos para Stripe (Ej: $10.00 -> 1000)
        total_amount += int(product.price * 100) * quantity 

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'mxn',
                    'product_data': {
                        'name': 'Pedido en CleverFix',
                        'description': 'Refacciones y componentes',
                    },
                    'unit_amount': total_amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='http://127.0.0.1:8000/success/',
            cancel_url='http://127.0.0.1:8000/cart/',
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return render(request, 'store/cart.html', {'error': str(e)})

def payment_success(request):
    """Limpia el carrito después de un pago exitoso"""
    if 'cart' in request.session:
        del request.session['cart']
    return render(request, 'store/success.html', {'page_title': '¡Pago Exitoso!'})

# --- USUARIOS, REGISTRO Y VERIFICACIÓN ---

def register_view(request):
    """Registro de nuevo usuario y creación de perfil"""
    if request.method == 'POST':
        form = ExtendedRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            
            # El perfil se crea vía Signal, aquí solo lo actualizamos
            profile = user.profile
            profile.first_name = form.cleaned_data['first_name']
            profile.last_name = form.cleaned_data['last_name']
            profile.address_1 = form.cleaned_data['address_1']
            profile.city = form.cleaned_data['city']
            profile.zip_code = form.cleaned_data['zip_code']
            profile.telephone = form.cleaned_data['telephone']
            
            # Generar token de 6 dígitos
            token = str(random.randint(100000, 999999))
            profile.auth_token = token
            profile.save()
            
            send_verification_email(user, token)
            login(request, user)
            
            return redirect('verify_code') 
    else:
        form = ExtendedRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

def verify_account(request, token):
    """Verificación automática vía enlace de correo"""
    profile = get_object_or_404(CustomerProfile, auth_token=token)
    profile.is_verified = True
    profile.save()
    return render(request, 'registration/verification_success.html', {'page_title': '¡Cuenta Verificada!'})

def verify_code_view(request):
    """Verificación manual por código ingresado por el usuario"""
    if request.method == 'POST':
        codigo_usuario = request.POST.get('codigo_ingresado')
        perfil = CustomerProfile.objects.filter(auth_token=codigo_usuario).first()
        
        if perfil:
            perfil.is_verified = True
            perfil.save()
            messages.success(request, "¡Cuenta verificada con éxito!")
            return redirect('account_dashboard') 
        else:
            return render(request, 'registration/verify_code.html', {
                'error': 'Código incorrecto',
                'page_title': 'Ingresar Código'
            })
            
    return render(request, 'registration/verify_code.html', {'page_title': 'Ingresar Código'})

# --- VISTAS DE MI CUENTA ---

@login_required
def account_dashboard(request):
    """Panel principal del cliente"""
    profile, created = CustomerProfile.objects.get_or_create(user=request.user)
    return render(request, 'registration/dashboard.html', {'profile': profile})

@login_required
def address_book(request):
    """Gestión de datos de envío"""
    profile, created = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        profile.address_1 = request.POST.get('address_1')
        profile.city = request.POST.get('city')
        profile.zip_code = request.POST.get('zip_code')
        profile.telephone = request.POST.get('telephone')
        profile.save()
        messages.success(request, "Dirección actualizada.")
        return redirect('address_book')
    return render(request, 'registration/address_book.html', {'profile': profile})