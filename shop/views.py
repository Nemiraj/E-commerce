from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import (
    Product, Category, Order, OrderItem, UserProfile, 
    ProductReview, Wishlist, Coupon
)
from .forms import ReviewForm, UserProfileForm, CouponApplyForm


def product_list(request):
    products = Product.objects.filter(available=True).annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__approved=True))
    )
    categories = Category.objects.all()
    
    category_slug = request.GET.get('category')
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', 'newest')
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'rating':
        products = products.order_by('-avg_rating')
    else:
        products = products.order_by('-created_at')
    
    cart = request.session.get('cart', {})
    cart_count = sum(item['quantity'] for item in cart.values())
    
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    context = {
        'products': products,
        'categories': categories,
        'cart_count': cart_count,
        'current_category': category_slug,
        'search_query': search_query,
        'sort_by': sort_by,
        'wishlist_ids': wishlist_ids,
    }
    return render(request, 'shop/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    cart = request.session.get('cart', {})
    cart_count = sum(item['quantity'] for item in cart.values())
    
    reviews = ProductReview.objects.filter(product=product, approved=True).order_by('-created_at')[:10]
    is_wishlisted = False
    user_review = None
    
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(user=request.user, product=product).exists()
        user_review = ProductReview.objects.filter(user=request.user, product=product).first()
    
    # Get all product images
    all_images = product.get_all_images()
    additional_images = product.images.all()
    
    context = {
        'product': product,
        'cart_count': cart_count,
        'reviews': reviews,
        'is_wishlisted': is_wishlisted,
        'user_review': user_review,
        'review_form': ReviewForm() if request.user.is_authenticated else None,
        'average_rating': product.get_average_rating(),
        'review_count': product.get_review_count(),
        'all_images': all_images,
        'additional_images': additional_images,
    }
    return render(request, 'shop/product_detail.html', context)


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if product.stock <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Product is out of stock!'})
        messages.error(request, 'Product is out of stock!')
        return redirect('product_detail', slug=product.slug)
    
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    
    current_quantity = cart.get(product_id_str, {}).get('quantity', 0)
    if current_quantity + 1 > product.stock:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': f'Only {product.stock} items available in stock!'})
        messages.error(request, f'Only {product.stock} items available in stock!')
        return redirect('product_detail', slug=product.slug)
    
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': 1,
            'image': product.image.url if product.image else None,
        }
    
    request.session['cart'] = cart
    cart_count = sum(item['quantity'] for item in cart.values())
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart!',
            'cart_count': cart_count
        })
    
    messages.success(request, f'{product.name} added to cart!')
    return redirect(request.META.get('HTTP_REFERER', 'product_list'))


def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    coupon_code = request.session.get('coupon_code')
    coupon = None
    discount = 0
    
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
        except Coupon.DoesNotExist:
            request.session.pop('coupon_code', None)
    
    for product_id, item in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            item_total = float(item['price']) * item['quantity']
            cart_items.append({
                'id': product_id,
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'total': item_total,
                'image': item.get('image'),
                'stock': product.stock,
            })
            total += item_total
        except Product.DoesNotExist:
            continue
    
    if coupon and total > 0:
        discount = coupon.calculate_discount(total)
    
    final_total = total - discount
    cart_count = sum(item['quantity'] for item in cart.values())
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'discount': discount,
        'final_total': final_total,
        'cart_count': cart_count,
        'coupon': coupon,
        'coupon_form': CouponApplyForm(),
    }
    return render(request, 'shop/cart.html', context)


@require_POST
def update_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if product_id_str in cart:
        try:
            product = Product.objects.get(id=product_id)
            if quantity > product.stock:
                messages.error(request, f'Only {product.stock} items available in stock!')
                return redirect('view_cart')
            
            if quantity > 0:
                cart[product_id_str]['quantity'] = quantity
            else:
                del cart[product_id_str]
        except Product.DoesNotExist:
            del cart[product_id_str]
    
    request.session['cart'] = cart
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = sum(item['quantity'] for item in cart.values())
        return JsonResponse({'success': True, 'cart_count': cart_count})
    
    return redirect('view_cart')


