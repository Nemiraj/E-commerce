from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, Order, OrderItem, UserProfile, ProductReview, Wishlist, Coupon, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'get_image_preview', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    
    def get_image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', obj.image.url)
        return "No image"
    get_image_preview.short_description = 'Image'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'available', 'get_avg_rating', 'created_at']
    list_filter = ['available', 'category', 'created_at']
    list_editable = ['price', 'stock', 'available']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'get_avg_rating', 'get_review_count']
   
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock', 'available')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Statistics', {
            'fields': ('get_avg_rating', 'get_review_count', 'created_at', 'updated_at')
        }),
    )
    
    def get_avg_rating(self, obj):
        return obj.get_average_rating()
    get_avg_rating.short_description = 'Avg Rating'
    
    def get_review_count(self, obj):
        return obj.get_review_count()
    get_review_count.short_description = 'Reviews'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'order')
    readonly_fields = ('created_at',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0
    readonly_fields = ['get_cost']
    
    def get_cost(self, obj):
        return f'${obj.get_cost()}'
    get_cost.short_description = 'Cost'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'first_name', 'last_name', 'email', 'city', 'status', 'total_amount', 'discount_amount', 'created_at']
    list_filter = ['status', 'created_at', 'coupon']
    list_editable = ['status']
    search_fields = ['first_name', 'last_name', 'email', 'id']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'get_final_total']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'first_name', 'last_name', 'email')
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'postal_code')
        }),
        ('Order Details', {
            'fields': ('status', 'total_amount', 'discount_amount', 'coupon', 'get_final_total', 'created_at', 'updated_at')
        }),
    )
    
    def get_final_total(self, obj):
        return f'${obj.total_amount - obj.discount_amount}'
    get_final_total.short_description = 'Final Total'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone', 'city']
    list_filter = ['created_at']


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'approved', 'created_at']
    list_filter = ['approved', 'rating', 'created_at']
    list_editable = ['approved']
    search_fields = ['product__name', 'user__username', 'comment']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'product__name']
    date_hierarchy = 'created_at'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'min_purchase', 'active', 'is_valid_display', 'used_count', 'usage_limit', 'valid_from', 'valid_to']
    list_filter = ['active', 'discount_type', 'valid_from', 'valid_to']
    list_editable = ['active']
    search_fields = ['code', 'description']
    readonly_fields = ['used_count', 'is_valid_display']
    
    fieldsets = (
        ('Coupon Information', {
            'fields': ('code', 'description', 'active')
        }),
        ('Discount Details', {
            'fields': ('discount_type', 'discount_value', 'min_purchase', 'max_discount')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'usage_limit', 'used_count', 'is_valid_display')
        }),
    )
    
    def is_valid_display(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Invalid</span>')
    is_valid_display.short_description = 'Status'
