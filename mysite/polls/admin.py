from django.contrib import admin
from .models import TeaShop, Drink, Favorite

# 自訂 TeaShop 的 Admin 管理介面
@admin.register(TeaShop)
class TeaShopAdmin(admin.ModelAdmin):
    # 列表頁顯示的欄位
    list_display = ['id', 'name', 'rating', 'phone', 'address', 'drinks_count', 'created_at']

    # 可以篩選的欄位
    list_filter = ['rating', 'created_at']

    # 可以搜尋的欄位
    search_fields = ['name', 'address', 'phone']

    # 預設排序（評分高的在最上面）
    ordering = ['-rating', 'name']

    # 每頁顯示的項目數
    list_per_page = 20

    # 詳細頁面的欄位分組
    fieldsets = (
        ('基本資料', {
            'fields': ('name', 'rating', 'phone', 'address')
        }),
        ('位置資訊', {
            'fields': ('latitude', 'longitude'),
        }),
        ('營業資訊', {
            'fields': ('opening_hours',),
        }),
        ('系統資訊', {
            'fields': ('place_id', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    # 唯讀欄位
    readonly_fields = ['created_at', 'place_id']

    def drinks_count(self, obj):
        """顯示飲料品項數量"""
        return obj.drinks.count()
    drinks_count.short_description = '飲料品項數'


# 自訂 Drink 的 Admin 管理介面
@admin.register(Drink)
class DrinkAdmin(admin.ModelAdmin):
    # 列表頁顯示的欄位
    list_display = ['id', 'name', 'tea_shop', 'milk_type', 'tea_type', 'topping', 'price_display', 'created_at']

    # 可以篩選的欄位
    list_filter = ['milk_type', 'tea_type', 'topping', 'tea_shop', 'created_at']

    # 可以搜尋的欄位
    search_fields = ['name', 'tea_shop__name', 'description']

    # 預設排序
    ordering = ['tea_shop', 'name']

    # 每頁顯示的項目數
    list_per_page = 20

    # 詳細頁面的欄位分組
    fieldsets = (
        ('基本資料', {
            'fields': ('tea_shop', 'name', 'description', 'milk_type', 'tea_type', 'topping')
        }),
        ('小杯', {
            'fields': ('has_small', 'price_small'),
        }),
        ('中杯', {
            'fields': ('has_medium', 'price_medium'),
        }),
        ('大杯', {
            'fields': ('has_large', 'price_large'),
        }),
    )

    def price_display(self, obj):
        """顯示價格範圍"""
        return obj.get_price_range()
    price_display.short_description = '價格'


# 自訂 Favorite 的 Admin 管理介面
@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    # 列表頁顯示的欄位
    list_display = ['id', 'user', 'favorite_type', 'get_favorite_item', 'created_at']

    # 可以篩選的欄位
    list_filter = ['favorite_type', 'created_at']

    # 可以搜尋的欄位
    search_fields = ['user__username', 'tea_shop__name', 'drink__name']

    # 預設排序
    ordering = ['-created_at']

    # 每頁顯示的項目數
    list_per_page = 20

    def get_favorite_item(self, obj):
        """顯示收藏的項目"""
        if obj.favorite_type == 'shop':
            return obj.tea_shop.name if obj.tea_shop else '-'
        else:
            return obj.drink.name if obj.drink else '-'
    get_favorite_item.short_description = '收藏項目'

