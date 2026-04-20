from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from store import views

urlpatterns = [
    # --- PANEL DE ADMINISTRACIÓN ---
    path('admin/', admin.site.urls),

    # --- AUTENTICACIÓN Y REGISTRO ---
    path('accounts/', include('django.contrib.auth.urls')), 
    path('register/', views.register_view, name='register'),
    
    # VERIFICACIÓN DE CUENTA
    # 1. Vía enlace directo (Token en URL)
    path('verify/<str:token>/', views.verify_account, name='verify_account'),
    # 2. Vía ingreso manual del código
    path('verify-account/', views.verify_code_view, name='verify_code'),
    # 3. Página de éxito (Check verde)
    path('verification-success/', views.verify_account, {'token': None}, name='verification_success'),

    # --- PÁGINA PRINCIPAL / CATÁLOGO ---
    path('', views.product_list, name='home'),

    # --- FILTROS DE NAVEGACIÓN (Estructura Jerárquica) ---
    path('category/<slug:category_slug>/', views.product_list, name='category_filter'),
    path('category/<slug:category_slug>/<slug:type_slug>/', views.product_list, name='type_filter'),
    path('category/<slug:category_slug>/<slug:type_slug>/<slug:model_slug>/', views.product_list, name='model_filter'),

    # --- DETALLE DE PRODUCTO ---
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),

    # --- GESTIÓN DEL CARRITO ---
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),

    # --- PASARELA DE PAGOS (STRIPE) ---
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('success/', views.payment_success, name='payment_success'),

    # --- GESTIÓN DE CUENTA DE USUARIO ---
    path('account/dashboard/', views.account_dashboard, name='account_dashboard'),
    path('account/address-book/', views.address_book, name='address_book'),
    path('account/orders/', views.product_list, name='my_orders'), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)