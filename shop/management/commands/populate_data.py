from django.core.management.base import BaseCommand
from shop.models import Category, Product


class Command(BaseCommand):
    help = 'Populate database with sample products'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating categories and products...')
        
        electronics = Category.objects.create(
            name='Electronics',
            description='Electronic devices and gadgets'
        )
        
        clothing = Category.objects.create(
            name='Clothing',
            description='Fashion and apparel'
        )
        
        home = Category.objects.create(
            name='Home & Garden',
            description='Home improvement and garden supplies'
        )
        
        products = [
            {
                'name': 'Wireless Headphones',
                'category': electronics,
                'description': 'Premium wireless headphones with noise cancellation and 30-hour battery life. Perfect for music lovers and commuters.',
                'price': 149.99,
                'stock': 25,
            },
            {
                'name': 'Smartphone',
                'category': electronics,
                'description': 'Latest flagship smartphone with 6.5-inch display, triple camera system, and 5G connectivity.',
                'price': 799.99,
                'stock': 15,
            },
            {
                'name': 'Laptop',
                'category': electronics,
                'description': 'Powerful laptop with Intel i7 processor, 16GB RAM, and 512GB SSD. Ideal for work and gaming.',
                'price': 1299.99,
                'stock': 10,
            },
            {
                'name': 'Smart Watch',
                'category': electronics,
                'description': 'Fitness tracking smartwatch with heart rate monitor, GPS, and water resistance.',
                'price': 299.99,
                'stock': 30,
            },
            {
                'name': 'Cotton T-Shirt',
                'category': clothing,
                'description': 'Comfortable 100% cotton t-shirt available in multiple colors. Classic fit for everyday wear.',
                'price': 24.99,
                'stock': 100,
            },
            {
                'name': 'Denim Jeans',
                'category': clothing,
                'description': 'Premium denim jeans with modern fit and durable construction. Available in various sizes.',
                'price': 59.99,
                'stock': 50,
            },
            {
                'name': 'Winter Jacket',
                'category': clothing,
                'description': 'Warm winter jacket with waterproof exterior and thermal insulation. Perfect for cold weather.',
                'price': 129.99,
                'stock': 20,
            },
            {
                'name': 'Running Shoes',
                'category': clothing,
                'description': 'Lightweight running shoes with cushioned sole and breathable mesh upper.',
                'price': 89.99,
                'stock': 40,
            },
            {
                'name': 'Coffee Maker',
                'category': home,
                'description': 'Programmable coffee maker with 12-cup capacity and auto-brew feature.',
                'price': 79.99,
                'stock': 18,
            },
            {
                'name': 'Garden Tool Set',
                'category': home,
                'description': 'Complete 10-piece garden tool set with ergonomic handles and carrying case.',
                'price': 45.99,
                'stock': 25,
            },
            {
                'name': 'Bed Sheets Set',
                'category': home,
                'description': 'Luxury 4-piece bed sheets set made from premium Egyptian cotton.',
                'price': 69.99,
                'stock': 35,
            },
            {
                'name': 'LED Desk Lamp',
                'category': home,
                'description': 'Adjustable LED desk lamp with USB charging port and touch controls.',
                'price': 34.99,
                'stock': 45,
            },
        ]
        
        for product_data in products:
            Product.objects.create(**product_data)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {len(products)} products in 3 categories'))