@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)
    
    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        messages.success(request, 'Item removed from cart!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = sum(item['quantity'] for item in cart.values())
        return JsonResponse({'success': True, 'cart_count': cart_count})
    
    return redirect('view_cart')


@require_POST
def apply_coupon(request):
    form = CouponApplyForm(request.POST)
    if form.is_valid():
        code = form.cleaned_data['code']
        try:
            coupon = Coupon.objects.get(code=code)
            if coupon.is_valid():
                request.session['coupon_code'] = code
                messages.success(request, f'Coupon "{code}" applied successfully!')
            else:
                messages.error(request, 'This coupon is not valid or has expired.')
        except Coupon.DoesNotExist:
            messages.error(request, 'Invalid coupon code.')
    else:
        messages.error(request, 'Please enter a valid coupon code.')
    
    return redirect('view_cart')


@require_POST
def remove_coupon(request):
    request.session.pop('coupon_code', None)
    messages.info(request, 'Coupon removed.')
    return redirect('view_cart')


def checkout(request):
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.warning(request, 'Your cart is empty!')
        return redirect('product_list')
    
    cart_items = []
    total = 0
    
    for product_id, item in cart.items():
        item_total = float(item['price']) * item['quantity']
        cart_items.append({
            'id': product_id,
            'name': item['name'],
            'price': item['price'],
            'quantity': item['quantity'],
            'total': item_total,
        })
        total += item_total
    
    if request.method == 'POST':
        order = Order.objects.create(
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            address=request.POST.get('address'),
            city=request.POST.get('city'),
            postal_code=request.POST.get('postal_code'),
            total_amount=total,
        )
        
        for product_id, item in cart.items():
            product = Product.objects.get(id=product_id)
            OrderItem.objects.create(
                order=order,
                product=product,
                price=item['price'],
                quantity=item['quantity'],
            )
        
        request.session['cart'] = {}
        return redirect('order_confirmation', order_id=order.id)
    
    cart_count = sum(item['quantity'] for item in cart.values())
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_count,
    }
    return render(request, 'shop/checkout.html', context)

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Verify ownership if user is logged in
    if request.user.is_authenticated and order.user != request.user:
        messages.error(request, 'You do not have permission to view this order.')
        return redirect('product_list')
    
    cart_count = 0
    
    context = {
        'order': order,
        'cart_count': cart_count,
    }
    return render(request, 'shop/order_confirmation.html', context)


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    cart_count = sum(item['quantity'] for item in request.session.get('cart', {}).values())
    
    context = {
        'order': order,
        'cart_count': cart_count,
    }
    return render(request, 'shop/order_detail.html', context)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    cart_count = sum(item['quantity'] for item in request.session.get('cart', {}).values())
    
    context = {
        'orders': orders,
        'cart_count': cart_count,
    }
    return render(request, 'shop/order_history.html', context)


# Authentication Views
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('product_list')
    else:
        form = UserCreationForm()
    
    cart_count = sum(item['quantity'] for item in request.session.get('cart', {}).values())
    
    return render(request, 'shop/register.html', {
        'form': form,
        'cart_count': cart_count,
    })


@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user.profile)
    
    cart_count = sum(item['quantity'] for item in request.session.get('cart', {}).values())
    
    context = {
        'form': form,
        'cart_count': cart_count,
    }
    return render(request, 'shop/profile.html', context)


# Review Views
@login_required
@require_POST
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = ReviewForm(request.POST)
    
    if form.is_valid():
        review, created = ProductReview.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={
                'rating': form.cleaned_data['rating'],
                'comment': form.cleaned_data['comment'],
            }
        )
        if created:
            messages.success(request, 'Review added successfully!')
        else:
            messages.success(request, 'Review updated successfully!')
    else:
        messages.error(request, 'Please correct the errors in your review.')
    
    return redirect('product_detail', slug=product.slug)


# Wishlist Views
@login_required
@require_POST
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if not created:
        wishlist_item.delete()
        is_wishlisted = False
        message = 'Removed from wishlist'
    else:
        is_wishlisted = True
        message = 'Added to wishlist'
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_wishlisted': is_wishlisted,
            'message': message
        })
    
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'product_list'))


@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    cart_count = sum(item['quantity'] for item in request.session.get('cart', {}).values())
    
    context = {
        'wishlist_items': wishlist_items,
        'cart_count': cart_count,
    }
    return render(request, 'shop/wishlist.html', context)
